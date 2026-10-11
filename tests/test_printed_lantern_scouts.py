"""Printed Lantern Scouts: public, once-per-Battle Stratagem-set reaction."""
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


def at(rank=Rank.MIDDLE, front=HERE):
    return Position(front, rank)


def choices(engine, state, effect):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, EffectChoice) and a.effect == effect
    ]


def setup(game, *, rank=Rank.MIDDLE, scout_front=HERE,
          defender_plan=None, second_scout=False):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=107, first_player=1)
    state.slot(0, at(rank, scout_front)).force = "the-lantern-scouts"
    if second_scout:
        state.slot(0, at(Rank.REAR)).force = "the-lantern-scouts"
    if defender_plan:
        state.stratagems[0] = StratagemState(defender_plan, fronts=(HERE,))
    state.players[0].hand[:] = ["guarded"]
    state.players[1].hand[:] = ["the-center-must-hold"]
    state.players[1].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(
            a for a in engine.legal_actions(state) if isinstance(a, Discard)
        ))
    play = next(
        a for a in engine.legal_actions(state)
        if isinstance(a, PlayStratagem)
        and a.card_id == "the-center-must-hold"
        and a.fronts == (HERE,)
    )
    engine.apply(state, play)
    return engine, state


def test_accept_inspects_new_plan_draws_then_discards_without_action(game):
    engine, state = setup(game)
    actions = choices(engine, state, "lantern-scouts-react")
    assert len(actions) == 2
    assert {a.skip for a in actions} == {True, False}
    assert not state.stratagems[1].known_to_mask & 1
    before_hand = len(state.players[0].hand)
    before_ops = state.operations_this_battle[0]

    engine.apply(state, next(a for a in actions if not a.skip))
    assert state.stratagems[1].known_to_mask & 1
    discards = choices(engine, state, "lantern-scouts-discard")
    assert discards
    assert len(state.players[0].hand) == before_hand + 1
    discard = next(a for a in discards if a.card_id == "guarded")
    engine.apply(state, discard)

    assert len(state.players[0].hand) == before_hand
    assert "guarded" in state.players[0].discard
    assert state.operations_this_battle[0] == before_ops
    assert state.active_player == 1
    assert not choices(engine, state, "lantern-scouts-react")


def test_decline_does_not_disclose_stratagem_or_draw(game):
    engine, state = setup(game)
    engine.apply(state, next(
        a for a in choices(engine, state, "lantern-scouts-react") if a.skip
    ))
    assert not state.stratagems[1].known_to_mask & 1
    assert state.players[0].hand == ["guarded"]
    assert state.active_player == 1


@pytest.mark.parametrize("rank,front", [
    (Rank.FRONT, HERE),
    (Rank.MIDDLE, Front.THIRD),
])
def test_wrong_rank_or_front_does_not_react(game, rank, front):
    engine, state = setup(game, rank=rank, scout_front=front)
    assert not choices(engine, state, "lantern-scouts-react")
    assert state.active_player == 1


def test_two_scouts_react_separately_to_same_set(game):
    engine, state = setup(game, second_scout=True)
    first = next(
        a for a in choices(engine, state, "lantern-scouts-react")
        if not a.skip and a.source.position == at(Rank.MIDDLE)
    )
    engine.apply(state, first)
    engine.apply(state, next(
        a for a in choices(engine, state, "lantern-scouts-discard")
        if a.card_id == "guarded"
    ))
    remaining = choices(engine, state, "lantern-scouts-react")
    assert len(remaining) == 2
    assert next(a for a in remaining if not a.skip).source.position == at(Rank.REAR)
    engine.apply(state, next(a for a in remaining if a.skip))
    assert state.active_player == 1


def test_hidden_scout_stratagem_and_visible_reaction_are_independent(game):
    engine, state = setup(game, defender_plan="the-scouts-had-warned-them")
    choices_hidden = choices(engine, state, "stratagem-scout-reveal")
    assert choices_hidden
    engine.apply(state, next(a for a in choices_hidden if a.skip))
    assert choices(engine, state, "lantern-scouts-react")
    assert state.stratagems[0].card_id == "the-scouts-had-warned-them"
