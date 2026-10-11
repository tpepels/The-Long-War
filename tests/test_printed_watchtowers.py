"""Printed Watchtowers of Eren: inspect, then optionally draw/discard."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import ActivateAbility, BeginTurn, Discard, EffectChoice
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
FRONT = Front.SECOND
POSITION = Position(FRONT, Rank.MIDDLE)


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def setup(game, *, plan="the-center-must-hold", plan_front=FRONT, revealed=False):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=211, first_player=0)
    state.slot(0, POSITION).force = "the-watchtowers-of-eren"
    if plan is not None:
        state.stratagems[1] = StratagemState(
            plan, fronts=(plan_front,), revealed=revealed
        )
    state.players[0].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(
            a for a in engine.legal_actions(state) if isinstance(a, Discard)
        ))
    state.players[0].hand[:] = ["guarded"]
    return engine, state


def abilities(engine, state):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, ActivateAbility)
        and a.card_id == "the-watchtowers-of-eren"
    ]


def choices(engine, state, kind):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, EffectChoice) and a.effect == kind
    ]


def test_ability_inspects_stratagem_before_optional_card_cycle(game):
    engine, state = setup(game)
    actions = abilities(engine, state)
    assert len(actions) == 1
    assert not state.stratagems[1].known_to_mask & 1
    engine.apply(state, actions[0])
    assert state.stratagems[1].known_to_mask & 1
    assert not state.stratagems[1].revealed
    assert state.slot(0, POSITION).force_ability_used
    assert state.operations_this_battle[0] == 1
    cycle = choices(engine, state, "watchtowers-cycle")
    assert len(cycle) == 2 and {a.skip for a in cycle} == {True, False}
    assert state.players[0].hand == ["guarded"]
    assert not abilities(engine, state)


def test_declining_cycle_does_not_draw_or_discard(game):
    engine, state = setup(game)
    engine.apply(state, abilities(engine, state)[0])
    engine.apply(state, next(
        a for a in choices(engine, state, "watchtowers-cycle") if a.skip
    ))
    assert state.players[0].hand == ["guarded"]
    assert not choices(engine, state, "watchtowers-discard")
    assert state.stratagems[1].known_to_mask & 1
    assert state.operations_this_battle[0] == 1
    assert state.operations_this_battle[1] == 0
    assert state.active_player == 0
    assert not abilities(engine, state)


def test_accepting_cycle_draws_then_requires_one_chosen_discard(game):
    engine, state = setup(game)
    before_drawn = state.cards_drawn_this_battle[0]
    engine.apply(state, abilities(engine, state)[0])
    engine.apply(state, next(
        a for a in choices(engine, state, "watchtowers-cycle") if not a.skip
    ))
    discards = choices(engine, state, "watchtowers-discard")
    assert discards and any(a.card_id == "guarded" for a in discards)
    assert len(state.players[0].hand) == 2
    assert state.cards_drawn_this_battle[0] == before_drawn + 1
    engine.apply(state, next(a for a in discards if a.card_id == "guarded"))
    assert len(state.players[0].hand) == 1
    assert "guarded" in state.players[0].discard
    assert state.operations_this_battle[0] == 1
    assert state.active_player == 0


@pytest.mark.parametrize("plan,front,revealed", [
    (None, FRONT, False),
    ("the-center-must-hold", Front.FOURTH, False),
    ("the-center-must-hold", FRONT, True),
])
def test_no_eligible_hidden_plan_means_no_ability(game, plan, front, revealed):
    engine, state = setup(game, plan=plan, plan_front=front, revealed=revealed)
    assert not abilities(engine, state)


def test_plan_in_other_active_front_can_be_inspected(game):
    engine, state = setup(game, plan_front=Front.THIRD)
    assert abilities(engine, state)
    engine.apply(state, abilities(engine, state)[0])
    assert state.stratagems[1].known_to_mask & 1
