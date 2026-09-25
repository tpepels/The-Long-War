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
    active = session.state.active_player
    if session.state.pending_draw_discard_for == active:
        snapshot = session.snapshot(active)
        discard = next(
            action
            for action in snapshot["legal_actions"]
            if action["kind"] == "Discard"
        )
        result = session.act(discard["key"], active)
        assert result["viewer"] == active
        assert session.state.active_player == active
        assert session.state.pending_draw_discard_for is None


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


def test_opening_turn_uses_normal_discard_then_draw_at_hand_limit() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)

    session.mulligan([0, 1], 0)
    session.mulligan([], 1)

    active = session.state.active_player
    assert session.setup_complete is True
    assert len(session.state.players[active].hand) == 10
    assert session.state.pending_draw_discard_for == active

    private = session.snapshot(active)
    assert private["pending_draw_discard_for"] == active
    assert private["legal_actions"]
    assert all(
        action["kind"] == "Discard"
        for action in private["legal_actions"]
    )

    discard = private["legal_actions"][0]
    result = session.act(discard["key"], active)

    assert result["viewer"] == active
    assert result["active_player"] == active
    assert result["pending_draw_discard_for"] is None
    assert len(session.state.players[active].hand) == 10
    assert "start-of-turn draw" in session.log[0]


def test_hotseat_card_operation_returns_to_privacy_gate() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player

    snapshot = session.snapshot(active)
    action = next(
        item
        for item in snapshot["legal_actions"]
        if item["kind"] not in {"Pass", "Discard"}
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


def test_action_payload_uses_canonical_force_and_story_targets() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    session.state.players[active].hand = [
        "the-fifty-men",
        "the-lamps-went-dark",
    ]
    session.state.players[active].command = 20
    snapshot = session.snapshot(active)

    force = next(
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlayForce"
    )
    assert force["position"]["front"] in (0, 1, 2, 3)
    assert force["position"]["rank"] in ("front", "rear")
    assert force["targets"] == []
    assert force["command_cost"] == 2

    stories = [
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlayStory"
        and action["card_id"] == "the-lamps-went-dark"
    ]
    assert stories
    assert {action["ongoing_slot"] for action in stories} <= {0, 1}
    assert 2 not in {action["ongoing_slot"] for action in stories}


def test_snapshot_exposes_four_fronts_command_and_two_story_limit() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    snapshot = session.snapshot(session.state.active_player)

    assert snapshot["front_control"] == [None, None, None, None]
    assert snapshot["players"][0]["command"] == 20
    assert snapshot["players"][1]["command"] == 20
    assert snapshot["story_limit"] == 2
    assert snapshot["stories"] == [[], []]


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
        if item["kind"] == "PlayStratagem"
        and item["card_id"] == "the-storm-broke"
    )
    result = session.act(action["key"], active)

    assert player.command == before_command - action["command_cost"]
    assert result["viewer"] is None
    assert result["active_player"] == opponent
    assert session.state.stratagems[active].card_id == "the-storm-broke"

    public = session.snapshot(opponent)
    assert public["stratagems"][active] == {
        "card_id": "the-storm-broke",
    }
    assert public["last_action"]["card_id"] == "the-storm-broke"


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


def test_first_pass_hands_opponent_a_normal_turn_and_stays_open() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    session.state.operations_this_battle[:] = [1, 1]
    first = session.state.active_player
    second = 1 - first

    if len(session.state.players[second].hand) >= session.engine.hand_limit:
        card = session.state.players[second].hand.pop()
        session.state.players[second].deck.append(card)

    first_snapshot = session.snapshot(first)
    first_pass = next(
        action
        for action in first_snapshot["legal_actions"]
        if action["kind"] == "Pass"
    )
    result = session.act(first_pass["key"], first)

    assert result["battle"] == 1
    assert session.state.active_player == second
    assert session.state.pass_order == [first]
    assert session.state.players[first].passed is True
    assert session.state.players[second].passed is False


def test_intervening_operation_clears_pass_in_browser_state() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    first = session.state.active_player
    second = 1 - first
    session.state.operations_this_battle[:] = [1, 1]
    session.state.players[second].hand = ["the-fifty-men"]
    session.state.players[second].deck = ["followed"]
    session.state.players[second].command = 20

    first_pass = next(
        action
        for action in session.snapshot(first)["legal_actions"]
        if action["kind"] == "Pass"
    )
    session.act(first_pass["key"], first)

    second_view = session.snapshot(second)
    force = next(
        action
        for action in second_view["legal_actions"]
        if action["kind"] == "PlayForce"
        and action["card_id"] == "the-fifty-men"
    )
    session.act(force["key"], second)

    assert session.state.battle == 1
    assert session.state.pass_order == []
    assert not session.state.players[0].passed
    assert not session.state.players[1].passed


def test_two_consecutive_passes_end_battle_and_first_passer_starts_next() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    session.state.operations_this_battle[:] = [1, 1]
    first = session.state.active_player
    second = 1 - first

    if len(session.state.players[second].hand) >= session.engine.hand_limit:
        card = session.state.players[second].hand.pop()
        session.state.players[second].deck.append(card)

    first_pass = next(
        action
        for action in session.snapshot(first)["legal_actions"]
        if action["kind"] == "Pass"
    )
    session.act(first_pass["key"], first)

    second_pass = next(
        action
        for action in session.snapshot(second)["legal_actions"]
        if action["kind"] == "Pass"
    )
    result = session.act(second_pass["key"], second)

    assert result["battle"] == 2
    assert session.state.active_player == first
    assert session.state.pass_order == []
    assert session.log[-1] == (
        f"Battle II begins. Player {first + 1} starts."
    )
