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


@dataclass
class CoinState:
    stage: int = 0
    first_choice: str | None = None
    actor: int = 0
    turns: int = 0
    payoff: float = 0.0

    def clone(self):
        return CoinState(
            self.stage, self.first_choice, self.actor,
            self.turns, self.payoff
        )

    def copy_from(self, other):
        self.stage = other.stage
        self.first_choice = other.first_choice
        self.actor = other.actor
        self.turns = other.turns
        self.payoff = other.payoff


class HiddenMatchingPennies(ToyGame):
    """Known zero-sum equilibrium: both players choose H with probability 1/2.

    Player 1 never observes player 0's coin, despite the sequential engine
    storing it in the determinized state.
    """

    def is_terminal(self, state):
        return state.stage == 2

    def legal_actions(self, state):
        return [] if self.is_terminal(state) else ["H", "T"]

    def apply(self, state, action):
        if state.stage == 0:
            state.first_choice = action
            state.actor = 1
            state.stage = 1
        elif state.stage == 1:
            state.payoff = 1.0 if action == state.first_choice else -1.0
            state.actor = 0
            state.stage = 2
        else:
            raise AssertionError("terminal action")
        state.turns += 1

    def state_key(self, state):
        return (state.stage, state.actor, state.first_choice, state.payoff)

    def information_set_id(self, state, player):
        return (player, state.stage)


def test_hidden_observation_does_not_leak_opponent_choice() -> None:
    game = HiddenMatchingPennies()
    heads = CoinState(stage=1, first_choice="H", actor=1)
    tails = CoinState(stage=1, first_choice="T", actor=1)
    assert game.state_key(heads) != game.state_key(tails)
    assert game.information_set_id(heads, 1) == game.information_set_id(tails, 1)


def test_generic_mccfr_learns_known_matching_pennies_equilibrium() -> None:
    game = HiddenMatchingPennies()
    nodes = {}
    rng = random.Random(20261009)
    for _ in range(6000):
        for traverser in (0, 1):
            traverse_game(
                game, CoinState(), traverser, depth=0, max_turn_depth=2,
                nodes=nodes, rng=rng,
                frontier_value=lambda state, player: game.evaluate(state, player),
            )
    assert set(nodes) == {(0, 0), (1, 1)}
    for node in nodes.values():
        strategy = node.average_strategy(["H", "T"])
        assert sum(strategy.values()) == pytest.approx(1.0)
        assert abs(strategy["H"] - 0.5) < 0.20


@dataclass
class BranchState:
    path: tuple[str, ...] = ()
    actor: int = 0

    def clone(self):
        return BranchState(self.path, self.actor)

    def copy_from(self, other):
        self.path, self.actor = other.path, other.actor


class ExhaustiveTreeGame(ToyGame):
    def __init__(self, payoffs):
        self.payoffs = payoffs

    def is_terminal(self, state):
        return len(state.path) == 4

    def legal_actions(self, state):
        return [] if self.is_terminal(state) else ["a", "b", "c"]

    def apply(self, state, action):
        state.path = (*state.path, action)
        state.actor = 1 - state.actor

    def completed_turn(self, before, after, action):
        return True

    def state_key(self, state):
        return state.path

    def information_set_id(self, state, player):
        return (player, state.path)

    def terminal_utility(self, state, player):
        return (
            float(self.payoffs[state.path])
            if player == 0 else -float(self.payoffs[state.path])
        )


def test_generic_alpha_beta_matches_exhaustive_minimax_oracle() -> None:
    from itertools import product

    leaves = list(product("abc", repeat=4))
    for seed in (1, 9, 52, 131):
        rng = random.Random(seed)
        payoffs = {leaf: rng.randrange(-10, 11) for leaf in leaves}
        game = ExhaustiveTreeGame(payoffs)

        def oracle(path, actor):
            if len(path) == 4:
                return payoffs[path]
            children = [oracle((*path, a), 1 - actor) for a in "abc"]
            return max(children) if actor == 0 else min(children)

        expected = oracle((), 0)
        result = GenericAlphaBetaSearch(
            game, candidate_width=3
        ).search(
            BranchState(), root_player=0, depth=4,
            alpha=-inf, beta=inf,
            budget=SearchBudget(10000), transposition={}, scratch=[],
        )
        assert result == expected
