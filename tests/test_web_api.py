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


def test_hotseat_mulligans_are_private_and_then_start_match_with_turn_draw() -> None:
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
    assert len(session.state.players[session.state.active_player].hand) == 11
    assert "draws 1 card at the start of the turn" in session.log[-1]


def test_hotseat_card_action_returns_to_privacy_gate() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player

    snapshot = session.snapshot(active)
    action = next(
        item
        for item in snapshot["legal_actions"]
        if item["kind"] not in {"Pass", "ChooseFirst"}
    )
    result = session.act(action["key"], active)

    assert result["viewer"] is None
    assert result["needs_reveal"] is True
    assert result["hand"] == []


def test_computer_mode_mulligan_then_returns_control_to_human() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="computer", seed=1701)
    assert session.snapshot(0)["phase"] == "mulligan"

    result = session.mulligan([], 0)

    assert result["phase"] == "complete" or result["active_player"] == 0
    if result["phase"] != "complete":
        assert result["viewer"] == 0
        assert result["legal_actions"]


def test_action_payload_exposes_structured_board_targets_and_command_costs() -> None:
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
    assert subject["command_cost"] == 2

    scheme = next(
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlayScheme"
    )
    assert scheme["front"] in (0, 1, 2)
    assert scheme["position"] is None
    assert scheme["command_cost"] == 2


def test_snapshot_exposes_front_control_and_command() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    snapshot = session.snapshot(session.state.active_player)

    assert snapshot["front_control"] == [None, None, None]
    assert snapshot["players"][0]["command"] == 20
    assert snapshot["players"][1]["command"] == 20


def test_stratagem_action_is_paid_and_public_to_opponent() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    opponent = 1 - active

    player = session.state.players[active]
    if "the-storm-broke" in player.deck:
        player.deck.remove("the-storm-broke")
        player.hand.append("the-storm-broke")
    elif "the-storm-broke" not in player.hand:
        raise AssertionError("Expected Stratagem in the player's zones")

    before_command = player.command
    before = session.snapshot(active)
    action = next(
        item
        for item in before["legal_actions"]
        if item["kind"] == "SetStratagem"
        and item["card_id"] == "the-storm-broke"
    )
    result = session.act(action["key"], active)

    assert player.command == before_command - action["command_cost"]
    assert result["viewer"] is None
    assert result["active_player"] == opponent
    assert session.state.stratagems[active].card_id == "the-storm-broke"
    assert session.state.stratagems[active].revealed is True

    public = session.snapshot(opponent)
    assert public["stratagems"][active] == {
        "hidden": False,
        "card_id": "the-storm-broke",
        "revealed": True,
    }
    assert public["last_action"]["card_id"] == "the-storm-broke"


def test_setting_public_stratagem_ends_operation_and_returns_to_privacy_gate() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    session.state.players[active].hand = ["the-storm-broke", "the-fifty-men"]

    result = session.act("stratagem:the-storm-broke", active)

    assert result["viewer"] is None
    assert result["active_player"] == 1 - active
    assert result["needs_reveal"] is True

    opponent = session.snapshot(1 - active)
    assert opponent["stratagems"][active]["hidden"] is False
    assert opponent["stratagems"][active]["card_id"] == "the-storm-broke"


def test_standard_browser_session_has_no_draw_or_cycle_operation() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    snapshot = session.snapshot(active)

    assert not any(
        action["kind"] in {"Draw", "Cycle"}
        for action in snapshot["legal_actions"]
    )


def test_battle_transition_log_handles_fixed_next_starter() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    session.state.operations_this_battle[:] = [1, 1]
    first = session.state.active_player
    second = 1 - first

    first_snapshot = session.snapshot(first)
    first_pass = next(
        action for action in first_snapshot["legal_actions"]
        if action["kind"] == "Pass"
    )
    session.act(first_pass["key"], first)

    second_snapshot = session.snapshot(second)
    second_pass = next(
        action for action in second_snapshot["legal_actions"]
        if action["kind"] == "Pass"
    )
    result = session.act(second_pass["key"], second)

    assert result["battle"] == 2
    assert session.state.active_player == first
    assert session.log[-1] == (
        f"Battle II begins. Player {first + 1} starts."
    )
