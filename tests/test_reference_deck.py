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


def _deck_paths() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "decks").glob("*.json")
        if path.name != "index.json"
    )


def _deck(path: Path) -> list[str]:
    return json.loads(path.read_text(encoding="utf-8"))["cards"]


def _cards() -> dict[str, dict]:
    data = load_card_file(ROOT / "cards" / "cards.json")
    return {card["id"]: card for card in data["cards"]}


def test_reference_decks_are_canonical_and_legal() -> None:
    cards = _cards()
    paths = _deck_paths()
    assert paths

    for path in paths:
        deck = _deck(path)
        assert set(deck) <= set(cards)
        validate_deck_definition(deck, cards)


def test_minimum_deck_size_is_a_floor_not_an_exact_size() -> None:
    cards = _cards()
    base = _deck(_deck_paths()[0])
    extra = next(
        card_id
        for card_id, card in cards.items()
        if not card["unique"] and base.count(card_id) < 4
    )

    validate_deck_definition([*base, extra], cards)


def test_too_small_deck_is_rejected() -> None:
    cards = _cards()
    base = _deck(_deck_paths()[0])
    with pytest.raises(InvalidDeckDefinition, match="at least"):
        validate_deck_definition(base[: MINIMUM_DECK_SIZE - 1], cards)


def test_force_and_name_minimums_are_not_required() -> None:
    assert MINIMUM_FORCE_COUNT == 0
    assert MINIMUM_PRINTED_NAME_COUNT == 0

    cards = _cards()
    pool = [
        card_id
        for card_id, card in cards.items()
        if card["type"] not in {"force", "name"} and not card["unique"]
    ]
    deck = [
        card_id
        for card_id in pool
        for _ in range(4)
    ][:MINIMUM_DECK_SIZE]

    assert len(deck) == MINIMUM_DECK_SIZE
    validate_deck_definition(deck, cards)


def test_unique_and_non_unique_copy_limits() -> None:
    cards = _cards()
    base = _deck(_deck_paths()[0])

    unique = next(card_id for card_id in base if cards[card_id]["unique"])
    with pytest.raises(InvalidDeckDefinition, match="maximum is 1"):
        validate_deck_definition([*base, unique], cards)

    non_unique = next(
        card_id
        for card_id in base
        if not cards[card_id]["unique"] and base.count(card_id) <= 2
    )
    four_copies = [
        *base,
        *([non_unique] * (4 - base.count(non_unique))),
    ]
    validate_deck_definition(four_copies, cards)

    with pytest.raises(InvalidDeckDefinition, match="maximum is 4"):
        validate_deck_definition([*four_copies, non_unique], cards)
