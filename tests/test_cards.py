from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from longwar.cards import STORY_FORMS, cards_by_type, load_card_file, validate_card_data
from longwar.decks import validate_deck_definition

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_card_pool_has_exactly_80_unique_cards() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    ids = [card["id"] for card in data["cards"]]
    assert len(ids) == 80
    assert len(ids) == len(set(ids))
    assert {card["type"] for card in data["cards"]} == {
        "force", "bond", "name", "story", "stratagem"
    }


def test_every_card_has_world_classifications() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        assert card["classes"]
        assert len(card["classes"]) == len(set(card["classes"]))


def test_names_and_heroes_are_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))
    heroes = [card for card in data["cards"] if card.get("hero")]
    assert heroes
    assert all(card["type"] == "force" and card["unique"] for card in heroes)


def test_narratives_have_specific_forms_and_public_ongoing_metadata() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    narratives = cards_by_type(data, "story")
    assert {card["story_form"] for card in narratives} == STORY_FORMS
    assert all(isinstance(card["ongoing"], bool) for card in narratives)


def test_all_cards_define_valid_rule_blocks() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    allowed = {"property", "timing", "trigger", "effect", "continuous", "cost", "replacement"}
    for card in data["cards"]:
        blocks = card["rule_blocks"]
        assert all(block["kind"] in allowed for block in blocks)
        assert all(block["text"].strip() for block in blocks)
        if card["text"]:
            assert blocks, card["title"]


def test_player_facing_card_text_uses_canonical_vocabulary() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    obsolete = re.compile(r"\b(?:Subject|Link|Plot|Scheme|Veiled Story|Story)\b", re.IGNORECASE)
    for card in data["cards"]:
        assert not obsolete.search(card.get("text", "")), card["title"]


def test_active_decks_use_only_canonical_cards_and_current_minimum_rules() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    for filename in ("reference.json", "avaros-line.json", "mara-rear.json", "sera-support.json"):
        deck = json.loads((ROOT / "decks" / filename).read_text(encoding="utf-8"))["cards"]
        assert set(deck) <= set(cards)
        validate_deck_definition(deck, cards)


@pytest.mark.parametrize("value", [None, True, 0, 128, 1.5])
def test_printed_command_cost_is_positive_native_safe_integer(value) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    data["cards"][0]["command_cost"] = value
    with pytest.raises(ValueError, match="command_cost"):
        validate_card_data(data)
