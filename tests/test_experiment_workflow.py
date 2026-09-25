from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
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


def test_canonical_ismcts_rollout_policy_default_is_greedy():
    assert inspect.signature(ISMCTSAgent).parameters["rollout_policy"].default == "greedy"
    assert inspect.signature(make_agent).parameters["ismcts_rollout_policy"].default == "greedy"
    assert inspect.signature(simulate_games).parameters["ismcts_rollout_policy"].default == "greedy"


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


def test_live_skip_raises_partial_score_from_progress(
    tmp_path,
    monkeypatch,
    capsys,
):
    progress = tmp_path / "cell.progress"
    progress.write_text(
        json.dumps({
            "completed": 7,
            "total": 24,
            "wins": [6, 1],
        }),
        encoding="utf-8",
    )
    cell = ("reference", "a-first", tmp_path / "out.json", progress, [])

    @contextmanager
    def fake_skip_reader():
        yield lambda: True

    monkeypatch.setattr(runner, "_skip_key_reader", fake_skip_reader)

    def run_cell(_cell, stop_event):
        while not stop_event.is_set():
            time.sleep(0.001)
        return None

    def format_progress(_cell, state):
        return "row", int(state["wins"][0]), int(state["wins"][1])

    with pytest.raises(runner.ExperimentSkipped) as skipped:
        runner._run_cells_with_live_progress(
            [cell],
            jobs=1,
            games_per_cell=24,
            run_cell=run_cell,
            format_result=lambda _result: "",
            table_header="table",
            score_labels=("A", "B"),
            format_progress=format_progress,
        )

    assert skipped.value.partial["score_a"] == 6
    assert skipped.value.partial["score_b"] == 1
    assert skipped.value.partial["completed"] == 7
    assert skipped.value.partial["total"] == 24


def test_strength_benchmark_reports_live_progress():
    source = inspect.getsource(runner.benchmark_strength)
    assert '"--progress-file", str(progress)' in source
    assert "_run_cells_with_live_progress" in source


def test_strength_sanity_check_defaults(monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_experiments.py", "strength-bench"],
    )
    args = runner.parse_args()
    assert args.games == 24
    assert args.jobs == 8
    assert args.iterations == 100_000
    assert args.alpha_nodes == 20_000
    assert args.time_budget_seconds == pytest.approx(5.0)


def test_makefile_has_one_configurable_experiment_entrypoint():
    source = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "experiments:" in source
    assert "EXPERIMENT ?= strength-bench" in source
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


def test_no_dedicated_rule_experiment_runner() -> None:
    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    assert "longwar.cardflow" not in source
    assert 'sub.add_parser("run"' not in source


def test_no_duplicate_batch_search_entry_point():
    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    assert "overnight-search" not in source
    assert "run_overnight_search" not in source
    assert 'BENCH_ROOT / "overnight"' not in source


def test_experiment_runner_exposes_only_alpha_beta_sanity_check(monkeypatch):
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["run_experiments.py", "strength-bench"],
    )
    assert runner.parse_args().command == "strength-bench"

    source = (ROOT / "tools" / "run_experiments.py").read_text(encoding="utf-8")
    for obsolete in (
        '"ismcts-match"',
        '"suite"',
        '"overnight-search"',
        '"search-bench"',
        '"mcts-bench"',
        '"exploration-sweep"',
        "run_suite",
        "benchmark_ismcts_match",
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

