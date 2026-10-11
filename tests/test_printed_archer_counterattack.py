"""The Archers Were Ready: one free basic Archer Attack *after* a legal enemy Attack."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import Attack, BeginTurn, Discard, EffectChoice
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
HERE = Front.SECOND


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank):
    return Position(HERE, rank)


def setup(game, *, defending_plan="the-archers-were-ready",
          used_archer=False, screen=False, assigned_front=HERE):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=170, first_player=0)
    state.slot(0, at(Rank.MIDDLE)).force = "the-ash-bowmen"
    state.slot(0, at(Rank.REAR)).force = "the-fifty-men"
    state.slot(1, at(Rank.MIDDLE)).force = "the-fifty-men"
    state.slot(1, at(Rank.REAR)).force = "the-crow-archers"
    state.slot(1, at(Rank.REAR)).used_attack = used_archer
    if screen:
        state.slot(0, at(Rank.MIDDLE)).force = "the-red-shields"
        # A legal Skirmisher must also be present for the incoming Attack.
        state.slot(0, at(Rank.FRONT)).force = "the-ash-bowmen"
        attack_source = at(Rank.FRONT)
    else:
        attack_source = at(Rank.MIDDLE)
    if defending_plan:
        state.stratagems[1] = StratagemState(
            defending_plan, fronts=(assigned_front,)
        )
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    incoming = Attack(
        source=attack_source,
        target=at(Rank.MIDDLE),
        classification="skirmisher",
    )
    assert incoming in engine.legal_actions(state)
    engine.apply(state, incoming)
    return engine, state


def choices(engine, state, kind):
    return [
        a for a in engine.legal_actions(state)
        if isinstance(a, EffectChoice) and a.effect == kind
    ]


def test_reveal_then_free_attack_follows_original_attack_and_uses_archer(game):
    engine, state = setup(game)
    # The first hostile Attack has already resolved and cannot be undone.
    assert state.slot(1, at(Rank.MIDDLE)).shaken
    assert not state.slot(0, at(Rank.REAR)).exhausted
    decision = choices(engine, state, "stratagem-archer-reveal")
    assert len(decision) == 2
    assert {a.skip for a in decision} == {True, False}

    engine.apply(state, next(a for a in decision if not a.skip))
    assert state.stratagems[1].revealed
    counter = choices(engine, state, "stratagem-archer-attack")
    # This Archer can also legally attack Middle when enemy Frontline is
    # empty; the reaction must offer every legal basic Archer target.
    assert len(counter) == 2
    assert all(choice.source.position == at(Rank.REAR) for choice in counter)
    rear = next(choice for choice in counter
                if choice.destination.position == at(Rank.REAR))
    engine.apply(state, rear)

    assert state.slot(0, at(Rank.REAR)).exhausted
    assert state.slot(1, at(Rank.REAR)).used_attack
    assert state.slot(1, at(Rank.MIDDLE)).shaken
    assert state.stratagems[1] is None
    assert "the-archers-were-ready" in state.players[1].discard
    assert state.operations_this_battle[1] == 0
    assert state.operations_this_battle[0] == 1
    assert state.actions_this_turn == 1
    assert state.active_player == 0


def test_declining_keeps_hidden_stratagem_and_finishes_attacker_action(game):
    engine, state = setup(game)
    engine.apply(
        state, next(a for a in choices(engine, state, "stratagem-archer-reveal")
                    if a.skip),
    )
    assert state.stratagems[1].card_id == "the-archers-were-ready"
    assert not state.stratagems[1].revealed
    assert not state.slot(0, at(Rank.REAR)).exhausted
    assert not state.slot(1, at(Rank.REAR)).used_attack
    assert state.operations_this_battle[0] == 1
    assert state.operations_this_battle[1] == 0


@pytest.mark.parametrize("kwargs", [
    {"used_archer": True},
    {"assigned_front": Front.THIRD},
    {"defending_plan": "the-center-must-hold"},
    {"screen": True},
])
def test_ineligible_face_down_plan_has_only_private_decline(game, kwargs):
    engine, state = setup(game, **kwargs)
    options = choices(engine, state, "stratagem-archer-reveal")
    assert len(options) == 1
    assert options[0].skip
    engine.apply(state, options[0])
    assert not state.stratagems[1].revealed
    assert state.operations_this_battle[1] == 0


def test_no_defending_plan_skips_response(game):
    engine, state = setup(game, defending_plan=None)
    assert not choices(engine, state, "stratagem-archer-reveal")
    assert state.operations_this_battle[0] == 1
