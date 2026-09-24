from __future__ import annotations

import json

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games
from longwar.telemetry import Telemetry

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.integration


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
    assert fifty["plays_per_draw"] >= 0
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

def test_telemetry_aggregates_ismcts_rollout_cutoffs() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=505, first_player=0)
    telemetry = Telemetry()
    telemetry.start_game(state)
    action = engine.legal_actions(state)[0]

    telemetry.before_action(
        engine,
        state,
        state.active_player,
        action,
        {
            "agent": "ismcts",
            "candidate_count": 4,
            "search_nodes": 20,
            "completed_depth": 3,
            "ismcts_rollouts_stopped_terminal": 7,
            "ismcts_rollouts_stopped_battle_boundary": 11,
            "ismcts_rollouts_stopped_depth": 2,
            "ismcts_rollout_actions": 53,
        },
    )

    cutoffs = telemetry.summary()["decisions"]["ismcts"][
        "ismcts_rollout_cutoffs"
    ]
    assert cutoffs["iterations"] == 20
    assert cutoffs["terminal"] == 7
    assert cutoffs["battle_boundary"] == 11
    assert cutoffs["depth"] == 2
    assert cutoffs["terminal_rate"] == pytest.approx(7 / 20)
    assert cutoffs["battle_boundary_rate"] == pytest.approx(11 / 20)
    assert cutoffs["depth_rate"] == pytest.approx(2 / 20)
    assert cutoffs["rollout_actions"] == 53
    assert cutoffs["mean_rollout_actions_per_iteration"] == pytest.approx(
        53 / 20
    )

