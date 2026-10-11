"""No Step Back: optional interrupt of targeted Tactic or basic Attack affliction.

The Attack still counts as used; a prevented affliction must not consume Guarded
or alter the target's current statuses. Neither response costs an Action.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from longwar.game.actions import Attack, BeginTurn, Discard, EffectChoice, PlayTactic
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank, StratagemState

ROOT = Path(__file__).resolve().parents[1]
HERE = Front.SECOND


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank=Rank.MIDDLE):
    return Position(HERE, rank)


def setup(game, *, stratagem="no-step-back", plan_front=HERE, guarded=False):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=420, first_player=0)
    state.slot(0, at()).force = "the-ash-bowmen"
    defender = state.slot(1, at())
    defender.force = "the-fifty-men"
    defender.guarded = guarded
    if stratagem:
        state.stratagems[1] = StratagemState(stratagem, fronts=(plan_front,))
    state.players[0].hand[:] = ["they-let-them-through"]
    state.players[0].command = 20
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    return engine, state


def choices(engine, state, name):
    return [a for a in engine.legal_actions(state)
            if isinstance(a, EffectChoice) and a.effect == name]


def decide(engine, state, name, reveal):
    options = choices(engine, state, name)
    assert options
    engine.apply(state, next(a for a in options if a.skip != reveal))


def attack(engine, state):
    action = Attack(at(), at(), "skirmisher")
    assert action in engine.legal_actions(state)
    engine.apply(state, action)


def tactic(engine, state):
    options = [a for a in engine.legal_actions(state)
               if isinstance(a, PlayTactic)
               and a.card_id == "they-let-them-through"
               and a.target is not None and a.target.player == 1
               and a.target.position == at()]
    assert options
    engine.apply(state, options[0])


def test_attack_interrupt_prevents_affliction_but_attack_is_spent(game):
    engine, state = setup(game, guarded=True)
    attack(engine, state)
    # Affliction has not been applied before the defender's reveal choice.
    assert not state.slot(1, at()).shaken
    assert len(choices(engine, state, "stratagem-no-step-attack")) == 2
    decide(engine, state, "stratagem-no-step-attack", reveal=True)
    assert not state.slot(1, at()).shaken
    assert state.slot(1, at()).guarded  # cancel before consuming Guarded
    assert state.slot(0, at()).used_attack
    assert "no-step-back" in state.players[1].discard
    assert state.stratagems[1] is None
    assert state.operations_this_battle[0] == 1
    assert state.operations_this_battle[1] == 0
    assert state.active_player == 0


def test_attack_decline_allows_normal_affliction_and_keeps_plan(game):
    engine, state = setup(game)
    attack(engine, state)
    decide(engine, state, "stratagem-no-step-attack", reveal=False)
    # The later generic Archer-reaction prompt must also decline privately.
    follow_up = choices(engine, state, "stratagem-archer-reveal")
    if follow_up:
        assert len(follow_up) == 1 and follow_up[0].skip
        engine.apply(state, follow_up[0])
    assert state.slot(1, at()).shaken
    assert state.slot(0, at()).used_attack
    assert not state.stratagems[1].revealed
    assert state.operations_this_battle[0] == 1


def test_tactic_interrupt_blocks_both_action_and_name_strength_suppression(game):
    engine, state = setup(game)
    defender = state.slot(1, at())
    defender.bond = "stood-fast-with"
    defender.name = "namar"
    before = engine.position_strength(state, 1, at())
    tactic(engine, state)
    assert len(choices(engine, state, "stratagem-no-step-tactic")) == 2
    decide(engine, state, "stratagem-no-step-tactic", reveal=True)
    assert defender.suppression_mask == 0
    assert engine.position_strength(state, 1, at()) == before
    assert "they-let-them-through" in state.players[0].discard
    assert "no-step-back" in state.players[1].discard
    assert state.operations_this_battle[0] == 1
    assert state.operations_this_battle[1] == 0


def test_tactic_decline_resolves_effect_then_discards_tactic(game):
    engine, state = setup(game)
    tactic(engine, state)
    decide(engine, state, "stratagem-no-step-tactic", reveal=False)
    assert state.slot(1, at()).suppression_mask != 0
    assert state.stratagems[1].card_id == "no-step-back"
    assert "they-let-them-through" in state.players[0].discard


@pytest.mark.parametrize("case", ["wrong_front", "other_plan"])
def test_ineligible_hidden_plan_has_only_private_decline(game, case):
    engine, state = setup(
        game,
        stratagem="no-step-back" if case == "wrong_front" else "the-center-must-hold",
        plan_front=Front.THIRD if case == "wrong_front" else HERE,
    )
    tactic(engine, state)
    options = choices(engine, state, "stratagem-no-step-tactic")
    assert len(options) == 1 and options[0].skip
    engine.apply(state, options[0])
    assert state.slot(1, at()).suppression_mask != 0


def test_tactic_without_defender_plan_has_no_extra_pending_choice(game):
    engine, state = setup(game, stratagem=None)
    tactic(engine, state)
    assert not choices(engine, state, "stratagem-no-step-tactic")
    assert state.slot(1, at()).suppression_mask != 0


def test_archer_defense_still_works_after_forced_no_step_decline(game):
    engine, state = setup(game, stratagem="the-archers-were-ready")
    state.slot(1, at(Rank.REAR)).force = "the-crow-archers"
    state.slot(0, at(Rank.REAR)).force = "the-fifty-men"
    attack(engine, state)
    pre = choices(engine, state, "stratagem-no-step-attack")
    assert len(pre) == 1 and pre[0].skip
    engine.apply(state, pre[0])
    assert state.slot(1, at()).shaken
    assert len(choices(engine, state, "stratagem-archer-reveal")) == 2
