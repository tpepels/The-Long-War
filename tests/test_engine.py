from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import (
    BoardTarget,
    ChooseFirst,
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


def test_links_help_immediately_and_namar_rewards_frontline() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-fifty-men", "followed", "namar"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 4

    engine.apply(state, PlayLink("followed", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 5

    engine.apply(state, PlayName("namar", CENTER_FRONT))
    assert engine.position_strength(state, 0, CENTER_FRONT) == 11


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


def test_he_never_came_returns_open_link_when_no_name_is_attached() -> None:
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
    assert slot.link is None
    assert "followed" in state.players[0].hand


def test_carried_name_cannot_be_plot_target() -> None:
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

    assert engine.position_strength(state, 0, CENTER_FRONT) == 5


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

    assert engine.front_strength(state, 0, Front.LEFT) == 9
    assert engine.front_strength(state, 1, Front.LEFT) == 2


def test_they_chose_another_moves_link_and_attached_name() -> None:
    engine, state = fresh_state(first_player=0)
    source = state.slot(0, LEFT_FRONT)
    destination = state.slot(0, CENTER_FRONT)
    source.subject = "the-fifty-men"
    source.link = "followed"
    source.name = "oren"
    destination.subject = "the-house-at-orra"
    state.players[0].hand = ["they-chose-another"]

    engine.apply(
        state,
        PlayPlot(
            "they-chose-another",
            (
                BoardTarget(0, LEFT_FRONT),
                BoardTarget(0, CENTER_FRONT),
            ),
        ),
    )

    assert source.subject == "the-fifty-men"
    assert source.link is None
    assert source.name is None
    assert destination.subject == "the-house-at-orra"
    assert destination.link == "followed"
    assert destination.name == "oren"


def test_namar_frontline_bonus_does_not_apply_in_rear() -> None:
    engine, state = fresh_state()
    rear = Position(Front.CENTER, Rank.REAR)
    slot = state.slot(0, rear)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    slot.name = "namar"

    assert engine.position_strength(state, 0, rear) == 9


def test_lamps_scheme_penalizes_played_subject() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[1].hand = ["the-lamps-went-dark"]
    state.players[0].hand = ["the-fifty-men"]

    engine.apply(state, PlayScheme("the-lamps-went-dark", Front.CENTER))
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))

    assert state.scheme(1, Front.CENTER) is None
    assert "the-lamps-went-dark" in state.players[1].discard
    assert engine.position_strength(state, 0, CENTER_FRONT) == 1


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
    assert engine.position_strength(state, 1, CENTER_FRONT) == 7


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
    assert engine.position_strength(state, 1, CENTER_FRONT) == 7


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
