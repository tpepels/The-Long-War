from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.agents.mccfr_agent import MCCFRAgent
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.parallel_mccfr import (
    merge_replica_policies,
    train_parallel_mccfr,
)

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def test_replica_merge_pools_reach_weighted_strategy_sums() -> None:
    base = {
        "schema_version": 1,
        "algorithm": "depth_limited_external_sampling_mccfr",
        "execution_backend": "test",
        "iterations": 2,
        "traversals": 4,
        "max_depth": 2,
        "infosets": {
            "root": {
                "visits": 2,
                "average_visits": 2,
                "regret_sum": {"a": 3.0, "b": -1.0},
                "strategy_sum": {"a": 1.5, "b": 0.5},
                "average_strategy": {"a": 0.75, "b": 0.25},
                "current_strategy": {"a": 1.0, "b": 0.0},
            }
        },
    }
    other = {
        **base,
        "infosets": {
            "root": {
                "visits": 3,
                "average_visits": 3,
                "regret_sum": {"a": -1.0, "b": 5.0},
                "strategy_sum": {"a": 0.5, "b": 2.5},
                "average_strategy": {"a": 1.0 / 6.0, "b": 5.0 / 6.0},
                "current_strategy": {"a": 0.0, "b": 1.0},
            }
        },
    }
    summaries = [
        {
            "iterations": 2,
            "traversals": 4,
            "information_sets": 1,
            "max_depth": 2,
            "mean_sampled_utility_p0": 0.2,
            "mean_sampled_utility_p1": -0.2,
        },
        {
            "iterations": 2,
            "traversals": 4,
            "information_sets": 1,
            "max_depth": 2,
            "mean_sampled_utility_p0": 0.4,
            "mean_sampled_utility_p1": -0.4,
        },
    ]

    merged, summary = merge_replica_policies(
        [base, other],
        summaries,
        seeds=[11, 22],
        iterations_per_worker=2,
    )

    root = merged["infosets"]["root"]
    assert root["visits"] == 5
    assert root["average_visits"] == 5
    assert root["strategy_sum"] == {"a": 2.0, "b": 3.0}
    assert root["average_strategy"] == pytest.approx({"a": 0.4, "b": 0.6})
    assert root["regret_sum"] == {"a": 2.0, "b": 4.0}
    assert root["current_strategy"] == pytest.approx(
        {"a": 1.0 / 3.0, "b": 2.0 / 3.0}
    )
    assert summary["iterations"] == 4
    assert summary["traversals"] == 8


def test_two_worker_training_exports_a_usable_policy() -> None:
    card_data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]

    policy, summary = train_parallel_mccfr(
        card_data,
        deck,
        deck,
        seed=701,
        iterations_per_worker=2,
        workers=2,
        max_depth=1,
        leaf_scale=100.0,
    )

    assert summary["iterations"] == 4
    assert policy["parallel_training"]["workers"] == 2
    assert policy["infosets"]

    engine = GameEngine(card_data)
    state = engine.new_game(deck, deck, seed=19, first_player=0)
    action = MCCFRAgent(seed=9, policy=policy, deterministic=True).choose(
        engine,
        state,
    )
    assert action in engine.legal_actions(state)
