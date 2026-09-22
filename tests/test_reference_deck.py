from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine

ROOT = Path(__file__).resolve().parents[1]


def test_v01_reference_deck_is_legal_and_contains_all_schemes() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]

    GameEngine(data).validate_deck(deck)
    assert len(deck) == 30
    assert {
        "the-lamps-went-dark",
        "the-road-was-cut",
        "the-hidden-oars",
        "the-witness-lied",
    } <= set(deck)


def test_expanded_archetype_decks_are_legal_and_choose_one_hero() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    engine = GameEngine(data)

    for filename in (
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ):
        deck = json.loads(
            (ROOT / "decks" / filename).read_text(encoding="utf-8")
        )["cards"]
        engine.validate_deck(deck)
        assert len(deck) == 30
        heroes = [
            card_id
            for card_id in deck
            if cards[card_id].get("hero", False)
        ]
        assert len(heroes) == 1
