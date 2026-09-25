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
from longwar.game.model import FRONT_COUNT, Phase
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
DECK_FILE = ROOT / "decks" / "reference.json"


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

    # The final opponent turn includes its normal draw. Make one hand slot
    # available without changing the total card multiset; start_turn will draw
    # this exact top card back before the final Pass.
    if len(state.players[1].hand) >= engine.hand_limit:
        card = state.players[1].hand.pop()
        state.players[1].deck.append(card)

    engine.apply(state, Pass())
    assert state.pending_final_operation_for == 1
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


def test_role_bonuses_apply_without_universal_line_defense() -> None:
    engine, state = setup_state()

    ship_front = pos(0, Rank.FRONT)
    state.slot(0, ship_front).force = "seven-black-ships"
    assert engine.position_strength(state, 0, ship_front) == 4

    sword_front = pos(1, Rank.FRONT)
    state.slot(0, sword_front).force = "the-fifty-men"
    assert engine.position_strength(state, 0, sword_front) == 5

    spear_front = pos(2, Rank.FRONT)
    spear_rear = pos(2, Rank.REAR)
    state.slot(0, spear_front).force = "those-who-came-back"
    state.slot(0, spear_rear).force = "seven-black-ships"
    assert engine.position_strength(state, 0, spear_front) == 4

    archer_front = pos(3, Rank.FRONT)
    archer_rear = pos(3, Rank.REAR)
    state.slot(0, archer_front).force = "the-fifty-men"
    state.slot(0, archer_rear).force = "the-crow-archers"
    assert engine.position_strength(state, 0, archer_rear) == 6

    healer_rear = pos(1, Rank.REAR)
    state.slot(0, healer_rear).force = "the-white-hands-of-elara"
    assert engine.position_strength(state, 0, sword_front) == 7

    ship_rear = pos(0, Rank.REAR)
    state.slot(0, ship_rear).force = "seven-black-ships"
    assert engine.position_strength(state, 0, ship_rear) == 5

    stronghold_rear = pos(2, Rank.REAR)
    state.slot(0, stronghold_rear).force = "the-house-of-reed"
    assert engine.position_strength(state, 0, stronghold_rear) == 6


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
    state.players[0].hand = ["the-three-brothers-of-avar"]
    state.players[0].command = 20

    legal = engine.legal_actions(state)
    assert PlayForce("the-three-brothers-of-avar", front) in legal
    assert PlayForce("the-three-brothers-of-avar", rear) not in legal

    make_named(
        state,
        0,
        front,
        force="the-three-brothers-of-avar",
    )
    make_named(state, 1, front, temporary=100)
    resolve_battle_by_passing(engine, state)

    assert state.slot(0, front).force is None
    assert state.slot(0, rear).force == "the-three-brothers-of-avar"


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
    target.bond = "swore-to"
    target.name = "iria"
    state.players[0].command = 5

    action = Maneuver(source, destination)
    assert action in engine.legal_actions(state)
    engine.apply(state, action)

    assert state.slot(0, destination).force == "seven-black-ships"
    assert state.slot(0, destination).bond == "followed"
    assert state.slot(0, destination).name == "namar"
    assert state.slot(0, source).force is None
    assert state.slot(0, source).bond == "swore-to"
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


def test_first_pass_gives_opponent_one_final_turn_with_normal_draw() -> None:
    engine, state = setup_state()
    state.operations_this_battle[:] = [1, 1]
    state.active_player = 0

    moved = state.players[1].hand.pop()
    state.players[1].discard.append(moved)
    assert len(state.players[1].hand) == 9
    before_drawn = state.cards_drawn_this_battle[1]

    engine.apply(state, Pass())

    assert state.active_player == 1
    assert state.pending_final_operation_for == 1
    assert len(state.players[1].hand) == 10
    assert state.cards_drawn_this_battle[1] == before_drawn + 1


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


def test_ongoing_stories_are_public_and_limited_to_two_per_player() -> None:
    engine, state = setup_state()
    stories = [
        "the-lamps-went-dark",
        "the-road-was-cut",
        "the-hidden-oars",
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
    hero_b = "mara-queen-of-cinders"
    state.players[0].hand = [hero_a, hero_b, "the-storm-broke", "the-tide-rose"]
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

    engine.apply(state, PlayStratagem("the-storm-broke"))
    assert state.stratagem_used[0] is True

    state.active_player = 0
    legal = engine.legal_actions(state)
    assert PlayStratagem("the-tide-rose") not in legal


def test_first_passer_starts_next_battle() -> None:
    engine, state = setup_state()
    resolve_battle_by_passing(engine, state)
    assert state.battle == 2
    assert state.active_player == 0
