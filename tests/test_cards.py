from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from longwar.cards import (
    CARD_CAPABILITY_BITS,
    NARRATIVE_FORMS,
    cards_by_type,
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
    assert all(card["narrative_form"] in NARRATIVE_FORMS for card in narratives)
    assert all(isinstance(card["ongoing"], bool) for card in narratives)


def test_all_cards_define_valid_rule_blocks() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    allowed = {"property", "timing", "trigger", "effect", "continuous", "cost", "replacement", "constraint"}
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
    for filename in (
        "mobility-open-bonds.json",
        "persistent-elite-heroes.json",
        "narrative-command.json",
        "battlefield-control-stratagems.json",
        "momentum-orders.json",
        "necessity-attrition.json",
    ):
        deck = json.loads((ROOT / "decks" / filename).read_text(encoding="utf-8"))["cards"]
        assert set(deck) <= set(cards)
        validate_deck_definition(deck, cards)


@pytest.mark.parametrize("value", [None, True, 0, 128, 1.5])
def test_printed_command_cost_is_positive_native_safe_integer(value) -> None:
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


def test_ordinary_new_card_can_reuse_existing_mechanics_without_catalogue_edits() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    template = next(
        card
        for card in data["cards"]
        if card["type"] == "force" and not card.get("hero")
    )
    clone = json.loads(json.dumps(template))
    clone["id"] = "test-new-force"
    clone["title"] = "Test New Force"
    data["cards"].append(clone)

    validate_card_data(data)


def test_card_capability_registry_is_compact_and_native_safe() -> None:
    bits = list(CARD_CAPABILITY_BITS.values())
    assert bits
    assert len(bits) == len(set(bits))
    assert len(bits) <= 64
    assert all(bit > 0 and bit & (bit - 1) == 0 for bit in bits)


def test_every_compiled_capability_comes_from_the_shared_registry() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        compiled = compile_card_mechanics(card)
        capabilities = compiled["_capabilities"]
        assert set(capabilities) <= set(CARD_CAPABILITY_BITS)
        assert compiled["_capability_bits"] == sum(
            CARD_CAPABILITY_BITS[name]
            for name in capabilities
        )
