from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    BoardTarget,
    ChooseFirst,
    Draw,
    Front,
    GameEngine,
    Pass,
    Phase,
    PlayLink,
    PlayName,
    PlayPlot,
    PlayScheme,
    PlaySubject,
    Position,
    SetStratagem,
    Rank,
)

ROOT = Path(__file__).resolve().parents[1]
CENTER_FRONT = Position(Front.CENTER, Rank.FRONT)
LEFT_FRONT = Position(Front.LEFT, Rank.FRONT)


def engine_and_deck() -> tuple[GameEngine, list[str]]:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    return engine, deck


def fresh_state(*, first_player: int = 0):
    engine, deck = engine_and_deck()
    state = engine.new_game(deck, deck, seed=42, first_player=first_player)
    return engine, state


def test_setup_draws_ten_and_keeps_twenty_in_deck() -> None:
    _, state = fresh_state()
    assert [len(player.hand) for player in state.players] == [10, 10]
    assert [len(player.deck) for player in state.players] == [20, 20]
    assert state.battle == 1
    assert state.phase is Phase.BATTLE

def test_draw_is_a_once_per_battle_normal_action() -> None:
    engine, state = fresh_state(first_player=0)
    hand_before = len(state.players[0].hand)
    deck_before = len(state.players[0].deck)

    assert any(isinstance(action, Draw) for action in engine.legal_actions(state))
    engine.apply(state, Draw())

    assert len(state.players[0].hand) == hand_before + 1
    assert len(state.players[0].deck) == deck_before - 1
    assert state.draw_used == [True, False]
    assert state.active_player == 1

    state.active_player = 0
    assert not any(isinstance(action, Draw) for action in engine.legal_actions(state))


def test_draw_is_not_legal_with_an_empty_deck() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].deck.clear()
    assert not any(isinstance(action, Draw) for action in engine.legal_actions(state))


def test_battle_draw_resets_for_the_next_battle() -> None:
    engine, state = fresh_state(first_player=0)
    state.draw_used = [True, True]
    state.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.phase is Phase.CHOOSE_FIRST
    assert state.draw_used == [False, False]



def test_links_help_immediately_and_namar_rewards_frontline() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-fifty-men", "followed", "namar"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 6

    engine.apply(state, PlayLink("followed", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 7

    engine.apply(state, PlayName("namar", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 13


def test_iria_can_move_subject_with_attachments_to_adjacent_position() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-fifty-men", "followed", "iria"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    engine.apply(state, PlayLink("followed", CENTER_FRONT))
    engine.apply(state, PlayName("iria", CENTER_FRONT, LEFT_FRONT))

    assert not state.slot(0, CENTER_FRONT).occupied
    moved = state.slot(0, LEFT_FRONT)
    assert moved.complete
    assert moved.name == "iria"


def test_story_is_false_breaks_link_and_returns_name() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    slot.name = "namar"
    state.players[1].hand = ["the-story-is-false"]

    engine.apply(
        state,
        PlayPlot(
            "the-story-is-false",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert slot.link is None
    assert slot.name is None
    assert "namar" in state.players[0].hand
    assert "followed" in state.players[0].discard


def test_story_is_false_weakens_bare_subject() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    state.players[1].hand = ["the-story-is-false"]

    engine.apply(
        state,
        PlayPlot(
            "the-story-is-false",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert slot.link is None
    assert engine.position_strength(state, 0, CENTER_FRONT) == 4


def test_story_is_false_does_not_trigger_old_swore_to_penalty() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "swore-to"
    slot.name = "namar"
    state.players[1].hand = ["the-story-is-false"]

    engine.apply(
        state,
        PlayPlot(
            "the-story-is-false",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert slot.link is None
    assert slot.name is None
    assert "swore-to" in state.players[0].discard
    assert "namar" in state.players[0].hand


def test_he_never_came_returns_name_but_leaves_subject_and_link() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "swore-to"
    slot.name = "namar"
    state.players[1].hand = ["he-never-came"]

    engine.apply(
        state,
        PlayPlot(
            "he-never-came",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert slot.link == "swore-to"
    assert slot.name is None
    assert "namar" in state.players[0].hand


def test_he_never_came_weakens_subject_when_no_name_is_attached() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[1].hand = ["he-never-came"]

    engine.apply(
        state,
        PlayPlot(
            "he-never-came",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert slot.link == "followed"
    assert slot.name is None
    assert engine.position_strength(state, 0, CENTER_FRONT) == 5


def test_he_never_came_is_useful_against_bare_subject() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    state.players[1].hand = ["he-never-came"]

    engine.apply(
        state,
        PlayPlot(
            "he-never-came",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert slot.subject == "the-fifty-men"
    assert engine.position_strength(state, 0, CENTER_FRONT) == 4


def test_carried_protects_its_subject_from_opponent_plot() -> None:
    engine, state = fresh_state(first_player=1)
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "carried"
    slot.name = "namar"
    state.players[1].hand = ["he-never-came"]

    actions = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayPlot)
        and action.card_id == "he-never-came"
        and action.targets == (BoardTarget(0, CENTER_FRONT),)
        for action in actions
    )


def test_children_gain_temporary_strength_when_link_played() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-children-of-the-salt-road", "followed"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(
        state,
        PlaySubject("the-children-of-the-salt-road", CENTER_FRONT),
    )
    engine.apply(state, PlayLink("followed", CENTER_FRONT))

    assert engine.position_strength(state, 0, CENTER_FRONT) == 6


def test_battle_scoring_and_loser_chooses_next_first_player() -> None:
    engine, state = fresh_state(first_player=0)
    state.slot(0, Position(Front.LEFT, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(0, Position(Front.CENTER, Rank.FRONT)).subject = "the-fifty-men"
    state.slot(1, Position(Front.RIGHT, Rank.FRONT)).subject = "the-fifty-men"

    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.players[0].victories == 1
    assert state.phase is Phase.CHOOSE_FIRST
    assert state.chooser == 1
    assert state.active_player == 1

    engine.apply(state, ChooseFirst(1))
    assert state.phase is Phase.BATTLE
    assert state.active_player == 1
    assert state.battle == 2


def test_defied_reduces_opposing_front_strength() -> None:
    engine, state = fresh_state()
    left0 = state.slot(0, LEFT_FRONT)
    left0.subject = "the-fifty-men"
    left0.link = "defied"
    left0.name = "oren"

    left1 = state.slot(1, LEFT_FRONT)
    left1.subject = "the-fifty-men"

    assert engine.front_strength(state, 0, Front.LEFT) == 11
    assert engine.front_strength(state, 1, Front.LEFT) == 4


def test_they_chose_another_moves_subject_and_all_attachments() -> None:
    engine, state = fresh_state(first_player=0)
    source = state.slot(0, LEFT_FRONT)
    destination_position = Position(Front.RIGHT, Rank.REAR)
    destination = state.slot(0, destination_position)
    source.subject = "the-fifty-men"
    source.link = "followed"
    source.name = "oren"
    state.players[0].hand = ["they-chose-another"]

    engine.apply(
        state,
        PlayPlot(
            "they-chose-another",
            (
                BoardTarget(0, LEFT_FRONT),
                BoardTarget(0, destination_position),
            ),
        ),
    )

    assert not source.occupied
    assert destination.subject == "the-fifty-men"
    assert destination.link == "followed"
    assert destination.name == "oren"


def test_they_chose_another_respects_frontline_only_subjects() -> None:
    engine, state = fresh_state(first_player=0)
    source = state.slot(0, LEFT_FRONT)
    source.subject = "the-three-brothers-of-avar"
    state.players[0].hand = ["they-chose-another"]

    actions = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayPlot)
        and action.card_id == "they-chose-another"
        and len(action.targets) == 2
        and action.targets[1].position.rank is Rank.REAR
        for action in actions
    )


def test_namar_frontline_bonus_does_not_apply_in_rear() -> None:
    engine, state = fresh_state()
    rear = Position(Front.CENTER, Rank.REAR)
    slot = state.slot(0, rear)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    slot.name = "namar"

    assert engine.position_strength(state, 0, rear) == 9


def test_face_down_scheme_adds_front_strength_until_revealed() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-lamps-went-dark"]

    assert engine.front_strength(state, 0, Front.CENTER) == 0
    engine.apply(state, PlayScheme("the-lamps-went-dark", Front.CENTER))
    assert engine.front_strength(state, 0, Front.CENTER) == 1

    scheme = state.scheme(0, Front.CENTER)
    assert scheme is not None
    scheme.revealed = True
    assert engine.front_strength(state, 0, Front.CENTER) == 0


def test_lamps_scheme_penalizes_played_subject() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[1].hand = ["the-lamps-went-dark"]
    state.players[0].hand = ["the-fifty-men"]

    engine.apply(state, PlayScheme("the-lamps-went-dark", Front.CENTER))
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))

    assert state.scheme(1, Front.CENTER) is None
    assert "the-lamps-went-dark" in state.players[1].discard
    assert engine.position_strength(state, 0, CENTER_FRONT) == 3


def test_road_cut_discards_link_as_scheme_trigger() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[1].hand = ["the-road-was-cut"]
    state.players[0].hand = ["followed"]
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"

    engine.apply(state, PlayScheme("the-road-was-cut", Front.CENTER))
    engine.apply(state, PlayLink("followed", CENTER_FRONT))

    assert state.slot(0, CENTER_FRONT).link is None
    assert "followed" in state.players[0].discard
    assert "the-road-was-cut" in state.players[1].discard


def test_hidden_oars_resolves_before_second_pass_scores_battle() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[1].hand = ["the-hidden-oars"]
    state.slot(1, CENTER_FRONT).subject = "the-fifty-men"

    engine.apply(state, PlayScheme("the-hidden-oars", Front.CENTER))
    engine.apply(state, Pass())

    assert state.scheme(1, Front.CENTER) is None
    assert engine.position_strength(state, 1, CENTER_FRONT) == 9


def test_witness_lied_triggers_only_when_plot_targets_own_front() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[1].hand = ["the-witness-lied"]
    state.players[0].hand = ["the-story-is-false"]
    state.slot(1, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(1, CENTER_FRONT).link = "followed"

    engine.apply(state, PlayScheme("the-witness-lied", Front.CENTER))
    engine.apply(
        state,
        PlayPlot(
            "the-story-is-false",
            (BoardTarget(1, CENTER_FRONT),),
        ),
    )

    assert state.scheme(1, Front.CENTER) is None
    assert engine.position_strength(state, 1, CENTER_FRONT) == 9


def test_teyra_reveals_scheme_without_resolving_it() -> None:
    engine, state = fresh_state(first_player=0)
    state.schemes[1][int(Front.CENTER)] = __import__(
        "longwar.game.model", fromlist=["SchemeState"]
    ).SchemeState("the-lamps-went-dark")
    slot = state.slot(0, CENTER_FRONT)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    state.players[0].hand = ["teyra"]

    engine.apply(state, PlayName("teyra", CENTER_FRONT))

    scheme = state.scheme(1, Front.CENTER)
    assert scheme is not None
    assert scheme.revealed is True
    assert scheme.card_id == "the-lamps-went-dark"



def test_line_defense_and_swordsman_role_stack() -> None:
    engine, state = fresh_state()
    front = Position(Front.CENTER, Rank.FRONT)
    rear = Position(Front.CENTER, Rank.REAR)

    state.slot(0, front).subject = "the-fifty-men"
    assert engine.position_strength(state, 0, front) == 6

    state.slot(0, front).subject = None
    state.slot(0, rear).subject = "the-fifty-men"
    assert engine.position_strength(state, 0, rear) == 4


def test_spearman_rewards_a_subject_behind_it() -> None:
    engine, state = fresh_state()
    front = Position(Front.CENTER, Rank.FRONT)
    rear = Position(Front.CENTER, Rank.REAR)
    state.slot(0, front).subject = "those-who-came-back"

    assert engine.position_strength(state, 0, front) == 4
    state.slot(0, rear).subject = "the-house-at-orra"
    assert engine.position_strength(state, 0, front) == 5


def test_archer_rewards_a_subject_in_front() -> None:
    engine, state = fresh_state()
    front = Position(Front.CENTER, Rank.FRONT)
    rear = Position(Front.CENTER, Rank.REAR)
    state.slot(0, rear).subject = "the-children-of-the-salt-road"

    assert engine.position_strength(state, 0, rear) == 3
    state.slot(0, front).subject = "the-fifty-men"
    assert engine.position_strength(state, 0, rear) == 5


def test_healer_strengthens_subject_directly_in_front() -> None:
    engine, state = fresh_state()
    front = Position(Front.CENTER, Rank.FRONT)
    rear = Position(Front.CENTER, Rank.REAR)
    state.slot(0, front).subject = "the-fifty-men"
    state.slot(0, rear).subject = "the-white-hands-of-elara"

    assert engine.position_strength(state, 0, rear) == 2
    assert engine.position_strength(state, 0, front) == 8


def test_healer_is_rear_only() -> None:
    engine, state = fresh_state()
    state.players[0].hand = ["the-white-hands-of-elara"]

    actions = engine.legal_actions(state)
    healer_actions = [
        action
        for action in actions
        if isinstance(action, PlaySubject)
        and action.card_id == "the-white-hands-of-elara"
    ]
    assert healer_actions
    assert all(action.position.rank is Rank.REAR for action in healer_actions)


def test_ship_and_stronghold_prefer_rear() -> None:
    engine, state = fresh_state()
    rear = Position(Front.CENTER, Rank.REAR)

    state.slot(0, rear).subject = "seven-black-ships"
    assert engine.position_strength(state, 0, rear) == 5

    state.slot(0, rear).subject = "the-house-at-orra"
    assert engine.position_strength(state, 0, rear) == 5


def test_hero_is_strong_and_buffs_adjacent_subjects() -> None:
    engine, state = fresh_state()
    hero_position = Position(Front.CENTER, Rank.FRONT)
    adjacent = Position(Front.LEFT, Rank.FRONT)
    state.slot(0, hero_position).subject = "avaros-the-bronze-king"
    state.slot(0, adjacent).subject = "the-fifty-men"

    assert engine.position_strength(state, 0, hero_position) == 8
    assert engine.position_strength(state, 0, adjacent) == 7


def test_deck_requires_exactly_one_hero() -> None:
    from longwar.game.engine import InvalidDeck

    engine, deck = engine_and_deck()
    engine.validate_deck(deck)

    without_hero = list(deck)
    without_hero.remove("avaros-the-bronze-king")
    without_hero.append("seven-black-ships")

    try:
        engine.validate_deck(without_hero)
    except InvalidDeck as exc:
        assert "exactly one Hero" in str(exc)
    else:
        raise AssertionError("Deck without a Hero should be invalid")


def test_stratagem_is_free_pre_action_and_only_one_may_be_set_per_battle() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = [
        "the-storm-broke",
        "the-tide-rose",
        "the-fifty-men",
    ]

    engine.apply(state, SetStratagem("the-storm-broke"))

    assert state.active_player == 0
    assert state.stratagem_used[0] is True
    assert state.stratagem(0) is not None
    assert state.stratagem(0).revealed is False
    assert not any(
        isinstance(action, SetStratagem)
        for action in engine.legal_actions(state)
    )

    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    assert state.active_player == 1


def test_storm_reveals_on_ship_and_modifies_ships_and_archers_for_both_players() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    state.players[0].hand = ["the-storm-broke", "seven-black-ships"]

    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, PlaySubject("seven-black-ships", rear))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, rear) == 7

    state.slot(1, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(1, rear).subject = "the-children-of-the-salt-road"
    assert engine.position_strength(state, 1, rear) == 3


def test_high_tide_reveals_on_pass_and_changes_line_defense_and_ships() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(0, rear).subject = "seven-black-ships"
    state.players[0].hand = ["the-tide-rose"]

    engine.apply(state, SetStratagem("the-tide-rose"))
    engine.apply(state, Pass())

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, CENTER_FRONT) == 5
    assert engine.position_strength(state, 0, rear) == 6


def test_ground_gave_way_reveals_from_rear_and_shifts_both_ranks() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    state.players[0].hand = ["the-ground-gave-way", "the-fifty-men"]

    engine.apply(state, SetStratagem("the-ground-gave-way"))
    engine.apply(state, PlaySubject("the-fifty-men", rear))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, rear) == 5

    state.slot(1, CENTER_FRONT).subject = "the-fifty-men"
    assert engine.position_strength(state, 1, CENTER_FRONT) == 5


def test_bronze_teeth_hurts_trigger_subject_and_its_controllers_frontline() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-bronze-teeth", "the-fifty-men"]
    state.players[1].hand = ["the-fifty-men"]

    engine.apply(state, SetStratagem("the-bronze-teeth"))
    engine.apply(state, PlaySubject("the-fifty-men", LEFT_FRONT))
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, LEFT_FRONT) == 5
    assert engine.position_strength(state, 1, CENTER_FRONT) == 4


def test_false_muster_cancels_story_then_locks_own_immediate_stories() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-false-muster", "the-fifty-men"]
    state.players[1].hand = ["the-story-is-false"]
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(0, CENTER_FRONT).link = "followed"

    engine.apply(state, SetStratagem("the-false-muster"))
    engine.apply(state, PlaySubject("the-fifty-men", LEFT_FRONT))
    engine.apply(
        state,
        PlayPlot(
            "the-story-is-false",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert state.stratagem(0).revealed is True
    assert state.slot(0, CENTER_FRONT).link == "followed"
    assert "the-story-is-false" in state.players[1].discard

    state.players[0].hand = ["he-never-came", "the-lamps-went-dark"]
    actions = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayPlot)
        and action.card_id == "he-never-came"
        for action in actions
    )
    assert any(
        isinstance(action, PlayScheme)
        and action.card_id == "the-lamps-went-dark"
        for action in actions
    )


def test_wooden_gift_revalues_named_and_unnamed_subjects() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.LEFT, Rank.REAR)
    state.players[0].hand = ["the-wooden-gift", "the-fifty-men"]
    state.players[1].hand = ["oren"]

    engine.apply(state, SetStratagem("the-wooden-gift"))
    engine.apply(state, PlaySubject("the-fifty-men", rear))

    enemy = state.slot(1, CENTER_FRONT)
    enemy.subject = "the-fifty-men"
    enemy.link = "followed"
    engine.apply(state, PlayName("oren", CENTER_FRONT))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, rear) == 5
    assert engine.position_strength(state, 1, CENTER_FRONT) == 10


def test_opposing_stratagems_can_reveal_and_stack() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    state.players[0].hand = ["the-storm-broke"]
    state.players[1].hand = ["the-storm-broke", "seven-black-ships"]

    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, Pass())
    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, PlaySubject("seven-black-ships", rear))

    assert state.stratagem(0).revealed is True
    assert state.stratagem(1).revealed is True
    assert engine.position_strength(state, 1, rear) == 9


def test_untriggered_stratagem_reveals_and_discards_at_battle_end() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-storm-broke"]

    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert "the-storm-broke" in state.players[0].discard
    assert any(
        event.kind == "reveal"
        and event.zone == "stratagem"
        and event.card_id == "the-storm-broke"
        and event.reason == "battle_end"
        for event in state.observations
    )


def test_setting_stratagem_is_free_and_one_opportunity_per_battle() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-storm-broke", "the-tide-rose"]
    turn_number = state.turn_number

    engine.apply(state, SetStratagem("the-storm-broke"))

    assert state.active_player == 0
    assert state.turn_number == turn_number
    assert state.stratagem_used[0] is True
    assert state.stratagem(0) is not None
    assert state.stratagem(0).card_id == "the-storm-broke"

    # The opportunity is spent, not merely the physical slot. Even if a future
    # effect ever cleared the slot, a second Stratagem would remain illegal.
    state.stratagems[0] = None
    assert not any(
        isinstance(action, SetStratagem)
        for action in engine.legal_actions(state)
    )


def test_unrevealed_stratagem_is_revealed_after_scoring_then_reset() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-storm-broke"]

    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, Pass())
    engine.apply(state, Pass())

    assert state.battle == 2
    assert state.stratagem(0) is None
    assert state.stratagem_used == [False, False]
    assert "the-storm-broke" in state.players[0].discard
    assert any(
        event.kind == "reveal"
        and event.zone == "stratagem"
        and event.card_id == "the-storm-broke"
        and event.reason == "battle_end"
        for event in state.observations
    )


def test_storm_reveals_on_ship_and_changes_ship_and_archer_strength() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    archer_rear = Position(Front.LEFT, Rank.REAR)
    state.players[0].hand = ["the-storm-broke", "seven-black-ships"]

    engine.apply(state, SetStratagem("the-storm-broke"))
    engine.apply(state, PlaySubject("seven-black-ships", rear))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, rear) == 7

    state.slot(0, archer_rear).subject = "the-children-of-the-salt-road"
    assert engine.position_strength(state, 0, archer_rear) == 1


def test_tide_reveals_on_pass_and_disables_line_defense() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.LEFT, Rank.REAR)
    state.players[0].hand = ["the-tide-rose"]
    state.slot(0, CENTER_FRONT).subject = "the-fifty-men"
    state.slot(0, rear).subject = "seven-black-ships"

    engine.apply(state, SetStratagem("the-tide-rose"))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 6

    engine.apply(state, Pass())

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, CENTER_FRONT) == 5
    assert engine.position_strength(state, 0, rear) == 6


def test_ground_gave_way_rewards_rear_and_penalizes_frontline() -> None:
    engine, state = fresh_state(first_player=0)
    rear = Position(Front.CENTER, Rank.REAR)
    front = Position(Front.LEFT, Rank.FRONT)
    state.players[0].hand = ["the-ground-gave-way", "the-fifty-men"]

    engine.apply(state, SetStratagem("the-ground-gave-way"))
    engine.apply(state, PlaySubject("the-fifty-men", rear))
    state.slot(0, front).subject = "the-fifty-men"

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, rear) == 5
    assert engine.position_strength(state, 0, front) == 5


def test_bronze_teeth_punishes_trigger_subject_but_costs_controller() -> None:
    engine, state = fresh_state(first_player=0)
    own_front = Position(Front.LEFT, Rank.FRONT)
    enemy_front = Position(Front.CENTER, Rank.FRONT)
    state.players[0].hand = ["the-bronze-teeth"]
    state.players[1].hand = ["the-fifty-men"]
    state.slot(0, own_front).subject = "the-fifty-men"

    engine.apply(state, SetStratagem("the-bronze-teeth"))
    engine.apply(state, Pass())
    engine.apply(state, PlaySubject("the-fifty-men", enemy_front))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 1, enemy_front) == 4
    assert engine.position_strength(state, 0, own_front) == 5


def test_false_muster_cancels_immediate_story_and_locks_own_stories() -> None:
    engine, state = fresh_state(first_player=0)
    state.players[0].hand = ["the-false-muster", "the-fifty-men"]
    state.players[1].hand = ["he-never-came"]

    engine.apply(state, SetStratagem("the-false-muster"))
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    engine.apply(
        state,
        PlayPlot(
            "he-never-came",
            (BoardTarget(0, CENTER_FRONT),),
        ),
    )

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, CENTER_FRONT) == 6
    assert "he-never-came" in state.players[1].discard

    state.players[0].hand = ["the-story-is-false", "the-lamps-went-dark"]
    actions = engine.legal_actions(state)
    assert not any(
        isinstance(action, PlayPlot)
        and action.card_id == "the-story-is-false"
        for action in actions
    )
    assert any(
        isinstance(action, PlayScheme)
        and action.card_id == "the-lamps-went-dark"
        for action in actions
    )


def test_wooden_gift_penalizes_named_and_rewards_unnamed_subjects() -> None:
    engine, state = fresh_state(first_player=0)
    own_front = Position(Front.LEFT, Rank.FRONT)
    enemy_front = Position(Front.CENTER, Rank.FRONT)
    state.players[0].hand = ["the-wooden-gift", "the-fifty-men"]
    state.players[1].hand = ["namar"]

    engine.apply(state, SetStratagem("the-wooden-gift"))
    engine.apply(state, PlaySubject("the-fifty-men", own_front))

    enemy = state.slot(1, enemy_front)
    enemy.subject = "the-fifty-men"
    enemy.link = "followed"
    engine.apply(state, PlayName("namar", enemy_front))

    assert state.stratagem(0).revealed is True
    assert engine.position_strength(state, 0, own_front) == 7
    assert engine.position_strength(state, 1, enemy_front) == 11
