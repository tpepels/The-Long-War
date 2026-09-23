from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine

ROOT = Path(__file__).resolve().parents[1]


def _deck(filename: str) -> list[str]:
    return json.loads(
        (ROOT / "decks" / filename).read_text(encoding="utf-8")
    )["cards"]


def test_reference_deck_is_legal_and_subject_forward() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    deck = _deck("reference.json")

    GameEngine(data).validate_deck(deck)
    assert len(deck) == 30
    assert sum(cards[card_id]["type"] == "subject" for card_id in deck) == 10
    assert sum(cards[card_id]["type"] == "name" for card_id in deck) == 6
    assert sum(cards[card_id]["type"] == "stratagem" for card_id in deck) == 3
    assert sum(
        cards[card_id]["type"] == "plot" and cards[card_id].get("veiled", False)
        for card_id in deck
    ) == 3


def test_expanded_archetype_decks_are_legal_subject_forward_and_choose_one_hero() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    engine = GameEngine(data)

    for filename in (
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ):
        deck = _deck(filename)
        engine.validate_deck(deck)
        assert len(deck) == 30
        assert sum(cards[card_id]["type"] == "subject" for card_id in deck) == 10
        assert sum(cards[card_id]["type"] == "name" for card_id in deck) == 6
        heroes = [
            card_id
            for card_id in deck
            if cards[card_id].get("hero", False)
        ]
        assert len(heroes) == 1
