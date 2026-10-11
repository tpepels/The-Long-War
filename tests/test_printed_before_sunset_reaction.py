"""Before Sunset: Scout/Ship reaction to opponent setting a Stratagem."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import BeginTurn, Discard, EffectChoice, PlayStratagem
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, NarrativeState

ROOT = Path(__file__).resolve().parents[1]
PLAN, NEAR, FAR = Front.SECOND, Front.THIRD, Front.FOURTH


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(front, rank=Rank.MIDDLE):
    return Position(front, rank)


def setup(game, *, scout_front=NEAR, scout_card="the-lantern-scouts",
          target_count=1, plan_front=PLAN, already_used=False):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=649, first_player=1)
    if plan_front == FAR:
        state.battle = 3
    state.narratives[0].append(
        NarrativeState(
            "before-sunset-the-ford-would-be-ours",
            triggered_this_battle=already_used,
        )
    )
    if scout_card is not None:
        state.slot(0, at(scout_front)).force = scout_card
    for rank in (Rank.FRONT, Rank.REAR)[:target_count]:
        # Don't overwrite a Scout already occupying the same position.
        state.slot(0, at(plan_front, rank)).force = "the-fifty-men"
    state.players[1].hand[:] = ["the-center-must-hold"]
    state.players[1].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    state.players[1].hand[:] = ["the-center-must-hold"]
    play = next(
        a for a in engine.legal_actions(state)
        if isinstance(a, PlayStratagem)
        and a.card_id == "the-center-must-hold"
        and a.fronts == (plan_front,)
    )
    engine.apply(state, play)
    return engine, state


def buff_choices(engine, state):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, EffectChoice) and a.effect == "before-sunset-buff"
    ]


def test_adjacent_scout_inspects_then_buffs_one_formation(game):
    engine, state = setup(game)
    assert state.stratagems[1].known_to_mask & 1
    assert not state.stratagems[1].revealed
    assert state.narratives[0][0].triggered_this_battle
    picks = buff_choices(engine, state)
    assert len(picks) == 1 and not picks[0].skip
    assert picks[0].source.position == at(PLAN, Rank.FRONT)
    assert state.slot(0, at(PLAN, Rank.FRONT)).temporary_strength == 0
    engine.apply(state, picks[0])
    assert state.slot(0, at(PLAN, Rank.FRONT)).temporary_strength == 2
    assert state.operations_this_battle[0] == 0
    assert state.operations_this_battle[1] == 1


def test_multiple_recipients_require_exactly_one_selected(game):
    engine, state = setup(game, target_count=2)
    picks = buff_choices(engine, state)
    assert len(picks) == 2
    assert not any(a.skip for a in picks)
    engine.apply(state, next(a for a in picks
                             if a.source.position == at(PLAN, Rank.REAR)))
    assert state.slot(0, at(PLAN, Rank.REAR)).temporary_strength == 2
    assert state.slot(0, at(PLAN, Rank.FRONT)).temporary_strength == 0


def test_inspection_still_triggers_when_no_friendly_target(game):
    engine, state = setup(game, target_count=0)
    assert not buff_choices(engine, state)
    assert state.stratagems[1].known_to_mask & 1
    assert state.narratives[0][0].triggered_this_battle
    assert state.operations_this_battle[0] == 0


def test_same_front_ship_also_qualifies(game):
    engine, state = setup(game, scout_front=PLAN, scout_card="seven-black-ships")
    assert state.stratagems[1].known_to_mask & 1
    assert len(buff_choices(engine, state)) >= 1


@pytest.mark.parametrize("situation", ["no_scout", "too_far", "already_used"])
def test_ineligible_narrative_does_not_inspect_or_buff(game, situation):
    kw = {}
    if situation == "no_scout":
        kw["scout_card"] = None
    elif situation == "too_far":
        kw["plan_front"] = FAR
        kw["scout_front"] = PLAN
    else:
        kw["already_used"] = True
    engine, state = setup(game, **kw)
    assert not state.stratagems[1].known_to_mask & 1
    assert not buff_choices(engine, state)
    assert state.narratives[0][0].triggered_this_battle == (situation == "already_used")
