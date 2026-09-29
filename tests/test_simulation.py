from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
import longwar.simulate as simulation_module
from longwar.simulate import SimulationBatchCell, simulate_games, simulate_games_batch

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.integration


def test_random_games_finish() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    report = simulate_games(engine, deck, deck, games=25, seed=99)

    assert sum(report.wins) + report.censored_games == 25
    assert 0 <= report.first_player_wins <= sum(report.wins)
    assert report.max_turns <= 500
    assert [outcome["game"] for outcome in report.game_outcomes] == list(range(25))
    assert [outcome["seed"] for outcome in report.game_outcomes] == list(range(99, 124))
    assert [outcome["first_player"] for outcome in report.game_outcomes] == [index % 2 for index in range(25)]
    assert tuple(sum(outcome["winner"] == player for outcome in report.game_outcomes) for player in range(2)) == report.wins
    assert sum(bool(outcome["censored"]) for outcome in report.game_outcomes) == report.censored_games
    assert sum(
        outcome["winner"] is not None
        and outcome["winner"] == outcome["first_player"]
        for outcome in report.game_outcomes
    ) == report.first_player_wins
    assert json.loads(json.dumps(asdict(report)))["game_outcomes"] == report.game_outcomes


def test_parallel_random_simulation_preserves_seeded_results_and_telemetry() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    serial = simulate_games(
        engine,
        deck,
        deck,
        games=12,
        seed=501,
        jobs=1,
        agent_names=("random", "random"),
    )
    parallel = simulate_games(
        engine,
        deck,
        deck,
        games=12,
        seed=501,
        jobs=8,
        agent_names=("random", "random"),
    )

    assert parallel.game_outcomes == serial.game_outcomes
    assert parallel.wins == serial.wins
    assert parallel.censored_games == serial.censored_games
    assert parallel.first_player_wins == serial.first_player_wins
    assert parallel.mean_turns == pytest.approx(serial.mean_turns)
    assert parallel.max_turns == serial.max_turns
    assert parallel.telemetry["actions"] == serial.telemetry["actions"]
    assert parallel.telemetry["cards"] == serial.telemetry["cards"]
    assert parallel.telemetry["passes"] == serial.telemetry["passes"]
    assert parallel.telemetry["battles"] == serial.telemetry["battles"]
    assert parallel.telemetry["progression"] == serial.telemetry["progression"]
    assert parallel.telemetry["human_flow"] == serial.telemetry["human_flow"]


def test_shared_batch_scheduler_preserves_seeded_cell_results() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    mobility = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    elite = json.loads(
        (ROOT / "decks" / "persistent-elite-heroes.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    expected_mobility = simulate_games(
        engine,
        mobility,
        mobility,
        games=6,
        seed=901,
        jobs=1,
        agent_names=("random", "random"),
    )
    expected_elite = simulate_games(
        engine,
        elite,
        elite,
        games=6,
        seed=907,
        jobs=1,
        agent_names=("random", "random"),
    )

    reports = simulate_games_batch(
        engine,
        [
            SimulationBatchCell(
                key="mobility",
                deck_a=mobility,
                deck_b=mobility,
                games=6,
                seed=901,
            ),
            SimulationBatchCell(
                key="elite",
                deck_a=elite,
                deck_b=elite,
                games=6,
                seed=907,
            ),
        ],
        jobs=8,
        common_options={"agent_names": ("random", "random")},
    )

    assert reports["mobility"].game_outcomes == expected_mobility.game_outcomes
    assert reports["mobility"].telemetry == expected_mobility.telemetry
    assert reports["elite"].game_outcomes == expected_elite.game_outcomes
    assert reports["elite"].telemetry == expected_elite.telemetry


def test_simulation_can_skip_one_failed_game_without_polluting_aggregates(monkeypatch) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    original_make_agent = simulation_module.make_agent
    failing_agent_seeds = {7_010_003, 7_010_004}

    class FailingAgent:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def choose(self, engine, state):
            raise RuntimeError("synthetic game failure")

    def flaky_make_agent(name, engine, agent_seed, **kwargs):
        agent = original_make_agent(name, engine, agent_seed, **kwargs)
        if agent_seed in failing_agent_seeds:
            return FailingAgent(agent)
        return agent

    monkeypatch.setattr(simulation_module, "make_agent", flaky_make_agent)

    report = simulate_games(
        engine,
        deck,
        deck,
        games=3,
        seed=701,
        jobs=1,
        agent_names=("random", "random"),
        skip_failed_games=True,
    )

    assert report.games == 3
    assert report.completed_games == 2
    assert report.failed_games == 1
    assert report.decisive_games + report.censored_games + report.failed_games == 3
    assert [outcome["game"] for outcome in report.game_outcomes] == [0, 2]
    assert len(report.failed_game_outcomes) == 1
    failure = report.failed_game_outcomes[0]
    assert {
        key: failure[key]
        for key in (
            "game",
            "seed",
            "first_player",
            "error_type",
            "error",
            "actions_completed",
        )
    } == {
        "game": 1,
        "seed": 702,
        "first_player": 1,
        "error_type": "RuntimeError",
        "error": "synthetic game failure",
        "actions_completed": 0,
    }
    assert "synthetic game failure" in failure["traceback"]
    assert report.telemetry["progression"]["match_length"]["matches"] == 2


def test_card_conservation_guard_identifies_first_missing_card() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "persistent-elite-heroes.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=1761,
        first_player=0,
        opening_bonus=False,
    )
    expected = (
        simulation_module.Counter(deck),
        simulation_module.Counter(deck),
    )

    simulation_module._assert_card_conservation(state, expected)

    missing = state.players[0].hand.pop()
    with pytest.raises(RuntimeError, match=rf"missing=.*{missing}"):
        simulation_module._assert_card_conservation(
            state,
            expected,
            action=None,
        )


def test_action_horizon_is_recorded_as_censoring() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    report = simulate_games(
        engine,
        deck,
        deck,
        games=1,
        seed=198,
        max_actions=1,
        agent_names=("random", "random"),
    )

    assert report.wins == (0, 0)
    assert report.censored_games == 1
    assert report.decisive_games == 0
    assert report.censor_rate == pytest.approx(1.0)
    outcome = report.game_outcomes[0]
    assert {
        key: outcome[key]
        for key in ("game", "seed", "first_player", "winner", "censored")
    } == {
        "game": 0,
        "seed": 198,
        "first_player": 0,
        "winner": None,
        "censored": True,
    }
    assert outcome["censor_reason"] in {
        "zero-command-action-horizon",
        "pending-effect-action-horizon",
        "active-action-horizon",
    }
    assert outcome["actions_completed"] == 1
    assert outcome["final_battle"] == 1
    assert len(outcome["final_command"]) == 2
    assert outcome["recent_actions"]
    match_length = report.telemetry["progression"]["match_length"]
    assert match_length["matches"] == 1
    assert match_length["censored_matches"] == 1
    assert match_length["final_battle_number"]["median"] == 1
    assert match_length["censored_final_battle_number"]["median"] == 1
    assert match_length["resolved_battles_per_match"]["median"] == 0

    exposed = [
        stats
        for stats in report.telemetry["cards"].values()
        if stats["games_drawn"] > 0
    ]
    assert exposed
    assert all(stats["decisive_games_drawn"] == 0 for stats in exposed)
    assert all(stats["win_rate_when_drawn"] is None for stats in exposed)


def test_simulation_supports_distinct_agent_labels() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    report = simulate_games(
        engine,
        deck,
        deck,
        games=2,
        seed=199,
        agent_names=("heuristic", "heuristic"),
        agent_labels=("candidate-a", "candidate-b"),
        agent_overrides=({}, {}),
        agent_seed_offsets=(11, 22),
    )

    assert report.agents == ("candidate-a", "candidate-b")
    decisions = report.telemetry["decisions"]
    assert "candidate-a" in decisions
    assert "candidate-b" in decisions


@pytest.mark.parametrize("override", [False, True])
def test_simulation_cli_resolves_canonical_defaults_and_explicit_overrides(tmp_path, override):
    from longwar.rules import GameRules

    output = tmp_path / "simulation.json"
    command = [
        sys.executable, str(ROOT / "tools/simulate.py"),
        "--games", "2", "--seed", "401", "--output", str(output),
    ]
    if override:
        command.extend(["--starting-command", "19", "--command-cap", "19"])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    rules = GameRules.standard()
    expected = {
        "starting_command": 19 if override else rules.starting_command,
        "command_cap": 19 if override else rules.command_cap,
    }
    assert {key: report["simulation_variant"][key] for key in expected} == expected
    assert sum(report["wins"]) + report["censored_games"] == 2
    assert report["censor_rate"] == pytest.approx(report["censored_games"] / 2)
    assert report["heuristic_config"]["exploration"] == pytest.approx(0.0)
    assert "Draw" not in report["telemetry"]["actions"]


def test_simulation_reclaims_memory_between_moves_and_games(monkeypatch) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    releases = []

    monkeypatch.setattr(
        simulation_module,
        "_release_process_memory",
        lambda: releases.append(True),
    )

    report = simulate_games(
        engine,
        deck,
        deck,
        games=1,
        seed=299,
        agent_names=("random", "random"),
    )

    assert report.games == 1
    # Once per move, once after the game, and once before returning the report.
    assert len(releases) >= report.max_turns + 2
