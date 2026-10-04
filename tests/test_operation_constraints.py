from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    BoardTarget,
    ConstraintKind,
    EndTurn,
    Front,
    GameEngine,
    Maneuver,
    OperationConstraint,
    Pass,
    PlayForce,
    PlayNarrative,
    PlayStratagem,
    Position,
    Rank,
)
from longwar.game.model import NarrativeState, StratagemState


ROOT = Path(__file__).resolve().parents[1]


def fresh():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=280926,
        first_player=0,
        opening_bonus=False,
    )
    state.players[0].command = 20
    state.players[1].command = 20
    state.battle = 3
    # Keep turn-flow tests below out of the mandatory discard-before-draw
    # substep. Individual tests install the exact cards they need.
    state.players[0].hand.clear()
    state.players[1].hand.clear()
    return engine, state


def named(state, player: int, position: Position, *, bond: str = "followed"):
    slot = state.slot(player, position)
    slot.force = "the-fifty-men"
    slot.bond = bond
    slot.name = "namar"
    return slot


def test_multiple_next_action_requirements_prefer_one_action_satisfying_all():
    engine, state = fresh()
    source = Position(Front.THIRD, Rank.FRONT)
    destination = Position(Front.SECOND, Rank.FRONT)
    named(state, 0, source)
    state.operations_this_battle[:] = [1, 1]
    state.constraints[:] = [
        OperationConstraint(
            "the-battle-had-chosen-them",
            0,
            ConstraintKind.AFFECT_FRONT,
            0,
            front=Front.SECOND,
        ),
        OperationConstraint(
            "they-had-gone-too-far",
            0,
            ConstraintKind.MANEUVER,
            0,
        ),
    ]

    legal = engine.legal_actions(state)
    assert Maneuver(source, destination) in legal
    assert EndTurn() in legal
    assert all(
        action == Maneuver(source, destination) or isinstance(action, EndTurn)
        for action in legal
    )


def test_conflicting_front_requirements_allow_union_of_satisfiable_requirements():
    engine, state = fresh()
    state.players[0].hand = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.constraints[:] = [
        OperationConstraint(
            "every-banner-turned-toward-them",
            0,
            ConstraintKind.AFFECT_FRONT,
            0,
            front=Front.FIRST,
        ),
        OperationConstraint(
            "the-battle-had-chosen-them",
            0,
            ConstraintKind.AFFECT_FRONT,
            1,
            front=Front.FOURTH,
        ),
    ]

    legal = engine.legal_actions(state)
    force_fronts = {
        action.position.front
        for action in legal
        if isinstance(action, PlayForce)
    }
    assert force_fronts == {Front.FIRST, Front.FOURTH}
    assert Pass() not in legal


def test_impossible_requirement_does_not_block_normal_action_or_endturn():
    engine, state = fresh()
    state.players[0].hand = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.constraints[:] = [
        OperationConstraint(
            "the-king-had-given-the-order",
            0,
            ConstraintKind.SPECIFIC_MANEUVER,
            0,
            source_position=Position(Front.SECOND, Rank.FRONT),
            direction="left",
        )
    ]

    legal = engine.legal_actions(state)
    assert Pass() not in legal
    assert EndTurn() in legal
    assert any(isinstance(action, PlayForce) for action in legal)


def test_front_selecting_stratagem_consumes_existing_front_obligation():
    engine, state = fresh()
    state.players[0].hand = ["no-step-back"]
    state.constraints[:] = [
        OperationConstraint(
            "the-battle-had-chosen-them",
            0,
            ConstraintKind.AFFECT_FRONT,
            0,
            front=Front.SECOND,
        )
    ]
    action = PlayStratagem(
        "no-step-back",
        fronts=(Front.SECOND,),
    )

    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    assert not state.constraints


def test_battle_had_chosen_them_creates_front_obligation_after_first_card():
    engine, state = fresh()
    state.narratives[0] = [
        NarrativeState(
            "the-battle-had-chosen-them",
            fronts=(Front.SECOND,),
        )
    ]
    state.players[0].hand = ["the-fifty-men", "the-fifty-men"]

    engine.apply(
        state,
        PlayForce(
            "the-fifty-men",
            Position(Front.SECOND, Rank.FRONT),
        ),
    )

    assert state.narratives[0][0].triggered_players_mask == 1
    assert state.active_player == 0
    assert state.actions_this_turn == 1
    assert any(
        item.kind is ConstraintKind.AFFECT_FRONT
        and item.player == 0
        and item.front is Front.SECOND
        for item in state.constraints
    )
    legal = engine.legal_actions(state)
    assert EndTurn() in legal
    assert {
        action.position.front
        for action in legal
        if isinstance(action, PlayForce)
    } == {Front.SECOND}


def test_no_one_would_be_first_to_leave_pins_named_formations():
    engine, state = fresh()
    state.narratives[0] = [
        NarrativeState(
            "no-one-would-be-first-to-leave",
            fronts=(Front.SECOND,),
        )
    ]
    source = Position(Front.SECOND, Rank.FRONT)
    named(state, 1, source)
    state.active_player = 1
    state.operations_this_battle[:] = [1, 1]

    legal = engine.legal_actions(state)
    assert Maneuver(source, Position(Front.FIRST, Rank.FRONT)) not in legal
    assert Maneuver(source, Position(Front.THIRD, Rank.FRONT)) not in legal


def test_king_had_given_order_waits_until_next_turn_then_forces_free_maneuver():
    engine, state = fresh()
    source = Position(Front.SECOND, Rank.FRONT)
    target = Position(Front.FIRST, Rank.FRONT)
    named(state, 0, source)
    state.players[0].hand = [
        "the-king-had-given-the-order",
        "the-fifty-men",
    ]
    state.players[1].hand = []
    state.players[1].deck.clear()
    state.players[1].discard.clear()

    play = PlayNarrative(
        "the-king-had-given-the-order",
        targets=(BoardTarget(0, source),),
        ongoing_slot=0,
        direction="left",
    )
    assert play in engine.legal_actions(state)
    engine.apply(state, play)

    # The Warning says "next turn", so Action 2 of this turn is not constrained.
    assert state.active_player == 0
    assert state.actions_this_turn == 1
    assert any(isinstance(action, PlayForce) for action in engine.legal_actions(state))

    engine.apply(state, EndTurn())
    assert state.active_player == 1
    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())
    assert state.active_player == 0

    legal = engine.legal_actions(state)
    assert Maneuver(source, target) in legal
    assert EndTurn() in legal
    assert all(
        action == Maneuver(source, target) or isinstance(action, EndTurn)
        for action in legal
    )
    assert engine.command_cost_for_action(state, Maneuver(source, target)) == 0


def test_they_had_gone_too_far_creates_next_battle_maneuver_obligation():
    engine, state = fresh()
    state.narratives[0] = [NarrativeState("they-had-gone-too-far")]
    for front in (Front.FIRST, Front.SECOND, Front.THIRD):
        state.slot(0, Position(front, Rank.FRONT)).force = "the-fifty-men"
    state.operations_this_battle[:] = [1, 1]
    state.players[1].hand = []

    engine.apply(state, Pass())
    assert state.active_player == 1
    engine.apply(state, EndTurn())
    assert state.active_player == 0
    engine.apply(state, EndTurn())

    assert state.battle == 4
    assert not any(
        narrative.card_id == "they-had-gone-too-far"
        for narrative in state.narratives[0]
    )
    assert any(
        item.kind is ConstraintKind.MANEUVER and item.player == 0
        for item in state.constraints
    )


def test_there_was_no_road_back_allows_entry_but_not_exit():
    engine, state = fresh()
    state.stratagems[0] = StratagemState(
        "there-was-no-road-back",
        fronts=(Front.SECOND,),
    )
    source = Position(Front.SECOND, Rank.FRONT)
    named(state, 1, source)
    state.active_player = 1
    state.operations_this_battle[:] = [1, 1]

    legal = engine.legal_actions(state)
    assert Maneuver(source, Position(Front.FIRST, Rank.FRONT)) not in legal
    assert Maneuver(source, Position(Front.THIRD, Rank.FRONT)) not in legal

    outside = Position(Front.THIRD, Rank.REAR)
    named(state, 1, outside)
    assert Maneuver(outside, Position(Front.SECOND, Rank.REAR)) in engine.legal_actions(state)


def test_line_had_begun_to_move_forces_direction_and_makes_first_maneuver_free():
    engine, state = fresh()
    state.stratagems[0] = StratagemState(
        "the-line-had-begun-to-move",
        direction="left",
    )
    source = Position(Front.SECOND, Rank.FRONT)
    left = Position(Front.FIRST, Rank.FRONT)
    right = Position(Front.THIRD, Rank.FRONT)
    named(state, 1, source)
    state.active_player = 1
    state.operations_this_battle[:] = [1, 1]

    legal = engine.legal_actions(state)
    assert Maneuver(source, left) in legal
    assert Maneuver(source, right) not in legal
    assert engine.command_cost_for_action(
        state, Maneuver(source, left)
    ) == 0


def test_every_banner_turned_toward_them_constrains_both_next_actions():
    engine, state = fresh()
    state.players[0].hand = [
        "every-banner-turned-toward-them",
        "the-fifty-men",
    ]
    state.players[1].hand = ["the-fifty-men"]
    state.players[1].deck.clear()
    state.players[1].discard.clear()
    play = PlayStratagem(
        "every-banner-turned-toward-them",
        fronts=(Front.SECOND,),
    )
    assert play in engine.legal_actions(state)
    engine.apply(state, play)

    # The controller's next Action can be Action 2 of the same turn.
    assert state.active_player == 0
    legal = engine.legal_actions(state)
    assert EndTurn() in legal
    assert {
        action.position.front
        for action in legal
        if isinstance(action, PlayForce)
    } == {Front.SECOND}
    assert {item.player for item in state.constraints} == {0, 1}

    # Ending the turn does not consume the obligation. The opponent's first
    # Action is constrained in the same way.
    engine.apply(state, EndTurn())
    assert state.active_player == 1
    legal = engine.legal_actions(state)
    assert EndTurn() in legal
    assert {
        action.position.front
        for action in legal
        if isinstance(action, PlayForce)
    } == {Front.SECOND}


def test_had_been_ordered_forward_gains_strength_and_keeps_direction_if_possible():
    engine, state = fresh()
    source = Position(Front.THIRD, Rank.FRONT)
    middle = Position(Front.SECOND, Rank.FRONT)
    left = Position(Front.FIRST, Rank.FRONT)
    right = Position(Front.THIRD, Rank.FRONT)
    slot = named(
        state,
        0,
        source,
        bond="had-been-ordered-forward",
    )
    before = engine.position_strength(state, 0, source)
    state.operations_this_battle[:] = [1, 1]
    state.players[1].hand = []

    engine.apply(state, Maneuver(source, middle))
    after = engine.position_strength(state, 0, middle)
    assert after == before + 2

    assert state.active_player == 0
    assert state.actions_this_turn == 1
    legal = engine.legal_actions(state)
    assert Maneuver(middle, left) in legal
    assert Maneuver(middle, right) not in legal


def test_normal_action_consumes_an_impossible_next_action_requirement():
    engine, state = fresh()
    state.players[0].hand = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.constraints[:] = [
        OperationConstraint(
            "the-king-had-given-the-order",
            0,
            ConstraintKind.SPECIFIC_MANEUVER,
            0,
            source_position=Position(Front.SECOND, Rank.FRONT),
            direction="left",
        )
    ]

    legal = engine.legal_actions(state)
    assert Pass() not in legal
    action = next(action for action in legal if isinstance(action, PlayForce))
    engine.apply(state, action)
    assert not state.constraints
