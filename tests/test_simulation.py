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
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.integration


def test_random_games_finish() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    report = simulate_games(engine, deck, deck, games=25, seed=99)

    assert sum(report.wins) == 25
    assert 0 <= report.first_player_wins <= 25
    assert report.max_turns < 500
    assert [outcome["seed"] for outcome in report.game_outcomes] == list(range(99, 124))
    assert [outcome["first_player"] for outcome in report.game_outcomes] == [index % 2 for index in range(25)]
    assert tuple(sum(outcome["winner"] == player for outcome in report.game_outcomes) for player in range(2)) == report.wins
    assert sum(outcome["winner"] == outcome["first_player"] for outcome in report.game_outcomes) == report.first_player_wins
    assert json.loads(json.dumps(asdict(report)))["game_outcomes"] == report.game_outcomes


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
    assert sum(report["wins"]) == 2
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
