from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    Cycle,
    Discard,
    EffectChoice,
    EndTurn,
    Front,
    GameEngine,
    Maneuver,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayNarrative,
    PlayStratagem,
    Position,
    Rank,
)
from longwar.game.model import FRONT_COUNT, Phase, NarrativeState, StratagemState
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "mobility-open-bonds.json"


def setup_state(
    *,
    seed: int = 4100,
    first_player: int = 0,
    opening_bonus: bool = False,
    rules: GameRules | None = None,
    battle: int = 3,
):
    data = load_card_file(CARD_FILE)
    deck = json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]
    engine = GameEngine(data, rules=rules or GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=seed,
        first_player=first_player,
        opening_bonus=opening_bonus,
    )
    # Most focused card-mechanics tests predate the expanding battlefield and
    # intentionally exercise arbitrary Fronts. Start those fixtures at Battle
    # III, where all four are active. Battle-flow tests override this to I/II.
    state.battle = battle
    return engine, state


def pos(front: int, rank: Rank = Rank.FRONT) -> Position:
    return Position(Front(front), rank)


def slot_number(player: int, position: Position) -> int:
    return (
        player * FRONT_COUNT * len(Rank)
        + int(position.front) * len(Rank)
        + list(Rank).index(position.rank)
    )


def make_named(
    state,
    player: int,
    position: Position,
    *,
    force: str = "the-fifty-men",
    bond: str = "followed",
    name: str = "namar",
    temporary: int = 0,
):
    slot = state.slot(player, position)
    slot.force = force
    slot.bond = bond
    slot.name = name
    slot.temporary_strength = temporary
    return slot


def effect_choices(
    engine: GameEngine,
    state,
    effect: str | None = None,
) -> list[EffectChoice]:
    actions = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, EffectChoice)
    ]
    if effect is not None:
        actions = [action for action in actions if action.effect == effect]
    return actions


def apply_explicit_retreat(
    engine: GameEngine,
    state,
    player: int,
    front: Front,
) -> None:
    """Apply one synthetic explicit Retreat through the real effect resolver."""
    slots_per_player = FRONT_COUNT * len(Rank)
    source = slot_number(player, pos(int(front), Rank.FRONT))
    destination = slot_number(player, pos(int(front), Rank.REAR))
    state.pending_effects[:] = [{
        "kind": 9,  # EFFECT_RETREAT
        "player": player,
        "card": -1,
        "source": source,
        "aux": destination,
        "source_mask": 0,
        "dest_mask": 0,
        "flags": 0,
    }]
    state.active_player = player
    retreat = next(
        action
        for action in effect_choices(engine, state, "retreat")
        if not action.skip
    )
    engine.apply(state, retreat)


def _finish_closing_turn(engine: GameEngine, state) -> None:
    """Resolve mandatory draw substeps, then end the current closing turn."""
    for _ in range(32):
        legal = engine.legal_actions(state)
        end_turn = next(
            (action for action in legal if isinstance(action, EndTurn)),
            None,
        )
        if end_turn is not None:
            engine.apply(state, end_turn)
            return

        # A closing turn still begins with the normal automatic draw. If that
        # draw pushes the hand above the limit, cleanup must finish before
        # EndTurn becomes legal.
        discard = next(
            (action for action in legal if isinstance(action, Discard)),
            None,
        )
        if discard is not None:
            engine.apply(state, discard)
            continue

        effect = next(
            (
                action
                for action in legal
                if isinstance(action, EffectChoice) and action.skip
            ),
            None,
        )
        if effect is None:
            effect = next(
                (action for action in legal if isinstance(action, EffectChoice)),
                None,
            )
        if effect is not None:
            engine.apply(state, effect)
            continue

        raise AssertionError(
            "closing turn exposed neither EndTurn nor a mandatory substep: "
            f"{legal!r}"
        )
    raise AssertionError("closing turn did not settle")


def resolve_battle_by_passing(engine: GameEngine, state) -> None:
    """Finish a Battle from the fixed post-Pass two-turn closing state.

    Focused Battle-resolution tests do not need to manufacture an artificial
    no-action hand just to make the initiating Pass legal. Real Pass legality
    and its first closing-turn draw are covered separately below.
    """
    state.pass_order[:] = [0]
    state.players[0].passed = True
    state.players[1].passed = False
    state.closing_turns_remaining = engine.rules.closing_turns_after_pass
    state.active_player = 1
    state.actions_this_turn = 0

    _finish_closing_turn(engine, state)
    assert state.closing_turns_remaining == 1
    assert state.active_player == 0
    _finish_closing_turn(engine, state)


def test_battlefield_is_four_fronts_by_three_ranks() -> None:
    _engine, state = setup_state()
    assert FRONT_COUNT == 4
    assert len(state.board) == 2
    assert all(len(side) == 4 for side in state.board)
    assert all(len(front) == 3 for side in state.board for front in side)
    assert list(Rank) == [Rank.FRONT, Rank.MIDDLE, Rank.REAR]
    assert list(Front) == [
        Front.FIRST,
        Front.SECOND,
        Front.THIRD,
        Front.FOURTH,
    ]


def test_active_fronts_expand_by_battle() -> None:
    engine, state = setup_state(battle=1)
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert PlayForce("the-fifty-men", pos(1)) in legal
    assert PlayForce("the-fifty-men", pos(1, Rank.MIDDLE)) in legal
    assert PlayForce("the-fifty-men", pos(2)) in legal
    assert PlayForce("the-fifty-men", pos(0)) not in legal
    assert PlayForce("the-fifty-men", pos(3)) not in legal

    state.battle = 2
    legal = engine.legal_actions(state)
    assert PlayForce("the-fifty-men", pos(0)) in legal
    assert PlayForce("the-fifty-men", pos(3)) not in legal

    state.battle = 3
    legal = engine.legal_actions(state)
    assert PlayForce("the-fifty-men", pos(3)) in legal


def test_front_selecting_cards_cannot_target_inactive_fronts() -> None:
    engine, state = setup_state(battle=1)
    state.players[0].hand = [
        "before-sunset-the-ford-would-be-ours",
        "no-step-back",
    ]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert PlayNarrative(
        "before-sunset-the-ford-would-be-ours",
        ongoing_slot=0,
        fronts=(Front.SECOND,),
    ) in legal
    assert PlayNarrative(
        "before-sunset-the-ford-would-be-ours",
        ongoing_slot=0,
        fronts=(Front.FIRST,),
    ) not in legal
    assert PlayStratagem(
        "no-step-back",
        fronts=(Front.SECOND,),
    ) in legal
    assert PlayStratagem(
        "no-step-back",
        fronts=(Front.FIRST,),
    ) not in legal

    state.battle = 2
    legal = engine.legal_actions(state)
    assert PlayNarrative(
        "before-sunset-the-ford-would-be-ours",
        ongoing_slot=0,
        fronts=(Front.FIRST,),
    ) in legal
    assert PlayStratagem(
        "no-step-back",
        fronts=(Front.FIRST,),
    ) in legal


def test_maneuver_cannot_enter_inactive_front() -> None:
    engine, state = setup_state(battle=1)
    source = pos(2, Rank.MIDDLE)
    make_named(state, 0, source)

    legal = engine.legal_actions(state)

    assert Maneuver(source, pos(1, Rank.MIDDLE)) in legal
    assert Maneuver(source, pos(3, Rank.MIDDLE)) not in legal


def test_printed_strength_effects_apply_without_hidden_role_rules() -> None:
    engine, state = setup_state()

    frontline = pos(0, Rank.FRONT)
    middle = pos(0, Rank.MIDDLE)
    rear = pos(0, Rank.REAR)

    state.slot(0, frontline).force = "the-fifty-men"
    assert engine.position_strength(state, 0, frontline) == 4
    state.slot(0, frontline).force = "seven-black-ships"
    assert engine.position_strength(state, 0, frontline) == 4

    state.slot(0, rear).force = "seven-black-ships"
    assert engine.position_strength(state, 0, rear) == 5

    state.slot(0, frontline).force = "the-red-shields"
    state.slot(0, middle).force = None
    state.slot(0, rear).force = None
    assert engine.position_strength(state, 0, frontline) == 4

    state.slot(0, middle).force = "the-fifty-men"
    # Middle is directly behind Frontline, so Red Shields gets +1.
    assert engine.position_strength(state, 0, frontline) == 5

    state.slot(0, rear).force = "the-white-hands-of-elara"
    # White Hands is Rear-only. From Rear it supports the Middle/Support Force
    # directly in front of it, not the Frontline two ranks away.
    assert engine.position_strength(state, 0, middle) == 6
    assert engine.position_strength(state, 0, frontline) == 5

    state.slot(0, rear).force = "the-crow-archers"
    # Middle is directly ahead of Rear.
    assert engine.position_strength(state, 0, rear) == 6
    assert engine.front_strength(state, 0, Front.FIRST) >= (
        engine.position_strength(state, 0, frontline)
        + engine.position_strength(state, 0, middle)
        + engine.position_strength(state, 0, rear)
    )


def test_role_labels_alone_do_not_add_strength() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.REAR)
    state.slot(0, target).force = "the-house-of-reed"
    assert engine.position_strength(state, 0, target) == 3


def test_printed_deploy_restrictions_are_enforced() -> None:
    engine, state = setup_state()
    state.players[0].hand = [
        "the-red-shields",
        "the-white-hands-of-elara",
        "avaros-the-bronze-king",
    ]
    state.players[0].command = 20
    legal = engine.legal_actions(state)

    assert PlayForce("the-red-shields", pos(0, Rank.FRONT)) in legal
    assert PlayForce("the-red-shields", pos(0, Rank.MIDDLE)) not in legal
    assert PlayForce("the-red-shields", pos(0, Rank.REAR)) not in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.REAR)) in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.MIDDLE)) not in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.FRONT)) not in legal
    assert PlayForce("avaros-the-bronze-king", pos(2, Rank.FRONT)) in legal
    assert PlayForce("avaros-the-bronze-king", pos(2, Rank.REAR)) not in legal


def test_bond_and_name_can_be_prepared_before_force_and_contribute_zero() -> None:
    engine, state = setup_state()
    target = pos(0)
    state.players[0].hand = ["followed", "namar", "the-fifty-men"]
    state.players[0].command = 20
    # Keep the opponent below the hand limit so its automatic turn-start draw
    # resolves immediately while this test hands control back to player 0.
    state.players[1].hand = []

    legal = engine.legal_actions(state)
    assert PlayBond("followed", target) in legal
    assert PlayName("namar", target) in legal

    engine.apply(state, PlayBond("followed", target))
    state.active_player = 0
    engine.apply(state, PlayName("namar", target))

    slot = state.slot(0, target)
    assert slot.force is None
    assert slot.bond == "followed"
    assert slot.name == "namar"
    assert slot.complete is False
    assert engine.position_strength(state, 0, target) == 0

    state.active_player = 0
    engine.apply(state, PlayForce("the-fifty-men", target))
    assert slot.complete is True
    assert engine.position_strength(state, 0, target) > 0


def test_losing_front_does_not_move_deploy_restricted_force() -> None:
    engine, state = setup_state()
    front = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)
    state.players[0].hand = ["the-red-shields"]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert PlayForce("the-red-shields", front) in legal
    assert PlayForce("the-red-shields", rear) not in legal

    make_named(state, 0, front, force="the-red-shields")
    make_named(state, 1, front, temporary=100)
    resolve_battle_by_passing(engine, state)

    assert state.slot(0, front).force == "the-red-shields"
    assert state.slot(0, rear).occupied is False

def test_maneuver_moves_named_formation_to_adjacent_empty_same_rank() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.MIDDLE)
    destination = pos(1, Rank.MIDDLE)
    make_named(state, 0, source)
    state.players[0].command = 5

    action = Maneuver(source, destination)
    assert action in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, action) == 1

    engine.apply(state, action)
    assert state.slot(0, source).occupied is False
    assert state.slot(0, destination).complete is True
    assert state.players[0].command == 4


def test_maneuver_swaps_complete_contents_with_incomplete_formation() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.REAR)
    destination = pos(2, Rank.REAR)
    make_named(state, 0, source, force="seven-black-ships")
    target = state.slot(0, destination)
    target.bond = "stood-fast-with"
    target.name = "iria"
    state.players[0].command = 5

    action = Maneuver(source, destination)
    assert action in engine.legal_actions(state)
    engine.apply(state, action)

    assert state.slot(0, destination).force == "seven-black-ships"
    assert state.slot(0, destination).bond == "followed"
    assert state.slot(0, destination).name == "namar"
    assert state.slot(0, source).force is None
    assert state.slot(0, source).bond == "stood-fast-with"
    assert state.slot(0, source).name == "iria"


def test_maneuver_allows_orthogonal_vertical_but_not_diagonal_or_two_step() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.MIDDLE)
    make_named(state, 0, source)
    state.players[0].command = 5
    legal = engine.legal_actions(state)

    assert Maneuver(source, pos(1, Rank.FRONT)) in legal
    assert Maneuver(source, pos(1, Rank.REAR)) in legal
    assert Maneuver(source, pos(0, Rank.MIDDLE)) in legal
    assert Maneuver(source, pos(2, Rank.MIDDLE)) in legal
    assert Maneuver(source, pos(0, Rank.FRONT)) not in legal
    assert Maneuver(source, pos(2, Rank.REAR)) not in legal
    assert Maneuver(source, pos(3, Rank.MIDDLE)) not in legal


def test_press_strength_tracks_opposing_exhaustion_in_same_front() -> None:
    engine, state = setup_state()
    own = pos(1, Rank.FRONT)
    enemy = pos(1, Rank.REAR)

    state.slot(0, own).force = "the-ash-bowmen"
    state.slot(1, enemy).force = "the-fifty-men"

    assert engine.position_strength(state, 0, own) == 4

    state.slot(1, enemy).exhausted = True
    assert engine.position_strength(state, 0, own) == 5

    state.slot(1, enemy).exhausted = False
    assert engine.position_strength(state, 0, own) == 4


def test_supply_raid_steals_command_and_respects_floor() -> None:
    engine, state = setup_state()
    target = pos(1, Rank.FRONT)
    enemy_supply = pos(1, Rank.REAR)

    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 5
    state.slot(1, enemy_supply).force = "the-house-of-reed"

    engine.apply(state, PlayForce("the-unnamed-host", target))

    assert state.players[0].command == 4
    assert state.players[1].command == 4

    engine, state = setup_state()
    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 1
    state.slot(1, enemy_supply).force = "the-house-of-reed"

    engine.apply(state, PlayForce("the-unnamed-host", target))

    assert state.players[0].command == 3
    assert state.players[1].command == 1


def test_supply_raid_does_not_trigger_without_live_supply() -> None:
    engine, state = setup_state()
    target = pos(1, Rank.FRONT)
    enemy = pos(1, Rank.REAR)

    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 5
    state.slot(1, enemy).force = "the-fifty-men"

    engine.apply(state, PlayForce("the-unnamed-host", target))

    assert state.players[0].command == 3
    assert state.players[1].command == 5


def test_supply_discounts_only_the_formation_directly_ahead() -> None:
    engine, state = setup_state()
    rear = pos(1, Rank.REAR)
    middle = pos(1, Rank.MIDDLE)
    front = pos(1, Rank.FRONT)
    other_middle = pos(2, Rank.MIDDLE)

    state.slot(0, rear).force = "the-house-of-reed"
    state.players[0].hand = ["followed", "namar"]

    assert engine.command_cost_for_action(state, PlayBond("followed", middle)) == 0
    assert engine.command_cost_for_action(state, PlayName("namar", middle)) == 2
    assert engine.command_cost_for_action(state, PlayBond("followed", front)) == 1
    assert (
        engine.command_cost_for_action(state, PlayBond("followed", other_middle))
        == 1
    )


def test_supply_from_middle_can_discount_front_attachments() -> None:
    engine, state = setup_state()
    middle = pos(1, Rank.MIDDLE)
    front = pos(1, Rank.FRONT)

    state.slot(0, middle).force = "the-fifty-men"
    state.slot(0, middle).bond = "supplied-by"

    assert engine.command_cost_for_action(state, PlayBond("followed", front)) == 0
    assert engine.command_cost_for_action(state, PlayName("namar", front)) == 2


def test_supplied_by_requires_bonded_and_stops_when_bond_text_is_suppressed() -> None:
    engine, state = setup_state()
    rear = pos(1, Rank.REAR)
    middle = pos(1, Rank.MIDDLE)
    source = state.slot(0, rear)
    source.bond = "supplied-by"

    assert engine.command_cost_for_action(state, PlayBond("followed", middle)) == 1

    source.force = "the-fifty-men"
    assert engine.command_cost_for_action(state, PlayBond("followed", middle)) == 0

    # SUPPRESS_BOND_TEXT is the native bit value 2; state IO intentionally
    # exposes the mask so black-box tests can verify suppressed card text.
    source.suppression_mask = 2
    assert engine.command_cost_for_action(state, PlayBond("followed", middle)) == 1


def test_multiple_supply_effects_stack_with_bond_zero_and_name_one_minima() -> None:
    engine, state = setup_state()
    rear = pos(1, Rank.REAR)
    middle = pos(1, Rank.MIDDLE)
    source = state.slot(0, rear)
    source.force = "the-house-of-reed"
    source.bond = "supplied-by"

    assert engine.command_cost_for_action(state, PlayBond("followed", middle)) == 0
    assert engine.command_cost_for_action(state, PlayName("iria", middle)) == 1
    assert engine.command_cost_for_action(state, PlayName("namar", middle)) == 1


def test_supply_raid_ignores_inactive_or_suppressed_supply() -> None:
    engine, state = setup_state()
    target = pos(1, Rank.FRONT)
    enemy_rear = pos(1, Rank.REAR)
    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 5

    state.slot(1, pos(1, Rank.MIDDLE)).force = "the-house-of-reed"
    engine.apply(state, PlayForce("the-unnamed-host", target))
    assert state.players[0].command == 3
    assert state.players[1].command == 5

    engine, state = setup_state()
    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 5
    source = state.slot(1, enemy_rear)
    source.force = "the-fifty-men"
    source.bond = "supplied-by"
    source.suppression_mask = 2

    engine.apply(state, PlayForce("the-unnamed-host", target))
    assert state.players[0].command == 3
    assert state.players[1].command == 5


def test_supply_steal_gives_exactly_what_was_taken_above_floor_one() -> None:
    engine, state = setup_state()
    target = pos(1, Rank.FRONT)
    enemy_supply = pos(1, Rank.REAR)
    state.players[0].hand = ["the-unnamed-host"]
    state.players[0].command = 5
    state.players[1].command = 2
    state.slot(1, enemy_supply).force = "the-house-of-reed"

    engine.apply(state, PlayForce("the-unnamed-host", target))

    assert state.players[0].command == 4
    assert state.players[1].command == 1


def test_shared_spoils_refund_requires_class_and_enemy_supply() -> None:
    target = pos(1, Rank.FRONT)
    enemy_supply = pos(1, Rank.REAR)

    engine, state = setup_state()
    state.players[0].hand = ["shared-the-spoils-with"]
    state.players[0].command = 5
    state.slot(0, target).force = "the-unnamed-host"
    state.slot(1, enemy_supply).force = "the-house-of-reed"
    engine.apply(state, PlayBond("shared-the-spoils-with", target))
    assert state.players[0].command == 5

    engine, state = setup_state()
    state.players[0].hand = ["shared-the-spoils-with"]
    state.players[0].command = 5
    state.slot(0, target).force = "the-fifty-men"
    state.slot(1, enemy_supply).force = "the-house-of-reed"
    engine.apply(state, PlayBond("shared-the-spoils-with", target))
    assert state.players[0].command == 4

    engine, state = setup_state()
    state.players[0].hand = ["shared-the-spoils-with"]
    state.players[0].command = 5
    state.slot(0, target).force = "the-unnamed-host"
    engine.apply(state, PlayBond("shared-the-spoils-with", target))
    assert state.players[0].command == 4


def test_lost_front_exhausts_every_force_there_and_blocks_maneuver() -> None:
    engine, state = setup_state()
    front = 1
    for rank in Rank:
        make_named(state, 0, pos(front, rank))
    make_named(state, 1, pos(front, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    for rank in Rank:
        assert state.slot(0, pos(front, rank)).exhausted is True
    assert state.slot(1, pos(front, Rank.FRONT)).exhausted is False

    state.active_player = 0
    state.actions_this_turn = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    exhausted_source = pos(front, Rank.MIDDLE)
    assert not any(
        isinstance(action, Maneuver) and action.source == exhausted_source
        for action in engine.legal_actions(state)
    )


def test_exhaustion_round_trips_and_blocks_horizontal_and_vertical_maneuver() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.MIDDLE)
    make_named(state, 0, source).exhausted = True

    cloned = state.clone()
    assert cloned.slot(0, source).exhausted is True

    packed = engine._native_core_instance.from_game_state(state)
    exported = engine._native_core_instance.export_state(packed)
    assert exported["board"][0][1][1]["exhausted"] is True

    legal = engine.legal_actions(state)
    assert Maneuver(source, pos(1, Rank.REAR)) not in legal
    assert Maneuver(source, pos(2, Rank.MIDDLE)) not in legal


def test_pass_is_forced_only_when_no_action_is_legal() -> None:
    engine, state = setup_state(battle=1)
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert Pass() not in legal
    assert EndTurn() in legal

    state.players[0].hand.clear()
    state.actions_this_turn = 0
    assert engine.legal_actions(state) == [Pass()]

def test_cycle_counts_as_a_legal_action_and_prevents_pass() -> None:
    engine, state = setup_state(battle=1)
    state.active_player = 0
    state.players[0].hand = ["followed", "namar"]
    state.players[0].command = 0

    legal = engine.legal_actions(state)

    assert Cycle("followed", "namar") in legal
    assert Pass() not in legal
    assert EndTurn() in legal


def test_pass_gives_opponent_first_closing_turn_with_normal_draw() -> None:
    engine, state = setup_state(battle=1)
    state.active_player = 0
    state.players[0].hand.clear()

    moved = state.players[1].hand.pop()
    state.players[1].deck.append(moved)
    assert len(state.players[1].hand) == engine.opening_hand_size - 1
    before_drawn = state.cards_drawn_this_battle[1]

    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())

    assert state.battle == 1
    assert state.active_player == 1
    assert state.pass_order == [0]
    assert state.players[0].passed is True
    assert state.closing_turns_remaining == 2
    assert len(state.players[1].hand) == engine.opening_hand_size
    assert state.cards_drawn_this_battle[1] == before_drawn + 1

def test_pass_starts_exactly_two_closing_turns() -> None:
    engine, state = setup_state(battle=1)
    state.active_player = 0
    state.players[0].hand.clear()
    state.players[1].hand.clear()
    state.players[1].deck.clear()
    state.players[1].discard.clear()

    engine.apply(state, Pass())
    assert state.closing_turns_remaining == 2
    assert state.active_player == 1

    assert engine.legal_actions(state) == [EndTurn()]
    engine.apply(state, EndTurn())
    assert state.closing_turns_remaining == 1
    assert state.active_player == 0

    # The passer gets the second closing turn and may end it voluntarily even
    # if their start-of-turn draw creates a legal Action.
    assert EndTurn() in engine.legal_actions(state)
    engine.apply(state, EndTurn())

    assert state.battle == 2
    assert state.pass_order == []
    assert state.players[0].passed is False
    assert state.active_player == 1

def test_closing_turn_with_no_action_ends_without_a_second_pass() -> None:
    engine, state = setup_state(battle=1)
    state.active_player = 0
    state.players[0].hand.clear()
    state.players[1].hand.clear()
    state.players[1].deck.clear()
    state.players[1].discard.clear()

    engine.apply(state, Pass())

    assert state.active_player == 1
    assert state.pass_order == [0]
    assert Pass() not in engine.legal_actions(state)
    assert engine.legal_actions(state) == [EndTurn()]

def test_battle_ends_after_closing_turns_and_non_passer_starts_next() -> None:
    engine, state = setup_state(battle=1)
    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    assert state.active_player == 1
    assert state.pass_order == []
    assert state.players[0].passed is False
    assert state.players[1].passed is False


def test_turn_allows_up_to_two_actions_and_voluntary_end_turn() -> None:
    engine, state = setup_state()
    state.active_player = 0
    state.players[0].hand = ["the-fifty-men", "the-red-shields"]
    state.players[0].command = 20

    first = PlayForce("the-fifty-men", pos(1, Rank.FRONT))
    second = PlayForce("the-red-shields", pos(2, Rank.FRONT))
    assert first in engine.legal_actions(state)
    assert EndTurn() in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, EndTurn()) == 0

    engine.apply(state, first)
    assert state.active_player == 0
    assert state.actions_this_turn == 1
    assert second in engine.legal_actions(state)
    assert EndTurn() in engine.legal_actions(state)

    engine.apply(state, second)
    assert state.active_player == 1
    assert state.actions_this_turn == 0


def test_cycle_discards_two_and_draws_one_as_one_action() -> None:
    engine, state = setup_state()
    state.active_player = 0
    state.players[0].hand = ["followed", "namar"]
    state.players[0].deck = ["the-fifty-men"]
    state.players[0].discard.clear()

    cycle = Cycle("followed", "namar")
    assert cycle in engine.legal_actions(state)
    engine.apply(state, cycle)

    assert state.players[0].hand == ["the-fifty-men"]
    assert Counter(state.players[0].discard) == Counter(["followed", "namar"])
    assert state.actions_this_turn == 1
    assert state.active_player == 0

def test_turn_at_hand_limit_draws_then_requires_overflow_discard() -> None:
    rules = GameRules.standard()
    rules = rules.with_overrides(opening_hand_size=rules.hand_limit)
    engine, state = setup_state(opening_bonus=True, rules=rules)
    assert len(state.players[0].hand) == engine.hand_limit + 1
    assert state.pending_draw_discard_for == 0

    legal = engine.legal_actions(state)
    assert legal
    assert all(isinstance(action, Discard) for action in legal)

    discarded = legal[0].card_id
    deck_after_draw = len(state.players[0].deck)
    engine.apply(state, legal[0])

    assert state.pending_draw_discard_for is None
    assert len(state.players[0].hand) == engine.hand_limit
    assert len(state.players[0].deck) == deck_after_draw
    assert discarded in state.players[0].discard
    assert state.active_player == 0


def test_completion_draw_resolves_before_the_next_players_turn_draw() -> None:
    engine, state = setup_state()
    state.active_player = 0
    state.players[0].hand = (
        ["the-fifty-men"] * (engine.hand_limit - 1) + ["oren"]
    )
    state.players[0].deck = ["the-red-shields", "seven-black-ships"]
    # Avoid conflating Oren's completion draw with player 1's ordinary
    # turn-start hand-limit cleanup after the operation finishes.
    state.players[1].hand = []
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    deck_before = len(state.players[0].deck)

    engine.apply(state, PlayName("oren", target))

    assert state.pending_draw_discard_for is None
    assert state.pending_draw_count == 0
    assert state.pending_draw_finish_operation is False
    assert len(state.players[0].hand) == engine.hand_limit
    assert len(state.players[0].deck) == deck_before - 1
    assert state.active_player == 0
    assert state.actions_this_turn == 1


def test_unnamed_host_requires_open_bond_to_maneuver_unnamed() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
    state.slot(0, source).force = "the-unnamed-host"

    assert Maneuver(source, destination) not in engine.legal_actions(state)

    state.slot(0, source).bond = "followed"
    assert Maneuver(source, destination) in engine.legal_actions(state)


def test_hero_retinue_bond_allows_unnamed_maneuver_only_when_adjacent_to_hero() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
    state.slot(0, source).force = "the-fifty-men"
    state.slot(0, source).bond = "marched-beneath-the-banner-of"

    assert Maneuver(source, destination) not in engine.legal_actions(state)

    state.slot(0, pos(0, Rank.FRONT)).force = "avaros-the-bronze-king"
    assert Maneuver(source, destination) in engine.legal_actions(state)



def test_lost_front_does_not_trigger_legacy_breakthrough_replacement() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT), force="the-iron-boars", temporary=10)
    make_named(state, 1, pos(0, Rank.FRONT))

    resolve_battle_by_passing(engine, state)

    assert state.slot(1, pos(0, Rank.FRONT)).named is True
    assert state.slot(1, pos(0, Rank.REAR)).occupied is False

def test_open_bond_first_maneuver_is_free_only_once_per_battle() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    right = pos(2, Rank.FRONT)
    state.slot(0, source).force = "the-unnamed-host"
    state.slot(0, source).bond = "followed"

    maneuver = Maneuver(source, right)
    assert maneuver in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, maneuver) == 0

    engine.apply(state, maneuver)
    state.active_player = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    back = Maneuver(right, source)
    assert back in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, back) == 1


def test_arel_first_maneuver_is_free_while_controller_has_empty_front() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    right = pos(2, Rank.FRONT)
    make_named(state, 0, source, name="arel")

    maneuver = Maneuver(source, right)
    assert engine.command_cost_for_action(state, maneuver) == 0


def test_iven_discounts_card_in_its_front_while_behind_on_command() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT), name="iven")
    state.players[0].command = 5
    state.players[1].command = 10
    state.players[0].hand = ["the-fifty-men"]

    action = PlayForce("the-fifty-men", pos(0, Rank.REAR))
    assert action in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, action) == 1


def test_tovan_name_discount_applies_only_to_first_card_in_front_each_battle() -> None:
    engine, state = setup_state()
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        name="tovan-the-quartermaster",
    )
    state.players[0].hand = ["the-fifty-men", "oren"]

    first = PlayForce("the-fifty-men", pos(0, Rank.REAR))
    assert engine.command_cost_for_action(state, first) == 1
    engine.apply(state, first)

    state.active_player = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    second = PlayName("oren", pos(0, Rank.REAR))
    assert second in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, second) == 2


def test_yara_discounts_only_first_narrative_each_battle() -> None:
    engine, state = setup_state()
    state.slot(0, pos(0, Rank.REAR)).force = "yara-the-chronicler"
    state.players[0].hand = [
        "before-sunset-the-ford-would-be-ours",
        "no-road-was-too-long",
    ]

    first = PlayNarrative(
        "before-sunset-the-ford-would-be-ours",
        ongoing_slot=0,
        fronts=(Front.FIRST,),
    )
    assert first in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, first) == 1
    engine.apply(state, first)

    state.active_player = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    second = PlayNarrative("no-road-was-too-long", ongoing_slot=1)
    assert second in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, second) == 2


def test_long_march_regains_command_only_on_first_maneuver_into_empty_each_battle() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.narratives[0] = [NarrativeState("the-long-march")]
    first = pos(1, Rank.FRONT)
    second = pos(2, Rank.FRONT)
    third = pos(3, Rank.FRONT)
    make_named(state, 0, first)

    engine.apply(state, Maneuver(first, second))

    assert state.players[0].command == 5
    assert state.narratives[0][0].triggered_this_battle is True

    state.active_player = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    engine.apply(state, Maneuver(second, third))

    assert state.players[0].command == 4


def test_named_narrative_trigger_regains_command_and_discards_itself() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.narratives[0] = [NarrativeState("they-returned-with-names")]
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    state.players[0].hand = ["asha-the-shield-bearer"]

    engine.apply(state, PlayName("asha-the-shield-bearer", target))

    assert state.players[0].command == 5
    assert state.narratives[0] == []
    assert "they-returned-with-names" in state.players[0].discard


def test_opposing_named_narrative_trigger_belongs_to_other_player() -> None:
    engine, state = setup_state()
    state.players[1].command = 5
    state.narratives[1] = [NarrativeState("they-were-gathering-there")]
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    state.players[0].hand = ["asha-the-shield-bearer"]

    engine.apply(state, PlayName("asha-the-shield-bearer", target))

    assert state.players[1].command == 6
    assert state.narratives[1] == []
    assert "they-were-gathering-there" in state.players[1].discard


def test_muster_false_triggers_when_opponent_fills_both_ranks_of_front() -> None:
    engine, state = setup_state()
    state.players[1].command = 5
    state.narratives[1] = [NarrativeState("the-muster-was-false")]
    state.slot(0, pos(0, Rank.REAR)).force = "the-fifty-men"
    state.players[0].hand = ["the-fifty-men"]

    engine.apply(state, PlayForce("the-fifty-men", pos(0, Rank.FRONT)))

    assert state.players[1].command == 6
    assert state.narratives[1] == []
    assert "the-muster-was-false" in state.players[1].discard


def test_bought_time_for_can_pay_extra_to_draw_two_with_sequential_hand_limit() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    state.players[0].command = 10
    state.players[0].hand = (
        ["bought-time-for"]
        + ["the-fifty-men"] * (engine.hand_limit - 1)
    )
    state.players[0].deck = ["seven-black-ships", "the-red-shields"]
    # Let player 1's normal turn-start draw resolve immediately after the
    # invested operation finishes.
    state.players[1].hand = []

    normal = PlayBond("bought-time-for", target)
    invested = PlayBond("bought-time-for", target, extra_payment=1)
    legal = engine.legal_actions(state)
    assert normal in legal
    assert invested in legal
    assert engine.command_cost_for_action(state, normal) == 1
    assert engine.command_cost_for_action(state, invested) == 2

    engine.apply(state, invested)

    assert state.players[0].command == 8
    assert len(state.players[0].hand) == engine.hand_limit + 1
    assert state.pending_draw_discard_for == 0
    assert state.pending_draw_count == 0
    assert state.pending_draw_finish_operation is True

    engine.apply(state, engine.legal_actions(state)[0])
    assert len(state.players[0].hand) == engine.hand_limit
    assert state.pending_draw_discard_for is None
    assert state.active_player == 0
    assert state.actions_this_turn == 1


def test_baggage_warning_can_discard_another_card_to_regain_command() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.players[0].hand = [
        "the-baggage-was-abandoned",
        "the-fifty-men",
    ]

    decline = PlayNarrative("the-baggage-was-abandoned")
    trade = PlayNarrative(
        "the-baggage-was-abandoned",
        discard_card_id="the-fifty-men",
    )
    legal = engine.legal_actions(state)
    assert decline in legal
    assert trade in legal

    engine.apply(state, trade)

    assert state.players[0].command == 6
    assert "the-fifty-men" in state.players[0].discard
    assert "the-baggage-was-abandoned" in state.players[0].discard


@pytest.mark.parametrize(
    "destination",
    [
        pos(2, Rank.FRONT),
        pos(1, Rank.MIDDLE),
    ],
)
def test_marched_with_can_move_formation_when_played_onto_force(
    destination: Position,
) -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    state.slot(0, source).force = "the-fifty-men"
    state.players[0].hand = ["marched-with"]

    decline = PlayBond("marched-with", source)
    move = PlayBond(
        "marched-with",
        source,
        move_destination=destination,
    )
    legal = engine.legal_actions(state)
    assert decline in legal
    assert move in legal

    engine.apply(state, move)

    assert state.slot(0, source).force is None
    assert state.slot(0, source).bond is None
    assert state.slot(0, destination).force == "the-fifty-men"
    assert state.slot(0, destination).bond == "marched-with"


def test_trusted_bond_refunds_command_when_formation_becomes_named() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    state.players[0].command = 5
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "trusted"
    state.players[0].hand = ["asha-the-shield-bearer"]

    engine.apply(state, PlayName("asha-the-shield-bearer", target))

    assert state.slot(0, target).named is True
    assert state.players[0].command == 5



def test_lost_front_does_not_trigger_legacy_stronghold_retreat_replacement() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 0, pos(0, Rank.REAR), force="the-house-of-reed")
    make_named(state, 1, pos(0, Rank.FRONT), temporary=20)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.REAR)).force == "the-house-of-reed"
    assert state.slot(0, pos(0, Rank.FRONT)).named is True

def test_blocked_road_prevents_opponent_card_move_into_its_front() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    state.slot(0, source).force = "the-fifty-men"
    state.slot(1, pos(1, Rank.REAR)).force = "the-fifty-men"
    state.slot(1, pos(1, Rank.REAR)).bond = "blocked-the-road-for"
    state.players[0].hand = ["marched-with"]

    blocked_move = PlayBond(
        "marched-with",
        source,
        move_destination=destination,
    )
    assert blocked_move not in engine.legal_actions(state)
    assert PlayBond("marched-with", source) in engine.legal_actions(state)


def test_immobile_force_cannot_be_moved_by_line_wheeled() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.REAR)
    state.slot(0, source).force = "the-house-of-reed"
    state.players[0].hand = ["the-line-wheeled"]

    actions = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayStratagem)
        and action.card_id == "the-line-wheeled"
    ]
    assert actions
    assert all(
        all(target.position != source for target in action.targets)
        for action in actions
    )


def test_battle_only_temporary_strength_resets_after_battle() -> None:
    engine, state = setup_state(battle=1)
    target = pos(1, Rank.FRONT)
    make_named(state, 0, target, temporary=4)

    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    assert state.slot(0, target).complete is True
    assert state.slot(0, target).temporary_strength == 0


def test_battle_resolves_four_fronts_independently_without_battle_winner() -> None:
    engine, state = setup_state(battle=3)

    make_named(state, 0, pos(0))
    make_named(state, 1, pos(1))
    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert len(snapshot["front_scores"]) == 4
    assert snapshot["front_results"] == [0, 1, None, None]
    assert snapshot["fronts_lost"] == [1, 1]
    assert "winner" not in snapshot
    assert state.winner is None
    assert state.battle == 4



def test_incomplete_formations_and_prepared_cards_persist_between_battles() -> None:
    engine, state = setup_state()
    incomplete = state.slot(0, pos(3))
    incomplete.force = "the-fifty-men"
    incomplete.bond = "followed"

    prepared_bond = state.slot(0, pos(2, Rank.MIDDLE))
    prepared_bond.bond = "swore-again-to"
    prepared_name = state.slot(0, pos(1, Rank.REAR))
    prepared_name.name = "namar"

    resolve_battle_by_passing(engine, state)

    persisted = state.slot(0, pos(3))
    assert persisted.force == "the-fifty-men"
    assert persisted.bond == "followed"
    assert persisted.name is None
    assert state.slot(0, pos(2, Rank.MIDDLE)).bond == "swore-again-to"
    assert state.slot(0, pos(2, Rank.MIDDLE)).force is None
    assert state.slot(0, pos(1, Rank.REAR)).name == "namar"
    assert state.slot(0, pos(1, Rank.REAR)).force is None
    assert "the-fifty-men" not in state.players[0].discard
    assert "followed" not in state.players[0].discard
    assert "swore-again-to" not in state.players[0].discard
    assert "namar" not in state.players[0].discard


def test_battle_resolution_leaves_all_battlefield_positions_in_place() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)
    make_named(state, 0, pos(1, Rank.REAR), force="seven-black-ships")
    make_named(state, 1, pos(1, Rank.FRONT), temporary=100)
    make_named(state, 0, pos(2, Rank.FRONT))
    make_named(state, 0, pos(2, Rank.REAR), force="seven-black-ships")
    make_named(state, 1, pos(2, Rank.FRONT), temporary=100)
    make_named(state, 0, pos(3, Rank.FRONT))
    make_named(state, 1, pos(3, Rank.FRONT))

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.FRONT)).named is True
    assert state.slot(0, pos(0, Rank.REAR)).occupied is False
    assert state.slot(0, pos(1, Rank.REAR)).force == "seven-black-ships"
    assert state.slot(0, pos(2, Rank.FRONT)).named is True
    assert state.slot(0, pos(2, Rank.REAR)).force == "seven-black-ships"
    assert state.slot(0, pos(3, Rank.FRONT)).named is True


def test_lost_front_does_not_drive_off_persistent_bonds_or_names() -> None:
    engine, state = setup_state(seed=4690)
    target = pos(0, Rank.REAR)
    make_named(
        state,
        0,
        target,
        force="seven-black-ships",
        bond="stayed-behind-for",
        name="namar",
    )
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    slot = state.slot(0, target)
    assert slot.force == "seven-black-ships"
    assert slot.bond == "stayed-behind-for"
    assert slot.name == "namar"


def test_lost_front_does_not_trigger_retreat_bond_side_effects() -> None:
    engine, state = setup_state(seed=4692)
    state.players[0].command = 10
    state.battle_start_command[0] = 10
    target = pos(0, Rank.FRONT)
    make_named(state, 0, target, bond="endured-with")
    make_named(state, 1, target, temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, target).bond == "endured-with"
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_refunded"][0] == 0


def test_core_resolution_never_invokes_explicit_retreat_side_effects() -> None:
    engine, state = setup_state(seed=4691)
    target = pos(0, Rank.FRONT)
    make_named(state, 0, target, bond="endured-with")
    make_named(state, 1, target, temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, target).bond == "endured-with"
    assert state.slot(0, pos(0, Rank.REAR)).occupied is False

def test_maneuver_accepts_prepared_destination_but_rejects_immobile_force() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    make_named(state, 0, source)
    state.slot(0, destination).bond = "followed"

    # Core Maneuver may swap with any own occupied position, including a
    # prepared-only Bond/Name position.
    assert Maneuver(source, destination) in engine.legal_actions(state)

    reed = pos(2, Rank.REAR)
    make_named(state, 0, reed, force="the-house-of-reed")
    assert not any(
        isinstance(action, Maneuver) and action.source == reed
        for action in engine.legal_actions(state)
    )


def test_explicit_unnamed_maneuver_and_all_banners_forward() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    state.slot(0, source).force = "the-grey-riders"
    assert Maneuver(source, destination) in engine.legal_actions(state)

    state.slot(0, source).force = "the-fifty-men"
    assert Maneuver(source, destination) not in engine.legal_actions(state)

    state.stratagems[0] = StratagemState("all-banners-forward")
    action = Maneuver(source, destination)
    assert action in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, action) == 0


def test_rallied_behind_sorin_and_rear_support_use_printed_costs() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    state.players[0].hand = ["rallied-behind", "sorin", "the-fifty-men"]
    state.players[0].command = 5
    state.players[1].command = 10

    assert engine.command_cost_for_action(
        state, PlayBond("rallied-behind", target)
    ) == 0

    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    assert engine.command_cost_for_action(state, PlayName("sorin", target)) == 1

    state.slot(0, target).force = None
    state.slot(0, target).bond = None
    state.slot(0, target).name = None
    state.slot(0, pos(0, Rank.REAR)).force = "nara-builder-of-walls"
    assert engine.command_cost_for_action(
        state, PlayForce("the-fifty-men", target)
    ) == 1


def test_red_duelists_ignore_rear_strength_during_front_resolution() -> None:
    engine, state = setup_state()
    state.slot(0, pos(0, Rank.FRONT)).force = "the-red-duelists"
    state.slot(0, pos(0, Rank.MIDDLE)).force = "the-fifty-men"
    state.slot(0, pos(0, Rank.REAR)).force = "seven-black-ships"
    state.slot(1, pos(0, Rank.FRONT)).force = "the-fifty-men"
    state.slot(1, pos(0, Rank.MIDDLE)).force = "the-fifty-men"
    state.slot(1, pos(0, Rank.REAR)).force = "seven-black-ships"

    resolve_battle_by_passing(engine, state)

    # Red Duelists suppress only Rear Strength. Middle/Support still counts.
    assert state.last_battle_snapshot["front_scores"][0] == [7, 8]


def test_ground_was_held_breaks_tie_only_for_single_frontline_named_side() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.REAR))
    state.stratagems[0] = StratagemState("the-ground-was-held")

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["fronts_lost"][1] >= 1
    assert state.last_battle_snapshot["fronts_lost"][0] == 0


def test_lines_held_and_tovan_reduce_front_command_loss_penalty() -> None:
    engine, state = setup_state()
    battle = state.battle
    state.players[0].command = 5
    state.players[1].command = 20
    state.battle_start_command[:] = [5, 20]
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)
    state.stratagems[0] = StratagemState("the-lines-held")

    resolve_battle_by_passing(engine, state)
    expected = min(
        engine.rules.command_cap,
        5 + max(
            engine.rules.command_recovery_floor,
            engine.command_recovery_for_battle(battle),
        ),
    )
    assert state.players[0].command == expected

    engine, state = setup_state(seed=4702)
    battle = state.battle
    state.players[0].command = 5
    state.players[1].command = 20
    state.battle_start_command[:] = [5, 20]
    state.slot(0, pos(0, Rank.REAR)).force = "tovan-the-quartermaster"
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)
    expected = min(
        engine.rules.command_cap,
        5 + max(
            engine.rules.command_recovery_floor,
            engine.command_recovery_for_battle(battle),
        ),
    )
    assert state.players[0].command == expected


def test_targeted_stratagem_play_choices_are_legal_actions() -> None:
    engine, state = setup_state(seed=4710)
    state.players[0].hand = [
        "no-step-back",
        "the-center-must-hold",
        "the-flank-was-refused",
        "the-battle-turned-east",
    ]
    state.players[0].command = 20

    legal = engine.legal_actions(state)

    assert PlayStratagem(
        "no-step-back",
        fronts=(Front.FIRST,),
    ) in legal
    assert PlayStratagem(
        "the-center-must-hold",
        fronts=(Front.SECOND, Front.THIRD),
    ) in legal
    assert PlayStratagem(
        "the-flank-was-refused",
        fronts=(Front.FOURTH,),
    ) in legal
    assert PlayStratagem(
        "the-battle-turned-east",
        direction="left",
    ) in legal
    assert PlayStratagem(
        "the-battle-turned-east",
        direction="right",
    ) in legal


@pytest.mark.parametrize(
    "action",
    [
        PlayStratagem(
            "there-was-no-road-back",
            fronts=(Front.SECOND,),
        ),
        PlayStratagem(
            "every-banner-turned-toward-them",
            fronts=(Front.SECOND,),
        ),
        PlayStratagem(
            "the-line-had-begun-to-move",
            direction="right",
        ),
    ],
)
def test_stratagem_reveals_when_its_hidden_identity_would_constrain_opponent(
    action: PlayStratagem,
) -> None:
    engine, state = setup_state(seed=47101)
    state.players[0].hand = [action.card_id]
    state.players[0].command = 20

    assert action in engine.legal_actions(state)
    engine.apply(state, action)

    assert state.stratagems[0] is not None
    assert state.stratagems[0].revealed is True


def test_battle_turned_east_makes_only_chosen_direction_free() -> None:
    engine, state = setup_state(seed=4711)
    source = pos(1)
    make_named(state, 0, source)
    state.stratagems[0] = StratagemState(
        "the-battle-turned-east",
        direction="right",
    )

    chosen = Maneuver(source, pos(2))
    assert engine.command_cost_for_action(state, chosen) == 0
    assert engine.command_cost_for_action(
        state,
        Maneuver(source, pos(0)),
    ) == 1

    assert state.stratagems[0].revealed is False
    engine.apply(state, chosen)
    assert state.stratagems[0].revealed is True



def test_no_step_back_does_not_create_core_lost_front_removal() -> None:
    engine, state = setup_state(seed=4712)
    state.stratagems[0] = StratagemState(
        "no-step-back",
        fronts=(Front.FIRST,),
    )
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.FRONT)).named is True
    assert "the-fifty-men" not in state.players[0].discard

def _pause_resolution_on_battle_end_draw(state) -> None:
    """Arrange a public Battle-end draw that pauses before Stratagem discard."""
    target = pos(3, Rank.REAR)
    make_named(state, 0, target)
    state.narratives[0] = [
        NarrativeState(
            "they-lived-to-tell-it",
            target_player=0,
            target_position=target,
        )
    ]
    # Player 0 draws once in the closing sequence, reaching the hand limit.
    # The Saga's Battle-end draw must then create overflow and pause for cleanup.
    state.players[0].hand[:] = state.players[0].hand[:9]


def test_conditional_stratagem_stays_hidden_when_battle_end_effect_does_not_fire() -> None:
    engine, state = setup_state(seed=47121)
    state.stratagems[0] = StratagemState("the-lines-held")
    _pause_resolution_on_battle_end_draw(state)

    resolve_battle_by_passing(engine, state)

    assert state.pending_draw_discard_for == 0
    assert state.stratagems[0] is not None
    assert state.stratagems[0].revealed is False


def test_conditional_stratagem_reveals_when_battle_end_effect_fires() -> None:
    engine, state = setup_state(seed=47122)
    state.stratagems[0] = StratagemState("the-lines-held")
    make_named(state, 1, pos(0), temporary=100)
    _pause_resolution_on_battle_end_draw(state)

    resolve_battle_by_passing(engine, state)

    assert state.pending_draw_discard_for == 0
    assert state.stratagems[0] is not None
    assert state.stratagems[0].revealed is True
    assert state.battle_resolution["front_loss_command_penalty"][0] == 0


def test_center_must_hold_resolves_chosen_pair_by_combined_strength() -> None:
    engine, state = setup_state(seed=4713)
    state.stratagems[0] = StratagemState(
        "the-center-must-hold",
        fronts=(Front.FIRST, Front.SECOND),
    )
    make_named(state, 0, pos(0), temporary=2)
    make_named(state, 1, pos(1))

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["front_results"][:2] == [0, 0]


def test_flank_refused_ignores_edge_and_bonuses_adjacent_formations() -> None:
    engine, state = setup_state(seed=4714)
    state.stratagems[0] = StratagemState(
        "the-flank-was-refused",
        fronts=(Front.FIRST,),
    )
    make_named(state, 0, pos(0))
    make_named(state, 0, pos(1, Rank.FRONT))
    make_named(state, 0, pos(1, Rank.REAR), force="seven-black-ships")

    raw_adjacent_strength = engine.front_strength(
        state, 0, Front.SECOND
    )
    resolve_battle_by_passing(engine, state)

    scores = state.last_battle_snapshot["front_scores"]
    assert scores[0][0] == 0
    assert scores[1][0] == raw_adjacent_strength + 2


def test_trap_closed_drives_off_encircled_middle_frontline() -> None:
    engine, state = setup_state(seed=4715)
    state.stratagems[0] = StratagemState("the-trap-closed")
    for front in range(3):
        make_named(state, 0, pos(front), temporary=100)
    make_named(state, 1, pos(1))

    resolve_battle_by_passing(engine, state)

    assert state.slot(1, pos(1, Rank.FRONT)).occupied is False
    assert state.slot(1, pos(1, Rank.REAR)).occupied is False


@pytest.mark.parametrize("battle", range(1, 10))
def test_command_recovery_formula(battle: int) -> None:
    rules = GameRules.standard().with_overrides(
        starting_command=20,
        command_cap=100,
        command_collapse_threshold=0,
    )
    engine, state = setup_state(seed=4200 + battle, rules=rules)
    initial_command = 10
    state.battle = battle
    state.players[0].command = initial_command
    state.players[1].command = initial_command
    state.battle_start_command[:] = [initial_command, initial_command]

    resolve_battle_by_passing(engine, state)

    actual_recovery = max(
        rules.command_recovery_floor,
        rules.command_recovery_for_battle(battle),
    )
    expected = initial_command + actual_recovery
    assert state.players[0].command == expected
    assert state.players[1].command == expected


def test_command_recovery_loses_one_per_lost_front_and_caps_at_configured_limit() -> None:
    rules = GameRules.standard().with_overrides(
        starting_command=20,
        command_cap=20,
    )
    engine, state = setup_state(rules=rules)
    state.players[0].command = 5
    state.players[1].command = rules.command_cap - 1
    state.battle_start_command[:] = [5, rules.command_cap - 1]

    make_named(state, 1, pos(0))
    make_named(state, 1, pos(1))

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["fronts_lost"] == [2, 0]
    base = engine.command_recovery_for_battle(state.last_battle_snapshot["battle"])
    expected_p0 = min(
        engine.rules.command_cap,
        max(0, 5 - 2) + max(engine.rules.command_recovery_floor, base),
    )
    expected_p1 = min(
        engine.rules.command_cap,
        (rules.command_cap - 1) + max(engine.rules.command_recovery_floor, base),
    )
    assert state.players[0].command == expected_p0
    assert state.players[1].command == expected_p1


def test_command_collapse_lower_command_loses_and_equal_threshold_uses_first_passer() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        command_recovery_start=0,
        command_recovery_decrement=0,
        command_recovery_floor=1,
    )
    engine, state = setup_state(rules=rules, battle=1)
    state.players[0].command = 0
    state.players[1].command = 6
    state.battle_start_command[:] = [0, 6]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.COMPLETE
    assert state.winner == 1

    engine, state = setup_state(seed=4301, rules=rules, battle=1)
    state.players[0].command = 0
    state.players[1].command = 0
    state.battle_start_command[:] = [0, 0]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.COMPLETE
    assert state.winner == 1
    assert state.battle == 1


def test_hand_deck_discard_and_named_formations_persist_between_battles() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0))
    state.players[0].discard.append(state.players[0].hand.pop())
    # Restore the configured hand-limit size so Battle-end refill does not move cards.
    state.players[0].hand.append(state.players[0].deck.pop())
    cards_before = Counter(
        state.players[0].hand
        + state.players[0].deck
        + state.players[0].discard
    )
    discarded_before = Counter(state.players[0].discard)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0)).complete is True
    cards_after = Counter(
        state.players[0].hand
        + state.players[0].deck
        + state.players[0].discard
    )
    assert cards_after == cards_before
    assert Counter(state.players[0].discard) >= discarded_before


def test_empty_draw_pile_reshuffles_discard_only_when_draw_is_required() -> None:
    engine, state = setup_state()
    state.players[0].hand.clear()
    state.players[1].hand = ["the-fifty-men"] * (engine.hand_limit - 1)
    state.players[1].deck.clear()
    state.players[1].discard = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    engine.apply(state, Pass())

    assert len(state.players[1].hand) == engine.hand_limit
    assert state.players[1].discard == []
    assert state.deck_reshuffles[1] == 1


def test_ongoing_narrative_slot_does_not_receive_adjacent_front_discount() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    slot = state.slot(0, target)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "elian"
    state.players[0].hand = ["the-long-march"]
    state.players[0].command = 20

    narrative = PlayNarrative("the-long-march", ongoing_slot=0)
    assert narrative in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, narrative) == 2


def test_ongoing_narratives_are_public_and_respect_configured_limit() -> None:
    rules = GameRules.standard().with_overrides(ongoing_narrative_limit=2)
    engine, state = setup_state(rules=rules)
    assert engine.ongoing_narrative_limit == rules.ongoing_narrative_limit
    narratives = [
        "the-long-march",
        "they-returned-with-names",
        "the-crows-came-down",
    ]
    state.players[0].hand = list(narratives)
    state.players[0].command = 20
    state.players[1].hand = []

    first = PlayNarrative(narratives[0], ongoing_slot=0)
    assert first in engine.legal_actions(state)
    engine.apply(state, first)

    state.active_player = 0
    second = PlayNarrative(narratives[1], ongoing_slot=1)
    assert second in engine.legal_actions(state)
    engine.apply(state, second)

    assert [narrative.card_id for narrative in state.narratives[0]] == narratives[:2]
    state.active_player = 0
    legal = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayNarrative) and action.card_id == narratives[2]
        for action in legal
    )



def test_hero_force_and_name_allowances_are_separate_once_per_battle() -> None:
    engine, state = setup_state()
    hero_force = "avaros-the-bronze-king"
    hero_name = "kael-the-roadless"
    state.players[0].hand = [
        hero_force,
        hero_name,
        "the-ground-was-held",
        "the-lines-held",
    ]
    # Avoid an unrelated post-draw hand-limit pause when Action 2 hands the
    # turn to player 1.
    state.players[1].hand.clear()
    state.players[0].command = 20

    force_action = PlayForce(hero_force, pos(1, Rank.FRONT))
    assert force_action in engine.legal_actions(state)
    engine.apply(state, force_action)
    assert state.hero_used[0] & 1
    assert not state.hero_used[0] & 2

    legal = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayForce) and action.card_id == hero_name
        for action in legal
    )
    name_action = PlayName(hero_name, pos(2, Rank.FRONT))
    assert name_action in legal
    engine.apply(state, name_action)
    assert state.hero_used[0] == 3

    state.active_player = 0
    state.actions_this_turn = 0
    first_stratagem = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayStratagem)
        and action.card_id == "the-ground-was-held"
    )
    engine.apply(state, first_stratagem)
    assert state.stratagem_used[0] == 1

    state.active_player = 0
    state.actions_this_turn = 0
    assert not any(
        isinstance(action, PlayStratagem)
        and action.card_id == "the-lines-held"
        for action in engine.legal_actions(state)
    )


def test_non_passer_starts_next_battle() -> None:
    engine, state = setup_state(battle=1)
    resolve_battle_by_passing(engine, state)
    assert state.battle == 2
    assert state.active_player == 1

def test_iria_makes_only_the_next_maneuver_free() -> None:
    engine, state = setup_state(seed=4801)
    make_named(state, 0, pos(0, Rank.FRONT), name="iria")
    state.slot(1, pos(0, Rank.FRONT)).force = "the-fifty-men"
    state.slot(1, pos(0, Rank.FRONT)).bond = "followed"
    state.players[0].hand = []
    state.players[0].command = 5
    state.players[1].hand = ["namar"]
    state.players[1].command = 5
    state.active_player = 1

    engine.apply(state, PlayName("namar", pos(0, Rank.FRONT)))

    assert state.free_maneuver_available[0] is True
    # The opponent has used only Action 1. End their turn so Iria's
    # controller becomes the actor before checking the stored discount.
    engine.apply(state, EndTurn())
    assert state.active_player == 0
    maneuver = Maneuver(pos(0, Rank.FRONT), pos(1, Rank.FRONT))
    assert maneuver in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, maneuver) == 0

    engine.apply(state, maneuver)
    assert state.free_maneuver_available[0] is False
    assert any(
        event["kind"] == "discount"
        and event["detail"] == "free_maneuver"
        and event["source_card"] == "iria"
        for event in engine.last_command_diagnostics()
    )


def test_elian_completion_exposes_optional_adjacent_swap() -> None:
    engine, state = setup_state(seed=4802)
    make_named(state, 0, pos(0, Rank.FRONT))
    target = state.slot(0, pos(1, Rank.FRONT))
    target.force = "seven-black-ships"
    target.bond = "stood-fast-with"
    state.players[0].hand = ["elian"]

    engine.apply(state, PlayName("elian", pos(1, Rank.FRONT)))

    choices = effect_choices(engine, state, "swap")
    assert any(choice.skip for choice in choices)
    swap = next(choice for choice in choices if not choice.skip)
    engine.apply(state, swap)

    assert state.slot(0, pos(0, Rank.FRONT)).name == "elian"
    assert state.slot(0, pos(1, Rank.FRONT)).name == "namar"


def test_veyra_force_can_take_an_adjacent_prepared_component() -> None:
    engine, state = setup_state(seed=4803)
    state.slot(0, pos(0, Rank.FRONT)).bond = "stood-fast-with"
    state.players[0].hand = ["veyra-keeper-of-oaths"]

    engine.apply(
        state,
        PlayForce("veyra-keeper-of-oaths", pos(1, Rank.FRONT)),
    )

    choices = effect_choices(engine, state, "transfer-component")
    transfer = next(
        choice
        for choice in choices
        if not choice.skip and choice.card_id == "stood-fast-with"
    )
    engine.apply(state, transfer)

    assert state.slot(0, pos(0, Rank.FRONT)).bond is None
    assert state.slot(0, pos(1, Rank.FRONT)).bond == "stood-fast-with"


def test_late_banner_gets_its_free_maneuver_even_while_unnamed() -> None:
    engine, state = setup_state(seed=4804)
    state.slot(0, pos(1, Rank.FRONT)).bond = "followed"
    state.players[0].hand = ["the-late-banner"]

    engine.apply(state, PlayForce("the-late-banner", pos(1, Rank.FRONT)))

    choices = effect_choices(engine, state, "free-maneuver")
    choice = next(choice for choice in choices if not choice.skip)
    engine.apply(state, choice)

    assert any(
        event["kind"] == "discount"
        and event["detail"] == "free_maneuver"
        and event["source_card"] == "the-late-banner"
        for event in engine.last_command_diagnostics()
    )


def test_carried_oath_can_transfer_after_unnamed_force_maneuvers() -> None:
    engine, state = setup_state(seed=4805)
    source = pos(0, Rank.FRONT)
    arrived = pos(1, Rank.FRONT)
    receiver = pos(2, Rank.FRONT)
    state.slot(0, source).force = "the-grey-riders"
    state.slot(0, source).bond = "carried-the-oath-of"
    state.slot(0, receiver).force = "the-fifty-men"
    state.players[0].command = 5

    engine.apply(state, Maneuver(source, arrived))

    transfer = next(
        choice
        for choice in effect_choices(engine, state, "transfer-component")
        if not choice.skip
    )
    engine.apply(state, transfer)

    assert state.slot(0, arrived).bond is None
    assert state.slot(0, receiver).bond == "carried-the-oath-of"


def test_grey_riders_choose_which_adjacent_front_gets_their_strength() -> None:
    engine, state = setup_state(seed=4806)
    source = pos(0, Rank.FRONT)
    state.slot(0, source).force = "the-grey-riders"
    expected = engine.position_strength(state, 0, source)

    resolve_battle_by_passing(engine, state)

    choices = effect_choices(engine, state, "front-contribution")
    choice = next(
        action for action in choices if action.front == Front.SECOND
    )
    engine.apply(state, choice)

    scores = state.last_battle_snapshot["front_scores"]
    assert scores[0][0] == 0
    assert scores[1][0] == expected


def test_thornbow_suppression_can_be_redirected_to_asha() -> None:
    engine, state = setup_state(seed=4807)
    make_named(
        state,
        0,
        pos(0, Rank.REAR),
        force="the-thornbow-hunters",
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        name="asha-the-shield-bearer",
    )
    make_named(
        state,
        1,
        pos(0, Rank.REAR),
        force="seven-black-ships",
    )
    rear_strength = engine.position_strength(
        state, 1, pos(0, Rank.REAR)
    )

    resolve_battle_by_passing(engine, state)

    suppress = next(
        action
        for action in effect_choices(engine, state, "suppress")
        if not action.skip
    )
    engine.apply(state, suppress)

    intercept = next(
        action
        for action in effect_choices(engine, state, "intercept")
        if not action.skip
    )
    engine.apply(state, intercept)

    assert state.last_battle_snapshot["front_scores"][0][1] == rear_strength


def test_held_the_line_for_sacrifices_formation_and_suppresses_target() -> None:
    engine, state = setup_state(seed=4808)
    source = pos(0, Rank.FRONT)
    make_named(state, 0, source, bond="held-the-line-for")
    make_named(state, 1, pos(0, Rank.FRONT))
    make_named(
        state,
        1,
        pos(0, Rank.REAR),
        force="seven-black-ships",
    )
    rear_strength = engine.position_strength(
        state, 1, pos(0, Rank.REAR)
    )

    resolve_battle_by_passing(engine, state)

    sacrifice = next(
        action
        for action in effect_choices(engine, state, "sacrifice")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.position == pos(0, Rank.FRONT)
        )
    )
    engine.apply(state, sacrifice)

    assert "held-the-line-for" in state.players[0].discard
    assert state.last_battle_snapshot["front_scores"][0][1] == rear_strength


def test_tala_can_retreat_before_strength_comparison() -> None:
    engine, state = setup_state(seed=4809)
    make_named(state, 0, pos(0, Rank.FRONT), name="tala")

    resolve_battle_by_passing(engine, state)

    retreat = next(
        action
        for action in effect_choices(engine, state, "retreat")
        if not action.skip
    )
    engine.apply(state, retreat)

    assert state.slot(0, pos(0, Rank.FRONT)).occupied is False
    assert state.slot(0, pos(0, Rank.REAR)).name == "tala"


def test_feigned_retreat_swaps_one_front_before_comparison() -> None:
    engine, state = setup_state(seed=4810)
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        force="the-fifty-men",
    )
    make_named(
        state,
        0,
        pos(0, Rank.REAR),
        force="seven-black-ships",
    )
    state.stratagems[0] = StratagemState("they-let-them-through")

    resolve_battle_by_passing(engine, state)

    swap = next(
        action
        for action in effect_choices(engine, state, "swap")
        if not action.skip
    )
    engine.apply(state, swap)

    assert state.slot(0, pos(0, Rank.FRONT)).force == "seven-black-ships"
    assert state.slot(0, pos(0, Rank.REAR)).force == "the-fifty-men"


def test_sela_can_move_sideways_after_explicit_retreat() -> None:
    engine, state = setup_state(seed=4811)
    make_named(state, 0, pos(0, Rank.FRONT), name="sela")

    apply_explicit_retreat(engine, state, 0, Front.FIRST)

    move = next(
        action
        for action in effect_choices(engine, state, "move")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.position == pos(1, Rank.REAR)
        )
    )
    engine.apply(state, move)

    assert state.slot(0, pos(1, Rank.REAR)).name == "sela"


def test_neris_name_can_move_sideways_after_explicit_retreat() -> None:
    engine, state = setup_state(seed=4812)
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        name="neris-the-ferryman",
    )

    apply_explicit_retreat(engine, state, 0, Front.FIRST)

    move = next(
        action
        for action in effect_choices(engine, state, "move")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.position == pos(1, Rank.REAR)
        )
    )
    engine.apply(state, move)

    assert (
        state.slot(0, pos(1, Rank.REAR)).name
        == "neris-the-ferryman"
    )


def test_covered_withdrawal_grants_free_maneuver_after_explicit_adjacent_retreat() -> None:
    engine, state = setup_state(seed=4813)
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(
        state,
        0,
        pos(1, Rank.REAR),
        bond="covered-the-withdrawal-of",
    )

    apply_explicit_retreat(engine, state, 0, Front.FIRST)

    maneuver = next(
        action
        for action in effect_choices(engine, state, "free-maneuver")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.position == pos(2, Rank.REAR)
        )
    )
    engine.apply(state, maneuver)

    assert (
        state.slot(0, pos(2, Rank.REAR)).bond
        == "covered-the-withdrawal-of"
    )


def test_wall_did_not_break_resolves_battle_end_reward_and_recovery() -> None:
    engine, state = setup_state(seed=4814)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[0].hand = []
    state.players[0].discard = ["followed"]
    make_named(state, 0, pos(0, Rank.FRONT))
    state.narratives[0] = [
        NarrativeState(
            "the-wall-did-not-break",
            fronts=(Front.FIRST,),
        )
    ]

    resolve_battle_by_passing(engine, state)

    recover = next(
        action
        for action in effect_choices(engine, state, "recover")
        if not action.skip and action.card_id == "followed"
    )
    engine.apply(state, recover)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_refunded"][0] >= 1
    assert snapshot["command_before_collapse"][0] == 11
    assert state.players[0].command == min(
        engine.rules.command_cap,
        snapshot["command_before_collapse"][0]
        + snapshot["recovery_actual"][0],
    )
    assert "followed" in state.players[0].hand
    assert "the-wall-did-not-break" in state.players[0].discard



def test_return_to_full_hand_triggers_hand_limit_cleanup() -> None:
    engine, state = setup_state(seed=48140)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    # Player 0's closing-turn draw raises this to exactly 10.
    state.players[0].hand = ["the-fifty-men"] * 9
    state.players[0].discard = ["followed"]
    make_named(state, 0, pos(0, Rank.FRONT))
    state.narratives[0] = [
        NarrativeState(
            "the-wall-did-not-break",
            fronts=(Front.FIRST,),
        )
    ]

    resolve_battle_by_passing(engine, state)

    assert len(state.players[0].hand) == engine.hand_limit
    recover = next(
        action
        for action in effect_choices(engine, state, "recover")
        if not action.skip and action.card_id == "followed"
    )
    engine.apply(state, recover)

    assert len(state.players[0].hand) == engine.hand_limit + 1
    assert state.pending_draw_discard_for == 0
    assert all(
        isinstance(action, Discard)
        for action in engine.legal_actions(state)
    )


def test_before_sunset_draws_at_battle_end_and_records_refund() -> None:
    engine, state = setup_state(seed=4815)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[0].hand = []
    make_named(state, 0, pos(0, Rank.FRONT))
    state.narratives[0] = [
        NarrativeState(
            "before-sunset-the-ford-would-be-ours",
            fronts=(Front.FIRST,),
        )
    ]

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot["command_refunded"][0] >= 2
    assert snapshot["cards_drawn"][0] >= 1
    assert "before-sunset-the-ford-would-be-ours" in state.players[0].discard


def test_start_of_battle_move_cannot_enter_inactive_front() -> None:
    engine, state = setup_state(seed=48160, battle=1)
    make_named(state, 0, pos(2, Rank.FRONT), name="meren")

    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    moves = [
        action
        for action in effect_choices(engine, state, "move")
        if not action.skip and action.destination is not None
    ]
    destinations = {
        action.destination.position
        for action in moves
    }

    assert pos(1, Rank.FRONT) in destinations
    assert pos(3, Rank.FRONT) not in destinations


def test_meren_repositions_before_first_turn_of_next_battle() -> None:
    engine, state = setup_state(seed=4816, battle=1)
    make_named(state, 0, pos(1, Rank.FRONT), name="meren")

    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    move = next(
        action
        for action in effect_choices(engine, state, "move")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.position == pos(2, Rank.FRONT)
        )
    )
    engine.apply(state, move)

    assert state.slot(0, pos(2, Rank.FRONT)).name == "meren"


def test_dust_riders_can_fill_the_position_they_vacated() -> None:
    engine, state = setup_state(seed=4820)
    source = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
    follower = pos(0, Rank.FRONT)
    state.slot(0, source).force = "the-dust-riders"
    make_named(state, 0, follower)
    state.players[0].command = 5

    engine.apply(state, Maneuver(source, destination))

    move = next(
        action
        for action in effect_choices(engine, state, "move")
        if (
            not action.skip
            and action.source is not None
            and action.source.position == follower
            and action.destination is not None
            and action.destination.position == source
        )
    )
    engine.apply(state, move)

    assert state.slot(0, source).named is True
    assert state.slot(0, follower).occupied is False


def test_black_company_grants_the_swapped_formation_a_free_maneuver() -> None:
    engine, state = setup_state(seed=4821)
    source = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
    make_named(state, 0, source, force="the-black-company")
    make_named(state, 0, destination, force="seven-black-ships")
    state.players[0].command = 5

    engine.apply(state, Maneuver(source, destination))

    choices = effect_choices(engine, state, "free-maneuver")
    assert any(
        not action.skip
        and action.source is not None
        and action.source.position == source
        for action in choices
    )


def test_kept_pace_with_follows_only_a_named_formation_maneuver() -> None:
    engine, state = setup_state(seed=4822)
    mover = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
    follower = pos(0, Rank.FRONT)
    make_named(state, 0, mover)
    make_named(state, 0, follower, bond="kept-pace-with")
    state.players[0].command = 5

    engine.apply(state, Maneuver(mover, destination))

    choices = effect_choices(engine, state, "move")
    assert any(
        not action.skip
        and action.source is not None
        and action.source.position == follower
        and action.destination is not None
        and action.destination.position == mover
        for action in choices
    )

    engine2, state2 = setup_state(seed=4823)
    state2.slot(0, mover).force = "the-grey-riders"
    make_named(state2, 0, follower, bond="kept-pace-with")
    state2.players[0].command = 5

    engine2.apply(state2, Maneuver(mover, destination))

    assert not effect_choices(engine2, state2, "move")


def test_teren_can_swap_two_other_adjacent_formations() -> None:
    engine, state = setup_state(seed=4824)
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    left = pos(2, Rank.FRONT)
    right = pos(3, Rank.FRONT)
    make_named(state, 0, source, name="teren")
    make_named(state, 0, left, force="the-fifty-men")
    make_named(state, 0, right, force="seven-black-ships")
    state.players[0].command = 5

    engine.apply(state, Maneuver(source, destination))

    swap = next(
        action
        for action in effect_choices(engine, state, "swap")
        if (
            not action.skip
            and action.source is not None
            and action.destination is not None
            and {
                action.source.position,
                action.destination.position,
            }
            == {left, right}
        )
    )
    engine.apply(state, swap)

    assert state.slot(0, left).force == "seven-black-ships"
    assert state.slot(0, right).force == "the-fifty-men"


def test_mara_reacts_when_opponent_maneuvers_into_her_front() -> None:
    engine, state = setup_state(seed=4825)
    make_named(state, 0, pos(0, Rank.FRONT))
    mara_slot = pos(1, Rank.REAR)
    make_named(state, 1, mara_slot, name="mara")
    state.players[0].command = 5
    state.active_player = 0

    engine.apply(
        state,
        Maneuver(pos(0, Rank.FRONT), pos(1, Rank.FRONT)),
    )

    choices = effect_choices(engine, state, "free-maneuver")
    assert state.active_player == 1
    assert any(
        not action.skip
        and action.source is not None
        and action.source.position == mara_slot
        for action in choices
    )


def test_first_spear_can_suppress_lower_printed_frontline_strength() -> None:
    engine, state = setup_state(seed=4826)
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        force="the-first-spear",
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        force="the-thornbow-hunters",
    )

    resolve_battle_by_passing(engine, state)

    suppress = next(
        action
        for action in effect_choices(engine, state, "suppress")
        if (
            not action.skip
            and action.destination is not None
            and action.destination.player == 1
            and action.destination.position == pos(0, Rank.FRONT)
        )
    )
    engine.apply(state, suppress)

    assert state.last_battle_snapshot["front_scores"][0][1] == 0


def test_old_guard_discount_requires_a_named_rear_formation() -> None:
    engine, state = setup_state(seed=4827)
    rear = pos(0, Rank.REAR)
    front = pos(0, Rank.FRONT)
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 20

    state.slot(0, rear).force = "the-old-guard"
    assert (
        engine.command_cost_for_action(
            state,
            PlayForce("the-fifty-men", front),
        )
        == 2
    )

    state.slot(0, rear).bond = "followed"
    state.slot(0, rear).name = "namar"
    assert (
        engine.command_cost_for_action(
            state,
            PlayForce("the-fifty-men", front),
        )
        == 1
    )


def test_rovan_force_can_ignore_opposing_rear_strength() -> None:
    engine, state = setup_state(seed=4828)
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        force="rovan-the-gatebreaker",
    )
    make_named(
        state,
        1,
        pos(0, Rank.REAR),
        force="seven-black-ships",
    )

    resolve_battle_by_passing(engine, state)

    assert any(
        not action.skip
        and action.destination is not None
        and action.destination.player == 1
        and action.destination.position == pos(0, Rank.REAR)
        for action in effect_choices(engine, state, "suppress")
    )



def test_lost_front_does_not_offer_alda_retreat_replacement() -> None:
    engine, state = setup_state(seed=4829)
    frontline = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)
    make_named(state, 0, frontline)
    make_named(state, 0, rear, force="alda-keeper-of-the-ford")
    make_named(state, 1, frontline, temporary=100)

    resolve_battle_by_passing(engine, state)

    assert not effect_choices(engine, state, "protect-retreat")
    assert state.slot(0, frontline).named is True
    assert state.slot(0, rear).force == "alda-keeper-of-the-ford"


def test_battle_resolution_does_not_displace_stayed_behind_bond() -> None:
    engine, state = setup_state(seed=48291)
    frontline = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)

    make_named(state, 0, frontline)
    make_named(
        state,
        0,
        rear,
        force="alda-keeper-of-the-ford",
        bond="stayed-behind-for",
        name="namar",
    )
    make_named(state, 1, frontline, temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, frontline).named is True
    assert state.slot(0, rear).force == "alda-keeper-of-the-ford"
    assert state.slot(0, rear).bond == "stayed-behind-for"

def test_they_lived_to_tell_it_rewards_a_surviving_target() -> None:
    engine, state = setup_state(seed=4830)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[0].hand = []
    target = pos(0, Rank.FRONT)
    make_named(state, 0, target)
    state.narratives[0] = [
        NarrativeState(
            "they-lived-to-tell-it",
            target_player=0,
            target_position=target,
        )
    ]

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_refunded"][0] >= 1
    assert snapshot["command_before_collapse"][0] == 11
    assert state.players[0].command == min(
        engine.rules.command_cap,
        snapshot["command_before_collapse"][0]
        + snapshot["recovery_actual"][0],
    )
    assert snapshot["cards_drawn"][0] >= 1
    assert "they-lived-to-tell-it" in state.players[0].discard


def test_all_reserves_forward_charges_only_additional_moves() -> None:
    engine, state = setup_state(seed=4831)
    make_named(state, 0, pos(0, Rank.REAR))
    make_named(
        state,
        0,
        pos(1, Rank.REAR),
        force="seven-black-ships",
    )
    state.players[0].hand = ["all-reserves-forward"]
    state.players[0].command = 20

    actions = [
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayStratagem)
        and action.card_id == "all-reserves-forward"
    ]
    one = next(action for action in actions if len(action.targets) == 1)
    two = next(action for action in actions if len(action.targets) == 2)
    assert engine.command_cost_for_action(state, one) == 2
    assert engine.command_cost_for_action(state, two) == 3

    engine.apply(state, two)

    assert state.slot(0, pos(0, Rank.FRONT)).force is not None
    assert state.slot(0, pos(1, Rank.FRONT)).force is not None
    assert state.slot(0, pos(0, Rank.REAR)).occupied is False
    assert state.slot(0, pos(1, Rank.REAR)).occupied is False


def test_torren_grants_another_named_formation_a_free_maneuver() -> None:
    engine, state = setup_state(seed=4832)
    for front in range(4):
        make_named(
            state,
            0,
            pos(front, Rank.FRONT),
            force=(
                "seven-black-ships"
                if front == 1
                else "the-fifty-men"
            ),
            name="torren" if front == 0 else "namar",
        )
    state.players[0].command = 5

    engine.apply(
        state,
        Maneuver(pos(0, Rank.FRONT), pos(1, Rank.FRONT)),
    )

    choices = effect_choices(engine, state, "free-maneuver")
    assert any(
        not action.skip
        and action.source is not None
        and action.source.position != pos(1, Rank.FRONT)
        for action in choices
    )


def test_black_company_after_swap_triggers_only_as_maneuver_initiator() -> None:
    engine, state = setup_state(seed=48321)
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    make_named(
        state,
        0,
        source,
        force="seven-black-ships",
    )
    make_named(
        state,
        0,
        destination,
        force="the-black-company",
    )
    state.players[0].command = 10

    # Black Company is displaced by the other formation's Maneuver. That is
    # movement caused by a swap, not Black Company initiating a Maneuver.
    engine.apply(state, Maneuver(source, destination))
    assert effect_choices(engine, state, "free-maneuver") == []

    engine, state = setup_state(seed=48322)
    make_named(
        state,
        0,
        source,
        force="the-black-company",
    )
    make_named(
        state,
        0,
        destination,
        force="seven-black-ships",
    )
    state.players[0].command = 10

    engine.apply(state, Maneuver(source, destination))
    choices = effect_choices(engine, state, "free-maneuver")
    assert any(
        not choice.skip
        and choice.source is not None
        and choice.source.position == source
        for choice in choices
    )


def test_free_maneuver_chain_cannot_return_to_same_formation() -> None:
    engine, state = setup_state(seed=48323)
    avaros = pos(0, Rank.FRONT)
    torren = pos(1, Rank.FRONT)

    make_named(
        state,
        0,
        avaros,
        force="avaros-the-bronze-king",
        name="namar",
    )
    make_named(
        state,
        0,
        torren,
        force="the-fifty-men",
        name="torren",
    )
    state.slot(0, pos(2, Rank.FRONT)).force = "seven-black-ships"
    state.slot(0, pos(3, Rank.FRONT)).force = "the-grey-riders"
    state.players[0].command = 10

    # Avaros initiates the operation and grants Torren a free Maneuver.
    engine.apply(state, Maneuver(avaros, torren))
    first_chain = [
        choice
        for choice in effect_choices(engine, state, "free-maneuver")
        if not choice.skip
    ]
    torren_maneuver = next(
        choice
        for choice in first_chain
        if choice.source is not None
        and choice.source.position == avaros
        and choice.destination is not None
        and choice.destination.position == torren
    )
    engine.apply(state, torren_maneuver)

    # Torren's trigger may offer another Named Formation, but Avaros already
    # initiated a Maneuver in this operation. The chain therefore cannot
    # return to Avaros.
    follow_up = effect_choices(engine, state, "free-maneuver")
    assert follow_up
    assert all(choice.skip for choice in follow_up)


def test_banner_singers_trigger_after_narrative_command_gain() -> None:
    engine, state = setup_state(seed=4833)
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    other_named = pos(2, Rank.FRONT)
    make_named(state, 0, source)
    make_named(state, 0, other_named)
    state.slot(0, pos(3, Rank.REAR)).force = "the-banner-singers"
    state.narratives[0] = [NarrativeState("the-long-march")]
    state.players[0].command = 5

    engine.apply(state, Maneuver(source, destination))

    choices = effect_choices(engine, state, "free-maneuver")
    # Banner Singers still triggers, but the formation that initiated the
    # operation's Maneuver cannot initiate a second Maneuver in the same
    # operation-resolution chain.
    assert all(
        action.skip
        or action.source is None
        or action.source.position != destination
        for action in choices
    )
    assert any(
        not action.skip
        and action.source is not None
        and action.source.position == other_named
        for action in choices
    )


def test_chained_mandatory_recoveries_do_not_dead_end_after_first_consumes_target() -> None:
    engine, state = setup_state(seed=48334)

    # Keep this focused on stale queued recoveries rather than hand-limit
    # cleanup introduced by returning a card to a full opening hand.
    state.players[0].hand.clear()
    state.players[0].discard[:] = ["followed"]
    recovery = {
        "kind": 4,  # EFFECT_RECOVER
        "player": 0,
        "card": -1,
        "source": -1,
        "aux": 2,  # CARD_BOND
        "source_mask": 0,
        "dest_mask": 0,
        "flags": 0,
    }
    state.pending_effects = [dict(recovery), dict(recovery)]
    state.active_player = 0

    first = effect_choices(engine, state, "recover")
    assert first == [EffectChoice("recover", card_id="followed")]
    engine.apply(state, first[0])

    second = effect_choices(engine, state, "recover")
    assert second == [EffectChoice("recover", skip=True)]
    engine.apply(state, second[0])

    assert state.pending_effects == []
    assert "followed" in state.players[0].hand
    assert engine.legal_actions(state)


def test_stale_mandatory_pending_effect_resolves_as_forced_noop() -> None:
    engine, state = setup_state(seed=48335)

    # A mandatory recovery may have been legal when queued but become
    # impossible because an earlier queued recovery consumed the last Bond.
    state.players[0].discard.clear()
    state.pending_effects = [
        {
            "kind": 4,  # EFFECT_RECOVER
            "player": 0,
            "card": -1,
            "source": -1,
            "aux": 2,  # CARD_BOND
            "source_mask": 0,
            "dest_mask": 0,
            "flags": 0,
        }
    ]
    state.active_player = 0

    choices = effect_choices(engine, state, "recover")
    assert choices == [EffectChoice("recover", skip=True)]

    engine.apply(state, choices[0])

    assert state.pending_effects == []
    assert engine.legal_actions(state)


def test_guarded_blocks_an_opponents_pending_card_move() -> None:
    engine, state = setup_state(seed=4834)
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    make_named(state, 1, source, bond="guarded")

    # Synthetic pending effect: no first-80 card currently moves an opposing
    # formation directly, but Guarded is a continuous restriction on exactly
    # that shared card-effect movement path.
    state.pending_effects = [
        {
            "kind": 2,
            "player": 0,
            "card": -1,
            "source": -1,
            "aux": -1,
            "source_mask": 1 << slot_number(1, source),
            "dest_mask": 1 << slot_number(1, destination),
            "flags": 1,
        }
    ]
    state.active_player = 0

    choices = effect_choices(engine, state, "move")
    assert choices
    assert all(choice.skip for choice in choices)


@pytest.mark.parametrize(
    "destination",
    [
        pos(1, Rank.FRONT),
        pos(0, Rank.MIDDLE),
    ],
)
def test_eira_succession_resolver_moves_name_then_drives_off_source(
    destination: Position,
) -> None:
    engine, state = setup_state(seed=4835)
    source = pos(0, Rank.FRONT)
    make_named(state, 0, source, name="eira")
    target = state.slot(0, destination)
    target.force = "the-fifty-men"
    target.bond = "followed"

    # Exercise the resumable card-effect replacement resolver directly. This
    # state is intentionally synthetic; normal Battle resolution does not
    # remove incomplete formations or create automatic Retreats.
    state.pending_effects = [
        {
            "kind": 12,
            "player": 0,
            "card": -1,
            "source": slot_number(0, source),
            "aux": -1,
            "source_mask": 0,
            "dest_mask": 1 << slot_number(0, destination),
            "flags": 1,
        }
    ]
    state.active_player = 0

    succession = next(
        action
        for action in effect_choices(engine, state, "succession")
        if not action.skip
    )
    engine.apply(state, succession)

    assert state.slot(0, destination).name == "eira"
    assert state.slot(0, source).occupied is False
    assert "the-fifty-men" in state.players[0].discard
    assert "followed" in state.players[0].discard


