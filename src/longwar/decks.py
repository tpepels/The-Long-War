from __future__ import annotations

from collections import Counter
from typing import Any

MINIMUM_DECK_SIZE = 34
MINIMUM_FORCE_COUNT = 14
MINIMUM_PRINTED_NAME_COUNT = 6
NON_UNIQUE_COPY_LIMIT = 2
UNIQUE_COPY_LIMIT = 1


class InvalidDeckDefinition(ValueError):
    pass


def validate_deck_definition(
    deck: list[str] | tuple[str, ...],
    cards: dict[str, dict[str, Any]],
    *,
    minimum_size: int = MINIMUM_DECK_SIZE,
    minimum_force_count: int = MINIMUM_FORCE_COUNT,
    minimum_printed_name_count: int = MINIMUM_PRINTED_NAME_COUNT,
    non_unique_copy_limit: int = NON_UNIQUE_COPY_LIMIT,
    unique_copy_limit: int = UNIQUE_COPY_LIMIT,
) -> None:
    """Validate the canonical deck-construction rules.

    Decks may be larger than the minimum. Heroes count as Force-type cards
    because their printed type is Force; their dual Name mode does not count
    toward the printed-Name minimum.
    """
    if not isinstance(deck, (list, tuple)) or any(
        not isinstance(card_id, str) for card_id in deck
    ):
        raise InvalidDeckDefinition("A deck must be a list of card ids")

    if minimum_size < 1 or minimum_force_count < 0 or minimum_printed_name_count < 0:
        raise ValueError("deck minimums must be non-negative and size must be positive")
    if non_unique_copy_limit < 1 or unique_copy_limit < 1:
        raise ValueError("copy limits must be positive")

    if len(deck) < minimum_size:
        raise InvalidDeckDefinition(
            f"A legal deck must contain at least {minimum_size} cards, got {len(deck)}"
        )

    counts = Counter(deck)
    for card_id, count in counts.items():
        card = cards.get(card_id)
        if card is None:
            raise InvalidDeckDefinition(f"Unknown card: {card_id}")
        maximum = unique_copy_limit if card.get("unique", False) else non_unique_copy_limit
        if count > maximum:
            raise InvalidDeckDefinition(
                f"{card['title']} appears {count} times; maximum is {maximum}"
            )

    forces = sum(1 for card_id in deck if cards[card_id]["type"] == "force")
    if forces < minimum_force_count:
        raise InvalidDeckDefinition(
            f"A legal deck must contain at least {minimum_force_count} Force-type cards, "
            f"got {forces}"
        )

    names = sum(1 for card_id in deck if cards[card_id]["type"] == "name")
    if names < minimum_printed_name_count:
        raise InvalidDeckDefinition(
            f"A legal deck must contain at least {minimum_printed_name_count} printed Names, "
            f"got {names}"
        )
