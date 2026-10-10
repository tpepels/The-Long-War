"""Behavioral checks for the reviewed physical effect pass.

Every assertion is grounded in a named physical effect and deliberately checks
a transition or Strength result, not only matching text.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayForce, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, NarrativeState, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(front: int, rank: Rank):
    return Position(Front(front), rank)


def new_turn(game, card: str):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=93, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        choices = [a for a in engine.legal_actions(state) if isinstance(a, Discard)]
        assert choices
        engine.apply(state, choices[0])
    state.players[0].hand[:] = [card]
    state.players[0].command = 20
    return engine, state


def test_thornbow_rear_aura_raises_only_other_archers_in_same_front(game):
    engine, state = new_turn(game, "the-thornbow-hunters")
    hunter = at(1, Rank.REAR)
    archer = at(1, Rank.MIDDLE)
    unrelated = at(2, Rank.MIDDLE)
    state.slot(0, archer).force = "the-crow-archers"
    state.slot(0, unrelated).force = "the-crow-archers"
    before = engine.position_strength(state, 0, archer)
    unrelated_before = engine.position_strength(state, 0, unrelated)
    state.slot(0, hunter).force = "the-thornbow-hunters"
    assert engine.position_strength(state, 0, archer) == before + 1
    assert engine.position_strength(state, 0, unrelated) == unrelated_before
    state.slot(0, hunter).force = None
    assert engine.position_strength(state, 0, archer) == before


def test_battle_chose_them_counts_named_hero_only_once(game):
    engine, state = new_turn(game, "the-battle-had-chosen-them")
    source = at(1, Rank.FRONT)
    ordinary = at(1, Rank.MIDDLE)
    state.slot(0, source).force = "avaros-the-bronze-king"
    state.slot(0, source).bond = "guarded"
    state.slot(0, source).name = "mara"
    state.slot(0, ordinary).force = "the-fifty-men"
    before = engine.position_strength(state, 0, source)
    other_before = engine.position_strength(state, 0, ordinary)
    state.narratives[0].append(NarrativeState("the-battle-had-chosen-them"))
    assert engine.position_strength(state, 0, source) == before + 1
    assert engine.position_strength(state, 0, ordinary) == other_before


def test_unnamed_host_drains_only_one_command_without_collapse(game):
    engine, state = new_turn(game, "the-unnamed-host")
    place = at(1, Rank.FRONT)
    target = at(1, Rank.MIDDLE)
    state.slot(1, target).force = "the-fifty-men"
    state.slot(1, target).exhausted = True
    state.players[1].command = 2
    action = PlayForce("the-unnamed-host", place)
    assert action in engine.legal_actions(state)
    engine.apply(state, action)
    assert state.players[1].command == 1
    assert state.players[0].command == 20 - engine.cards["the-unnamed-host"]["command_cost"] + 1


def test_volley_red_strength_marker_lowers_target_exactly_two(game):
    engine, state = new_turn(game, "a-volley-before-dawn")
    target = at(1, Rank.REAR)
    state.slot(0, at(1, Rank.MIDDLE)).force = "the-crow-archers"
    state.slot(1, target).force = "the-fifty-men"
    before = engine.position_strength(state, 1, target)
    choices = [a for a in engine.legal_actions(state)
               if isinstance(a, PlayTactic) and a.card_id == "a-volley-before-dawn"
               and a.target is not None and a.target.position == target]
    assert choices
    engine.apply(state, choices[0])
    assert engine.position_strength(state, 1, target) == max(0, before - 2)


def test_salt_road_fleet_moves_other_force_toward_rear(game):
    engine, state = new_turn(game, "the-salt-road-fleet")
    other = at(1, Rank.FRONT)
    middle = at(1, Rank.MIDDLE)
    state.slot(0, other).force = "the-fifty-men"
    play = PlayForce("the-salt-road-fleet", at(1, Rank.REAR))
    assert play in engine.legal_actions(state)
    engine.apply(state, play)
    choices = [a for a in engine.legal_actions(state)
               if isinstance(a, EffectChoice)
               and a.destination is not None and a.destination.position == other]
    assert choices, engine.legal_actions(state)
    engine.apply(state, choices[0])
    assert state.slot(0, other).force is None
    assert state.slot(0, middle).force == "the-fifty-men"
