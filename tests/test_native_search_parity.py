"""Native/reference parity on an executable in-memory game catalogue.

The paper catalogue contains 131 identities but current main's native state
has a 128 identity cap. This fixture selects 128 EXISTING cards without
rewriting their rules and retains a real, valid deck so native algorithm
contract checks run independently of the pending paper-engine migration.
"""
from __future__ import annotations

import json
from math import inf
from pathlib import Path

import pytest

from longwar.algorithms.alpha_beta import AlphaBetaSearch, SearchBudget
from longwar.cards import load_card_file
from longwar.game.engine import GameEngine
from longwar.heuristics import StrategicEvaluator
from longwar.native_search import strategic_backend, mccfr_backend

pytestmark = pytest.mark.algorithm

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def small_real_game():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    # A small *runtime fixture*, not a change to authored cards. All cards
    # used by the original deck remain present and in the same code order.
    trimmed = dict(data)
    trimmed["cards"] = data["cards"][:128]
    assert len(trimmed["cards"]) == 128
    assert set(deck).issubset({card["id"] for card in trimmed["cards"]})
    engine = GameEngine(trimmed)
    return engine, deck


@pytest.mark.parametrize("seed,root_player", ((31, 0), (62, 1), (97, 0)))
def test_native_and_reference_strategic_evaluation_agree(
    small_real_game, seed, root_player
):
    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=seed, first_player=root_player, opening_bonus=False
    )
    fast_type, native_evaluator_type, budget_type, _limit_type, table_type, search = (
        strategic_backend()
    )
    fast = fast_type(engine)
    native_eval = native_evaluator_type(
        fast, sampled_opponent_resources=False
    )
    python_eval = StrategicEvaluator(sampled_opponent_resources=False)
    expected = python_eval._strategic_state_value(engine, state, root_player)
    observed = search(
        fast, state, root_player, 0, -inf, inf,
        budget_type(5000), 4, native_eval, table_type(1000),
    )
    assert observed == pytest.approx(expected, rel=1e-12, abs=1e-10)


def test_native_and_reference_alpha_beta_agree_at_forced_root(small_real_game):
    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=513, first_player=0, opening_bonus=False
    )
    # Sparse deterministic decision state: tiny branching and no hidden
    # draws. Both search algorithms are required to resolve the same turns.
    for player in state.players:
        player.hand.clear()
        player.deck.clear()
        player.discard.clear()
    state.active_player = 0
    state.actions_this_turn = 0
    state.pending_effects.clear()

    legal = engine.legal_actions(state)
    assert 1 <= len(legal) <= 3, len(legal)

    fast_type, native_evaluator_type, budget_type, _limit_type, table_type, search = (
        strategic_backend()
    )
    fast = fast_type(engine)
    native_eval = native_evaluator_type(fast, sampled_opponent_resources=False)
    python_eval = StrategicEvaluator(sampled_opponent_resources=False)
    expected = AlphaBetaSearch(engine, python_eval, candidate_width=10).search(
        state, root_player=0, depth=1, alpha=-inf, beta=inf,
        budget=SearchBudget(10000), transposition={}, scratch=[],
    )
    result = search(
        fast, state, 0, 1, -inf, inf,
        budget_type(10000), 10, native_eval, table_type(1000),
    )
    assert result == pytest.approx(expected, abs=1e-8)


@pytest.mark.parametrize("traverser", (0, 1))
def test_mccfr_native_leaf_evaluation_matches_public_evaluator(
    small_real_game, traverser
):
    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=997, first_player=0, opening_bonus=False
    )
    fast_node, fast_type, native_eval_type, scratch, traverse, _key = (
        mccfr_backend()
    )
    fast = fast_type(engine)
    evaluator = native_eval_type(fast, sampled_opponent_resources=False)
    packed = fast.from_game_state(state)
    scale = 100.0
    from math import tanh

    expected = tanh(float(evaluator.evaluate(packed, traverser)) / scale)
    actual = traverse(
        fast, packed, traverser, depth=0, max_depth=0,
        nodes={}, rng=__import__("random").Random(123),
        leaf_scale=scale, scratch=scratch(0), evaluator=evaluator,
    )
    assert actual == pytest.approx(expected, abs=1e-12)


def test_native_information_key_respects_player_observation(small_real_game):
    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=617, first_player=0, opening_bonus=False
    )
    fast_type, *_ = strategic_backend()
    fast = fast_type(engine)
    original = fast.information_key(fast.from_game_state(state), 0)

    hidden = state.clone()
    # Rearrange unseen opponent deck order without changing multiset.
    hidden.players[1].deck.reverse()
    assert fast.information_key(fast.from_game_state(hidden), 0) == original

    visible = state.clone()
    visible.players[0].command -= 1
    assert fast.information_key(fast.from_game_state(visible), 0) != original


@pytest.mark.parametrize("seed", (123, 456, 789, 20261009))
def test_observation_redacts_opponent_hand_composition(
    small_real_game, seed
):
    """Switch a hidden card between opponent hand/deck, preserving counts."""
    from longwar.game.actions import action_key

    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=seed, first_player=0, opening_bonus=False
    )
    fast_type, *_ = strategic_backend()
    native = fast_type(engine)
    previous = native.from_game_state(state)
    before = native.information_key(previous, 0)
    before_hash = native.information_hash(previous, 0)
    before_legal = {
        native.action_key(code) for code in native.legal_actions(previous)
    }

    hidden = state.clone()
    opponent = hidden.players[1]
    assert opponent.hand and opponent.deck
    # Exchange a card rather than changing observable zone lengths.
    replacement = next(
        (c for c in opponent.deck if c not in opponent.hand), None
    )
    if replacement is None:
        pytest.skip("Deck has no hidden alternative for this seed")
    removed = opponent.hand[0]
    opponent.hand[0] = replacement
    opponent.deck.remove(replacement)
    opponent.deck.append(removed)

    observed = native.from_game_state(hidden)
    assert native.information_key(observed, 0) == before
    assert native.information_hash(observed, 0) == before_hash
    assert native.information_key(observed, 1) != native.information_key(
        previous, 1
    )
    assert {
        native.action_key(code) for code in native.legal_actions(observed)
    } == before_legal
    assert {action_key(a) for a in engine.legal_actions(hidden)} == {
        action_key(a) for a in engine.legal_actions(state)
    }


def test_hidden_stratagem_identity_is_private_until_reveal_or_known(
    small_real_game,
):
    from longwar.game.model import StratagemState

    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=112, first_player=0, opening_bonus=False
    )
    native_type, *_ = strategic_backend()
    native = native_type(engine)
    ground = state.clone()
    ground.stratagems[1] = StratagemState("the-ground-was-held", revealed=False)
    lines = state.clone()
    lines.stratagems[1] = StratagemState("the-lines-held", revealed=False)

    def key(current, player):
        return native.information_key(native.from_game_state(current), player)

    assert key(ground, 0) == key(lines, 0)
    assert key(ground, 1) != key(lines, 1)

    revealed = ground.clone()
    revealed.stratagems[1].revealed = True
    assert key(revealed, 0) != key(lines, 0)

    explicitly_known = ground.clone()
    explicitly_known.stratagems[1].known_to_mask |= 1 << 0
    assert key(explicitly_known, 0) != key(lines, 0)


@pytest.mark.parametrize("seed", (17, 23, 37))
def test_observation_key_stable_under_private_deck_permutations(
    small_real_game, seed
):
    import random

    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=seed, first_player=0, opening_bonus=False
    )
    native_type, *_ = strategic_backend()
    native = native_type(engine)
    original = native.from_game_state(state)
    baseline = (native.information_key(original, 0),
                native.information_hash(original, 0))
    for shuffle_seed in range(12):
        altered = state.clone()
        random.Random(shuffle_seed).shuffle(altered.players[1].deck)
        changed = native.from_game_state(altered)
        assert (native.information_key(changed, 0),
                native.information_hash(changed, 0)) == baseline


def test_observation_distinguishes_public_and_owned_resources(small_real_game):
    engine, deck = small_real_game
    state = engine.new_game(
        deck, deck, seed=451, first_player=0, opening_bonus=False
    )
    native_type, *_ = strategic_backend()
    native = native_type(engine)
    reference = native.from_game_state(state)
    key = native.information_key(reference, 0)

    hand_changed = state.clone()
    player = hand_changed.players[0]
    alternate = next(card for card in player.deck if card not in player.hand)
    old = player.hand[0]
    player.hand[0] = alternate
    player.deck.remove(alternate)
    player.deck.append(old)
    assert native.information_key(native.from_game_state(hand_changed), 0) != key

    command_changed = state.clone()
    command_changed.players[1].command -= 1
    assert native.information_key(native.from_game_state(command_changed), 0) != key

    turn_changed = state.clone()
    turn_changed.turn_number += 1
    assert native.information_key(native.from_game_state(turn_changed), 0) != key
