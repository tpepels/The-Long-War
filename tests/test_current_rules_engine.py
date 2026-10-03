from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    Cycle,
    EndTurn,
    Front,
    GameEngine,
    Maneuver,
    Pass,
    PlayForce,
    PlayName,
    Position,
    Rank,
)


ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "mobility-open-bonds.json"


def game():
    data = load_card_file(CARD_FILE)
    deck = json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=31003,
        first_player=0,
        opening_bonus=False,
    )
    return engine, state


def position(front: Front, rank: Rank) -> Position:
    return Position(front, rank)


def test_current_battlefield_has_three_rows() -> None:
    _engine, state = game()
    assert list(Rank) == [Rank.FRONT, Rank.MIDDLE, Rank.REAR]
    assert all(len(front) == 3 for side in state.board for front in side)


def test_battle_one_allows_only_two_middle_fronts() -> None:
    engine, state = game()
    state.players[0].hand[:] = ["the-fifty-men"]

    plays = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayForce) and action.card_id == "the-fifty-men"
    ]
    assert plays
    assert {action.position.front for action in plays} == {
        Front.SECOND,
        Front.THIRD,
    }
    assert {action.position.rank for action in plays} == {
        Rank.FRONT,
        Rank.MIDDLE,
        Rank.REAR,
    }

    state.battle = 2
    plays = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayForce) and action.card_id == "the-fifty-men"
    ]
    assert {action.position.front for action in plays} == {
        Front.FIRST,
        Front.SECOND,
        Front.THIRD,
    }

    state.battle = 3
    plays = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayForce) and action.card_id == "the-fifty-men"
    ]
    assert {action.position.front for action in plays} == set(Front)


def test_normal_turn_takes_two_actions_before_switching_player() -> None:
    engine, state = game()
    state.players[0].hand[:] = ["the-fifty-men", "the-fifty-men"]

    first = PlayForce(
        "the-fifty-men",
        position(Front.SECOND, Rank.FRONT),
    )
    second = PlayForce(
        "the-fifty-men",
        position(Front.THIRD, Rank.FRONT),
    )

    assert first in engine.legal_actions(state)
    engine.apply(state, first)
    assert state.active_player == 0
    assert state.actions_this_turn == 1
    assert second in engine.legal_actions(state)

    engine.apply(state, second)
    assert state.active_player == 1
    assert state.actions_this_turn == 0


def test_cycle_is_an_action_and_prevents_pass_when_two_cards_are_in_hand() -> None:
    engine, state = game()
    state.players[0].command = 0
    state.players[0].hand[:] = ["the-fifty-men", "followed"]

    legal = engine.legal_actions(state)
    assert any(isinstance(action, Cycle) for action in legal)
    assert not any(isinstance(action, Pass) for action in legal)


def test_pass_starts_two_closing_turns_then_non_passer_starts_next_battle() -> None:
    engine, state = game()
    state.players[0].command = 0
    state.players[0].hand.clear()

    legal = engine.legal_actions(state)
    assert legal == [Pass()]

    engine.apply(state, Pass())
    assert state.closing_stage == 1
    assert state.closing_passer == 0
    assert state.active_player == 1
    assert state.pass_order == [0]

    assert EndTurn() in engine.legal_actions(state)
    engine.apply(state, EndTurn())
    assert state.closing_stage == 2
    assert state.active_player == 0

    assert EndTurn() in engine.legal_actions(state)
    engine.apply(state, EndTurn())
    assert state.battle == 2
    assert state.active_player == 1
    assert state.closing_stage == 0
    assert state.closing_passer is None


def test_prepared_and_incomplete_formations_persist_between_battles() -> None:
    engine, state = game()
    prepared = position(Front.SECOND, Rank.MIDDLE)
    state.slot(0, prepared).bond = "followed"
    state.players[0].command = 0
    state.players[0].hand.clear()

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

    assert state.battle == 2
    assert state.slot(0, prepared).bond == "followed"
    assert state.slot(0, prepared).force is None
    assert state.slot(0, prepared).name is None


def test_standard_maneuver_is_one_orthogonal_step() -> None:
    engine, state = game()
    source = position(Front.SECOND, Rank.MIDDLE)
    slot = state.slot(0, source)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "namar"
    state.players[0].command = 20

    maneuvers = {
        action.destination
        for action in engine.legal_actions(state)
        if isinstance(action, Maneuver) and action.source == source
    }
    assert position(Front.SECOND, Rank.FRONT) in maneuvers
    assert position(Front.SECOND, Rank.REAR) in maneuvers
    assert position(Front.THIRD, Rank.MIDDLE) in maneuvers
    assert position(Front.FIRST, Rank.MIDDLE) not in maneuvers


def test_hero_force_and_name_allowances_are_independent() -> None:
    engine, state = game()
    hero = next(
        card_id
        for card_id, card in engine.cards.items()
        if card.get("hero")
    )
    target = position(Front.SECOND, Rank.MIDDLE)
    state.players[0].hand[:] = [hero]
    state.players[0].command = 20

    state.hero_force_used[0] = 1
    state.hero_name_used[0] = 0
    legal = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayForce) and action.card_id == hero
        for action in legal
    )
    assert any(
        isinstance(action, PlayName)
        and action.card_id == hero
        and action.position == target
        for action in legal
    )

    state.hero_force_used[0] = 0
    state.hero_name_used[0] = 1
    legal = engine.legal_actions(state)
    assert any(
        isinstance(action, PlayForce)
        and action.card_id == hero
        and action.position == target
        for action in legal
    )
    assert not any(
        isinstance(action, PlayName) and action.card_id == hero
        for action in legal
    )
