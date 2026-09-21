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


def test_build_fifty_men_followed_namar() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-fifty-men", "followed", "namar"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(state, PlaySubject("the-fifty-men", CENTER_FRONT))
    engine.apply(state, PlayLink("followed", CENTER_FRONT))
    engine.apply(state, PlayName("namar", CENTER_FRONT))

    slot = state.slot(0, CENTER_FRONT)
    assert slot.complete
    assert engine.position_strength(state, 0, CENTER_FRONT) == 11


def test_iria_can_move_completed_legend_to_adjacent_position() -> None:
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


def test_swore_to_discards_subject_when_name_leaves() -> None:
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

    assert not slot.occupied
    assert "namar" in state.players[0].hand
    assert "the-fifty-men" in state.players[0].discard
    assert "swore-to" in state.players[0].discard


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


def test_children_gain_temporary_strength_when_link_attached() -> None:
    engine, state = fresh_state(first_player=1)
    state.players[0].hand = ["the-children-of-the-salt-road", "followed"]
    state.players[1].hand = []

    engine.apply(state, Pass())
    engine.apply(
        state,
        PlaySubject("the-children-of-the-salt-road", CENTER_FRONT),
    )
    engine.apply(state, PlayLink("followed", CENTER_FRONT))

    assert engine.position_strength(state, 0, CENTER_FRONT) == 4


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
