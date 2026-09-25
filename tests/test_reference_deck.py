from __future__ import annotations

import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.decks import (
    PLAYTEST_DECK_SIZE,
    PLAYTEST_FORCE_COUNT,
    PLAYTEST_PRINTED_NAME_COUNT,
    validate_deck_definition,
)


ROOT = Path(__file__).resolve().parents[1]


def _deck(filename: str) -> list[str]:
    return json.loads(
        (ROOT / "decks" / filename).read_text(encoding="utf-8")
    )["cards"]


def test_canonical_playtest_decks_match_34_14_6_format() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}

    for filename in (
        "reference.json",
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ):
        deck = _deck(filename)
        validate_deck_definition(
            deck,
            cards,
            exact_size=PLAYTEST_DECK_SIZE,
            exact_force_count=PLAYTEST_FORCE_COUNT,
            exact_printed_name_count=PLAYTEST_PRINTED_NAME_COUNT,
        )
        assert len(deck) == 34
        assert sum(cards[card_id]["type"] == "force" for card_id in deck) == 14
        assert sum(cards[card_id]["type"] == "name" for card_id in deck) == 6


def test_current_archetype_decks_keep_unique_hero_copies() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}

    for filename in (
        "reference.json",
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ):
        heroes = [
            card_id
            for card_id in _deck(filename)
            if cards[card_id].get("hero", False)
        ]
        assert len(heroes) == len(set(heroes))
