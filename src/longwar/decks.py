from __future__ import annotations

from collections import Counter
from typing import Any

# Current shipped playtest format. This is content/design policy, not a match rule.
PLAYTEST_DECK_SIZE = 34
NON_UNIQUE_COPY_LIMIT = 2
UNIQUE_COPY_LIMIT = 1
PLAYTEST_FORCE_COUNT = 14
PLAYTEST_PRINTED_NAME_COUNT = 6


class InvalidDeckDefinition(ValueError):
    pass


def validate_deck_definition(
    deck: list[str] | tuple[str, ...],
    cards: dict[str, dict[str, Any]],
    *,
    exact_size: int | None = None,
    non_unique_copy_limit: int = NON_UNIQUE_COPY_LIMIT,
    unique_copy_limit: int = UNIQUE_COPY_LIMIT,
    exact_force_count: int | None = None,
    exact_printed_name_count: int | None = None,
) -> None:
    """Validate optional deck-construction policy independently from game rules.

    The game engine only needs a runtime-safe list of known card ids. Construction
    formats may impose size/copy constraints without changing match semantics.
    """
    if not isinstance(deck, (list, tuple)) or any(
        not isinstance(card_id, str) for card_id in deck
    ):
        raise InvalidDeckDefinition("A deck must be a list of card ids")

    if exact_size is not None:
        if exact_size < 1:
            raise ValueError("exact_size must be positive")
        if len(deck) != exact_size:
            raise InvalidDeckDefinition(
                f"A deck in this format must contain exactly {exact_size} cards, "
                f"got {len(deck)}"
            )

    if non_unique_copy_limit < 1 or unique_copy_limit < 1:
        raise ValueError("copy limits must be positive")

    counts = Counter(deck)
    for card_id, count in counts.items():
        card = cards.get(card_id)
        if card is None:
            raise InvalidDeckDefinition(f"Unknown card: {card_id}")
        maximum = (
            unique_copy_limit
            if card.get("unique", False)
            else non_unique_copy_limit
        )
        if count > maximum:
            raise InvalidDeckDefinition(
                f"{card['title']} appears {count} times; maximum is {maximum}"
            )

    if exact_force_count is not None:
        forces = sum(
            1
            for card_id in deck
            if cards[card_id]["type"] == "force"
        )
        if forces != exact_force_count:
            raise InvalidDeckDefinition(
                f"A deck in this format must contain exactly "
                f"{exact_force_count} Force-type cards, got {forces}"
            )

    if exact_printed_name_count is not None:
        names = sum(
            1
            for card_id in deck
            if cards[card_id]["type"] == "name"
        )
        if names != exact_printed_name_count:
            raise InvalidDeckDefinition(
                f"A deck in this format must contain exactly "
                f"{exact_printed_name_count} printed Names, got {names}"
            )
