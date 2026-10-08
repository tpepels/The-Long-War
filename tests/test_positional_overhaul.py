"""Focused contracts for the October positional-mechanics replacement pass.

These are behavior tests, not frozen numbers for an unstable card pool.
"""
from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    ActivateAbility,
    BoardTarget,
    EffectChoice,
    Front,
    GameEngine,
    PlayBond,
    PlayForce,
    PlayTactic,
    Position,
    Rank,
)
from longwar.game.model import NarrativeState
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]


def setup():
    cards = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    engine = GameEngine(cards, rules=GameRules.standard())
    state = engine.new_game(deck, deck, seed=7026, first_player=0)
    state.battle = 3
    state.active_player = 0
    state.players[0].command = 20
    state.players[1].command = 20
    return engine, state


def p(front: int, rank: Rank = Rank.FRONT) -> Position:
    return Position(Front(front), rank)


def test_front_guard_prevents_exhaustion_from_a_gap():
    engine, state = setup()
    defended = p(1)
    other = p(2)
    state.slot(0, defended).force = "the-first-spear"
    state.slot(1, other).force = "the-fifty-men"
    state.players[0].hand = ["followed"]

    engine.apply(state, PlayBond("followed", p(3, Rank.REAR)))

    assert state.slot(0, defended).exhausted is False
    assert state.slot(1, other).exhausted is True


def test_hostile_tactic_exhausts_rear_force():
    engine, state = setup()
    rear = p(1, Rank.REAR)
    state.slot(1, rear).force = "the-fifty-men"
    state.players[0].hand = ["the-baggage-was-abandoned"]
    tactic = PlayTactic(
        "the-baggage-was-abandoned",
        target=BoardTarget(1, rear),
    )
    assert tactic in engine.legal_actions(state)
    engine.apply(state, tactic)

    assert state.slot(1, rear).exhausted is True


def test_raider_returns_attached_bond_only_after_line_opens():
    engine, state = setup()
    enemy = p(1, Rank.REAR)
    landing = p(1, Rank.MIDDLE)
    state.slot(1, enemy).force = "the-fifty-men"
    state.slot(1, enemy).bond = "followed"
    state.players[0].hand = ["seven-black-ships"]
    play = PlayForce("seven-black-ships", landing)
    assert play in engine.legal_actions(state)
    engine.apply(state, play)

    choices = [
        action for action in engine.legal_actions(state)
        if isinstance(action, EffectChoice)
        and not action.skip
        and action.destination is not None
        and action.destination.position == enemy
        and action.option == "bond"
    ]
    assert choices
    engine.apply(state, choices[0])

    assert state.slot(1, enemy).bond is None
    assert "followed" in state.players[1].hand


def test_narrative_exchanges_two_adjacent_friendly_fronts():
    engine, state = setup()
    left = p(1)
    right = p(2)
    state.slot(0, left).force = "the-fifty-men"
    state.slot(0, right).force = "thirty-spears"
    state.narratives[0] = [NarrativeState("no-road-was-too-long")]
    ability = ActivateAbility("no-road-was-too-long", narrative_slot=0)
    assert ability in engine.legal_actions(state)
    engine.apply(state, ability)

    choices = [
        action for action in engine.legal_actions(state)
        if isinstance(action, EffectChoice)
        and not action.skip
        and action.source is not None
        and action.destination is not None
        and action.source.position.front == Front.SECOND
        and action.destination.position.front == Front.THIRD
    ]
    assert choices
    engine.apply(state, choices[0])

    assert state.slot(0, left).force == "thirty-spears"
    assert state.slot(0, right).force == "the-fifty-men"


def test_narrative_exchanges_bonds_but_leaves_forces_in_place():
    engine, state = setup()
    left = p(1)
    right = p(2)
    state.slot(0, left).force = "the-fifty-men"
    state.slot(0, right).force = "thirty-spears"
    state.slot(0, left).bond = "followed"
    state.slot(0, right).bond = "guarded"
    state.narratives[0] = [NarrativeState("the-king-had-given-the-order")]
    ability = ActivateAbility("the-king-had-given-the-order", narrative_slot=0)
    assert ability in engine.legal_actions(state)
    engine.apply(state, ability)

    choices = [
        action for action in engine.legal_actions(state)
        if isinstance(action, EffectChoice)
        and not action.skip
        and action.source is not None
        and action.destination is not None
        and {action.source.position, action.destination.position} == {left, right}
    ]
    assert choices
    engine.apply(state, choices[0])

    assert state.slot(0, left).force == "the-fifty-men"
    assert state.slot(0, right).force == "thirty-spears"
    assert state.slot(0, left).bond == "guarded"
    assert state.slot(0, right).bond == "followed"
