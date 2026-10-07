from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    ActivateAbility,
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
    PlayOrder,
    PlayStratagem,
    PlayTactic,
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

def test_maneuver_cannot_enter_inactive_front() -> None:
    engine, state = setup_state(battle=1)
    source = pos(2, Rank.MIDDLE)
    make_named(state, 0, source)

    legal = engine.legal_actions(state)

    assert Maneuver(source, pos(1, Rank.MIDDLE)) in legal
    assert Maneuver(source, pos(3, Rank.MIDDLE)) not in legal

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

    for rank in (Rank.FRONT, Rank.MIDDLE, Rank.REAR):
        assert PlayForce("the-red-shields", pos(0, rank)) in legal
        assert PlayForce("avaros-the-bronze-king", pos(2, rank)) in legal

    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.REAR)) in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.MIDDLE)) in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.FRONT)) not in legal

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
    state.players[0].hand = ["followed", "namar"]

    assert engine.command_cost_for_action(state, PlayBond("followed", front)) == 0
    assert engine.command_cost_for_action(state, PlayName("namar", front)) == 2


def test_supplied_by_requires_bonded_and_stops_when_bond_text_is_suppressed() -> None:
    engine, state = setup_state()
    rear = pos(1, Rank.REAR)
    middle = pos(1, Rank.MIDDLE)
    source = state.slot(0, rear)
    source.bond = "supplied-by"
    state.players[0].hand = ["followed"]

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
    state.players[0].hand = ["followed", "iria", "namar"]

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


def test_v2_name_action_discount_changes_the_next_attachment_cost() -> None:
    engine, state = setup_state(seed=4508)
    source = pos(1, Rank.FRONT)
    target = pos(1, Rank.MIDDLE)
    make_named(state, 0, source, name="meren")
    state.slot(0, target).force = "the-fifty-men"
    state.players[0].hand[:] = ["followed"]
    state.players[0].command = 5

    ability = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, ActivateAbility)
        and action.card_id == "meren"
    )
    engine.apply(state, ability)

    choice = next(
        action
        for action in effect_choices(engine, state)
        if action.destination is not None
        and action.destination.player == 0
        and action.destination.position == target
    )
    engine.apply(state, choice)

    assert engine.command_cost_for_action(
        state, PlayBond("followed", target)
    ) == 0
    assert not any(
        isinstance(action, ActivateAbility)
        and action.card_id == "meren"
        for action in engine.legal_actions(state)
    )


def test_v2_becomes_named_remove_exhaustion_resolves_on_chosen_formation() -> None:
    engine, state = setup_state(seed=4509)
    source = pos(1, Rank.FRONT)
    target = pos(1, Rank.MIDDLE)
    source_slot = state.slot(0, source)
    source_slot.force = "the-fifty-men"
    source_slot.bond = "followed"
    target_slot = state.slot(0, target)
    target_slot.force = "the-fifty-men"
    target_slot.exhausted = True
    state.players[0].hand[:] = ["maelin"]
    state.players[0].command = 5

    engine.apply(state, PlayName("maelin", source))

    choice = next(
        action
        for action in effect_choices(engine, state)
        if action.destination is not None
        and action.destination.player == 0
        and action.destination.position == target
    )
    engine.apply(state, choice)

    assert state.slot(0, target).exhausted is False


def test_catch_your_breath_order_removes_exhaustion_and_is_discarded() -> None:
    engine, state = setup_state(seed=4510)
    healer = pos(1, Rank.FRONT)
    target = pos(1, Rank.MIDDLE)
    state.slot(0, healer).force = "the-white-hands-of-elara"
    target_slot = state.slot(0, target)
    target_slot.force = "the-fifty-men"
    target_slot.exhausted = True
    state.players[0].hand[:] = ["catch-your-breath"]
    state.players[0].command = 5

    order = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayOrder)
        and action.card_id == "catch-your-breath"
        and action.target is not None
        and action.target.position == target
    )
    engine.apply(state, order)

    assert state.slot(0, target).exhausted is False
    assert "catch-your-breath" not in state.players[0].hand
    assert "catch-your-breath" in state.players[0].discard


def test_v2_tactic_applies_strength_marker_and_is_discarded() -> None:
    engine, state = setup_state(seed=4511)
    target = pos(1, Rank.FRONT)
    state.slot(1, target).force = "the-fifty-men"
    state.players[0].hand[:] = ["the-baggage-was-abandoned"]
    state.players[0].command = 5

    tactic = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayTactic)
        and action.card_id == "the-baggage-was-abandoned"
        and action.target is not None
        and action.target.player == 1
        and action.target.position == target
    )
    engine.apply(state, tactic)

    assert state.slot(1, target).negative_strength_markers == [-2]
    assert "the-baggage-was-abandoned" not in state.players[0].hand
    assert "the-baggage-was-abandoned" in state.players[0].discard


def test_v2_veyra_becomes_named_grants_name_suppression_immunity() -> None:
    engine, state = setup_state(seed=4512)
    source = pos(1, Rank.FRONT)
    source_slot = state.slot(0, source)
    source_slot.force = "the-fifty-men"
    source_slot.bond = "followed"
    state.players[0].hand[:] = ["veyra-keeper-of-oaths"]
    state.players[0].command = 5

    engine.apply(state, PlayName("veyra-keeper-of-oaths", source))

    assert state.slot(0, source).name_suppression_immune is True


def test_v2_carried_oath_blocks_name_suppression_while_named() -> None:
    engine, state = setup_state(seed=4513)
    target = pos(1, Rank.FRONT)
    make_named(
        state,
        0,
        target,
        bond="carried-the-oath-of",
        name="namar",
    )
    state.active_player = 1
    state.players[1].hand[:] = ["they-returned-with-names"]
    state.players[1].command = 5

    tactic = next(
        action
        for action in engine.legal_actions(state)
        if isinstance(action, PlayTactic)
        and action.card_id == "they-returned-with-names"
        and action.target is not None
        and action.target.player == 0
        and action.target.position == target
    )
    engine.apply(state, tactic)

    assert state.slot(0, target).suppression_mask & 4 == 0


def test_v2_serai_becomes_named_marks_friendly_archers_in_front() -> None:
    engine, state = setup_state(seed=4514)
    source = pos(1, Rank.FRONT)
    archer = pos(1, Rank.MIDDLE)
    source_slot = state.slot(0, source)
    source_slot.force = "the-fifty-men"
    source_slot.bond = "followed"
    state.slot(0, archer).force = "the-crow-archers"
    state.players[0].hand[:] = ["serai-queen-of-crows"]
    state.players[0].command = 5

    engine.apply(state, PlayName("serai-queen-of-crows", source))

    assert state.slot(0, archer).temporary_strength == 1


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

    make_named(state, 0, pos(0, Rank.FRONT), force="the-iron-boars", temporary=10)
    make_named(state, 1, pos(0, Rank.FRONT))

    resolve_battle_by_passing(engine, state)

    assert state.slot(1, pos(0, Rank.FRONT)).named is True
    assert state.slot(1, pos(0, Rank.REAR)).occupied is False
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
    make_named(state, 1, pos(0, Rank.REAR))
    state.stratagems[0] = StratagemState("the-ground-was-held")

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["fronts_lost"][1] >= 1
    assert state.last_battle_snapshot["fronts_lost"][0] == 0

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


def test_lines_held_prevents_up_to_two_lost_front_command_penalties() -> None:
    engine, state = setup_state(seed=47122)
    state.stratagems[0] = StratagemState("the-lines-held")
    make_named(state, 1, pos(0), temporary=100)
    make_named(state, 1, pos(1), temporary=100)

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["fronts_lost"][0] == 2
    assert snapshot["front_loss_command_penalty"][0] == 0


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
        "no-road-was-too-long",
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


