from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.decks import (
    MINIMUM_DECK_SIZE,
    MINIMUM_FORCE_COUNT,
    MINIMUM_PRINTED_NAME_COUNT,
    InvalidDeckDefinition,
    validate_deck_definition,
)


ROOT = Path(__file__).resolve().parents[1]
DECK_FILES = (
    "mobility-open-bonds.json",
    "persistent-elite-heroes.json",
    "narrative-command.json",
    "battlefield-control-stratagems.json",
    "momentum-orders.json",
    "necessity-attrition.json",
)


def _deck(filename: str) -> list[str]:
    return json.loads((ROOT / "decks" / filename).read_text(encoding="utf-8"))["cards"]


def _cards():
    data = load_card_file(ROOT / "cards" / "cards.json")
    return {card["id"]: card for card in data["cards"]}


def test_active_reference_decks_are_canonical_and_legal() -> None:
    cards = _cards()
    for filename in DECK_FILES:
        deck = _deck(filename)
        validate_deck_definition(deck, cards)
        assert set(deck) <= set(cards)
        assert len(deck) >= MINIMUM_DECK_SIZE
        assert sum(
            cards[card_id]["type"] in {"force", "hero"}
            for card_id in deck
        ) >= MINIMUM_FORCE_COUNT
        assert sum(cards[card_id]["type"] == "name" for card_id in deck) >= MINIMUM_PRINTED_NAME_COUNT


def test_deck_minimums_are_not_exact_caps() -> None:
    cards = _cards()
    base = _deck("mobility-open-bonds.json")
    extra = next(
        card_id for card_id, card in cards.items()
        if not card["unique"] and base.count(card_id) < 4
    )
    larger = [*base, extra]
    validate_deck_definition(larger, cards)
    assert len(larger) > MINIMUM_DECK_SIZE


def test_33_cards_are_rejected() -> None:
    cards = _cards()
    with pytest.raises(InvalidDeckDefinition, match="at least 34"):
        validate_deck_definition(_deck("mobility-open-bonds.json")[:33], cards)


def test_force_and_name_minimums_are_required() -> None:
    cards = _cards()
    pool = [
        card_id
        for card_id, card in cards.items()
        if card["type"] not in {"force", "hero", "name"} and not card["unique"]
    ]
    deck = [
        card_id
        for card_id in pool
        for _ in range(4)
    ][:MINIMUM_DECK_SIZE]
    assert len(deck) == MINIMUM_DECK_SIZE

    with pytest.raises(InvalidDeckDefinition, match="at least 14 Force"):
        validate_deck_definition(deck, cards)

    with pytest.raises(InvalidDeckDefinition, match="at least 6 printed Names"):
        validate_deck_definition(deck, cards, minimum_force_count=0)


def test_unique_and_non_unique_copy_limits() -> None:
    cards = _cards()
    deck = _deck("mobility-open-bonds.json")

    unique = next(card_id for card_id in deck if cards[card_id]["unique"])
    with pytest.raises(InvalidDeckDefinition, match="maximum is 1"):
        validate_deck_definition([*deck, unique], cards)

    non_unique = next(
        card_id for card_id in deck
        if not cards[card_id]["unique"] and deck.count(card_id) <= 2
    )
    four_copies = [
        *deck,
        *([non_unique] * (4 - deck.count(non_unique))),
    ]
    validate_deck_definition(four_copies, cards)
    with pytest.raises(InvalidDeckDefinition, match="maximum is 4"):
        validate_deck_definition([*four_copies, non_unique], cards)


def test_heroes_have_no_deck_cap_beyond_unique_titles() -> None:
    cards = _cards()
    heroes = [card_id for card_id, card in cards.items() if card.get("hero")]
    assert len(heroes) >= 6
    deck = _deck("persistent-elite-heroes.json")
    assert len([card_id for card_id in deck if cards[card_id].get("hero")]) >= 4
    validate_deck_definition(deck, cards)

def test_reference_decks_cover_every_canonical_card() -> None:
    cards = _cards()
    covered = {
        card_id
        for filename in DECK_FILES
        for card_id in _deck(filename)
    }

    assert len(cards) == 128
    assert covered == set(cards)

