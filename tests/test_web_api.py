from __future__ import annotations

import json

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.agents.heuristic_agent import HeuristicAgent
from longwar.agents.ismcts_agent import (
    DEFAULT_ISMCTS_BELIEF_SAMPLES,
    DEFAULT_ISMCTS_ITERATIONS,
    DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH,
    ISMCTSAgent,
)
from longwar.web_api import PlaySession

ROOT = Path(__file__).resolve().parents[1]


def payloads() -> tuple[str, str]:
    cards = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
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


def test_browser_computer_ai_profiles_use_real_production_agents() -> None:
    card_json, deck_json = payloads()

    tactical = PlaySession(
        card_json,
        deck_json,
        mode="computer",
        seed=1701,
        ai_kind="tactical",
    )
    assert isinstance(tactical.agents[1], HeuristicAgent)
    assert tactical.snapshot(0)["ai_kind"] == "tactical"

    canonical = PlaySession(
        card_json,
        deck_json,
        mode="computer",
        seed=1701,
        ai_kind="canonical",
    )
    agent = canonical.agents[1]
    assert isinstance(agent, ISMCTSAgent)
    assert agent.iterations == DEFAULT_ISMCTS_ITERATIONS
    assert agent.belief_samples == DEFAULT_ISMCTS_BELIEF_SAMPLES
    assert agent.belief.diagnostics(canonical.state, 1).prior_type == "HypothesisDeckPrior"
    assert (
        agent.post_battle_rollout_depth
        == DEFAULT_ISMCTS_POST_BATTLE_ROLLOUT_DEPTH
    )
    assert canonical.snapshot(0)["ai_kind"] == "canonical"


def test_computer_mode_rejects_unknown_ai_profile() -> None:
    card_json, deck_json = payloads()
    with pytest.raises(ValueError, match="Unsupported AI kind"):
        PlaySession(
            card_json,
            deck_json,
            mode="computer",
            seed=1701,
            ai_kind="not-an-agent",
        )


def test_computer_mode_mulligan_then_returns_control_to_human() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="computer", seed=1701)
    assert session.snapshot(0)["phase"] == "mulligan"

    result = session.mulligan([], 0)

    assert result["phase"] == "complete" or result["active_player"] == 0
    if result["phase"] != "complete":
        assert result["viewer"] == 0
        assert result["legal_actions"]


def test_action_payload_uses_canonical_force_and_narrative_targets() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    session.state.players[active].hand = [
        "the-fifty-men",
        "the-long-march",
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

    narratives = [
        action
        for action in snapshot["legal_actions"]
        if action["kind"] == "PlayNarrative"
        and action["card_id"] == "the-long-march"
    ]
    assert narratives
    assert {action["ongoing_slot"] for action in narratives} <= {0, 1}
    assert 2 not in {action["ongoing_slot"] for action in narratives}


def test_snapshot_exposes_four_fronts_command_and_two_narrative_limit() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    snapshot = session.snapshot(session.state.active_player)

    assert snapshot["front_control"] == [None, None, None, None]
    assert snapshot["players"][0]["command"] == 20
    assert snapshot["players"][1]["command"] == 20
    assert snapshot["narrative_limit"] == 2
    assert snapshot["narratives"] == [[], []]


def test_stratagem_action_is_paid_and_hidden_from_opponent() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    opponent = 1 - active

    player = session.state.players[active]
    stratagem_id = "the-ground-was-held"
    player.hand = [stratagem_id]
    player.command = 20
    session.state.pending_draw_discard_for = None

    before_command = player.command
    before = session.snapshot(active)
    action = next(
        item
        for item in before["legal_actions"]
        if item["kind"] == "PlayStratagem"
        and item["card_id"] == stratagem_id
    )
    result = session.act(action["key"], active)

    assert player.command == before_command - action["command_cost"]
    assert result["viewer"] is None
    assert result["active_player"] == active
    assert result["actions_this_turn"] == 1
    assert session.state.stratagems[active].card_id == stratagem_id

    owner_view = session.snapshot(active)
    assert owner_view["stratagems"][active]["card_id"] == stratagem_id
    assert owner_view["stratagems"][active]["hidden"] is True

    opponent_view = session.snapshot(opponent)
    assert opponent_view["stratagems"][active]["card_id"] is None
    assert opponent_view["stratagems"][active]["hidden"] is True
    assert opponent_view["stratagems"][active]["revealed"] is False
    assert opponent_view["last_action"]["card_id"] is None
    assert opponent_view["last_action"]["hidden"] is True

def test_standard_browser_session_exposes_cycle_and_endturn_but_no_draw_action() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)
    active = session.state.active_player
    snapshot = session.snapshot(active)

    kinds = {action["kind"] for action in snapshot["legal_actions"]}
    assert "Draw" not in kinds
    assert "Cycle" in kinds
    assert "EndTurn" in kinds
    assert "Pass" not in kinds

def test_forced_pass_hands_opponent_first_closing_turn_and_draws() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    first = session.state.active_player
    second = 1 - first
    session.state.players[first].hand.clear()

    if len(session.state.players[second].hand) >= session.engine.hand_limit:
        card = session.state.players[second].hand.pop()
        session.state.players[second].deck.append(card)
    before_drawn = session.state.cards_drawn_this_battle[second]

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
    assert session.state.closing_turns_remaining == 2
    assert session.state.cards_drawn_this_battle[second] == before_drawn + 1

def test_action_during_closing_keeps_single_passer_and_countdown() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    first = session.state.active_player
    second = 1 - first
    session.state.players[first].hand.clear()
    session.state.players[second].hand = ["the-fifty-men"]
    session.state.players[second].deck = []
    session.state.players[second].discard = []
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
    assert session.state.active_player == second
    assert session.state.actions_this_turn == 1
    assert session.state.closing_turns_remaining == 2
    assert session.state.pass_order == [first]
    assert session.state.players[first].passed is True
    assert session.state.players[second].passed is False

def test_two_closing_endturns_end_battle_and_non_passer_starts_next() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="hotseat", seed=1701)
    finish_hotseat_mulligan(session)

    first = session.state.active_player
    second = 1 - first
    session.state.players[first].hand.clear()

    first_pass = next(
        action
        for action in session.snapshot(first)["legal_actions"]
        if action["kind"] == "Pass"
    )
    session.act(first_pass["key"], first)

    second_end = next(
        action
        for action in session.snapshot(second)["legal_actions"]
        if action["kind"] == "EndTurn"
    )
    session.act(second_end["key"], second)

    first_end = next(
        action
        for action in session.snapshot(first)["legal_actions"]
        if action["kind"] == "EndTurn"
    )
    result = session.act(first_end["key"], first)

    assert result["battle"] == 2
    assert session.state.active_player == second
    assert session.state.pass_order == []
    assert session.log[-1] == (
        f"Battle II begins. Player {second + 1} starts."
    )

def test_remote_mode_keeps_each_players_own_hand_private_but_visible() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="remote", seed=1701)
    p0 = session.snapshot(0)
    p1 = session.snapshot(1)

    assert p0["mode"] == "remote"
    assert p1["mode"] == "remote"
    assert p0["needs_reveal"] is False
    assert p1["needs_reveal"] is False
    assert p0["viewer"] == 0
    assert p1["viewer"] == 1

    # During the opening mulligan only the current mulligan player sees cards.
    assert p0["hand"]
    assert p1["hand"] == []

    session.mulligan([], 0)
    p0_waiting = session.snapshot(0)
    p1_turn = session.snapshot(1)
    assert p0_waiting["hand"] == []
    assert p1_turn["hand"]

    session.mulligan([], 1)
    p0 = session.snapshot(0)
    p1 = session.snapshot(1)

    # After setup both players keep seeing their own hand. Only the active
    # player receives legal actions.
    assert p0["hand"]
    assert p1["hand"]
    active = session.state.active_player
    assert bool(p0["legal_actions"]) == (active == 0)
    assert bool(p1["legal_actions"]) == (active == 1)


def test_remote_mode_has_no_ai_step() -> None:
    card_json, deck_json = payloads()
    session = PlaySession(card_json, deck_json, mode="remote", seed=1701)
    session.mulligan([], 0)
    session.mulligan([], 1)
    with pytest.raises(ValueError, match="AI opponent"):
        session.ai_step()
