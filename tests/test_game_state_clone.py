from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Position, Rank
from longwar.game.model import StoryState, StratagemState


ROOT = Path(__file__).resolve().parents[1]


def setup(seed: int, first_player: int = 0):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    return engine.new_game(
        deck,
        deck,
        seed=seed,
        first_player=first_player,
        opening_bonus=False,
    )


def test_game_state_clone_is_fully_isolated() -> None:
    state = setup(1234)
    position = Position(Front.FOURTH, Rank.REAR)
    slot = state.slot(0, position)
    slot.force = "seven-black-ships"
    slot.bond = "followed"
    slot.name = "namar"
    state.stories[0].append(StoryState("the-lamps-went-dark"))
    state.stratagems[0] = StratagemState("the-storm-broke")
    state.stratagem_used[0] = True
    state.pending_draw_discard_for = 1

    clone = state.clone()

    clone.players[0].hand.clear()
    clone.slot(0, position).force = "the-fifty-men"
    clone.stories[0][0].card_id = "the-road-was-cut"
    clone.stratagems[0].card_id = "the-tide-rose"
    clone.pass_order.append(0)
    clone.pending_draw_discard_for = None

    assert state.players[0].hand
    assert state.slot(0, position).force == "seven-black-ships"
    assert state.stories[0][0].card_id == "the-lamps-went-dark"
    assert state.stratagems[0].card_id == "the-storm-broke"
    assert state.pass_order == []
    assert state.pending_draw_discard_for == 1


def test_game_state_copy_from_reuses_containers_without_aliasing_source() -> None:
    source = setup(11)
    target = setup(22, first_player=1)
    position = Position(Front.FOURTH, Rank.REAR)

    source.players[0].discard.append("followed")
    source.players[1].passed = True
    source.pass_order.append(1)
    source.stratagem_used[0] = True
    source.stories[0].append(StoryState("the-lamps-went-dark"))
    source.stratagems[0] = StratagemState("the-storm-broke")
    slot = source.slot(0, position)
    slot.force = "seven-black-ships"
    slot.bond = "followed"
    slot.name = "namar"
    slot.temporary_strength = 2

    players_id = id(target.players)
    board_id = id(target.board)
    hand_id = id(target.players[0].hand)
    slot_id = id(target.slot(0, position))

    target.copy_from(source)

    assert id(target.players) == players_id
    assert id(target.board) == board_id
    assert id(target.players[0].hand) == hand_id
    assert id(target.slot(0, position)) == slot_id
    assert target.players[0].hand == source.players[0].hand
    assert target.players[0].discard == ["followed"]
    assert target.players[1].passed is True
    assert target.pass_order == [1]
    assert target.stratagem_used[0] is True
    assert target.stories[0][0].card_id == "the-lamps-went-dark"
    assert target.stratagems[0].card_id == "the-storm-broke"
    assert target.slot(0, position).force == "seven-black-ships"
    assert target.slot(0, position).temporary_strength == 2

    target.players[0].hand.clear()
    target.slot(0, position).force = "the-fifty-men"
    target.stories[0][0].card_id = "the-road-was-cut"

    assert source.players[0].hand
    assert source.slot(0, position).force == "seven-black-ships"
    assert source.stories[0][0].card_id == "the-lamps-went-dark"
