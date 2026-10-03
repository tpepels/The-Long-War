from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.decks import InvalidDeckDefinition, validate_deck_definition
from longwar.game import (
    Cycle,
    EndTurn,
    Front,
    GameEngine,
    Maneuver,
    Pass,
    PlayForce,
    PlayName,
    PlayStratagem,
    Position,
    Rank,
)
from longwar.protocol import CardType


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
    for player in state.players:
        player.hand.clear()
        player.deck.clear()
        player.discard.clear()
    state.players[0].command = 0

    legal = engine.legal_actions(state)
    assert legal == [Pass()]

    engine.apply(state, Pass())
    assert state.closing_stage == 1
    assert state.closing_passer == 0
    assert state.active_player == 1
    assert state.pass_order == [0]
    assert engine.legal_actions(state) == [EndTurn()]

    engine.apply(state, EndTurn())
    assert state.closing_stage == 2
    assert state.active_player == 0
    assert engine.legal_actions(state) == [EndTurn()]

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


def test_both_closing_turns_include_the_normal_draw() -> None:
    engine, state = game()
    for player in state.players:
        player.hand.clear()
        player.discard.clear()
    state.players[0].deck[:] = ["the-fifty-men"]
    state.players[1].deck[:] = ["the-fifty-men"]
    state.players[0].command = 0

    engine.apply(state, Pass())
    assert state.active_player == 1
    assert state.players[1].hand == ["the-fifty-men"]

    first_action = next(
        action
        for action in engine.legal_actions(state)
        if not isinstance(action, EndTurn)
    )
    engine.apply(state, first_action)
    assert EndTurn() in engine.legal_actions(state)
    engine.apply(state, EndTurn())

    assert state.active_player == 0
    assert state.players[0].hand == ["the-fifty-men"]


def test_lost_front_only_costs_command_and_does_not_remove_cards() -> None:
    engine, state = game()
    for player in state.players:
        player.hand.clear()
        player.deck.clear()
        player.discard.clear()
        player.command = 20

    own = position(Front.SECOND, Rank.MIDDLE)
    enemy = position(Front.SECOND, Rank.FRONT)
    state.slot(0, own).force = "the-fifty-men"
    state.slot(0, own).bond = "followed"
    state.slot(0, own).name = "namar"
    state.slot(1, enemy).force = "the-fifty-men"
    state.slot(1, enemy).temporary_strength = 10

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

    assert state.last_battle_snapshot is not None
    assert state.last_battle_snapshot["front_loss_command_penalty"][0] == 1
    assert state.slot(0, own).force == "the-fifty-men"
    assert state.slot(0, own).bond == "followed"
    assert state.slot(0, own).name == "namar"


def test_equal_collapse_means_the_passer_loses() -> None:
    engine, state = game()
    for player in state.players:
        player.hand.clear()
        player.deck.clear()
        player.discard.clear()
        player.command = 1

    p0_win = position(Front.SECOND, Rank.FRONT)
    p1_win = position(Front.THIRD, Rank.FRONT)
    state.slot(0, p0_win).force = "the-fifty-men"
    state.slot(0, p0_win).temporary_strength = 10
    state.slot(1, p0_win).force = "the-fifty-men"
    state.slot(1, p1_win).force = "the-fifty-men"
    state.slot(1, p1_win).temporary_strength = 10
    state.slot(0, p1_win).force = "the-fifty-men"

    engine.apply(state, Pass())
    engine.apply(state, EndTurn())
    engine.apply(state, EndTurn())

    assert state.phase.value == "complete"
    assert state.winner == 1


def test_stratagem_is_face_down_when_played() -> None:
    engine, state = game()
    stratagem = next(
        card_id
        for card_id, card in engine.cards.items()
        if card["type"] == CardType.STRATAGEM
    )
    state.players[0].hand[:] = [stratagem]
    state.players[0].command = 20

    action = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayStratagem) and action.card_id == stratagem
    )
    engine.apply(state, action)

    assert state.stratagems[0] is not None
    assert state.stratagems[0].card_id == stratagem
    assert state.stratagems[0].revealed is False


def test_current_deck_rules_are_34_cards_four_nonunique_one_unique() -> None:
    data = load_card_file(CARD_FILE)
    cards = {card["id"]: card for card in data["cards"]}

    non_force_name = [
        card_id
        for card_id, card in cards.items()
        if not card.get("unique", False)
        and card["type"] not in {CardType.FORCE, CardType.NAME}
    ]
    assert len(non_force_name) >= 9

    deck: list[str] = []
    for card_id in non_force_name:
        deck.extend([card_id] * min(4, 34 - len(deck)))
        if len(deck) == 34:
            break
    validate_deck_definition(deck, cards)

    too_many = list(deck)
    fifth = too_many[0]
    replace_at = next(
        i for i, card_id in enumerate(too_many)
        if card_id != fifth
    )
    too_many[replace_at] = fifth
    try:
        validate_deck_definition(too_many, cards)
    except InvalidDeckDefinition:
        pass
    else:
        raise AssertionError("five copies of a non-Unique card must be illegal")

    unique = next(
        card_id for card_id, card in cards.items()
        if card.get("unique")
    )
    unique_twice = list(deck)
    unique_twice[0] = unique
    unique_twice[1] = unique
    try:
        validate_deck_definition(unique_twice, cards)
    except InvalidDeckDefinition:
        pass
    else:
        raise AssertionError("two copies of a Unique card must be illegal")
