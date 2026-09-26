from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    Discard,
    Front,
    GameEngine,
    Maneuver,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayStory,
    PlayStratagem,
    Position,
    Rank,
)
from longwar.game.model import FRONT_COUNT, Phase, StoryState, StratagemState
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "mobility-open-bonds.json"


def setup_state(
    *,
    seed: int = 4100,
    first_player: int = 0,
    opening_bonus: bool = False,
):
    data = load_card_file(CARD_FILE)
    deck = json.loads(DECK_FILE.read_text(encoding="utf-8"))["cards"]
    engine = GameEngine(data, rules=GameRules.standard())
    state = engine.new_game(
        deck,
        deck,
        seed=seed,
        first_player=first_player,
        opening_bonus=opening_bonus,
    )
    return engine, state


def pos(front: int, rank: Rank = Rank.FRONT) -> Position:
    return Position(Front(front), rank)


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


def resolve_battle_by_passing(engine: GameEngine, state) -> None:
    state.active_player = 0
    state.operations_this_battle[:] = [1, 1]

    # The opponent gets a normal turn after the first Pass, including the
    # normal start-of-turn draw. Leave one hand slot so that draw can resolve
    # without entering the discard-before-draw substep.
    if len(state.players[1].hand) >= engine.hand_limit:
        card = state.players[1].hand.pop()
        state.players[1].deck.append(card)

    engine.apply(state, Pass())
    assert state.pass_order == [0]
    assert state.players[0].passed is True
    engine.apply(state, Pass())


def test_battlefield_is_four_fronts_by_two_ranks() -> None:
    _engine, state = setup_state()
    assert FRONT_COUNT == 4
    assert len(state.board) == 2
    assert all(len(side) == 4 for side in state.board)
    assert all(len(front) == 2 for side in state.board for front in side)
    assert list(Front) == [
        Front.FIRST,
        Front.SECOND,
        Front.THIRD,
        Front.FOURTH,
    ]


def test_printed_strength_effects_apply_without_hidden_role_rules() -> None:
    engine, state = setup_state()

    frontline = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)

    state.slot(0, frontline).force = "the-fifty-men"
    assert engine.position_strength(state, 0, frontline) == 5
    state.slot(0, frontline).force = "seven-black-ships"
    assert engine.position_strength(state, 0, frontline) == 4

    state.slot(0, rear).force = "seven-black-ships"
    assert engine.position_strength(state, 0, rear) == 5

    state.slot(0, frontline).force = "the-red-shields"
    state.slot(0, rear).force = None
    assert engine.position_strength(state, 0, frontline) == 4
    state.slot(0, rear).force = "the-white-hands-of-elara"
    # Red Shields gets its printed +1 for a Force behind it, while White Hands
    # separately gives the Force directly ahead +2.
    assert engine.position_strength(state, 0, frontline) == 7

    state.slot(0, rear).force = "the-crow-archers"
    assert engine.position_strength(state, 0, rear) == 6


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
    assert PlayForce("the-red-shields", pos(0, Rank.REAR)) not in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.REAR)) in legal
    assert PlayForce("the-white-hands-of-elara", pos(1, Rank.FRONT)) not in legal
    assert PlayForce("avaros-the-bronze-king", pos(2, Rank.FRONT)) in legal
    assert PlayForce("avaros-the-bronze-king", pos(2, Rank.REAR)) not in legal


def test_bond_and_name_can_be_prepared_before_force_and_contribute_zero() -> None:
    engine, state = setup_state()
    target = pos(0)
    state.players[0].hand = ["followed", "namar", "the-fifty-men"]
    state.players[0].command = 20

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


def test_force_deploy_rank_restriction_does_not_block_retreat() -> None:
    engine, state = setup_state()
    front = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)
    state.players[0].hand = ["the-red-shields"]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert PlayForce("the-red-shields", front) in legal
    assert PlayForce("the-red-shields", rear) not in legal

    make_named(
        state,
        0,
        front,
        force="the-red-shields",
    )
    make_named(state, 1, front, temporary=100)
    resolve_battle_by_passing(engine, state)

    assert state.slot(0, front).force is None
    assert state.slot(0, rear).force == "the-red-shields"


def test_maneuver_moves_named_formation_to_adjacent_empty_same_rank() -> None:
    engine, state = setup_state()
    source = pos(0)
    destination = pos(1)
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


def test_maneuver_has_no_vertical_or_non_adjacent_core_move() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.FRONT)
    make_named(state, 0, source)
    state.players[0].command = 5
    legal = engine.legal_actions(state)

    assert Maneuver(source, pos(0, Rank.REAR)) not in legal
    assert Maneuver(source, pos(2, Rank.FRONT)) not in legal


def test_first_pass_is_gated_but_emergency_pass_remains_available() -> None:
    engine, state = setup_state()
    state.players[0].hand = ["the-fifty-men"]
    state.players[0].command = 20
    state.operations_this_battle[:] = [0, 0]
    assert Pass() not in engine.legal_actions(state)

    state.players[0].hand.clear()
    state.players[0].command = 0
    assert engine.legal_actions(state) == [Pass()]


def test_first_pass_gives_opponent_a_normal_turn_with_normal_draw() -> None:
    engine, state = setup_state()
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    moved = state.players[1].hand.pop()
    state.players[1].deck.append(moved)
    assert len(state.players[1].hand) == 9
    before_drawn = state.cards_drawn_this_battle[1]

    engine.apply(state, Pass())

    assert state.battle == 1
    assert state.active_player == 1
    assert state.pass_order == [0]
    assert state.players[0].passed is True
    assert state.players[1].passed is False
    assert len(state.players[1].hand) == 10
    assert state.cards_drawn_this_battle[1] == before_drawn + 1


def test_non_pass_operation_clears_earlier_pass_and_play_continues() -> None:
    engine, state = setup_state()
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    state.players[1].hand = ["the-fifty-men"]
    state.players[1].deck = ["followed"]
    state.players[1].command = 20
    state.players[0].hand = []
    state.players[0].deck = ["namar"]

    engine.apply(state, Pass())
    assert state.pass_order == [0]
    assert state.active_player == 1

    engine.apply(state, PlayForce("the-fifty-men", pos(0)))

    assert state.battle == 1
    assert state.pass_order == []
    assert state.players[0].passed is False
    assert state.players[1].passed is False
    assert state.active_player == 0
    assert "namar" in state.players[0].hand


def test_emergency_first_pass_does_not_unlock_pass_for_opponent_with_legal_operation() -> None:
    engine, state = setup_state()
    state.operations_this_battle[:] = [0, 0]
    state.active_player = 0
    state.players[0].hand = []
    state.players[0].deck = []
    state.players[0].command = 0
    state.players[1].hand = ["the-fifty-men"]
    state.players[1].deck = ["followed"]
    state.players[1].command = 20

    assert engine.legal_actions(state) == [Pass()]
    engine.apply(state, Pass())

    assert state.active_player == 1
    assert state.pass_order == [0]
    assert Pass() not in engine.legal_actions(state)


def test_two_consecutive_passes_end_the_battle() -> None:
    engine, state = setup_state()
    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    assert state.active_player == 0  # first of the two consecutive passers
    assert state.pass_order == []
    assert state.players[0].passed is False
    assert state.players[1].passed is False


def test_turn_at_hand_limit_requires_discard_then_draw_before_operation() -> None:
    engine, state = setup_state(opening_bonus=True)
    assert len(state.players[0].hand) == 10
    assert state.pending_draw_discard_for == 0

    legal = engine.legal_actions(state)
    assert legal
    assert all(isinstance(action, Discard) for action in legal)

    discarded = legal[0].card_id
    deck_before = len(state.players[0].deck)
    engine.apply(state, legal[0])

    assert state.pending_draw_discard_for is None
    assert len(state.players[0].hand) == 10
    assert len(state.players[0].deck) == deck_before - 1
    assert discarded in state.players[0].discard
    assert state.active_player == 0


def test_completion_draw_at_hand_limit_pauses_for_discard_then_finishes_operation() -> None:
    engine, state = setup_state()
    state.active_player = 0
    state.players[0].hand = ["the-fifty-men"] * 9 + ["oren"]
    state.players[0].deck = ["the-red-shields", "seven-black-ships"]
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"

    engine.apply(state, PlayName("oren", target))

    assert state.pending_draw_discard_for == 0
    assert state.pending_draw_count == 1
    assert state.pending_draw_finish_operation is True
    assert state.active_player == 0
    assert len(state.players[0].hand) == 10
    assert all(isinstance(action, Discard) for action in engine.legal_actions(state))

    engine.apply(state, engine.legal_actions(state)[0])

    assert state.pending_draw_discard_for is None
    assert state.pending_draw_count == 0
    assert state.pending_draw_finish_operation is False
    assert len(state.players[0].hand) == 10
    assert state.active_player == 1


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


def test_breakthrough_drives_off_frontline_named_instead_of_retreating() -> None:
    engine, state = setup_state()
    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        force="the-iron-boars",
        temporary=10,
    )
    make_named(state, 1, pos(0, Rank.FRONT))

    resolve_battle_by_passing(engine, state)

    assert state.slot(1, pos(0, Rank.FRONT)).force is None
    assert state.slot(1, pos(0, Rank.REAR)).force is None


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

    first = PlayStory(
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
    second = PlayStory("no-road-was-too-long", ongoing_slot=1)
    assert second in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, second) == 2


def test_long_march_regains_command_only_on_first_maneuver_into_empty_each_battle() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.stories[0] = [StoryState("the-long-march")]
    first = pos(1, Rank.FRONT)
    second = pos(2, Rank.FRONT)
    third = pos(3, Rank.FRONT)
    make_named(state, 0, first)

    engine.apply(state, Maneuver(first, second))

    assert state.players[0].command == 5
    assert state.stories[0][0].triggered_this_battle is True

    state.active_player = 0
    state.pending_draw_discard_for = None
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = False
    engine.apply(state, Maneuver(second, third))

    assert state.players[0].command == 4


def test_named_narrative_trigger_regains_command_and_discards_itself() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.stories[0] = [StoryState("they-returned-with-names")]
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    state.players[0].hand = ["asha-the-shield-bearer"]

    engine.apply(state, PlayName("asha-the-shield-bearer", target))

    assert state.players[0].command == 5
    assert state.stories[0] == []
    assert "they-returned-with-names" in state.players[0].discard


def test_opposing_named_narrative_trigger_belongs_to_other_player() -> None:
    engine, state = setup_state()
    state.players[1].command = 5
    state.stories[1] = [StoryState("they-were-gathering-there")]
    target = pos(0, Rank.FRONT)
    state.slot(0, target).force = "the-fifty-men"
    state.slot(0, target).bond = "followed"
    state.players[0].hand = ["asha-the-shield-bearer"]

    engine.apply(state, PlayName("asha-the-shield-bearer", target))

    assert state.players[1].command == 6
    assert state.stories[1] == []
    assert "they-were-gathering-there" in state.players[1].discard


def test_muster_false_triggers_when_opponent_fills_both_ranks_of_front() -> None:
    engine, state = setup_state()
    state.players[1].command = 5
    state.stories[1] = [StoryState("the-muster-was-false")]
    state.slot(0, pos(0, Rank.REAR)).force = "the-fifty-men"
    state.players[0].hand = ["the-fifty-men"]

    engine.apply(state, PlayForce("the-fifty-men", pos(0, Rank.FRONT)))

    assert state.players[1].command == 6
    assert state.stories[1] == []
    assert "the-muster-was-false" in state.players[1].discard


def test_bought_time_for_can_pay_extra_to_draw_two_with_sequential_hand_limit() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    state.players[0].command = 10
    state.players[0].hand = ["bought-time-for"] + ["the-fifty-men"] * 9
    state.players[0].deck = ["seven-black-ships", "the-red-shields"]

    normal = PlayBond("bought-time-for", target)
    invested = PlayBond("bought-time-for", target, extra_payment=1)
    legal = engine.legal_actions(state)
    assert normal in legal
    assert invested in legal
    assert engine.command_cost_for_action(state, normal) == 1
    assert engine.command_cost_for_action(state, invested) == 2

    engine.apply(state, invested)

    assert state.players[0].command == 8
    assert len(state.players[0].hand) == 10
    assert state.pending_draw_discard_for == 0
    assert state.pending_draw_count == 1
    assert state.pending_draw_finish_operation is True

    engine.apply(state, engine.legal_actions(state)[0])
    assert len(state.players[0].hand) == 10
    assert state.pending_draw_discard_for is None
    assert state.active_player == 1


def test_baggage_warning_can_discard_another_card_to_regain_command() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.players[0].hand = [
        "the-baggage-was-abandoned",
        "the-fifty-men",
    ]

    decline = PlayStory("the-baggage-was-abandoned")
    trade = PlayStory(
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


def test_marched_with_can_move_formation_when_played_onto_force() -> None:
    engine, state = setup_state()
    source = pos(1, Rank.FRONT)
    destination = pos(2, Rank.FRONT)
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


def test_house_of_reed_is_driven_off_instead_of_frontline_retreat() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(
        state,
        0,
        pos(0, Rank.REAR),
        force="the-house-of-reed",
    )
    make_named(state, 1, pos(0, Rank.FRONT), temporary=20)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.REAR)).force is None
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
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    make_named(state, 0, target, temporary=4)

    resolve_battle_by_passing(engine, state)

    assert state.battle == 2
    assert state.slot(0, target).complete is True
    assert state.slot(0, target).temporary_strength == 0


def test_battle_resolves_four_fronts_independently_without_battle_winner() -> None:
    engine, state = setup_state()

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
    assert state.battle == 2


def test_incomplete_formations_are_discarded_before_retreat() -> None:
    engine, state = setup_state()
    incomplete = state.slot(0, pos(3))
    incomplete.force = "the-fifty-men"
    incomplete.bond = "followed"

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(3)).occupied is False
    assert "the-fifty-men" in state.players[0].discard
    assert "followed" in state.players[0].discard


def test_retreat_frontline_only_rear_only_both_and_tie() -> None:
    engine, state = setup_state()

    # Front 0: player 0 loses with Frontline only -> retreats to Rear.
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    # Front 1: player 0 loses with Rear only -> driven off.
    make_named(state, 0, pos(1, Rank.REAR), force="seven-black-ships")
    make_named(state, 1, pos(1, Rank.FRONT), temporary=100)

    # Front 2: player 0 loses with both -> Rear off, Frontline retreats.
    make_named(state, 0, pos(2, Rank.FRONT))
    make_named(state, 0, pos(2, Rank.REAR), force="seven-black-ships")
    make_named(state, 1, pos(2, Rank.FRONT), temporary=100)

    # Front 3: tied Named Formations -> neither moves.
    make_named(state, 0, pos(3, Rank.FRONT))
    make_named(state, 1, pos(3, Rank.FRONT))

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.FRONT)).occupied is False
    assert state.slot(0, pos(0, Rank.REAR)).complete is True

    assert state.slot(0, pos(1, Rank.REAR)).occupied is False

    assert state.slot(0, pos(2, Rank.FRONT)).occupied is False
    assert state.slot(0, pos(2, Rank.REAR)).force == "the-fifty-men"

    assert state.slot(0, pos(3, Rank.FRONT)).complete is True
    assert state.slot(1, pos(3, Rank.FRONT)).complete is True


def test_drive_off_persistence_bonds_and_names_apply() -> None:
    engine, state = setup_state(seed=4690)

    stayed = pos(0, Rank.REAR)
    make_named(
        state,
        0,
        stayed,
        force="seven-black-ships",
        bond="stayed-behind-for",
        name="namar",
    )
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    returned = pos(1, Rank.REAR)
    make_named(
        state,
        0,
        returned,
        force="seven-black-ships",
        bond="swore-again-to",
        name="edrin",
    )
    make_named(state, 1, pos(1, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    stayed_slot = state.slot(0, stayed)
    assert stayed_slot.force is None
    assert stayed_slot.bond == "stayed-behind-for"
    assert stayed_slot.name is None
    assert "namar" in state.players[0].hand

    returned_slot = state.slot(0, returned)
    assert returned_slot.occupied is False
    assert "swore-again-to" in state.players[0].hand
    assert "edrin" in state.players[0].hand


def test_seized_standard_returns_bond_only_after_an_actual_retreat() -> None:
    engine, state = setup_state(seed=4692)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[1].hand = ["the-fifty-men"] * 9
    state.players[1].deck = ["the-fifty-men"] * 20
    state.players[1].discard = []

    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        bond="seized-the-standard-of",
        temporary=20,
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        bond="followed",
        name="namar",
    )

    make_named(
        state,
        0,
        pos(1, Rank.FRONT),
        force="the-iron-boars",
        bond="seized-the-standard-of",
        temporary=20,
    )
    make_named(
        state,
        1,
        pos(1, Rank.FRONT),
        bond="endured-with",
        name="edrin",
    )

    resolve_battle_by_passing(engine, state)

    retreated = state.slot(1, pos(0, Rank.REAR))
    assert retreated.force == "the-fifty-men"
    assert retreated.bond is None
    assert retreated.name == "namar"
    assert "followed" in state.players[1].hand

    assert state.slot(1, pos(1, Rank.FRONT)).occupied is False
    assert state.slot(1, pos(1, Rank.REAR)).occupied is False
    assert "endured-with" in state.players[1].discard
    assert "endured-with" not in state.players[1].hand


def test_endured_with_regains_command_when_formation_retreats() -> None:
    engine, state = setup_state(seed=4691)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]

    make_named(
        state,
        0,
        pos(0, Rank.FRONT),
        bond="endured-with",
    )
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.REAR)).bond == "endured-with"
    assert state.players[0].command == 11


def test_maneuver_rejects_prepared_only_destination_and_immobile_force() -> None:
    engine, state = setup_state()
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    make_named(state, 0, source)
    state.slot(0, destination).bond = "followed"

    assert Maneuver(source, destination) not in engine.legal_actions(state)

    state.slot(0, destination).bond = None
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

    state.slot(0, pos(0, Rank.REAR)).force = "nara-builder-of-walls"
    assert engine.command_cost_for_action(
        state, PlayForce("the-fifty-men", target)
    ) == 1


def test_red_duelists_ignore_rear_strength_during_front_resolution() -> None:
    engine, state = setup_state()
    state.slot(0, pos(0, Rank.FRONT)).force = "the-red-duelists"
    state.slot(0, pos(0, Rank.REAR)).force = "seven-black-ships"
    state.slot(1, pos(0, Rank.FRONT)).force = "the-fifty-men"
    state.slot(1, pos(0, Rank.REAR)).force = "seven-black-ships"

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["front_scores"][0] == [3, 5]


def test_ground_was_held_breaks_tie_only_for_single_frontline_named_side() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.REAR))
    state.stratagems[0] = StratagemState("the-ground-was-held")

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["fronts_lost"][1] >= 1
    assert state.last_battle_snapshot["fronts_lost"][0] == 0


def test_lines_held_and_tovan_reduce_recovery_front_loss_penalty() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.players[1].command = 20
    state.battle_start_command[:] = [5, 20]
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)
    state.stratagems[0] = StratagemState("the-lines-held")

    resolve_battle_by_passing(engine, state)
    assert state.players[0].command == 15

    engine, state = setup_state(seed=4702)
    state.players[0].command = 5
    state.players[1].command = 20
    state.battle_start_command[:] = [5, 20]
    state.slot(0, pos(0, Rank.REAR)).force = "tovan-the-quartermaster"
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)
    assert state.players[0].command == 15


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


def test_battle_turned_east_makes_only_chosen_direction_free() -> None:
    engine, state = setup_state(seed=4711)
    source = pos(1)
    make_named(state, 0, source)
    state.stratagems[0] = StratagemState(
        "the-battle-turned-east",
        direction="right",
    )

    assert engine.command_cost_for_action(
        state,
        Maneuver(source, pos(2)),
    ) == 0
    assert engine.command_cost_for_action(
        state,
        Maneuver(source, pos(0)),
    ) == 1


def test_no_step_back_drives_off_instead_of_retreating() -> None:
    engine, state = setup_state(seed=4712)
    state.stratagems[0] = StratagemState(
        "no-step-back",
        fronts=(Front.FIRST,),
    )
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0, Rank.FRONT)).occupied is False
    assert state.slot(0, pos(0, Rank.REAR)).occupied is False
    assert "the-fifty-men" in state.players[0].discard


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


@pytest.mark.parametrize(
    ("battle", "expected"),
    [
        (1, 20),
        (2, 17),
        (3, 15),
        (4, 14),
        (5, 13),
        (6, 12),
        (7, 11),
        (8, 10),
        (9, 10),
    ],
)
def test_command_recovery_schedule(battle: int, expected: int) -> None:
    engine, state = setup_state(seed=4200 + battle)
    state.battle = battle
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]

    resolve_battle_by_passing(engine, state)

    assert state.players[0].command == expected
    assert state.players[1].command == expected


def test_command_recovery_loses_one_per_lost_front_and_caps_at_twenty() -> None:
    engine, state = setup_state()
    state.players[0].command = 5
    state.players[1].command = 19
    state.battle_start_command[:] = [5, 19]

    make_named(state, 1, pos(0))
    make_named(state, 1, pos(1))

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["fronts_lost"] == [2, 0]
    assert state.players[0].command == 13
    assert state.players[1].command == 20


def test_command_collapse_lower_command_loses_and_equal_low_continues() -> None:
    engine, state = setup_state()
    state.battle = 8
    state.players[0].command = 0
    state.players[1].command = 6
    state.battle_start_command[:] = [0, 6]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.COMPLETE
    assert state.winner == 1

    engine, state = setup_state(seed=4301)
    state.battle = 8
    state.players[0].command = 0
    state.players[1].command = 0
    state.battle_start_command[:] = [0, 0]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.BATTLE
    assert state.winner is None
    assert state.battle == 9


def test_hand_deck_discard_and_named_formations_persist_between_battles() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0))
    state.players[0].discard.append(state.players[0].hand.pop())
    # Restore hand size to ten from deck so Battle-end refill does not move cards.
    state.players[0].hand.append(state.players[0].deck.pop())
    hand_before = list(state.players[0].hand)
    deck_before = list(state.players[0].deck)
    discard_before = list(state.players[0].discard)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0)).complete is True
    assert state.players[0].hand == hand_before
    assert state.players[0].deck == deck_before
    assert state.players[0].discard == discard_before


def test_empty_draw_pile_reshuffles_discard_only_when_draw_is_required() -> None:
    engine, state = setup_state()
    state.players[1].hand = state.players[1].hand[:9]
    state.players[1].deck.clear()
    state.players[1].discard = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    engine.apply(state, Pass())

    assert len(state.players[1].hand) == 10
    assert state.players[1].discard == []
    assert state.deck_reshuffles[1] == 1


def test_ongoing_story_slot_does_not_receive_adjacent_front_discount() -> None:
    engine, state = setup_state()
    target = pos(0, Rank.FRONT)
    slot = state.slot(0, target)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "elian"
    state.players[0].hand = ["the-long-march"]
    state.players[0].command = 20

    story = PlayStory("the-long-march", ongoing_slot=1)
    assert story in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, story) == 2


def test_ongoing_stories_are_public_and_limited_to_two_per_player() -> None:
    engine, state = setup_state()
    assert engine.ongoing_narrative_limit == 2
    stories = [
        "the-long-march",
        "they-returned-with-names",
        "the-crows-came-down",
    ]
    state.players[0].hand = list(stories)
    state.players[0].command = 20

    first = PlayStory(stories[0], ongoing_slot=0)
    assert first in engine.legal_actions(state)
    engine.apply(state, first)

    state.active_player = 0
    second = PlayStory(stories[1], ongoing_slot=1)
    assert second in engine.legal_actions(state)
    engine.apply(state, second)

    assert [story.card_id for story in state.stories[0]] == stories[:2]
    state.active_player = 0
    legal = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayStory) and action.card_id == stories[2]
        for action in legal
    )


def test_hero_and_stratagem_allowances_are_once_per_battle() -> None:
    engine, state = setup_state()
    hero_a = "avaros-the-bronze-king"
    hero_b = "kael-the-roadless"
    state.players[0].hand = [hero_a, hero_b, "the-ground-was-held", "the-lines-held"]
    state.players[0].command = 20

    engine.apply(state, PlayForce(hero_a, pos(0)))
    assert state.hero_used[0] is True

    state.active_player = 0
    legal = engine.legal_actions(state)
    assert not any(
        isinstance(action, (PlayForce, PlayName))
        and action.card_id == hero_b
        for action in legal
    )

    engine.apply(state, PlayStratagem("the-ground-was-held"))
    assert state.stratagem_used[0] is True

    state.active_player = 0
    legal = engine.legal_actions(state)
    assert PlayStratagem("the-lines-held") not in legal


def test_first_passer_starts_next_battle() -> None:
    engine, state = setup_state()
    resolve_battle_by_passing(engine, state)
    assert state.battle == 2
    assert state.active_player == 0
