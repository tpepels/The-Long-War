from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Phase, Position, Rank

ROOT = Path(__file__).resolve().parents[1]


def engine_and_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=99, first_player=0)
    state.phase = Phase.BATTLE
    state.active_player = 0
    state.players[0].passed = False
    state.players[1].passed = False

    # A representative mid-Battle board deliberately contains:
    # - an empty own position for Subjects,
    # - a bare own Subject for Links,
    # - an own Subject with an open Link for Names,
    # - an own linked Subject plus another bare Subject for movement Plots,
    # - enemy linked / named Subjects for disruption Plots,
    # - empty Scheme slots.
    own_left = state.slot(0, Position(Front.LEFT, Rank.FRONT))
    own_left.subject = "the-fifty-men"
    own_left.link = "followed"
    own_left.name = "oren"

    own_center = state.slot(0, Position(Front.CENTER, Rank.REAR))
    own_center.subject = "the-house-at-orra"

    own_right = state.slot(0, Position(Front.RIGHT, Rank.REAR))
    own_right.subject = "seven-black-ships"
    own_right.link = "carried"

    enemy_left = state.slot(1, Position(Front.LEFT, Rank.FRONT))
    enemy_left.subject = "those-who-came-back"
    enemy_left.link = "defied"
    enemy_left.name = "teyra"

    enemy_center = state.slot(1, Position(Front.CENTER, Rank.FRONT))
    enemy_center.subject = "the-children-of-the-salt-road"
    enemy_center.link = "avenged"

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
