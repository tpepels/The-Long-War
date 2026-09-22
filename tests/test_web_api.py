from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.web_api import PlaySession

ROOT = Path(__file__).resolve().parents[1]


def payloads() -> tuple[str, str]:
    cards = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )
    return json.dumps(cards), json.dumps(deck)


def finish_hotseat_mulligan(session: PlaySession) -> None:
    session.mulligan([], 0)
    session.mulligan([], 1)


def test_hotseat_snapshot_hides_opening_hand_until_revealed() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)

    public = session.snapshot(None)
    assert public["phase"] == "mulligan"
    assert public["active_player"] == 0
    assert public["needs_reveal"] is True
    assert public["hand"] == []
    assert public["legal_actions"] == []

    private = session.snapshot(0)
    assert len(private["hand"]) == 10
    assert private["mulligan_available"] is True
    assert private["legal_actions"] == []


def test_hotseat_mulligans_are_private_and_then_start_match() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)

    first = session.mulligan([0, 1], 0)
    assert first["viewer"] is None
    assert first["phase"] == "mulligan"
    assert first["active_player"] == 1
    assert first["needs_reveal"] is True

    second = session.mulligan([], 1)
    assert second["viewer"] is None
    assert second["phase"] == "battle"
    assert second["needs_reveal"] is True
    assert session.setup_complete is True


def test_hotseat_action_returns_to_privacy_gate() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player

    result = session.act("pass", active)

    assert result["viewer"] is None
    assert result["needs_reveal"] is True
    assert result["hand"] == []


def test_heuristic_mode_mulligan_then_returns_control_to_human() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="heuristic", seed=1701)
    assert session.snapshot(0)["phase"] == "mulligan"

    result = session.mulligan([], 0)

    assert result["phase"] == "complete" or result["active_player"] == 0
    if result["phase"] != "complete":
        assert result["viewer"] == 0
        assert result["legal_actions"]


def test_action_payload_exposes_structured_board_targets() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    session.state.players[active].hand = [
        "the-fifty-men",
        "the-lamps-went-dark",
    ]
    snapshot = session.snapshot(active)

    subject = next(
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlaySubject"
    )
    assert subject["position"]["front"] in (0, 1, 2)
    assert subject["position"]["rank"] in ("front", "rear")
    assert subject["targets"] == []

    scheme = next(
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlayScheme"
    )
    assert scheme["front"] in (0, 1, 2)
    assert scheme["position"] is None


def test_snapshot_exposes_front_control() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    snapshot = session.snapshot(session.state.active_player)

    assert snapshot["front_control"] == [None, None, None]


def test_stratagem_action_is_free_and_hidden_from_opponent() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    opponent = 1 - active

    # Preserve the 30-card partition while forcing a Stratagem into the hand.
    player = session.state.players[active]
    if "the-storm-broke" in player.deck:
        player.deck.remove("the-storm-broke")
        player.hand.append("the-storm-broke")
    elif "the-storm-broke" not in player.hand:
        raise AssertionError("Expected Stratagem in the player's private zones")

    before = session.snapshot(active)
    set_action = next(
        action
        for action in before["legal_actions"]
        if action["kind"] == "SetStratagem"
        and action["card_id"] == "the-storm-broke"
    )
    result = session.act(set_action["key"], active)

    assert result["viewer"] == active
    assert result["active_player"] == active
    assert result["stratagems"][active]["card_id"] == "the-storm-broke"
    assert result["stratagems"][active]["revealed"] is False
    assert any(action["kind"] == "Pass" for action in result["legal_actions"])

    hidden = session.snapshot(opponent)
    assert hidden["stratagems"][active] == {
        "hidden": True,
        "card_id": None,
        "revealed": False,
    }


def test_setting_stratagem_keeps_hotseat_turn_private_to_same_player() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    session.state.players[active].hand = ["the-storm-broke", "the-fifty-men"]

    result = session.act("stratagem:the-storm-broke", active)

    assert result["viewer"] == active
    assert result["active_player"] == active
    assert result["needs_reveal"] is False
    assert result["stratagems"][active]["card_id"] == "the-storm-broke"
    assert result["stratagems"][active]["revealed"] is False
    assert any(action["kind"] == "PlaySubject" for action in result["legal_actions"])

    opponent = session.snapshot(1 - active)
    assert opponent["stratagems"][active]["hidden"] is True
    assert opponent["stratagems"][active]["card_id"] is None


def test_hotseat_draw_action_draws_one_and_moves_turn() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    before_hand = len(session.state.players[active].hand)
    before_deck = len(session.state.players[active].deck)

    snapshot = session.snapshot(active)
    draw = next(action for action in snapshot["legal_actions"] if action["kind"] == "Draw")
    result = session.act(draw["key"], active)

    assert len(session.state.players[active].hand) == before_hand + 1
    assert len(session.state.players[active].deck) == before_deck - 1
    assert session.state.draw_used[active] is True
    assert result["viewer"] is None
    assert result["needs_reveal"] is True
