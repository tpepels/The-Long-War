"""Reactive hidden Scout Stratagem: private look, selected Guarded recipient.

The trigger occurs when an opposing Stratagem is SET, not during the later
Battle comparison. Native pending choices may not spend the responder's Action.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayStratagem
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
HERE = Front.SECOND


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank=Rank.FRONT):
    return Position(HERE, rank)


def setup(game, *, defender_card="the-scouts-had-warned-them",
          scout=True, assigned_front=HERE, attacker_front=HERE):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=101, first_player=1)
    if defender_card is not None:
        state.stratagems[0] = StratagemState(
            defender_card, fronts=(assigned_front,)
        )
    state.slot(0, at()).force = "the-lantern-scouts" if scout else "the-fifty-men"
    state.slot(0, at(Rank.MIDDLE)).force = "the-fifty-men"
    state.players[1].hand[:] = ["the-center-must-hold"]
    state.players[1].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    plays = [a for a in engine.legal_actions(state)
             if isinstance(a, PlayStratagem)
             and a.card_id == "the-center-must-hold"
             and a.fronts == (attacker_front,)]
    assert plays
    engine.apply(state, plays[0])
    return engine, state


def effects(engine, state, name):
    return [a for a in engine.legal_actions(state)
            if isinstance(a, EffectChoice) and a.effect == name]


def test_reactive_scout_can_decline_without_revealing_hidden_identity(game):
    engine, state = setup(game)
    choices = effects(engine, state, "stratagem-scout-reveal")
    assert len(choices) == 2
    assert {a.skip for a in choices} == {True, False}
    assert not state.stratagems[0].revealed
    assert state.stratagems[1].known_to_mask & 1 == 0
    before = state.operations_this_battle[0]

    engine.apply(state, next(a for a in choices if a.skip))
    assert state.stratagems[0].card_id == "the-scouts-had-warned-them"
    assert not state.stratagems[0].revealed
    assert state.operations_this_battle[0] == before
    assert not state.slot(0, at()).guarded


def test_scout_reveals_inspects_new_plan_then_guards_chosen_force(game):
    engine, state = setup(game)
    before = state.operations_this_battle[0]
    reveal = next(a for a in effects(engine, state, "stratagem-scout-reveal")
                  if not a.skip)
    engine.apply(state, reveal)

    assert state.stratagems[1].known_to_mask & 1
    assert state.stratagems[0].revealed
    choices = effects(engine, state, "stratagem-scout-guard")
    assert len(choices) == 2
    assert not any(a.skip for a in choices)
    target = next(a for a in choices
                  if a.source is not None and a.source.position == at(Rank.MIDDLE))
    engine.apply(state, target)

    assert state.slot(0, at(Rank.MIDDLE)).guarded
    assert not state.slot(0, at()).guarded
    assert state.stratagems[0] is None
    assert "the-scouts-had-warned-them" in state.players[0].discard
    assert state.stratagems[1].card_id == "the-center-must-hold"
    assert state.operations_this_battle[0] == before


@pytest.mark.parametrize("kwargs", [
    {"scout": False},
    {"assigned_front": Front.THIRD},
    {"defender_card": "the-flank-was-refused"},
])
def test_ineligible_face_down_plan_receives_only_private_decline(game, kwargs):
    engine, state = setup(game, **kwargs)
    decisions = effects(engine, state, "stratagem-scout-reveal")
    assert len(decisions) == 1
    assert decisions[0].skip
    engine.apply(state, decisions[0])
    assert not state.stratagems[0].revealed
    assert not state.stratagems[1].known_to_mask & 1


def test_no_hidden_defensive_plan_requires_no_reaction_choice(game):
    engine, state = setup(game, defender_card=None)
    assert not effects(engine, state, "stratagem-scout-reveal")
