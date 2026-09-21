from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    return GameEngine(data), deck


def test_telemetry_contains_card_pass_battle_and_combo_metrics() -> None:
    engine, deck = setup()
    report = simulate_games(
        engine,
        deck,
        deck,
        games=20,
        seed=123,
        agent_names=("heuristic", "heuristic"),
    )

    telemetry = report.telemetry
    assert telemetry["battles"]["count"] >= 40
    assert telemetry["passes"]["events"] >= 40
    assert telemetry["cards"]
    assert "heuristic" in telemetry["decisions"]

    fifty = telemetry["cards"]["the-fifty-men"]
    assert fifty["draws"] > 0
    assert 0 <= fifty["play_rate_per_draw"] <= 1
    assert 0 <= fifty["unplayable_turn_rate"] <= 1

    assert telemetry["legend_combinations"]


def test_heuristic_beats_random_in_small_fixed_benchmark() -> None:
    engine, deck = setup()
    report = simulate_games(
        engine,
        deck,
        deck,
        games=80,
        seed=404,
        agent_names=("heuristic", "random"),
    )
    assert report.wins[0] > report.wins[1]
