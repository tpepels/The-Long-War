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
            "decision_seconds": 1.25,
            "search_timed_out": True,
            "ismcts_iterations": 20,
            "ismcts_rollouts_stopped_terminal": 7,
            "ismcts_rollouts_stopped_battle_boundary": 11,
            "ismcts_rollouts_stopped_depth": 2,
            "ismcts_rollout_actions": 53,
            "ismcts_root_reused": True,
            "ismcts_tree_nodes_before": 120,
            "ismcts_tree_nodes_added": 17,
            "ismcts_root_prior_visits": 9,
            "ismcts_tree_nodes_discarded": 70,
            "ismcts_tree_capacity_cutoffs": 4,
            "ismcts_tree_reset_reason": "context_changed",
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

    reuse = telemetry.summary()["decisions"]["ismcts"]["ismcts_tree_reuse"]
    assert reuse["searched_decisions"] == 1
    assert reuse["root_reused_decisions"] == 1
    assert reuse["root_reuse_rate"] == pytest.approx(1.0)
    assert reuse["tree_nodes_before_total"] == 120
    assert reuse["tree_nodes_added_total"] == 17
    assert reuse["root_prior_visits_total"] == 9
    assert reuse["tree_nodes_discarded_total"] == 70
    assert reuse["tree_capacity_cutoffs"] == 4
    assert reuse["tree_resets"] == {"context_changed": 1}
    assert reuse["mean_tree_nodes_before"] == pytest.approx(120.0)
    assert reuse["mean_tree_nodes_added"] == pytest.approx(17.0)
    assert reuse["mean_root_prior_visits"] == pytest.approx(9.0)

    decisions = telemetry.summary()["decisions"]["ismcts"]
    assert decisions["mean_decision_seconds"] == pytest.approx(1.25)
    assert decisions["max_decision_seconds"] == pytest.approx(1.25)
    assert decisions["timed_out_decisions"] == 1
    assert decisions["timeout_rate"] == pytest.approx(1.0)
