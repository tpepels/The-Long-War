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
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def fresh(*, rules: GameRules | None = None):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(
            encoding="utf-8"
        )
    )["cards"]
    engine = GameEngine(data, rules=rules)
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
    # Keep turn-flow tests below out of mandatory hand-limit cleanup.
    # Individual tests install the exact cards they need.
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
