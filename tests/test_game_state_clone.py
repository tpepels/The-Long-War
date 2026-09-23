from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


def test_game_state_fast_clone_is_fully_isolated() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=1234, first_player=0)

    state.players[0].discard.append("followed")
    slot = state.slot(0, Position(Front.CENTER, Rank.FRONT))
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.stratagem_used[0] = True

    clone = state.clone()
    assert clone.shuffle_seed == state.shuffle_seed

    clone.players[0].hand.clear()
    clone.players[0].discard.append("namar")
    clone.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "seven-black-ships"
    clone.stratagem_used[0] = False
    clone.pass_order.append(0)

    assert state.players[0].hand
    assert state.players[0].discard == ["followed"]
    assert state.slot(0, Position(Front.CENTER, Rank.FRONT)).subject == "the-fifty-men"
    assert state.stratagem_used[0] is True
    assert state.pass_order == []


def test_game_state_copy_from_reuses_containers_without_aliasing_source() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    source = engine.new_game(deck, deck, seed=11, first_player=0)
    target = engine.new_game(deck, deck, seed=22, first_player=1)

    source.players[0].discard.append("followed")
    source.players[1].passed = True
    source.pass_order.append(1)
    source.stratagem_used[0] = True
    slot = source.slot(0, Position(Front.RIGHT, Rank.REAR))
    slot.subject = "seven-black-ships"
    slot.temporary_strength = 2

    players_id = id(target.players)
    board_id = id(target.board)
    hand_id = id(target.players[0].hand)
    slot_id = id(target.slot(0, Position(Front.RIGHT, Rank.REAR)))

    target.copy_from(source)

    assert id(target.players) == players_id
    assert id(target.board) == board_id
    assert id(target.players[0].hand) == hand_id
    assert id(target.slot(0, Position(Front.RIGHT, Rank.REAR))) == slot_id
    assert target.players[0].hand == source.players[0].hand
    assert target.players[0].discard == ["followed"]
    assert target.players[1].passed is True
    assert target.pass_order == [1]
    assert target.stratagem_used[0] is True
    assert target.shuffle_seed == source.shuffle_seed
    assert target.slot(0, Position(Front.RIGHT, Rank.REAR)).subject == "seven-black-ships"
    assert target.slot(0, Position(Front.RIGHT, Rank.REAR)).temporary_strength == 2

    target.players[0].hand.clear()
    target.players[0].discard.append("namar")
    target.slot(0, Position(Front.RIGHT, Rank.REAR)).subject = "the-fifty-men"

    assert source.players[0].hand
    assert source.players[0].discard == ["followed"]
    assert source.slot(0, Position(Front.RIGHT, Rank.REAR)).subject == "seven-black-ships"
