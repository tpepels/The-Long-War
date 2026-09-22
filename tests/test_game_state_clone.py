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
