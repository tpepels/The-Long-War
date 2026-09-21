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


def test_hotseat_snapshot_hides_hand_until_revealed() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)

    public = session.snapshot(None)
    assert public["needs_reveal"] is True
    assert public["hand"] == []
    assert public["legal_actions"] == []

    active = public["active_player"]
    private = session.snapshot(active)
    assert len(private["hand"]) == 10
    assert any(action["key"] == "pass" for action in private["legal_actions"])


def test_hotseat_action_returns_to_privacy_gate() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    active = session.state.active_player

    result = session.act("pass", active)

    assert result["viewer"] is None
    assert result["needs_reveal"] is True
    assert result["hand"] == []


def test_heuristic_mode_returns_control_to_human() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="heuristic", seed=1701)

    assert session.state.phase.value == "complete" or session.state.active_player == 0
    snapshot = session.snapshot(0)
    if snapshot["phase"] != "complete":
        assert snapshot["viewer"] == 0
        assert snapshot["legal_actions"]
