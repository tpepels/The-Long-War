from __future__ import annotations

import importlib.util
import inspect
import json
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


def test_experiment_suite_runs_structural_battery_and_checkpoints(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(base, identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    match_calls = []
    strength_calls = []

    def fake_match(**kwargs):
        match_calls.append(kwargs)
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

    assert len(match_calls) == 6
    assert len(strength_calls) == 1
    assert len(manifest["experiments"]) == 7
    assert all(row["status"] == "passed" for row in manifest["experiments"])
    assert [row["name"] for row in manifest["experiments"]] == [
        "baseline-control",
        "tree-cold",
        "pw-0p5",
        "rollout-greedy",
        "rollout-depth-8",
        "rollout-epsilon-0",
        "baseline-vs-alpha-beta",
    ]
    assert match_calls[0]["belief_samples_b"] == 12
    assert match_calls[0]["max_tree_nodes_b"] == 400_000
    assert match_calls[1]["reuse_tree_b"] is False
    assert match_calls[2]["progressive_widening_b"] == pytest.approx(0.5)
    assert match_calls[3]["rollout_policy_b"] == "greedy"
    assert match_calls[4]["rollout_depth_b"] == 8
    assert match_calls[5]["rollout_epsilon_b"] == pytest.approx(0.0)
    assert strength_calls[0]["time_budget_seconds"] == pytest.approx(2.0)
    assert strength_calls[0]["belief_samples"] == 12
    assert strength_calls[0]["max_tree_nodes"] == 400_000
    assert manifest["decision_readiness"]["ready"] is True
    assert manifest["decision_readiness"]["blockers"] == []


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

    assert calls == 6
    assert manifest["experiments"][1]["name"] == "tree-cold"
    assert manifest["experiments"][1]["status"] == "skipped"
    assert manifest["skipped"] == ["tree-cold"]
    assert manifest["failures"] == []
    assert manifest["experiments"][-1]["name"] == "baseline-vs-alpha-beta"
    assert manifest["experiments"][-1]["status"] == "passed"
    assert "manually skipped comparisons: tree-cold" in (
        manifest["decision_readiness"]["warnings"]
    )


def test_suite_readiness_blocks_a_confidently_better_challenger(
    tmp_path,
    monkeypatch,
):
    suite_dir = tmp_path / "suite"

    def fake_artifact_directory(_base, _identity):
        suite_dir.mkdir(parents=True, exist_ok=True)
        return suite_dir

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "BENCH_ROOT", tmp_path / "bench")
    monkeypatch.setattr(
        runner,
        "artifact_directory",
        fake_artifact_directory,
    )

    calls = 0

    def fake_match(**_kwargs):
        nonlocal calls
        calls += 1
        suite_dir.mkdir(parents=True, exist_ok=True)
        path = tmp_path / f"match-{calls}.json"
        better = calls == 2
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
    readiness = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )["decision_readiness"]

    assert readiness["ready"] is False
    assert readiness["challengers_beating_baseline"] == [
        "tree-cold"
    ]
    assert readiness["blockers"] == [
        "predeclared challenger beats the baseline: tree-cold"
    ]


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

