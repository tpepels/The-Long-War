"""Contract tests deliberately use a game with no Long War imports/cards."""
from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf
from pathlib import Path

import pytest

from longwar.algorithms.game_interface import SearchGame
from longwar.algorithms.generic_alpha_beta import GenericAlphaBetaSearch, SearchBudget
from longwar.algorithms.generic_ismcts import GenericISMCTS
from longwar.algorithms.generic_mccfr import traverse_game

pytestmark = pytest.mark.algorithm


@dataclass
class ToyState:
    node: str = "root"
    actor: int = 0
    turns: int = 0
    payoff: float = 0.0

    def clone(self):
        return ToyState(self.node, self.actor, self.turns, self.payoff)

    def copy_from(self, other):
        self.node, self.actor = other.node, other.actor
        self.turns, self.payoff = other.turns, other.payoff


class ToyGame:
    """Two-player zero-sum tree with adversarial replies.

    Left -> opponent can yield -1; Right -> guaranteed +0.5 for player 0.
    Information keys depend only on the observable node, not game internals.
    """

    def active_player(self, state):
        return state.actor

    def is_terminal(self, state):
        return state.node.startswith("end-")

    def frontier_ready(self, state):
        return True

    def legal_actions(self, state):
        if state.node == "root":
            return ["L", "R"]
        if state.node in ("left", "right"):
            return ["x", "y"]
        return []

    def copy_state(self, source, reusable):
        if reusable is None:
            return source.clone()
        reusable.copy_from(source)
        return reusable

    def apply(self, state, action):
        if state.node == "root":
            state.node = "left" if action == "L" else "right"
            state.actor = 1
        elif state.node in ("left", "right"):
            state.payoff = (
                -1.0 if state.node == "left" and action == "y"
                else 1.0 if state.node == "left" else 0.5
            )
            state.node = "end-" + action
            state.actor = 0
        else:
            raise AssertionError("terminal action")
        state.turns += 1

    def completed_turn(self, before, after, action):
        return after.turns != before.turns

    def state_key(self, state):
        return state.node

    def information_set_id(self, state, player):
        return (player, state.node)

    def action_id(self, action):
        return action

    def is_priority_action(self, action):
        return False

    def action_score(self, state, player, action):
        return 0.0

    def evaluate(self, state, player):
        return self.terminal_utility(state, player) if self.is_terminal(state) else 0.0

    def terminal_utility(self, state, player):
        return state.payoff if player == 0 else -state.payoff


def test_generic_alpha_beta_solves_unrelated_game() -> None:
    game = ToyGame()
    search = GenericAlphaBetaSearch(game, candidate_width=2)
    budget = SearchBudget(100)
    result = search.search(
        ToyState(), root_player=0, depth=2,
        alpha=-inf, beta=inf, budget=budget, transposition={}, scratch=[],
    )
    assert result == pytest.approx(0.5)
    assert budget.nodes > 2


def test_generic_ismcts_prefers_minimax_safe_move() -> None:
    game = ToyGame()
    search = GenericISMCTS(
        game, seed=11, exploration=0.7,
        tree_turn_depth=2, rollout_actions=3,
    )
    result = search.search([ToyState(), ToyState()], iterations=800)
    assert result.action == "R"
    assert result.root_visits == 800
    assert sum(result.action_visits.values()) == 800


def test_generic_ismcts_rejects_incompatible_observations() -> None:
    game = ToyGame()
    with pytest.raises(ValueError, match="information set"):
        GenericISMCTS(game).search(
            [ToyState(), ToyState(node="left", actor=0)], iterations=3
        )


def test_generic_mccfr_accepts_unrelated_game() -> None:
    game = ToyGame()
    nodes = {}
    rng = random.Random(3)
    for _ in range(30):
        value = traverse_game(
            game, ToyState(), traverser=0, depth=0, max_turn_depth=2,
            nodes=nodes, rng=rng,
            frontier_value=lambda state, player: game.evaluate(state, player),
        )
        assert -1.0 <= value <= 1.0
    assert nodes
    assert all(node.visits > 0 for node in nodes.values())


def test_algorithm_sources_do_not_encode_long_war_rules() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("generic_alpha_beta.py", "generic_mccfr.py", "generic_ismcts.py"):
        source = (root / "src" / "longwar" / "algorithms" / name).read_text()
        assert "longwar.game" not in source
        assert "cards.json" not in source
        assert "_fe_" not in source
    for name in ("_alpha_beta_core.pxi", "_mccfr_core.pxi", "_ismcts_core.pxi"):
        source = (root / "src" / "longwar" / name).read_text()
        assert "_fe_" not in source, name
