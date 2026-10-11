"""Printed forced rearward moves: successful displacement and blocked afflictions."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank, front=Front.SECOND):
    return Position(front, rank)


def start(game, tactic, support="the-lantern-scouts"):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=77, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    state.players[0].hand[:] = [tactic]
    state.players[0].command = 20
    state.slot(0, at(Rank.REAR)).force = support
    state.slot(1, at(Rank.FRONT)).force = "the-fifty-men"
    return engine, state


def plays(engine, state, tactic, rank=Rank.FRONT):
    return [a for a in engine.legal_actions(state)
            if isinstance(a, PlayTactic) and a.card_id == tactic
            and a.target is not None and a.target.position == at(rank)]


def test_had_gone_too_far_moves_target_to_middle_when_empty(game):
    engine, state = start(game, "they-had-gone-too-far")
    actions = plays(engine, state, "they-had-gone-too-far")
    assert actions
    engine.apply(state, actions[0])
    assert state.slot(1, at(Rank.FRONT)).force is None
    moved = state.slot(1, at(Rank.MIDDLE))
    assert moved.force == "the-fifty-men"
    assert not moved.shaken


def test_had_gone_too_far_gives_shaken_only_when_destination_blocked(game):
    engine, state = start(game, "they-had-gone-too-far")
    state.slot(1, at(Rank.MIDDLE)).force = "the-fifty-men"
    engine.apply(state, plays(engine, state, "they-had-gone-too-far")[0])
    target = state.slot(1, at(Rank.FRONT))
    assert target.force == "the-fifty-men"
    assert target.shaken


def test_had_gone_too_far_obeys_opponent_bond_move_resistance(game):
    engine, state = start(game, "they-had-gone-too-far")
    state.slot(1, at(Rank.FRONT)).bond = "blocked-the-road-for"
    engine.apply(state, plays(engine, state, "they-had-gone-too-far")[0])
    assert state.slot(1, at(Rank.FRONT)).force == "the-fifty-men"
    assert state.slot(1, at(Rank.FRONT)).shaken
    assert state.slot(1, at(Rank.MIDDLE)).force is None


def test_had_gone_too_far_guarded_prevents_fallback_affliction(game):
    engine, state = start(game, "they-had-gone-too-far")
    state.slot(1, at(Rank.MIDDLE)).force = "the-fifty-men"
    state.slot(1, at(Rank.FRONT)).guarded = True
    engine.apply(state, plays(engine, state, "they-had-gone-too-far")[0])
    assert not state.slot(1, at(Rank.FRONT)).shaken
    assert not state.slot(1, at(Rank.FRONT)).guarded


@pytest.mark.parametrize("blocked", (False, True))
def test_line_was_baited_depletes_only_if_forced_move_succeeded(game, blocked):
    engine, state = start(game, "the-line-was-baited", support="the-ash-bowmen")
    if blocked:
        state.slot(1, at(Rank.MIDDLE)).force = "the-fifty-men"
    actions = plays(engine, state, "the-line-was-baited")
    assert actions
    engine.apply(state, actions[0])
    if blocked:
        assert state.slot(1, at(Rank.FRONT)).force == "the-fifty-men"
        assert not state.slot(1, at(Rank.FRONT)).depleted
    else:
        moved = state.slot(1, at(Rank.MIDDLE))
        assert moved.force == "the-fifty-men"
        assert moved.depleted


def test_tactics_require_friendly_class_here_and_cannot_target_rear(game):
    engine, state = start(game, "they-had-gone-too-far")
    state.slot(0, at(Rank.REAR)).force = None
    state.slot(0, at(Rank.REAR, front=Front.THIRD)).force = "the-lantern-scouts"
    assert not plays(engine, state, "they-had-gone-too-far")
    state.slot(0, at(Rank.REAR)).force = "the-lantern-scouts"
    state.slot(1, at(Rank.FRONT)).force = None
    state.slot(1, at(Rank.REAR)).force = "the-fifty-men"
    assert not [a for a in engine.legal_actions(state)
                if isinstance(a, PlayTactic) and a.card_id == "they-had-gone-too-far"]
