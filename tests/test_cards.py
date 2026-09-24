from __future__ import annotations

import json
import re

import pytest
from pathlib import Path

from longwar.cards import (
    STORY_FORMS,
    SUBJECT_ROLES,
    cards_by_type,
    load_card_file,
    validate_card_data,
)

ROOT = Path(__file__).resolve().parents[1]


def test_card_file_is_valid() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert len(data["cards"]) == 48


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


def test_every_subject_has_a_supported_role() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    subjects = cards_by_type(data, "subject")
    assert subjects
    assert all(card["role"] in SUBJECT_ROLES for card in subjects)
    assert {"swordsman", "spearman", "archer", "healer"} <= {
        card["role"] for card in subjects
    }


def test_every_name_is_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))


def test_stories_have_named_forms_and_veiled_state() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    stories = cards_by_type(data, "plot")
    assert {card["story_form"] for card in stories} == STORY_FORMS
    assert all(isinstance(card["veiled"], bool) for card in stories)


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


def test_reference_deck_has_exactly_one_hero() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = {card["id"]: card for card in data["cards"]}
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]

    heroes = [card_id for card_id in deck if cards[card_id].get("hero", False)]
    assert len(deck) == 34
    assert heroes == ["avaros-the-bronze-king"]
    assert set(deck) <= set(cards)
    assert len(set(deck)) == 30




def test_expanded_pool_offers_three_hero_choices() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    heroes = [card for card in data["cards"] if card.get("hero", False)]
    assert {card["id"] for card in heroes} == {
        "avaros-the-bronze-king",
        "mara-queen-of-cinders",
        "sera-mother-of-white-hands",
    }
    assert {card["role"] for card in heroes} == {
        "swordsman",
        "archer",
        "healer",
    }

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

        if card["type"] == "plot" and card.get("veiled"):
            assert blocks[0]["kind"] == "property"
            assert blocks[0]["label"] == "FACE-DOWN"
            assert blocks[0]["text"].startswith("+")
            assert "**Strength** in this **Front**." in blocks[0]["text"]
            assert [block["kind"] for block in blocks[:2]] == [
                "property",
                "trigger",
            ]
            assert blocks[1]["label"] == "WHEN"

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
    for card in cards_by_type(data, "link"):
        assert int(card.get("rules", {}).get("strength_bonus", 0)) > 0


def test_card_rules_text_uses_canonical_typography() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    concepts = re.compile(
        r"\b(?:Subjects?|Bonds?|Names?|Stories?|Strength|Fronts?|Frontline|Rear|"
        r"Command|Cycle|Battles?|Stratagems?|Pass(?:es|ed)?|Discard(?:ed)?|Return(?:ed)?|Move(?:d)?|"
        r"adjacent|discard pile|Veiled Story|Stratagem|Hero|Line Defense)\b",
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


def test_canonical_decks_use_six_names_and_fourteen_subjects() -> None:
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
        assert sum(by_id[card_id]["type"] == "subject" for card_id in deck) == 14
        assert sum(by_id[card_id]["type"] == "name" for card_id in deck) == 6
        assert sum(bool(by_id[card_id].get("hero")) for card_id in deck) == 1


@pytest.mark.parametrize("value", [None, True, 0, 4, 1.5])
def test_printed_command_cost_is_a_small_integer(value) -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    data["cards"][0]["command_cost"] = value
    with pytest.raises(ValueError, match="command_cost"):
        validate_card_data(data)
