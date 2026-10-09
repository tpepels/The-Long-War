"""Search boundary integration against the untrimmed current 131-card catalogue.

This intentionally tests runtime plumbing, not a claim that every printed
card effect or the whole paper rulebook is fully implemented in this branch.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game.engine import GameEngine
from longwar.native_search import strategic_backend, ismcts_backend, mccfr_backend

pytestmark = pytest.mark.algorithm
ROOT = Path(__file__).resolve().parents[1]


def test_integrated_search_handles_all_131_card_identities():
    card_data = load_card_file(ROOT / "cards" / "cards.json")
    assert len(card_data["cards"]) == 131
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text()
    )["cards"]
    engine = GameEngine(card_data)
    state = engine.new_game(
        deck, deck, seed=20261009, first_player=0, opening_bonus=False
    )
    fast_type, eval_type, budget_type, _limit, table_type, search = strategic_backend()
    fast = fast_type(engine)
    packed = fast.from_game_state(state)
    evaluator = eval_type(fast, sampled_opponent_resources=False)
    legal = fast.legal_actions(packed)
    assert legal

    result = search(
        fast, state, 0, 0, -math.inf, math.inf,
        budget_type(500), 4, evaluator, table_type(128),
    )
    assert math.isfinite(result)

    # Exercise the upper end of the card-identity range, which previously
    # overflowed signed int8_t slots and prevented construction at 131.
    expanded = state.clone()
    expanded.players[0].hand.append(card_data["cards"][-1]["id"])
    expanded_packed = fast.from_game_state(expanded)
    assert fast.information_key(expanded_packed, 0) != fast.information_key(
        packed, 0
    )
    assert fast.legal_actions(expanded_packed)

    _engine_type, _tree_type, _eval_type, mcts = ismcts_backend()
    mcts_result = mcts(
        fast, evaluator, [packed], 0,
        iterations=64, rollout_depth=2, post_battle_rollout_depth=0,
        tree_depth_limit=6, rollout_policy=2, seed=20261009,
    )
    assert mcts_result["action"] in legal
    assert mcts_result["iterations"] == 64

    _node_type, _fast_type, _eval_type, scratch_fn, traverse, _decoder = (
        mccfr_backend()
    )
    for traverser in (0, 1):
        leaf = traverse(
            fast, packed, traverser, depth=0, max_depth=0,
            nodes={}, rng=random.Random(20261009),
            scratch=scratch_fn(0), evaluator=evaluator,
        )
        assert math.isfinite(leaf)
