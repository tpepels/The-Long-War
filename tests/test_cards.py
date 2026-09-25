from __future__ import annotations

import json
import re

import pytest
from pathlib import Path

from longwar.cards import (
    STORY_FORMS,
    FORCE_ROLES,
    cards_by_type,
    load_card_file,
    validate_card_data,
)

ROOT = Path(__file__).resolve().parents[1]


def test_card_file_is_valid() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert len(data["cards"]) == 51


def test_every_card_has_world_classifications() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        assert card["classes"]
        assert len(card["classes"]) == len(set(card["classes"]))

    represented = {
        classification
        for card in data["cards"]
        for classification in card["classes"]
    }
    assert {"human", "god", "king", "ship"} <= represented


def test_every_force_has_a_supported_role() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    forces = cards_by_type(data, "force")
    assert forces
    assert all(card["role"] in FORCE_ROLES for card in forces)
    assert {"swordsman", "spearman", "archer", "healer"} <= {
        card["role"] for card in forces
    }


def test_every_name_is_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))


def test_stories_have_named_forms_and_public_ongoing_metadata() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    stories = cards_by_type(data, "story")
    assert {card["story_form"] for card in stories} == STORY_FORMS
    assert all(isinstance(card["ongoing"], bool) for card in stories)


def test_stratagem_pool_is_unique_and_rule_backed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    stratagems = cards_by_type(data, "stratagem")

    assert len(stratagems) == 8
    assert all(card["unique"] for card in stratagems)
    assert all(
        card.get("rules", {}).get("stratagem", {}).get("trigger", {}).get("event")
        == "played"
        for card in stratagems
    )
    assert {
        "the-storm-broke",
        "the-tide-rose",
        "the-ground-gave-way",
        "the-bronze-teeth",
        "the-false-muster",
        "the-wooden-gift",
        "the-broken-mast",
        "the-quiet-field",
    } == {card["id"] for card in stratagems}


def test_reference_deck_carries_multiple_unique_heroes() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]

    heroes = [card_id for card_id in deck if cards[card_id].get("hero", False)]
    assert len(deck) == 34
    assert set(heroes) == {
        "avaros-the-bronze-king",
        "lysa-of-the-salt-road",
        "theron-the-oathkeeper",
    }
    assert len(heroes) == len(set(heroes)) == 3
    assert set(deck) <= set(cards)




def test_expanded_pool_offers_six_dual_use_hero_choices() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    heroes = [card for card in data["cards"] if card.get("hero", False)]
    assert {card["id"] for card in heroes} == {
        "avaros-the-bronze-king",
        "mara-queen-of-cinders",
        "sera-mother-of-white-hands",
        "daran-the-red-shield",
        "lysa-of-the-salt-road",
        "theron-the-oathkeeper",
    }
    assert {card["role"] for card in heroes} >= {
        "swordsman",
        "spearman",
        "archer",
        "healer",
    }
    assert all(card["unique"] for card in heroes)
    assert all(card["hero_name_strength"] == 2 for card in heroes)

def test_all_cards_define_semantic_rule_blocks() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    allowed = {"property", "timing", "trigger", "effect", "continuous"}

    for card in data["cards"]:
        blocks = card["rule_blocks"]
        assert all(block["kind"] in allowed for block in blocks)
        assert all(block["text"].strip() for block in blocks)

        if card["text"]:
            assert blocks, card["title"]
        else:
            assert blocks == [], card["title"]

        properties = [i for i, block in enumerate(blocks) if block["kind"] == "property"]
        if properties:
            assert properties == list(range(len(properties))), card["title"]

        if card["type"] == "stratagem":
            assert blocks[0]["kind"] == "trigger"
            continuous = [i for i, block in enumerate(blocks) if block["kind"] == "continuous"]
            effects = [i for i, block in enumerate(blocks) if block["kind"] == "effect"]
            if continuous and effects:
                assert max(effects) < min(continuous), card["title"]


def test_player_facing_card_text_avoids_old_technical_terms() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        text = card.get("text", "")
        assert "complete" not in text.lower()
        assert not re.search(r"\b(?:link|plot|scheme)s?\b", text, re.IGNORECASE)


def test_all_bonds_have_immediate_game_value() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in cards_by_type(data, "bond"):
        assert int(card.get("rules", {}).get("strength_bonus", 0)) > 0


def test_card_rules_text_uses_canonical_typography() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    concepts = re.compile(
        r"\b(?:Forces?|Bonds?|Names?|Stories?|Strength|Fronts?|Frontline|Rear|"
        r"Command|Battles?|Stratagems?|Pass(?:es|ed)?|Discard(?:ed)?|Return(?:ed)?|Move(?:d)?|"
        r"adjacent|discard pile|Stratagem|Hero)\b",
        re.IGNORECASE,
    )

    titles = [card["title"] for card in data["cards"]]
    for card in data["cards"]:
        text = card.get("text", "")

        without_bold = re.sub(r"\*\*[^*]+\*\*", "", text)
        without_markup = re.sub(r"\*[^*]+\*", "", without_bold)
        assert not concepts.search(without_markup), (
            f"{card['title']} has an unformatted game concept: {text}"
        )

        text_without_italics = re.sub(r"(?<!\*)\*[^*]+\*(?!\*)", "", text)
        for title in titles:
            assert title not in text_without_italics, (
                f"{card['title']} references {title} without italics"
            )


def test_canonical_decks_use_six_names_and_fourteen_forces() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    by_id = {card["id"]: card for card in data["cards"]}
    for path in (
        ROOT / "decks" / "reference.json",
        ROOT / "decks" / "avaros-line.json",
        ROOT / "decks" / "mara-rear.json",
        ROOT / "decks" / "sera-support.json",
    ):
        deck = json.loads(path.read_text(encoding="utf-8"))["cards"]
        assert len(deck) == 34
        assert sum(by_id[card_id]["type"] == "force" for card_id in deck) == 14
        assert sum(by_id[card_id]["type"] == "name" for card_id in deck) == 6
        heroes = [card_id for card_id in deck if by_id[card_id].get("hero")]
        assert len(heroes) == 3
        assert len(heroes) == len(set(heroes))


@pytest.mark.parametrize("value", [None, True, 0, 4, 1.5])
def test_printed_command_cost_is_a_small_integer(value) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    data["cards"][0]["command_cost"] = value
    with pytest.raises(ValueError, match="command_cost"):
        validate_card_data(data)
