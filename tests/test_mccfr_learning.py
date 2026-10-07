from __future__ import annotations

import json
from pathlib import Path

import pytest


from longwar.cards import load_card_file
from longwar.game import EndTurn, Front, GameEngine, PlayForce, Position, Rank
from longwar.rules import GameRules
from longwar.game.model import StratagemState
from longwar.mccfr import (
    MCCFRTrainer,
    action_key,
    information_set_id,
    search_information_set_id,
)

ROOT = Path(__file__).resolve().parents[1]

pytestmark = [pytest.mark.research, pytest.mark.algorithm]


def setup(*, rules: GameRules | None = None):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data, rules=rules)
    state = engine.new_game(deck, deck, seed=19, first_player=0)
    return engine, deck, state


def test_fixed_state_training_is_reproducible() -> None:
    engine, deck, state = setup()
    state.battle = 3
    state.players[1].passed = True
    state.pass_order = [1]
    state.closing_turns_remaining = 2
    state.active_player = 0
    state.players[0].hand = ["the-fifty-men"]
    state.players[1].hand = []
    state.slot(0, Position(Front.FIRST, Rank.FRONT)).force = "the-fifty-men"
    state.slot(0, Position(Front.SECOND, Rank.FRONT)).force = "the-fifty-men"

    trainers = [
        MCCFRTrainer(engine, deck, deck, seed=55, max_depth=1),
        MCCFRTrainer(engine, deck, deck, seed=55, max_depth=1),
    ]
    for trainer in trainers:
        trainer.train_from_state(state, iterations=30)

    assert trainers[0].policy_payload() == trainers[1].policy_payload()


def test_mccfr_depth_counts_completed_turns_not_raw_actions() -> None:
    engine, deck, _state = setup()
    state = engine.new_game(
        deck,
        deck,
        seed=191,
        first_player=0,
        opening_bonus=False,
    )
    state.battle = 3
    target = Position(Front.FOURTH, Rank.REAR)
    for front in Front:
        for rank in Rank:
            position = Position(front, rank)
            if position != target:
                state.slot(0, position).force = "the-fifty-men"
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].deck = []
    state.players[0].discard = []
    state.players[1].hand = []
    state.players[1].deck = []
    state.players[1].discard = []
    state.pending_draw_discard_for = None

    play = PlayForce("the-fifty-men", target)
    assert play in engine.legal_actions(state)
    assert EndTurn() in engine.legal_actions(state)

    trainer = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=192,
        max_depth=1,
        direct_traversal=False,
    )
    trainer._traverse(state, 0, depth=0)

    same_turn = state.clone()
    engine.apply(same_turn, play, validate=False)
    assert same_turn.active_player == 0
    assert same_turn.actions_this_turn == 1
    assert (
        search_information_set_id(engine, same_turn, 0)
        in trainer.nodes
    )

    next_turn = state.clone()
    engine.apply(next_turn, EndTurn(), validate=False)
    assert next_turn.active_player == 1
    assert (
        search_information_set_id(engine, next_turn, 1)
        not in trainer.nodes
    )


def test_face_down_opponent_stratagem_identity_is_not_in_information_set() -> None:
    engine, _deck, state = setup()
    state.stratagems[1] = StratagemState(
        "the-ground-was-held",
        revealed=False,
    )
    first = information_set_id(state, 0)

    changed_hidden = state.clone()
    changed_hidden.stratagems[1].card_id = "the-lines-held"
    assert information_set_id(changed_hidden, 0) == first

    # The owner knows which card they set.
    assert information_set_id(changed_hidden, 1) != information_set_id(state, 1)

    # Public selections remain visible even while identity is hidden.
    chosen_front = state.clone()
    chosen_front.stratagems[1] = StratagemState(
        "no-step-back",
        fronts=(Front.FIRST,),
        revealed=False,
    )
    chosen_other_front = chosen_front.clone()
    chosen_other_front.stratagems[1].fronts = (Front.SECOND,)
    assert (
        information_set_id(chosen_front, 0)
        != information_set_id(chosen_other_front, 0)
    )

    # Once revealed, the opponent can distinguish the identity too.
    revealed = changed_hidden.clone()
    revealed.stratagems[1].revealed = True
    assert information_set_id(revealed, 0) != first


def test_public_stratagem_choice_order_does_not_change_information_set() -> None:
    _, _, state = setup()

    state.stratagems[1] = StratagemState(
        "the-center-must-hold",
        fronts=(Front.FIRST, Front.SECOND),
        revealed=False,
    )
    first = information_set_id(state, 0)
    reordered_fronts = state.clone()
    reordered_fronts.stratagems[1].fronts = (Front.SECOND, Front.FIRST)
    assert information_set_id(reordered_fronts, 0) == first

    first_target = (1, Position(Front.FIRST, Rank.REAR))
    second_target = (1, Position(Front.SECOND, Rank.REAR))
    state.stratagems[1] = StratagemState(
        "all-reserves-forward",
        targets=(first_target, second_target),
        revealed=False,
    )
    first = information_set_id(state, 0)
    reordered_targets = state.clone()
    reordered_targets.stratagems[1].targets = (
        second_target,
        first_target,
    )
    assert information_set_id(reordered_targets, 0) == first


def test_direct_longwar_traversal_matches_generic_core() -> None:
    # Full 10-card openings create a combinatorial Action-1 × Action-2 tree
    # now that MCCFR depth counts completed turns. Keep this as a backend
    # parity test with a small but still two-Action legal surface.
    rules = GameRules.standard().with_overrides(
        opening_hand_size=1,
        mulligan_max_cards=1,
    )
    engine, deck, _state = setup(rules=rules)
    direct = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=812,
        max_depth=1,
        direct_traversal=True,
    )
    generic = MCCFRTrainer(
        engine,
        deck,
        deck,
        seed=812,
        max_depth=1,
        direct_traversal=False,
    )

    # Root-deal training is the path that actually selects the primitive
    # traversal when enabled. Compare one deterministic completed-turn update:
    # longer stochastic runs are distributionally equivalent but need not stay
    # bit-identical after tiny floating-point differences alter sampled paths.
    direct_summary = direct.train(iterations=1)
    generic_summary = generic.train(iterations=1)

    assert direct_summary == generic_summary
    assert direct.policy_payload()["infosets"] == generic.policy_payload()["infosets"]
