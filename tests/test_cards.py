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
    assert {card["type"] for card in data["cards"]} == {
        "force",
        "bond",
        "name",
        "hero",
        "tactic",
        "order",
        "narrative",
        "stratagem",
    }


def test_card_classifications_match_family_grammar() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        assert isinstance(card["classes"], list)
        assert len(card["classes"]) == len(set(card["classes"]))
        if card["type"] in {"force", "name", "hero"}:
            assert card["classes"], card["id"]


def test_names_and_heroes_are_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))
    heroes = cards_by_type(data, "hero")
    assert heroes
    assert all(card["unique"] for card in heroes)
    assert all(set(card["modes"]) == {"force", "name"} for card in heroes)


def test_narratives_and_orders_use_current_family_grammar() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    narratives = cards_by_type(data, "narrative")
    orders = cards_by_type(data, "order")
    assert narratives and orders
    assert all(
        effect["timing"] in {"continuous", "action"}
        for card in narratives
        for effect in card.get("effects", [])
    )
    assert all(
        effect["timing"] == "play" and effect["scope"] == "self"
        for card in orders
        for effect in card.get("effects", [])
    )


def test_card_catalogue_has_one_executable_mechanics_schema() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all("rules" not in card for card in data["cards"])
    assert all(isinstance(card.get("design_rules"), dict) for card in data["cards"])


def test_all_cards_define_valid_rule_blocks() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    allowed = {"property", "timing", "trigger", "effect", "continuous", "cost", "replacement", "constraint"}
    for card in data["cards"]:
        blocks = card["rule_blocks"]
        assert all(block["kind"] in allowed for block in blocks)
        assert all(block["text"].strip() for block in blocks)
        if card["text"] and card["text"] != "No special rules.":
            assert blocks, card["title"]


def test_player_facing_card_text_uses_canonical_vocabulary() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    obsolete = re.compile(r"\b(?:Subject|Link|Plot|Scheme|Veiled|Story)\b", re.IGNORECASE)
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


def test_legacy_capability_registry_is_retired() -> None:
    assert CARD_CAPABILITY_BITS == {}


def test_compiled_mechanics_use_effect_schema_and_class_masks() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        compiled = compile_card_mechanics(card)
        assert compiled["_capabilities"] == ()
        assert compiled["_capability_bits"] == 0
        assert isinstance(compiled["_class_mask"], int)
        assert isinstance(compiled["_reference_mask"], int)
        assert compiled["effects"] == card["design_rules"]["effects"]
        assert compiled["modes"] == card["design_rules"]["modes"]


def test_cost_machine_rules_match_printed_minima_and_targets() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}

    iven = cards["iven"]["design_rules"]["effects"][1]
    assert iven["op"] == "global_discount"
    assert iven["minimum"] == 0

    salt_road = cards["the-salt-road-fleet"]["design_rules"]["effects"][0]
    assert salt_road["op"] == "front_tactic_discount"
    assert salt_road["minimum"] == 0

    alda = cards["alda-keeper-of-the-ford"]["design_rules"]["modes"]["force"][0]
    assert alda["op"] == "tactic_tax"
    assert alda["target"] == "self_or_directly_behind"


def test_canonical_cards_have_no_engine_sync_migration_channel() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all("engine_sync" not in card for card in data["cards"])


def test_canonical_pool_is_the_only_machine_readable_card_catalogue() -> None:
    catalogues = [path for path in (ROOT / "cards").rglob("*.json")
                  if "cards" in json.loads(path.read_text())]
    assert catalogues == [ROOT / "cards" / "cards.json"]
