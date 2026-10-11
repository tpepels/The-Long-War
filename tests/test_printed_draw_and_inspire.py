"""Executable parity for printed Bond draw choices and Narrative status repair."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.game.actions import (
    ActivateAbility, BeginTurn, Discard, EffectChoice, PlayBond, PlayNarrative,
)
from longwar.game.engine import GameEngine
from longwar.game.model import Front, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def game():
    engine = GameEngine.from_file(str(ROOT / "cards" / "cards.json"))
    deck = json.loads((ROOT / "decks" / "mobility-open-bonds.json").read_text())["cards"]
    return engine, deck


def at(rank=Rank.FRONT):
    return Position(Front.SECOND, rank)


def start(game, hand):
    engine, deck = game
    state = engine.new_game(deck, deck, seed=118, first_player=0)
    engine.apply(state, BeginTurn())
    while state.pending_draw_discard_for is not None:
        engine.apply(state, next(a for a in engine.legal_actions(state)
                                 if isinstance(a, Discard)))
    state.players[0].hand[:] = hand
    state.players[0].command = 20
    return engine, state


def effect_actions(engine, state):
    return [a for a in engine.legal_actions(state) if isinstance(a, EffectChoice)]


def test_swore_again_completes_named_and_adds_exactly_two_temporary_strength(game):
    engine, state = start(game, ["swore-again-to"])
    host = state.slot(0, at())
    host.force = "the-fifty-men"
    host.name = "mara"
    before_deck = list(state.players[0].deck)
    engine.apply(state, PlayBond("swore-again-to", at()))
    assert state.slot(0, at()).named
    assert state.slot(0, at()).temporary_strength == 2
    assert state.players[0].deck == before_deck
    assert len(state.players[0].hand) == 0  # no draw/discard from this Bond
    # The completed Name can independently trigger its own optional ability.


def test_swore_again_without_named_draws_before_discard_choice(game):
    engine, state = start(game, ["swore-again-to"])
    state.slot(0, at()).force = "the-fifty-men"
    deck_size = len(state.players[0].deck)
    engine.apply(state, PlayBond("swore-again-to", at()))
    assert len(state.players[0].deck) == deck_size - 1
    assert len(state.players[0].hand) == 1
    assert state.slot(0, at()).temporary_strength == 0
    choice = next(a for a in effect_actions(engine, state) if a.card_id is not None)
    engine.apply(state, choice)
    assert len(state.players[0].hand) == 0
    assert len(state.players[0].discard) >= 1


def test_watched_skies_returns_selected_hand_card_to_top_not_discard(game):
    engine, state = start(game, ["watched-the-skies-for", "the-fifty-men"])
    state.slot(0, at()).force = "the-old-guard"
    original_deck = list(state.players[0].deck)
    engine.apply(state, PlayBond("watched-the-skies-for", at()))
    assert len(state.players[0].deck) == len(original_deck) - 1
    assert len(state.players[0].hand) == 2  # kept card + the freshly drawn card
    choice = next(a for a in effect_actions(engine, state)
                  if a.card_id == "the-fifty-men")
    discard_before = len(state.players[0].discard)
    engine.apply(state, choice)
    assert state.players[0].deck[-1] == "the-fifty-men"
    assert len(state.players[0].deck) == len(original_deck)
    assert len(state.players[0].discard) == discard_before
    assert len(state.players[0].hand) == 1


@pytest.mark.parametrize("has_marker", (True, False))
def test_lived_to_tell_it_grants_inspired_after_optional_one_marker_cleanse(
    game, has_marker
):
    engine, state = start(game, ["they-lived-to-tell-it"])
    target = at(Rank.MIDDLE)
    host = state.slot(0, target)
    host.force = "the-fifty-men"
    host.shaken = True
    host.negative_strength_markers = [-2, -1] if has_marker else []

    narrative_play = next(a for a in engine.legal_actions(state)
                          if isinstance(a, PlayNarrative)
                          and a.card_id == "they-lived-to-tell-it")
    engine.apply(state, narrative_play)
    ability = next(a for a in engine.legal_actions(state)
                   if isinstance(a, ActivateAbility)
                   and a.card_id == "they-lived-to-tell-it")
    engine.apply(state, ability)
    action = next(a for a in effect_actions(engine, state)
                  if a.destination is not None and a.destination.position == target)
    engine.apply(state, action)
    assert state.slot(0, target).inspired
    assert not state.slot(0, target).shaken
    assert state.slot(0, target).negative_strength_markers == (
        [-1] if has_marker else []
    )


def test_lived_to_tell_it_targets_only_own_forces(game):
    engine, state = start(game, ["they-lived-to-tell-it"])
    state.slot(1, at()).force = "the-fifty-men"
    narrative_play = next(a for a in engine.legal_actions(state)
                          if isinstance(a, PlayNarrative)
                          and a.card_id == "they-lived-to-tell-it")
    engine.apply(state, narrative_play)
    assert not [a for a in engine.legal_actions(state)
                if isinstance(a, ActivateAbility)
                and a.card_id == "they-lived-to-tell-it"]
