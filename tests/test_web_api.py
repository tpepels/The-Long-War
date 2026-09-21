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
