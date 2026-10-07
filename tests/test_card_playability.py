from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Phase, Position, Rank
from longwar.game.model import StratagemState

ROOT = Path(__file__).resolve().parents[1]


def engine_and_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=99,
        first_player=0,
        opening_bonus=False,
    )
    state.phase = Phase.BATTLE
    # Use the fully active battlefield so rank-specific and edge-specific
    # deployment cards always have a constructible legal destination.
    state.battle = 3
    state.active_player = 0
    state.players[0].passed = False
    state.players[1].passed = False

    # A representative mid-Battle board deliberately contains:
    # - an empty own position for Forces,
    # - a bare own Force for Bonds,
    # - an own Force with an open Bond for Names,
    # - an own bonded Force plus another bare Force for movement Narratives,
    # - enemy bonded / Named Formations for disruption Narratives,
    # - empty ongoing Narrative slots.
    own_first = state.slot(0, Position(Front.FIRST, Rank.FRONT))
    own_first.force = "the-fifty-men"
    own_first.bond = "followed"
    own_first.name = "oren"

    own_second = state.slot(0, Position(Front.SECOND, Rank.REAR))
    own_second.force = "the-house-of-reed"

    own_third = state.slot(0, Position(Front.THIRD, Rank.REAR))
    own_third.force = "seven-black-ships"
    own_third.bond = "carried-the-oath-of"

    own_scout = state.slot(0, Position(Front.SECOND, Rank.MIDDLE))
    own_scout.force = "the-thornbow-hunters"

    enemy_first = state.slot(1, Position(Front.FIRST, Rank.FRONT))
    enemy_first.force = "the-black-company"
    enemy_first.bond = "guarded"
    enemy_first.name = "mara"

    enemy_second = state.slot(1, Position(Front.SECOND, Rank.FRONT))
    enemy_second.force = "the-vardai"
    enemy_second.bond = "stood-fast-with"

    state.stratagems[1] = StratagemState(
        "the-ground-was-held",
        fronts=(Front.SECOND,),
    )

    return engine, state, data


def test_every_current_card_has_a_constructible_legal_play() -> None:
    engine, state, data = engine_and_state()

    for card in data["cards"]:
        trial = state.clone()
        trial.players[0].hand = [card["id"]]
        legal = engine.legal_actions(trial)

        assert any(
            getattr(action, "card_id", None) == card["id"]
            for action in legal
        ), f"No legal play could be constructed for {card['title']}"
