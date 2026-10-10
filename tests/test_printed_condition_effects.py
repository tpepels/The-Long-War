"""Exact physical effect text and functional native status cards."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from longwar.game.actions import (
    BeginTurn, EffectChoice, PlayBond, PlayForce, PlayTactic, Attack, Discard
)
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank
from longwar.physical_effects import PRINTED_EFFECTS, PRINTED_EXECUTABLE_EFFECTS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from print_cards import load_print_cards  # noqa: E402


@pytest.fixture(scope="module")
def engine():
    return GameEngine.from_file(str(ROOT / "cards" / "cards.json"))


@pytest.fixture(scope="module")
def deck():
    return json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]


def setup(engine, deck, own_card, front=1):
    state = engine.new_game(deck, deck, seed=209, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state) if isinstance(a, Discard)))
    state.players[0].hand[:] = [own_card]
    state.players[0].command = 20
    return state


def pos(front, rank):
    return Position(Front(front), rank)


def test_reviewed_effect_specs_identical_to_current_physical_text():
    source = json.loads((ROOT / "cards" / "cards.json").read_text())
    by_id = {c["id"]: c for c in load_print_cards(base=source)["cards"]}
    assert len(PRINTED_EFFECTS) == 8
    for cid, effects in PRINTED_EFFECTS.items():
        assert effects == by_id[cid]["effects"]
        assert len(effects) == len(PRINTED_EXECUTABLE_EFFECTS[cid])


def test_crow_archers_play_empowers_and_attack_extends_to_middle(engine, deck):
    state = setup(engine, deck, "the-crow-archers")
    src = pos(1, Rank.REAR)
    middle = pos(1, Rank.MIDDLE)
    state.slot(1, middle).force = "the-fifty-men"
    engine.apply(state, PlayForce("the-crow-archers", src))
    assert state.slot(0, src).empowered
    a = Attack(src, middle, "archer")
    assert a in engine.legal_actions(state)
    state.slot(1, pos(1, Rank.FRONT)).force = "the-first-spear"
    assert a not in engine.legal_actions(state)


def test_old_guard_screens_while_shaken_but_not_depleted(engine, deck):
    s = setup(engine, deck, "the-fifty-men")
    src, mid, rear = pos(1, Rank.REAR), pos(1, Rank.MIDDLE), pos(1, Rank.REAR)
    s.slot(0, src).force = "the-crow-archers"
    s.slot(1, mid).force = "the-old-guard"
    s.slot(1, rear).force = "the-fifty-men"
    s.slot(1, mid).shaken = True
    a = Attack(src, rear, "archer")
    assert a not in engine.legal_actions(s)
    s.slot(1, mid).depleted = True
    assert a in engine.legal_actions(s)


@pytest.mark.parametrize(
    "card,benefit,clears_shaken",
    [
        ("guarded", "guarded", False),
        ("endured-with", "inspired", True),
    ],
)
def test_prepared_bond_can_grant_boon_to_another_force(
    engine, deck, card, benefit, clears_shaken
):
    s = setup(engine, deck, card)
    s.slot(0, pos(1, Rank.FRONT)).force = "the-fifty-men"
    s.slot(0, pos(1, Rank.FRONT)).shaken = True
    engine.apply(s, PlayBond(card, pos(1, Rank.REAR)))
    choices = [a for a in engine.legal_actions(s) if isinstance(a, EffectChoice)]
    assert choices, engine.legal_actions(s)
    assert any(a.destination and a.destination.position == pos(1, Rank.FRONT) for a in choices)
    engine.apply(s, next(a for a in choices if a.destination and a.destination.position == pos(1, Rank.FRONT)))
    assert getattr(s.slot(0, pos(1, Rank.FRONT)), benefit)
    assert s.slot(0, pos(1, Rank.FRONT)).shaken is (not clears_shaken)


@pytest.mark.parametrize(
    "card,target,condition",
    [
        ("the-red-duelists", pos(1, Rank.FRONT), "shaken"),
        ("the-iron-boars", pos(1, Rank.MIDDLE), "depleted"),
    ],
)
def test_attack_force_play_effect_afflicts_printed_target(engine, deck, card, target, condition):
    s = setup(engine, deck, card)
    s.slot(1, target).force = "the-fifty-men"
    src = pos(1, Rank.FRONT)
    engine.apply(s, PlayForce(card, src))
    choices = [a for a in engine.legal_actions(s) if isinstance(a, EffectChoice)]
    assert choices
    engine.apply(s, next(a for a in choices if a.destination and a.destination.position == target))
    assert getattr(s.slot(1, target), condition)


def test_first_spear_grants_guarded_directly_behind(engine, deck):
    s = setup(engine, deck, "the-first-spear")
    behind = pos(1, Rank.MIDDLE)
    s.slot(0, behind).force = "the-fifty-men"
    engine.apply(s, PlayForce("the-first-spear", pos(1, Rank.FRONT)))
    choices = [a for a in engine.legal_actions(s) if isinstance(a, EffectChoice)]
    assert choices
    engine.apply(s, choices[0])
    assert s.slot(0, behind).guarded


def test_baggage_affliction_order_consumes_guarded_before_shaken(engine, deck):
    s = setup(engine, deck, "the-baggage-was-abandoned")
    target = pos(1, Rank.REAR)
    s.slot(1, target).force = "the-fifty-men"
    s.slot(1, target).guarded = True
    engine.apply(s, next(a for a in engine.legal_actions(s) if isinstance(a, PlayTactic) and a.card_id == "the-baggage-was-abandoned" and a.target is not None and a.target.position == target))
    assert not s.slot(1, target).guarded
    assert not s.slot(1, target).exhausted
    assert s.slot(1, target).shaken
