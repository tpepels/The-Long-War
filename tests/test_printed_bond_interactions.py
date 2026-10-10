"""Physical Bond protection and Bond-only removal in the real native engine."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayBond, PlayForce
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    e = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return e, deck


def p(rank):
    return Position(Front.SECOND, rank)


def turn(game, active_player, card):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=292, first_player=active_player)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state) if isinstance(a, Discard)))
    state.players[active_player].hand[:] = [card]
    state.players[active_player].command = 20
    return engine, state


def test_seized_standard_returns_only_enemy_bond_not_name(game):
    e, s = turn(game, 0, "seized-the-standard-of")
    s.slot(0, p(Rank.FRONT)).force = "the-fifty-men"
    s.slot(1, p(Rank.MIDDLE)).force = "the-fifty-men"
    s.slot(1, p(Rank.MIDDLE)).bond = "guarded"
    s.slot(1, p(Rank.MIDDLE)).name = "mara"
    action = PlayBond("seized-the-standard-of", p(Rank.FRONT))
    assert action in e.legal_actions(s)
    e.apply(s, action)
    choices = [a for a in e.legal_actions(s) if isinstance(a, EffectChoice) and not a.skip]
    assert len(choices) == 1, choices
    assert choices[0].destination is not None
    assert choices[0].destination.position == p(Rank.MIDDLE)
    assert choices[0].option == "bond"
    e.apply(s, choices[0])
    assert s.slot(1, p(Rank.MIDDLE)).bond is None
    assert s.slot(1, p(Rank.MIDDLE)).name == "mara"
    assert "guarded" in s.players[1].hand


@pytest.mark.parametrize("protected", (False, True))
def test_opposing_move_cannot_shift_roadblock_bonded_formation(game, protected):
    e, s = turn(game, 1, "the-ash-bowmen")
    s.slot(0, p(Rank.FRONT)).force = "the-fifty-men"
    if protected:
        s.slot(0, p(Rank.FRONT)).bond = "blocked-the-road-for"
    a = PlayForce("the-ash-bowmen", p(Rank.REAR))
    assert a in e.legal_actions(s)
    e.apply(s, a)
    choices = [a for a in e.legal_actions(s)
               if isinstance(a, EffectChoice)
               and a.destination is not None
               and a.destination.position == p(Rank.FRONT)]
    if protected:
        assert not choices, choices
        assert s.slot(0, p(Rank.FRONT)).force == "the-fifty-men"
    else:
        assert choices, e.legal_actions(s)
        e.apply(s, choices[0])
        assert s.slot(0, p(Rank.MIDDLE)).force == "the-fifty-men"


def test_self_controlled_card_move_still_legal_with_roadblock(game):
    e, s = turn(game, 0, "the-damar")
    s.slot(0, p(Rank.MIDDLE)).force = "the-fifty-men"
    s.slot(0, p(Rank.MIDDLE)).bond = "blocked-the-road-for"
    e.apply(s, PlayForce("the-damar", p(Rank.REAR)))
    choices = [a for a in e.legal_actions(s) if isinstance(a, EffectChoice)
               and a.destination is not None
               and a.destination.position == p(Rank.MIDDLE)]
    assert choices
    e.apply(s, choices[0])
    assert s.slot(0, p(Rank.FRONT)).bond == "blocked-the-road-for"
