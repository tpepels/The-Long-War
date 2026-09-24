from __future__ import annotations

import json
from dataclasses import asdict

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.integration


def test_random_games_finish() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
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
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
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
