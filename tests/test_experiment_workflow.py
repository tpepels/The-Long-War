from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
import threading
import time
from argparse import Namespace
from pathlib import Path

import pytest

from longwar import fingerprint
from longwar.agents.ismcts_agent import DEFAULT_ISMCTS_EXPLORATION, ISMCTSAgent
from longwar.simulate import make_agent, simulate_games
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm
spec = importlib.util.spec_from_file_location("run_experiments", ROOT / "tools" / "run_experiments.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

simulate_spec = importlib.util.spec_from_file_location(
    "simulate_tool",
    ROOT / "tools" / "simulate.py",
)
simulate_tool = importlib.util.module_from_spec(simulate_spec)
simulate_spec.loader.exec_module(simulate_tool)


def test_fingerprint_tracks_native_includes_and_experiment_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(fingerprint, "ROOT", tmp_path)
    paths = ["src/longwar/_ismcts_core.pxi", "cards/cards.json",
             "decks/reference.json", "tools/run_experiments.py"]
    previous = fingerprint.current_game_fingerprint()
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed")
        current = fingerprint.current_game_fingerprint()
        assert current != previous
        previous = current
    product = tmp_path / "src/longwar/build.so"
    product.write_text("host-specific")
    assert fingerprint.current_game_fingerprint() == previous


def test_artifact_identity_keeps_budgets_seeds_and_sources_separate(tmp_path):
    config = {"iterations": 100_000, "seed": 1}
    first = fingerprint.artifact_directory(tmp_path, {"config": config, "game_fingerprint": "a"})
    for change in ({"iterations": 1, "seed": 1}, {"iterations": 100_000, "seed": 2}):
        assert fingerprint.artifact_directory(tmp_path, {"config": change, "game_fingerprint": "a"}) != first
    assert fingerprint.artifact_directory(tmp_path, {"config": config, "game_fingerprint": "b"}) != first
    assert json.loads((first / "config.json").read_text())["config"] == config


def test_game_rules_have_no_named_experiment_profile_api():
    for name in (
        "profile_names",
        "from_profile",
        "force_candidate",
        "force_experiment",
    ):
        assert not hasattr(GameRules, name)


def test_provisional_ismcts_exploration_default_is_shared():
    assert DEFAULT_ISMCTS_EXPLORATION == pytest.approx(0.3)
    assert inspect.signature(ISMCTSAgent).parameters["exploration"].default == DEFAULT_ISMCTS_EXPLORATION
    assert inspect.signature(make_agent).parameters["ismcts_exploration"].default == DEFAULT_ISMCTS_EXPLORATION
    assert inspect.signature(simulate_games).parameters["ismcts_exploration"].default == DEFAULT_ISMCTS_EXPLORATION


def test_ismcts_match_can_compare_rollout_controls():
    source = inspect.getsource(runner.benchmark_ismcts_match)
    assert '"ismcts_rollout_depth": rollout_depth_a' in source
    assert '"ismcts_rollout_depth": rollout_depth_b' in source
    assert '"ismcts_rollout_policy": rollout_policy_a' in source
    assert '"ismcts_rollout_policy": rollout_policy_b' in source
    assert '"--progress-file", str(progress)' in source
    assert "_run_cells_with_live_progress" in source


def test_live_progress_helpers_are_robust(tmp_path):
    progress = tmp_path / "cell.progress"
    assert runner._read_progress_count(progress, 24) == 0

    progress.write_text("7\n", encoding="utf-8")
    assert runner._read_progress_count(progress, 24) == 7

    progress.write_text("999\n", encoding="utf-8")
    assert runner._read_progress_count(progress, 24) == 24

    progress.write_text("not-a-number\n", encoding="utf-8")
    assert runner._read_progress_count(progress, 24) == 0

    progress.write_text(
        json.dumps({"completed": 7, "total": 24, "wins": [4, 3]}) + "\n",
        encoding="utf-8",
    )
    state = runner._read_progress_state(progress, 24)
    assert state == {"completed": 7, "total": 24, "wins": [4, 3]}
    assert runner._read_progress_count(progress, 24) == 7

    assert runner._format_duration(0) == "00:00"
    assert runner._format_duration(65) == "01:05"
    assert runner._format_duration(3661) == "1:01:01"

    source = inspect.getsource(runner._run_cells_with_live_progress)
    assert "\\x1b[2K" in source
    assert "line:<110" not in source
    assert "width = 20" in source
    assert "Press s to skip this experiment" in source
    assert "_run_command_until_stop" in inspect.getsource(runner.benchmark_ismcts_match)


def test_progress_snapshot_contains_partial_wins_and_replaces_atomically(tmp_path):
    progress = tmp_path / "cell.progress"

    simulate_tool._write_progress_snapshot(progress, 3, 24, (2, 1))
    assert json.loads(progress.read_text(encoding="utf-8")) == {
        "completed": 3,
        "total": 24,
        "wins": [2, 1],
    }
    assert not progress.with_suffix(progress.suffix + ".tmp").exists()

    simulate_tool._write_progress_snapshot(progress, 4, 24, (2, 2))
    assert json.loads(progress.read_text(encoding="utf-8")) == {
        "completed": 4,
        "total": 24,
        "wins": [2, 2],
    }


def test_live_progress_aggregates_partial_cell_scores_without_tty(tmp_path, capsys):
    cells = []
    snapshots = [
        ("reference", "a-first", [2, 0]),
        ("avaros", "b-first", [1, 1]),
    ]
    for deck, orientation, wins in snapshots:
        output = tmp_path / f"{deck}-{orientation}.json"
        progress = output.with_suffix(".progress")
        cells.append((deck, orientation, output, progress, ["unused"]))

    def run_cell(cell, _stop_event):
        deck, orientation, _output, progress, _command = cell
        wins = next(
            wins
            for expected_deck, expected_orientation, wins in snapshots
            if expected_deck == deck and expected_orientation == orientation
        )
        progress.write_text(
            json.dumps({"completed": 2, "total": 2, "wins": wins}) + "\n",
            encoding="utf-8",
        )
        return deck

    def format_progress(cell, state):
        deck, orientation, *_rest = cell
        a_wins, b_wins = state["wins"]
        return (
            f"{deck} {orientation} {state['completed']}/2 {a_wins}-{b_wins}",
            a_wins,
            b_wins,
        )

    results = runner._run_cells_with_live_progress(
        cells,
        jobs=2,
        games_per_cell=2,
        run_cell=run_cell,
        format_result=str,
        table_header="deck orientation games A-B",
        score_labels=("A", "B"),
        format_progress=format_progress,
    )

    assert sorted(results) == ["avaros", "reference"]
    output = capsys.readouterr().out
    assert "TOTAL A 3 - B 1" in output
    assert "4/4" in output
    assert "\x1b[" not in output


def test_cancelled_simulation_process_is_terminated(tmp_path):
    stop_event = threading.Event()
    pid_path = tmp_path / "child.pid"

    def request_stop():
        deadline = time.monotonic() + 5.0
        while not pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        stop_event.set()

    stopper = threading.Thread(target=request_stop)
    stopper.start()
    started = time.monotonic()
    completed = runner._run_command_until_stop(
        [
            sys.executable,
            "-c",
            (
                "import os, time; from pathlib import Path; "
                f"Path({str(pid_path)!r}).write_text(str(os.getpid())); "
                "time.sleep(30)"
            ),
        ],
        stop_event,
    )
    stopper.join(timeout=5.0)

    assert completed is False
    assert pid_path.is_file()
    assert time.monotonic() - started < 5.0
    pid = int(pid_path.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_skip_key_reader_restores_terminal_state_on_exception(monkeypatch):
    if runner.termios is None or runner.tty is None:
        pytest.skip("POSIX terminal controls unavailable")

    class FakeTTY:
        def isatty(self):
            return True

        def fileno(self):
            return 17

        def write(self, _text):
            return 0

        def flush(self):
            return None

    saved = ["saved-terminal-state"]
    restored = []
    monkeypatch.setattr(runner.sys, "stdin", FakeTTY())
    monkeypatch.setattr(runner.sys, "stdout", FakeTTY())
    monkeypatch.setattr(runner.termios, "tcgetattr", lambda fd: saved)
    monkeypatch.setattr(runner.tty, "setcbreak", lambda fd: None)
    monkeypatch.setattr(
        runner.termios,
        "tcsetattr",
        lambda fd, when, state: restored.append((fd, when, state)),
    )

    with pytest.raises(RuntimeError, match="boom"):
        with runner._skip_key_reader():
            raise RuntimeError("boom")

    assert restored == [(17, runner.termios.TCSADRAIN, saved)]


def test_optimization_schedule_is_seeded_randomized_and_excludes_strength_check():
    comparisons = [
        ("tree-cold", {"reuse_tree": False}),
        ("pw-0p5", {"progressive_widening": 0.5}),
        ("rollout-greedy", {"rollout_policy": "greedy"}),
        ("rollout-depth-8", {"rollout_depth": 8}),
        ("rollout-epsilon-0", {"rollout_epsilon": 0.0}),
    ]
    expected = {
        "tree-cold",
        "pw-0p5",
        "rollout-greedy",
        "rollout-depth-8",
        "rollout-epsilon-0",
    }

    first = runner._optimization_schedule(comparisons, 26092400)
    second = runner._optimization_schedule(comparisons, 26092400)

    assert first == second
    assert {item["name"] for item in first} == expected
    assert "optimized-vs-alpha-beta" not in {
        item["name"] for item in first
    }
    assert [item["name"] for item in first] != [
        name for name, _overrides in comparisons
    ]
    assert comparisons[0] == ("tree-cold", {"reuse_tree": False})


def test_strength_benchmark_reports_live_progress():
    source = inspect.getsource(runner.benchmark_strength)
    assert '"--progress-file", str(progress)' in source
    assert "_run_cells_with_live_progress" in source


def test_decision_grade_search_match_defaults(monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_experiments.py", "ismcts-match"],
    )
    match = runner.parse_args()
    assert match.games == 24
    assert match.jobs == 8
    assert match.time_budget_seconds == pytest.approx(2.0)
    assert match.a_belief_samples == 12
    assert match.b_belief_samples == 12
    assert match.a_rollout_epsilon == pytest.approx(0.12)
    assert match.b_rollout_epsilon == pytest.approx(0.12)

    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_experiments.py", "strength-bench"],
    )
    strength = runner.parse_args()
    assert strength.games == 24
    assert strength.jobs == 8
    assert strength.belief_samples == 12
    assert strength.rollout_epsilon == pytest.approx(0.12)


def test_makefile_has_one_configurable_experiment_entrypoint():
    source = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "experiments:" in source
    assert "EXPERIMENT ?= suite" in source
    assert "EXPERIMENT_ARGS ?=" in source
    assert "systemd-inhibit" in source

    for obsolete_target in (
        "ismcts-match:",
        "strength-bench:",
        "experiment-suite:",
        "mcts-bench:",
        "search-bench:",
        "cardflow-quick:",
        "cardflow-run:",
        "cardflow-max:",
        "overnight-search:",
    ):
        assert obsolete_target not in source


def test_experiment_suite_defaults_and_minimum(monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_experiments.py", "suite"],
    )
    args = runner.parse_args()
    assert args.games == 24
    assert args.jobs == 8
    assert args.time_budget_seconds == pytest.approx(2.0)
    assert args.iterations == 100_000
    assert args.alpha_nodes == 20_000
    assert args.stop_on_error is False

    args.games = 23
    with pytest.raises(SystemExit, match="at least 24"):
        runner.run_suite(args)


def test_experiment_suite_optimizes_before_strength_check(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(base, identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    match_calls = []
    strength_calls = []
    events = []

    def fake_match(**kwargs):
        match_calls.append(kwargs)
        events.append("match")
        path = tmp_path / f"match-{len(match_calls)}.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "candidate_a_win_rate": 0.5,
                    "paired_uncertainty": {"ci95": [0.45, 0.55]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    def fake_strength(**kwargs):
        strength_calls.append(kwargs)
        events.append("strength")
        path = tmp_path / "strength.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "mcts_win_rate": 0.5,
                    "paired_uncertainty": {"ci95": [0.45, 0.55]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BENCH_ROOT", tmp_path / "bench")
    monkeypatch.setattr(runner, "artifact_directory", fake_artifact_directory)
    monkeypatch.setattr(runner, "benchmark_ismcts_match", fake_match)
    monkeypatch.setattr(runner, "benchmark_strength", fake_strength)

    args = Namespace(
        games=24,
        jobs=8,
        iterations=100_000,
        alpha_nodes=20_000,
        time_budget_seconds=2.0,
        seed=26092400,
        stop_on_error=False,
    )
    manifest_path = runner.run_suite(args)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert len(match_calls) == 5
    assert len(strength_calls) == 1
    assert events == ["match"] * 5 + ["strength"]
    assert len(manifest["experiments"]) == 6
    assert all(row["status"] == "passed" for row in manifest["experiments"])
    assert manifest["schedule"][-1] == "optimized-vs-alpha-beta"
    assert set(manifest["optimization_schedule"]) == {
        "tree-cold",
        "pw-0p5",
        "rollout-greedy",
        "rollout-depth-8",
        "rollout-epsilon-0",
    }
    assert manifest["schedule"] == [
        *manifest["optimization_schedule"],
        "optimized-vs-alpha-beta",
    ]

    assert all(call["belief_samples_a"] == 12 for call in match_calls)
    assert all(call["belief_samples_b"] == 12 for call in match_calls)
    assert all(call["max_tree_nodes_a"] == 400_000 for call in match_calls)
    assert all(call["max_tree_nodes_b"] == 400_000 for call in match_calls)
    assert sum(call["reuse_tree_b"] is False for call in match_calls) == 1
    assert sum(
        call["progressive_widening_b"] == pytest.approx(0.5)
        for call in match_calls
    ) == 1
    assert sum(call["rollout_policy_b"] == "greedy" for call in match_calls) == 1
    assert sum(call["rollout_depth_b"] == 8 for call in match_calls) == 1
    assert sum(call["rollout_epsilon_b"] == pytest.approx(0.0) for call in match_calls) == 1

    assert strength_calls[0]["time_budget_seconds"] == pytest.approx(2.0)
    assert strength_calls[0]["belief_samples"] == 12
    assert strength_calls[0]["reuse_tree"] is True
    assert strength_calls[0]["rollout_policy"] == "cheap"
    assert strength_calls[0]["rollout_depth"] == 5
    assert strength_calls[0]["rollout_epsilon"] == pytest.approx(0.12)
    assert strength_calls[0]["max_tree_nodes"] == 400_000

    assert manifest["optimized_config"] == manifest["starting_config"]
    assert manifest["accepted_optimizations"] == []
    assert manifest["decision_readiness"]["ready"] is True
    assert manifest["decision_readiness"]["blockers"] == []


def test_suite_rolls_confident_improvements_into_later_tests_and_strength(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(_base, _identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    match_calls = []
    strength_calls = []

    def fake_match(**kwargs):
        match_calls.append(dict(kwargs))
        path = tmp_path / f"match-{len(match_calls)}.json"
        tree_challenger = (
            kwargs["reuse_tree_a"] is True
            and kwargs["reuse_tree_b"] is False
        )
        path.write_text(
            json.dumps({
                "overall": {
                    "candidate_a_win_rate": 0.40 if tree_challenger else 0.50,
                    "paired_uncertainty": {
                        "ci95": [0.32, 0.48]
                        if tree_challenger
                        else [0.44, 0.56],
                    },
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    def fake_strength(**kwargs):
        strength_calls.append(dict(kwargs))
        path = tmp_path / "strength.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "mcts_win_rate": 0.50,
                    "paired_uncertainty": {"ci95": [0.44, 0.56]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BENCH_ROOT", tmp_path / "bench")
    monkeypatch.setattr(runner, "artifact_directory", fake_artifact_directory)
    monkeypatch.setattr(runner, "benchmark_ismcts_match", fake_match)
    monkeypatch.setattr(runner, "benchmark_strength", fake_strength)

    manifest_path = runner.run_suite(Namespace(
        games=24,
        jobs=8,
        iterations=100_000,
        alpha_nodes=20_000,
        time_budget_seconds=2.0,
        seed=26092400,
        stop_on_error=False,
    ))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    tree_call_index = next(
        index
        for index, call in enumerate(match_calls)
        if call["reuse_tree_a"] is True and call["reuse_tree_b"] is False
    )
    for call in match_calls[tree_call_index + 1:]:
        assert call["reuse_tree_a"] is False
        assert call["reuse_tree_b"] is False

    assert manifest["accepted_optimizations"] == ["tree-cold"]
    assert manifest["optimized_config"]["reuse_tree"] is False
    assert strength_calls[0]["reuse_tree"] is False
    tree_entry = next(
        row for row in manifest["experiments"] if row["name"] == "tree-cold"
    )
    assert tree_entry["accepted"] is True
    assert tree_entry["incumbent_after"]["reuse_tree"] is False


def test_suite_manual_skip_continues_to_following_experiments(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(_base, _identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    calls = 0

    def fake_match(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise runner.ExperimentSkipped("test skip")
        path = tmp_path / f"match-{calls}.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "candidate_a_win_rate": 0.5,
                    "paired_uncertainty": {"ci95": [0.44, 0.56]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    def fake_strength(**_kwargs):
        path = tmp_path / "strength.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "mcts_win_rate": 0.5,
                    "paired_uncertainty": {"ci95": [0.44, 0.56]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BENCH_ROOT", tmp_path / "bench")
    monkeypatch.setattr(runner, "artifact_directory", fake_artifact_directory)
    monkeypatch.setattr(runner, "benchmark_ismcts_match", fake_match)
    monkeypatch.setattr(runner, "benchmark_strength", fake_strength)

    manifest_path = runner.run_suite(Namespace(
        games=24,
        jobs=8,
        iterations=100_000,
        alpha_nodes=20_000,
        time_budget_seconds=2.0,
        seed=26092400,
        stop_on_error=False,
    ))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert calls == 5
    skipped_rows = [
        row for row in manifest["experiments"] if row["status"] == "skipped"
    ]
    assert len(skipped_rows) == 1
    assert skipped_rows[0]["kind"] == "ismcts-match"
    assert manifest["skipped"] == [skipped_rows[0]["name"]]
    assert manifest["failures"] == []
    strength = next(
        row
        for row in manifest["experiments"]
        if row["name"] == "optimized-vs-alpha-beta"
    )
    assert strength["status"] == "passed"
    assert manifest["decision_readiness"]["ready"] is False
    assert "optimization phase incomplete" in (
        manifest["decision_readiness"]["blockers"]
    )


def test_confident_challenger_is_an_accepted_optimization_not_a_blocker(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(_base, _identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    def fake_match(**kwargs):
        path = tmp_path / (
            "tree.json"
            if kwargs["reuse_tree_b"] is False
            else f"match-{len(list(tmp_path.glob('match-*.json')))}.json"
        )
        better = kwargs["reuse_tree_a"] is True and kwargs["reuse_tree_b"] is False
        path.write_text(
            json.dumps({
                "overall": {
                    "candidate_a_win_rate": 0.40 if better else 0.50,
                    "paired_uncertainty": {
                        "ci95": [0.32, 0.48] if better else [0.44, 0.56],
                    },
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    def fake_strength(**_kwargs):
        path = tmp_path / "strength.json"
        path.write_text(
            json.dumps({
                "overall": {
                    "mcts_win_rate": 0.50,
                    "paired_uncertainty": {"ci95": [0.44, 0.56]},
                },
                "resources": {},
            }),
            encoding="utf-8",
        )
        return path

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BENCH_ROOT", tmp_path / "bench")
    monkeypatch.setattr(runner, "artifact_directory", fake_artifact_directory)
    monkeypatch.setattr(runner, "benchmark_ismcts_match", fake_match)
    monkeypatch.setattr(runner, "benchmark_strength", fake_strength)

    manifest_path = runner.run_suite(Namespace(
        games=24,
        jobs=8,
        iterations=100_000,
        alpha_nodes=20_000,
        time_budget_seconds=2.0,
        seed=26092400,
        stop_on_error=False,
    ))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["accepted_optimizations"] == ["tree-cold"]
    assert manifest["optimized_config"]["reuse_tree"] is False
    assert manifest["decision_readiness"]["ready"] is True
    assert manifest["decision_readiness"]["blockers"] == []


def test_no_dedicated_rule_experiment_runner() -> None:
    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    assert "longwar.cardflow" not in source
    assert 'sub.add_parser("run"' not in source


def test_no_duplicate_batch_search_entry_point():
    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    assert "overnight-search" not in source
    assert "run_overnight_search" not in source
    assert 'BENCH_ROOT / "overnight"' not in source


def test_experiment_runner_has_only_decision_grade_search_commands(monkeypatch):
    for command in ("ismcts-match", "strength-bench", "suite"):
        monkeypatch.setattr(
            runner.sys,
            "argv",
            ["run_experiments.py", command],
        )
        assert runner.parse_args().command == command

    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    for obsolete in (
        '"bench"',
        '"search-bench"',
        '"mcts-bench"',
        '"exploration-sweep"',
    ):
        assert obsolete not in source


def test_backend_parity_ignores_runtime_but_keeps_search_depth_and_outcomes(tmp_path):
    path = tmp_path / "match.json"
    payload = {
        "wins": [1, 1],
        "telemetry": {"decisions": {"strategic_heuristic": {
            "mean_completed_depth": 3,
            "mean_decision_seconds": 0.2,
            "max_decision_seconds": 0.3,
            "mean_searched_decision_seconds": 0.25,
        }}},
    }
    path.write_text(json.dumps(payload))
    expected = runner.normalized_payload(path)
    decision = payload["telemetry"]["decisions"]["strategic_heuristic"]
    for field in ("mean_decision_seconds", "max_decision_seconds",
                  "mean_searched_decision_seconds"):
        decision[field] *= 10
    path.write_text(json.dumps(payload))
    assert runner.normalized_payload(path) == expected

    decision["mean_completed_depth"] = 2
    path.write_text(json.dumps(payload))
    assert runner.normalized_payload(path) != expected

    decision["mean_completed_depth"] = 3
    payload["wins"] = [2, 0]
    path.write_text(json.dumps(payload))
    assert runner.normalized_payload(path) != expected


def test_canonical_validation_uses_only_current_standard_rules():
    data_source = inspect.getsource(runner.validate_data)
    validate_source = inspect.getsource(runner.validate)

    assert "GameRules.standard()" in data_source
    assert "profile_names()" not in data_source
    assert "from_profile(" not in data_source

    assert "standard_backend_parity" in validate_source
    assert "test_rule_variants.py" not in validate_source
    assert "not legacy_rule_experiment" in validate_source
    assert "parity_case" not in validate_source


@pytest.mark.parametrize("change", ["seed", "source"])
def test_validation_can_repeat_after_inputs_change(tmp_path, monkeypatch, change):
    monkeypatch.setattr(runner, "VALIDATION_ROOT", tmp_path)
    monkeypatch.setattr(fingerprint, "current_game_fingerprint", lambda: "before")
    outputs = []

    def fake_run(command, **_kwargs):
        outputs.append(Path(command[command.index("--output") + 1]))

    monkeypatch.setattr(runner, "run_command", fake_run)
    monkeypatch.setattr(runner, "normalized_payload", lambda path: {})
    runner.standard_backend_parity(seed=17)
    if change == "source":
        monkeypatch.setattr(fingerprint, "current_game_fingerprint", lambda: "after")
    runner.standard_backend_parity(seed=18 if change == "seed" else 17)
    assert outputs[0].parent == outputs[1].parent
    assert outputs[2].parent == outputs[3].parent
    assert outputs[0].parent != outputs[2].parent
    assert (outputs[0].parent / "config.json").is_file()
    assert (outputs[2].parent / "config.json").is_file()


def test_ismcts_uncertainty_pairs_orientations_by_seed():
    outcomes = {"reference": {
        "a-first": [{"seed": 1, "winner": 0}, {"seed": 2, "winner": 1}],
        "b-first": [{"seed": 2, "winner": 0}, {"seed": 1, "winner": 1}],
    }}
    result = runner.paired_ismcts_interval(outcomes)
    assert result["independent_deals"] == 2
    assert result["a_win_rate"] == 0.5
    assert result["ci95"][0] < 0.5 < result["ci95"][1]
    outcomes["reference"]["b-first"][0]["seed"] = 3
    with pytest.raises(ValueError, match="identical deal seeds"):
        runner.paired_ismcts_interval(outcomes)


def test_strength_uncertainty_pairs_orientations_by_seed():
    outcomes = {"reference": {
        "mcts-first": [{"seed": 1, "winner": 0}, {"seed": 2, "winner": 1}],
        "alpha-first": [{"seed": 2, "winner": 0}, {"seed": 1, "winner": 1}],
    }}
    result = runner.paired_strength_interval(outcomes)
    assert result["independent_deals"] == 2
    assert result["win_rate"] == 0.5
    assert result["ci95"][0] < 0.5 < result["ci95"][1]
    outcomes["reference"]["alpha-first"][0]["seed"] = 3
    with pytest.raises(ValueError, match="identical deal seeds"):
        runner.paired_strength_interval(outcomes)


@pytest.mark.integration
def test_quick_balance_pipeline_keeps_replay_metadata(tmp_path, monkeypatch):
    # Exercise real engine/simulation/report composition with one game per deck.
    from longwar.fingerprint import artifact_directory
    monkeypatch.setattr(runner, "artifact_directory", lambda base, identity: artifact_directory(tmp_path, identity))
    output = runner.balance_run(Namespace(preset="quick", games=1, seed=71, contexts=1, games_per_context=1))
    summary = json.loads((output / "summary.json").read_text())
    assert summary["simulation_games"] == 4
    assert summary["config"]["seed"] == 71
    match = json.loads((output / "reference--reference.json").read_text())
    assert len(match["deck_a"]) == 34
    assert "deck_size" not in match["rules"]
    assert match["game_fingerprint"] == summary["game_fingerprint"]
    assert (output / "playability.json").is_file()

