from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import (
    Discard,
    EffectChoice,
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
    rules: GameRules | None = None,
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
    assert engine.position_strength(state, 0, frontline) == 4
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
    assert len(state.players[1].hand) == engine.opening_hand_size - 1
    before_drawn = state.cards_drawn_this_battle[1]

    engine.apply(state, Pass())

    assert state.battle == 1
    assert state.active_player == 1
    assert state.pass_order == [0]
    assert state.players[0].passed is True
    assert state.players[1].passed is False
    assert len(state.players[1].hand) == engine.opening_hand_size
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
    rules = GameRules.standard()
    rules = rules.with_overrides(opening_hand_size=rules.hand_limit)
    engine, state = setup_state(opening_bonus=True, rules=rules)
    assert len(state.players[0].hand) == engine.hand_limit
    assert state.pending_draw_discard_for == 0

    legal = engine.legal_actions(state)
    assert legal
    assert all(isinstance(action, Discard) for action in legal)

    discarded = legal[0].card_id
    deck_before = len(state.players[0].deck)
    engine.apply(state, legal[0])

    assert state.pending_draw_discard_for is None
    assert len(state.players[0].hand) == engine.hand_limit
    assert len(state.players[0].deck) == deck_before - 1
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
    # discard-before-draw substep after the operation finishes.
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
    assert len(state.players[0].hand) == engine.hand_limit
    assert state.pending_draw_discard_for == 0
    assert state.pending_draw_count == 1
    assert state.pending_draw_finish_operation is True

    engine.apply(state, engine.legal_actions(state)[0])
    assert len(state.players[0].hand) == engine.hand_limit
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
    state.players[1].hand = ["the-fifty-men"] * (engine.hand_limit - 1)
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
    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_refunded"][0] >= 1
    assert snapshot["command_before_recovery"][0] == 11
    assert state.players[0].command == min(
        engine.rules.command_cap,
        snapshot["command_before_recovery"][0]
        + snapshot["recovery_actual"][0],
    )


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
    state.slot(0, pos(0, Rank.REAR)).force = "seven-black-ships"
    state.slot(1, pos(0, Rank.FRONT)).force = "the-fifty-men"
    state.slot(1, pos(0, Rank.REAR)).force = "seven-black-ships"

    resolve_battle_by_passing(engine, state)

    assert state.last_battle_snapshot["front_scores"][0] == [3, 4]


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
    expected = min(
        engine.rules.command_cap,
        5 + engine.command_recovery_for_battle(1),
    )
    assert state.players[0].command == expected

    engine, state = setup_state(seed=4702)
    state.players[0].command = 5
    state.players[1].command = 20
    state.battle_start_command[:] = [5, 20]
    state.slot(0, pos(0, Rank.REAR)).force = "tovan-the-quartermaster"
    make_named(state, 1, pos(0, Rank.FRONT), temporary=100)

    resolve_battle_by_passing(engine, state)
    expected = min(
        engine.rules.command_cap,
        5 + engine.command_recovery_for_battle(1),
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
        5 + max(engine.rules.command_recovery_floor, base - 2),
    )
    expected_p1 = min(
        engine.rules.command_cap,
        (rules.command_cap - 1) + max(engine.rules.command_recovery_floor, base),
    )
    assert state.players[0].command == expected_p0
    assert state.players[1].command == expected_p1


def test_command_collapse_lower_command_loses_and_equal_threshold_continues() -> None:
    rules = GameRules.standard().with_overrides(
        command_collapse_threshold=0,
        command_recovery_start=0,
        command_recovery_decrement=0,
        command_recovery_floor=1,
    )
    engine, state = setup_state(rules=rules)
    state.players[0].command = 0
    state.players[1].command = 6
    state.battle_start_command[:] = [0, 6]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.COMPLETE
    assert state.winner == 1

    engine, state = setup_state(seed=4301, rules=rules)
    state.players[0].command = 0
    state.players[1].command = 0
    state.battle_start_command[:] = [0, 0]
    resolve_battle_by_passing(engine, state)
    assert state.phase is Phase.BATTLE
    assert state.winner is None
    assert state.battle == 2


def test_hand_deck_discard_and_named_formations_persist_between_battles() -> None:
    engine, state = setup_state()
    make_named(state, 0, pos(0))
    state.players[0].discard.append(state.players[0].hand.pop())
    # Restore the configured hand-limit size so Battle-end refill does not move cards.
    state.players[0].hand.append(state.players[0].deck.pop())
    hand_before = list(state.players[0].hand)
    deck_before = list(state.players[0].deck)
    discard_before = list(state.players[0].discard)

    resolve_battle_by_passing(engine, state)

    assert state.slot(0, pos(0)).complete is True
    assert Counter(state.players[0].hand) == Counter(hand_before)
    assert state.players[0].deck == deck_before
    assert state.players[0].discard == discard_before


def test_empty_draw_pile_reshuffles_discard_only_when_draw_is_required() -> None:
    engine, state = setup_state()
    state.players[1].hand = ["the-fifty-men"] * (engine.hand_limit - 1)
    state.players[1].deck.clear()
    state.players[1].discard = ["the-fifty-men"]
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    engine.apply(state, Pass())

    assert len(state.players[1].hand) == engine.hand_limit
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

    story = PlayStory("the-long-march", ongoing_slot=0)
    assert story in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, story) == 2


def test_ongoing_stories_are_public_and_respect_configured_limit() -> None:
    rules = GameRules.standard().with_overrides(ongoing_narrative_limit=2)
    engine, state = setup_state(rules=rules)
    assert engine.ongoing_narrative_limit == rules.ongoing_narrative_limit
    stories = [
        "the-long-march",
        "they-returned-with-names",
        "the-crows-came-down",
    ]
    state.players[0].hand = list(stories)
    state.players[0].command = 20
    state.players[1].hand = []

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
    state.players[1].hand = []

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
    maneuver = Maneuver(pos(0, Rank.FRONT), pos(1, Rank.FRONT))
    assert maneuver in engine.legal_actions(state)
    assert engine.command_cost_for_action(state, maneuver) == 0

    engine.apply(state, maneuver)
    assert state.free_maneuver_available[0] is False


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
    assert any(not choice.skip for choice in choices)


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


def test_sela_can_move_sideways_after_forced_retreat() -> None:
    engine, state = setup_state(seed=4811)
    make_named(state, 0, pos(0, Rank.FRONT), name="sela")
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        temporary=100,
    )

    resolve_battle_by_passing(engine, state)

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


def test_neris_force_can_move_retreating_frontline_sideways() -> None:
    engine, state = setup_state(seed=4812)
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(
        state,
        0,
        pos(0, Rank.REAR),
        force="neris-the-ferryman",
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        temporary=100,
    )

    resolve_battle_by_passing(engine, state)

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

    assert state.slot(0, pos(1, Rank.REAR)).force == "the-fifty-men"
    assert "neris-the-ferryman" in state.players[0].discard


def test_covered_withdrawal_grants_free_maneuver_after_adjacent_retreat() -> None:
    engine, state = setup_state(seed=4813)
    make_named(state, 0, pos(0, Rank.FRONT))
    make_named(
        state,
        0,
        pos(1, Rank.REAR),
        bond="covered-the-withdrawal-of",
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        temporary=100,
    )

    resolve_battle_by_passing(engine, state)

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
    state.stories[0] = [
        StoryState(
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
    assert snapshot["command_before_recovery"][0] == 11
    assert state.players[0].command == min(
        engine.rules.command_cap,
        snapshot["command_before_recovery"][0]
        + snapshot["recovery_actual"][0],
    )
    assert "followed" in state.players[0].hand
    assert "the-wall-did-not-break" in state.players[0].discard


def test_before_sunset_draws_at_battle_end_and_records_refund() -> None:
    engine, state = setup_state(seed=4815)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[0].hand = []
    make_named(state, 0, pos(0, Rank.FRONT))
    state.stories[0] = [
        StoryState(
            "before-sunset-the-ford-would-be-ours",
            fronts=(Front.FIRST,),
        )
    ]

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot["command_refunded"][0] >= 2
    assert snapshot["cards_drawn"][0] >= 1
    assert "before-sunset-the-ford-would-be-ours" in state.players[0].discard


def test_meren_repositions_before_first_turn_of_next_battle() -> None:
    engine, state = setup_state(seed=4816)
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


def test_alda_can_be_driven_off_to_prevent_frontline_retreat() -> None:
    engine, state = setup_state(seed=4829)
    frontline = pos(0, Rank.FRONT)
    rear = pos(0, Rank.REAR)
    make_named(state, 0, frontline)
    make_named(
        state,
        0,
        rear,
        force="alda-keeper-of-the-ford",
    )
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        temporary=100,
    )

    resolve_battle_by_passing(engine, state)

    protect = next(
        action
        for action in effect_choices(engine, state, "protect-retreat")
        if not action.skip
    )
    engine.apply(state, protect)

    assert state.slot(0, frontline).named is True
    assert state.slot(0, rear).occupied is False
    assert "alda-keeper-of-the-ford" in state.players[0].discard


def test_stayed_behind_for_is_discarded_if_mandatory_retreat_displaces_it() -> None:
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
    make_named(
        state,
        1,
        pos(0, Rank.FRONT),
        temporary=100,
    )

    resolve_battle_by_passing(engine, state)

    decline = next(
        action
        for action in effect_choices(engine, state, "protect-retreat")
        if action.skip
    )
    engine.apply(state, decline)

    # Alda is driven off normally. Stayed Behind For persists through that
    # drive-off, but the mandatory Frontline Retreat then needs the same Rear
    # position. The prepared Bond is displaced to discard rather than silently
    # overwritten.
    assert state.slot(0, frontline).occupied is False
    assert state.slot(0, rear).named is True
    assert state.slot(0, rear).bond != "stayed-behind-for"
    assert "stayed-behind-for" in state.players[0].discard
    assert "namar" in state.players[0].hand


def test_they_lived_to_tell_it_rewards_a_surviving_target() -> None:
    engine, state = setup_state(seed=4830)
    state.battle = 8
    state.players[0].command = 10
    state.players[1].command = 10
    state.battle_start_command[:] = [10, 10]
    state.players[0].hand = []
    target = pos(0, Rank.FRONT)
    make_named(state, 0, target)
    state.stories[0] = [
        StoryState(
            "they-lived-to-tell-it",
            target_player=0,
            target_position=target,
        )
    ]

    resolve_battle_by_passing(engine, state)

    snapshot = state.last_battle_snapshot
    assert snapshot is not None
    assert snapshot["command_refunded"][0] >= 1
    assert snapshot["command_before_recovery"][0] == 11
    assert state.players[0].command == min(
        engine.rules.command_cap,
        snapshot["command_before_recovery"][0]
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
    state.stories[0] = [StoryState("the-long-march")]
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

    state.players[0].discard[:] = ["followed"]
    recovery = {
        "kind": 4,  # EFFECT_RECOVER
        "player": 0,
        "card": -1,
        "source": -1,
        "aux": 2,  # CARD_LINK
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
            "aux": 2,  # CARD_LINK
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
            "source_mask": 1 << 8,
            "dest_mask": 1 << 10,
            "flags": 1,
        }
    ]
    state.active_player = 0

    choices = effect_choices(engine, state, "move")
    assert choices
    assert all(choice.skip for choice in choices)


def test_eira_succession_resolver_moves_name_then_drives_off_source() -> None:
    engine, state = setup_state(seed=4835)
    source = pos(0, Rank.FRONT)
    destination = pos(1, Rank.FRONT)
    make_named(state, 0, source, name="eira")
    target = state.slot(0, destination)
    target.force = "the-fifty-men"
    target.bond = "followed"

    # Exercise the resumable replacement resolver directly. Normal Battle-end
    # cleanup removes incomplete formations before drive-off, so this state is
    # intentionally synthetic.
    state.pending_effects = [
        {
            "kind": 12,
            "player": 0,
            "card": -1,
            "source": 0,
            "aux": -1,
            "source_mask": 0,
            "dest_mask": 1 << 2,
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
