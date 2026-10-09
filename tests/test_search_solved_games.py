"""Solved-game oracles for all three generic search algorithms.

These are independently defined games, not Long War game states. Alpha-beta
is checked against analytic normal-play take-away and an exact minimax oracle.
ISMCTS is tested on both perfect-information optimal decisions and a hidden
chance-type root with a known expected value. The generic MCCFR adapter is
tested end-to-end on Kuhn poker using its known Nash value and exploitability.

No test calls the game-specific native kernels: those are compile-time
specializations and require their own native parity and correctness tests.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf

import pytest

from longwar.algorithms.generic_alpha_beta import GenericAlphaBetaSearch, SearchBudget
from longwar.algorithms.generic_ismcts import GenericISMCTS
from longwar.algorithms.generic_mccfr import traverse_game
from longwar.mccfr_verification import (
    KNOWN_P0_VALUE,
    all_deals,
    average_policy,
    exploitability,
    expected_value,
    kuhn_actor,
    kuhn_infoset,
    kuhn_terminal,
    kuhn_terminal_utility,
)

pytestmark = pytest.mark.algorithm


@dataclass
class TakeAway:
    stones: int
    actor: int = 0
    last_player: int | None = None

    def copy_from(self, source):
        self.stones = source.stones
        self.actor = source.actor
        self.last_player = source.last_player


class TakeAwayGame:
    """Normal-play one-pile Nim, take 1 or 2. 3k stones is a loss."""

    def active_player(self, state):
        return state.actor

    def is_terminal(self, state):
        return state.stones == 0

    def frontier_ready(self, state):
        return True

    def legal_actions(self, state):
        return tuple(x for x in (1, 2) if x <= state.stones)

    def copy_state(self, state, reusable):
        if reusable is None:
            reusable = TakeAway(state.stones)
        reusable.copy_from(state)
        return reusable

    def apply(self, state, action):
        assert action in self.legal_actions(state)
        state.stones -= action
        state.last_player = state.actor
        state.actor = 1 - state.actor

    def completed_turn(self, before, after, action):
        return True

    def state_key(self, state):
        return (state.stones, state.actor, state.last_player)

    def information_set_id(self, state, player):
        return self.state_key(state)

    def action_id(self, action):
        return str(action)

    def is_priority_action(self, action):
        return False

    def action_score(self, state, player, action):
        return 0.0

    def terminal_utility(self, state, player):
        if not self.is_terminal(state):
            raise ValueError("not terminal")
        return 1.0 if player == state.last_player else -1.0

    def evaluate(self, state, player):
        # Analytic evaluator only at terminal leaves. Tests give enough depth
        # that no other state should reach the frontier.
        if not self.is_terminal(state):
            raise AssertionError("search did not reach terminal")
        return self.terminal_utility(state, player)


@pytest.mark.parametrize("stones", range(1, 11))
def test_alpha_beta_solves_normal_play_nim_exactly(stones):
    game = TakeAwayGame()
    result = GenericAlphaBetaSearch(game, candidate_width=2).search(
        TakeAway(stones), root_player=0, depth=stones,
        alpha=-inf, beta=inf, budget=SearchBudget(10000),
        transposition={}, scratch=[],
    )
    assert result == (-1.0 if stones % 3 == 0 else 1.0)


@pytest.mark.parametrize("stones,winning_take", ((1, 1), (2, 2), (4, 1), (5, 2), (7, 1)))
@pytest.mark.parametrize("seed", (7, 17, 53))
def test_ismcts_finds_analytic_nim_winning_move(stones, winning_take, seed):
    game = TakeAwayGame()
    result = GenericISMCTS(
        game, seed=seed, exploration=0.75,
        tree_turn_depth=12, rollout_actions=12,
    ).search([TakeAway(stones)], iterations=1200)
    assert result.action == winning_take
    assert result.root_visits == 1200


@dataclass
class HiddenState:
    private_outcome: int
    stage: int = 0
    actor: int = 0
    payoff: float = 0.0

    def copy_from(self, source):
        self.private_outcome = source.private_outcome
        self.stage = source.stage
        self.actor = source.actor
        self.payoff = source.payoff


class HiddenDecision(TakeAwayGame):
    """A fair hidden outcome: risky EV=0, safe gives +0.4 for player 0."""

    def is_terminal(self, state):
        return state.stage == 1

    def legal_actions(self, state):
        return () if self.is_terminal(state) else ("safe", "risky")

    def copy_state(self, state, reusable):
        if reusable is None:
            reusable = HiddenState(state.private_outcome)
        reusable.copy_from(state)
        return reusable

    def apply(self, state, action):
        assert action in ("safe", "risky") and not self.is_terminal(state)
        state.payoff = 0.4 if action == "safe" else float(state.private_outcome)
        state.stage = 1

    def state_key(self, state):
        return (state.private_outcome, state.stage, state.payoff)

    def information_set_id(self, state, player):
        return (player, state.stage)

    def terminal_utility(self, state, player):
        return state.payoff if player == 0 else -state.payoff

    def evaluate(self, state, player):
        if not self.is_terminal(state):
            raise AssertionError("only terminal evaluations are allowed")
        return self.terminal_utility(state, player)


@pytest.mark.parametrize("seed", (1, 42, 20261009))
def test_ismcts_uses_private_beliefs_to_choose_higher_expected_value(seed):
    game = HiddenDecision()
    # Both states look identical to the actor and have equal probability.
    roots = [HiddenState(-1), HiddenState(+1)]
    assert game.information_set_id(roots[0], 0) == game.information_set_id(roots[1], 0)
    assert game.state_key(roots[0]) != game.state_key(roots[1])
    result = GenericISMCTS(
        game, seed=seed, exploration=0.9,
        tree_turn_depth=2, rollout_actions=2,
    ).search(roots, iterations=4000)
    assert result.action == "safe"


@dataclass
class KuhnMutable:
    cards: tuple[int, int]
    history: str = ""

    def copy_from(self, source):
        self.cards = source.cards
        self.history = source.history


class KuhnGame(TakeAwayGame):
    """Full Kuhn poker game tree behind the game-independent SearchGame API."""

    def active_player(self, state):
        return kuhn_actor(state)

    def is_terminal(self, state):
        return kuhn_terminal(state)

    def legal_actions(self, state):
        return () if self.is_terminal(state) else ("p", "b")

    def copy_state(self, state, reusable):
        if reusable is None:
            reusable = KuhnMutable(state.cards)
        reusable.copy_from(state)
        return reusable

    def apply(self, state, action):
        assert not self.is_terminal(state) and action in ("p", "b")
        state.history += action

    def state_key(self, state):
        return (state.cards, state.history)

    def information_set_id(self, state, player):
        return kuhn_infoset(state, player)

    def terminal_utility(self, state, player):
        return kuhn_terminal_utility(state, player)

    def evaluate(self, state, player):
        if not self.is_terminal(state):
            raise AssertionError("exact full Kuhn traversals must reach terminal")
        return self.terminal_utility(state, player)


def test_generic_mccfr_solves_kuhn_poker_through_searchgame_adapter():
    rng = random.Random(20261009)
    game = KuhnGame()
    nodes = {}
    deals = all_deals()
    for _ in range(30000):
        state = KuhnMutable(rng.choice(deals))
        for traverser in (0, 1):
            traverse_game(
                game, state, traverser, depth=0, max_turn_depth=4,
                nodes=nodes, rng=rng,
                frontier_value=lambda state, player: game.evaluate(state, player),
            )

    policy = average_policy(nodes)
    value = expected_value(policy)
    nash_exp, _, _ = exploitability(policy)
    assert len(nodes) == 12
    assert value == pytest.approx(KNOWN_P0_VALUE, abs=0.04)
    assert nash_exp < 0.08

@pytest.mark.parametrize("stones", range(1, 10))
def test_alpha_beta_solves_when_root_is_not_to_play(stones):
    game = TakeAwayGame()
    result = GenericAlphaBetaSearch(game, candidate_width=2).search(
        TakeAway(stones, actor=1), root_player=0, depth=stones,
        alpha=-inf, beta=inf, budget=SearchBudget(10000),
        transposition={}, scratch=[],
    )
    assert result == (1.0 if stones % 3 == 0 else -1.0)
