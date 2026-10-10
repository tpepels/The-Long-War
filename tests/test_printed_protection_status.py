"""Printed cleanser, Guarded screen, conditional Scout affliction, Bond exchange."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayForce, PlayNarrative, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    e = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    d = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return e, d


def pos(front, rank):
    return Position(Front(front), rank)


def start(game, card):
    e, d = game
    s = e.new_game(d, d, seed=211, first_player=0)
    e.apply(s, BeginTurn())
    while s.pending_draw_discard_for is not None:
        e.apply(s, next(a for a in e.legal_actions(s) if isinstance(a, Discard)))
    s.players[0].hand[:] = [card]
    s.players[0].command = 20
    return e, s


def choice(e, s, destination):
    matches = [a for a in e.legal_actions(s)
               if isinstance(a, EffectChoice) and a.destination is not None
               and a.destination.position == destination]
    assert matches, e.legal_actions(s)
    return matches[0]


def narrative(e, s, cid):
    return next(a for a in e.legal_actions(s)
                if isinstance(a, PlayNarrative) and a.card_id == cid)


def test_relief_column_cleans_all_temporary_negative_conditions_and_guards(game):
    e, s = start(game, "the-relief-column")
    target = pos(1, Rank.FRONT)
    s.slot(0, target).force = "the-fifty-men"
    s.slot(0, target).exhausted = True
    s.slot(0, target).shaken = True
    s.slot(0, target).depleted = True
    e.apply(s, PlayForce("the-relief-column", pos(1, Rank.MIDDLE)))
    e.apply(s, choice(e, s, target))
    slot = s.slot(0, target)
    assert not slot.exhausted and not slot.shaken and not slot.depleted
    assert slot.guarded


@pytest.mark.parametrize("prior_exhaustion,expected_shaken", [(False,False),(True,True)])
def test_scout_tactic_shakes_if_exhausted_otherwise_exhausts(game,prior_exhaustion,expected_shaken):
    e, s = start(game, "they-were-gathering-there")
    s.slot(0, pos(1,Rank.REAR)).force = "the-lantern-scouts"
    target = pos(1,Rank.FRONT)
    s.slot(1,target).force = "the-fifty-men"
    s.slot(1,target).exhausted = prior_exhaustion
    action = next(a for a in e.legal_actions(s)
                  if isinstance(a,PlayTactic)
                  and a.card_id == "they-were-gathering-there"
                  and a.target is not None and a.target.position == target)
    e.apply(s,action)
    assert s.slot(1,target).exhausted
    assert s.slot(1,target).shaken is expected_shaken


def test_wall_narrative_guards_and_grants_rear_strength_only_behind_middle_guard(game):
    e, s = start(game, "the-wall-did-not-break")
    guard = pos(1,Rank.MIDDLE)
    rear = pos(1,Rank.REAR)
    s.slot(0,guard).force = "the-old-guard"
    s.slot(0,rear).force = "the-fifty-men"
    before = e.position_strength(s,0,rear)
    e.apply(s,narrative(e,s,"the-wall-did-not-break"))
    assert e.position_strength(s,0,rear) == before + 1
    e.apply(s,choice(e,s,guard))
    assert s.slot(0,guard).guarded


def test_king_exchanges_bonds_and_rewards_formations_still_named(game):
    e, s = start(game, "the-king-had-given-the-order")
    first = pos(1,Rank.FRONT)
    second = pos(2,Rank.FRONT)
    s.slot(0,first).force = "the-fifty-men"
    s.slot(0,first).bond = "guarded"
    s.slot(0,first).name = "mara"
    s.slot(0,second).force = "the-fifty-men"
    s.slot(0,second).bond = "endured-with"
    s.slot(0,second).name = "eira"
    b0 = e.position_strength(s,0,first)
    b1 = e.position_strength(s,0,second)
    e.apply(s,narrative(e,s,"the-king-had-given-the-order"))
    options = [a for a in e.legal_actions(s)
               if isinstance(a,EffectChoice) and a.source is not None
               and a.destination is not None]
    assert options
    e.apply(s,options[0])
    assert s.slot(0,first).bond == "endured-with"
    assert s.slot(0,second).bond == "guarded"
    assert e.position_strength(s,0,first) == b0 + 1
    assert e.position_strength(s,0,second) == b1 + 1
