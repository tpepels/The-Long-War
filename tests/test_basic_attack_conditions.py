"""Paper Attack/condition grammar against the actual native game engine.

Small explicit boards isolate classification, screening, protection, use
limits, Strength and Battle cleanup from card-text compiler parity.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from longwar.game.actions import Attack, BeginTurn, Discard, EndTurn, action_key, action_from_key
from longwar.game.engine import GameEngine, IllegalAction
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def engine():
    return GameEngine.from_file(str(ROOT / "cards" / "cards.json"))


@pytest.fixture(scope="module")
def deck():
    return json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]


def board(engine, deck, seed=918):
    state = engine.new_game(deck, deck, seed=seed, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state) if isinstance(a, Discard)))
    return state


def place(state, player, front, rank, card):
    state.board[player][front][list(Rank).index(rank)].force = card
    return Position(Front(front), rank)


def attack_from(actions, name):
    return [a for a in actions if isinstance(a, Attack) and a.classification == name]


def test_native_python_attack_key_round_trip():
    action = Attack(Position(Front.SECOND, Rank.MIDDLE), Position(Front.SECOND, Rank.REAR), "archer")
    assert action_key(action) == "attack:archer:1:middle:1:rear"
    assert action_from_key(action_key(action)) == action


def test_archer_attack_exhausts_once_and_costs_one_action(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.REAR, "the-crow-archers")
    target = place(s, 1, 1, Rank.REAR, "the-red-shields")
    a = Attack(origin, target, "archer")
    assert a in engine.legal_actions(s)
    assert engine.command_cost_for_action(s, a) == 0
    before = s.players[0].command
    engine.apply(s, a)
    assert s.slot(1, target).exhausted
    assert s.slot(0, origin).used_attack
    assert s.players[0].command == before
    assert s.actions_this_turn == 1
    assert a not in engine.legal_actions(s)
    with pytest.raises(IllegalAction):
        engine.apply(s, a)


def test_guard_screens_archer_unless_empowered(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.REAR, "the-crow-archers")
    target = place(s, 1, 1, Rank.REAR, "the-red-shields")
    place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    a = Attack(origin, target, "archer")
    assert a not in engine.legal_actions(s)
    s.slot(0, origin).empowered = True
    assert a in engine.legal_actions(s)
    engine.apply(s, a)
    assert s.slot(1, target).exhausted
    assert not s.slot(0, origin).empowered
    assert s.slot(0, origin).used_attack


@pytest.mark.parametrize("status", ("shaken", "depleted"))
def test_unhealthy_guard_no_longer_screens(engine, deck, status):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.REAR, "the-crow-archers")
    target = place(s, 1, 1, Rank.REAR, "the-red-shields")
    blocker = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    setattr(s.slot(1, blocker), status, True)
    assert Attack(origin, target, "archer") in engine.legal_actions(s)


def test_skirmisher_shakes_and_inspired_prevents_shaken(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-black-company")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    action = Attack(origin, target, "skirmisher")
    before = engine.position_strength(s, 1, target)
    assert action in engine.legal_actions(s)
    engine.apply(s, action)
    assert s.slot(1, target).shaken
    assert engine.position_strength(s, 1, target) == max(0, before - 2)

    s2 = board(engine, deck, 71)
    o2 = place(s2, 0, 1, Rank.FRONT, "the-black-company")
    t2 = place(s2, 1, 1, Rank.MIDDLE, "the-first-spear")
    s2.slot(1, t2).inspired = True
    engine.apply(s2, Attack(o2, t2, "skirmisher"))
    assert s2.slot(1, t2).inspired
    assert not s2.slot(1, t2).shaken


def test_guarded_blocks_exactly_one_affliction(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-black-company")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    s.slot(1, target).guarded = True
    engine.apply(s, Attack(origin, target, "skirmisher"))
    assert not s.slot(1, target).shaken
    assert not s.slot(1, target).guarded


def test_raider_requires_open_opposing_frontline_and_depletes(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-iron-boars")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    block = place(s, 1, 1, Rank.FRONT, "the-red-shields")
    attack = Attack(origin, target, "raider")
    assert attack not in engine.legal_actions(s)
    s.slot(1, block).force = None
    assert attack in engine.legal_actions(s)
    before = engine.position_strength(s, 1, target)
    engine.apply(s, attack)
    assert s.slot(1, target).depleted
    assert engine.position_strength(s, 1, target) == max(0, before - 1)


def test_depleted_force_cannot_attack(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-black-company")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    s.slot(0, origin).depleted = True
    assert Attack(origin, target, "skirmisher") not in engine.legal_actions(s)


def test_rider_requires_active_adjacent_flanked_frontline(engine, deck):
    s = board(engine, deck)
    rider = place(s, 0, 2, Rank.MIDDLE, "the-grey-riders")
    target = place(s, 1, 1, Rank.FRONT, "the-first-spear")
    a = Attack(rider, target, "rider")
    assert a not in engine.legal_actions(s)  # Third Front is inactive in Battle I
    s.battle = 3
    assert a not in engine.legal_actions(s)  # Middle Rider does not itself create a flank
    place(s, 0, 2, Rank.FRONT, "the-red-shields")  # Adjacent opposing Frontline creates flank
    assert a in engine.legal_actions(s)
    s.slot(1, Position(Front.THIRD, Rank.FRONT)).force = "the-red-shields"
    assert a not in engine.legal_actions(s)
    s.slot(1, Position(Front.THIRD, Rank.FRONT)).force = None
    s.slot(0, rider).force = None
    place(s, 0, 2, Rank.REAR, "the-grey-riders")
    a_rear = Attack(Position(Front.THIRD, Rank.REAR), target, "rider")
    assert a_rear not in engine.legal_actions(s)


def test_attack_status_persists_in_native_copy_and_information_key(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-black-company")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    native = engine._native_core()
    base = native.from_game_state(s)
    before = native.information_key(base, 1)
    s.slot(1, target).guarded = True
    guarded = native.from_game_state(s)
    assert native.information_key(guarded, 1) != before
    assert native.information_key(guarded, 0) != before
    copy = s.clone()
    assert copy.slot(1, target).guarded
    engine.apply(s, Attack(origin, target, "skirmisher"))
    assert not s.slot(1, target).guarded
    assert s.slot(0, origin).used_attack


def test_battle_end_resets_temporary_afflictions_and_attack_use(engine, deck):
    s = board(engine, deck)
    origin = place(s, 0, 1, Rank.FRONT, "the-black-company")
    target = place(s, 1, 1, Rank.MIDDLE, "the-first-spear")
    engine.apply(s, Attack(origin, target, "skirmisher"))
    # End the turn and invoke one voluntary Pass on the opponent's next turn;
    # both closing turns retain their own normal draws.
    engine.apply(s, EndTurn())
    assert s.turn_draw_pending
    from longwar.game.actions import Pass
    engine.apply(s, Pass())
    for _ in range(2):
        assert s.turn_draw_pending
        engine.apply(s, BeginTurn())
        while s.pending_draw_discard_for is not None:
            engine.apply(s, next(a for a in engine.legal_actions(s) if isinstance(a, Discard)))
        engine.apply(s, EndTurn())
    # Battle-end loss Exhaustion is a mandatory player choice, so the Battle
    # may remain in its resolution phase until each lost Front is assigned.
    for _ in range(8):
        if s.battle >= 2 or s.winner is not None:
            break
        choices = [a for a in engine.legal_actions(s)
                   if isinstance(a, EffectChoice)
                   and a.effect == "lost-front-exhaust"]
        assert choices, engine.legal_actions(s)
        engine.apply(s, choices[0])
    assert s.battle >= 2 or s.winner is not None
    if s.winner is None:
        assert not s.slot(0, origin).used_attack
        assert not s.slot(1, target).shaken
