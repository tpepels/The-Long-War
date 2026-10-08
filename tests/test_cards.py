from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import (
    compile_card_mechanics,
    load_card_file,
    validate_card_data,
)
from longwar.decks import validate_deck_definition

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_card_pool_has_unique_ids_and_supported_types() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    ids = [card["id"] for card in data["cards"]]
    assert ids
    assert len(ids) == len(set(ids))
    assert {card["type"] for card in data["cards"]} <= {
        "force",
        "bond",
        "name",
        "hero",
        "tactic",
        "order",
        "narrative",
        "stratagem",
    }


def test_card_catalogue_has_one_executable_mechanics_schema() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        assert "rules" not in card
        assert isinstance(card.get("design_rules"), dict)


def test_all_current_cards_compile_their_mechanics() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        compiled = compile_card_mechanics(card)
        assert isinstance(compiled["_class_mask"], int)
        assert "_reference_mask" not in compiled
        assert isinstance(compiled["effects"], list)
        assert isinstance(compiled["modes"], dict)


def test_active_decks_reference_only_valid_cards() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}

    for path in sorted((ROOT / "decks").glob("*.json")):
        if path.name == "index.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        deck = payload.get("cards", [])
        if not isinstance(deck, list) or not deck:
            continue
        assert set(deck) <= set(cards), path
        validate_deck_definition(deck, cards)


@pytest.mark.parametrize("value", [None, True, -1, 128, 1.5])
def test_printed_command_cost_is_nonnegative_native_safe_integer(value) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    data["cards"][0]["command_cost"] = value
    with pytest.raises(ValueError, match="command_cost"):
        validate_card_data(data)


def test_unknown_design_mechanic_is_rejected_at_content_boundary() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    card = next(card for card in data["cards"] if card.get("design_rules"))
    card["design_rules"]["typo_mechanic"] = True

    with pytest.raises(ValueError, match="unsupported mechanic"):
        validate_card_data(data)


def test_new_card_can_reuse_existing_mechanics_without_catalogue_edits() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    template = next(card for card in data["cards"] if card["type"] == "force")
    clone = json.loads(json.dumps(template))
    clone["id"] = "test-new-force"
    clone["title"] = "Test New Force"
    data["cards"].append(clone)

    validate_card_data(data)


def test_obsolete_reference_metadata_is_rejected() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    data["cards"][0]["references"] = ["guard"]

    with pytest.raises(ValueError, match="obsolete references metadata"):
        validate_card_data(data)
