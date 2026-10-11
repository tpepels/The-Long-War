"""Printed The Lines Held: conditional hidden resolution-time reinforcement."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, EndTurn, Pass
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
HERE, ELSEWHERE = Front.SECOND, Front.THIRD


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank=Rank.MIDDLE, front=HERE):
    return Position(front, rank)


def setup(game, *, plan_front=HERE, middle_force="the-fifty-men"):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=844, first_player=0)
    if middle_force is not None:
        state.slot(0, at()).force = middle_force
    state.stratagems[0] = StratagemState("the-lines-held", fronts=(plan_front,))
    return engine, state


def resolve(engine, state):
    # A Pass, then both mandatory closing turns; complete all private
    # ineligible-Stratagem declines and any post-comparison Exhaustion picks.
    assert Pass() in engine.legal_actions(state)
    engine.apply(state, Pass())
    for _ in range(2):
        engine.apply(state, BeginTurn())
        while state.pending_draw_discard_for is not None:
            engine.apply(state, next(a for a in engine.legal_actions(state)
                                     if isinstance(a, Discard)))
        engine.apply(state, EndTurn())
    for _ in range(30):
        choices = [a for a in engine.legal_actions(state)
                   if isinstance(a, EffectChoice)]
        if not choices:
            break
        engine.apply(state, next((a for a in choices if a.skip), choices[0]))
    assert state.battle >= 2 or state.winner is not None
    assert state.last_battle_snapshot is not None


def score(state, player=0, front=HERE):
    return state.last_battle_snapshot["front_scores"][int(front)][player]


def test_moves_middle_stack_into_empty_frontline_and_adds_two_strength(game):
    engine, state = setup(game)
    mid = state.slot(0, at())
    mid.bond = "carried-the-oath-of"
    mid.name = "oren"
    mid.temporary_strength = 1
    mid.guarded = True
    mid.exhausted = True
    before = engine.front_strength(state, 0, HERE)
    resolve(engine, state)
    target = state.slot(0, at(Rank.FRONT))
    assert target.force == "the-fifty-men"
    assert target.bond == "carried-the-oath-of" and target.name == "oren"
    assert state.slot(0, at()).force is None
    assert score(state) == before + 2
    assert "the-lines-held" in state.players[0].discard


@pytest.mark.parametrize("block", ["force", "prepared_bond", "prepared_name"])
def test_nonempty_frontline_blocks_reinforcement(game, block):
    engine, state = setup(game)
    front = state.slot(0, at(Rank.FRONT))
    if block == "force":
        front.force = "the-crow-archers"
    elif block == "prepared_bond":
        front.bond = "carried-the-oath-of"
    else:
        front.name = "oren"
    before = engine.front_strength(state, 0, HERE)
    resolve(engine, state)
    assert state.slot(0, at()).force == "the-fifty-men"
    assert score(state) == before


def test_rank_restricted_middle_force_cannot_move_forward(game):
    engine, state = setup(game, middle_force="the-watchtowers-of-eren")
    before = engine.front_strength(state, 0, HERE)
    resolve(engine, state)
    assert state.slot(0, at()).force == "the-watchtowers-of-eren"
    assert state.slot(0, at(Rank.FRONT)).force is None
    assert score(state) == before


def test_only_stratagem_assigned_front_is_reinforced(game):
    engine, state = setup(game, plan_front=ELSEWHERE)
    before = engine.front_strength(state, 0, HERE)
    resolve(engine, state)
    assert state.slot(0, at()).force == "the-fifty-men"
    assert score(state) == before


def test_both_players_can_reinforce_before_strength_comparison(game):
    engine, state = setup(game)
    state.slot(1, at()).force = "the-crow-archers"
    state.stratagems[1] = StratagemState("the-lines-held", fronts=(HERE,))
    scores = [engine.front_strength(state, p, HERE) for p in (0, 1)]
    resolve(engine, state)
    for player in (0, 1):
        assert state.slot(player, at(Rank.FRONT)).force is not None
        assert state.slot(player, at()).force is None
        assert score(state, player) == scores[player] + 2


def test_no_middle_formation_leaves_hidden_plan_without_bonus(game):
    engine, state = setup(game, middle_force=None)
    resolve(engine, state)
    assert state.slot(0, at(Rank.FRONT)).force is None
    assert score(state) == 0
