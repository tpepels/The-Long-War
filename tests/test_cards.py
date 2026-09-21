from pathlib import Path

from longwar.cards import cards_by_type, load_card_file

ROOT = Path(__file__).resolve().parents[1]


def test_card_file_is_valid() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert len(data["cards"]) == 22


def test_every_name_is_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))


def test_card_rules_text_avoids_obsolete_composite_jargon() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in data["cards"]:
        text = card.get("text", "").lower()
        assert "legend" not in text
        assert "complete" not in text


def test_all_links_have_immediate_game_value() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    for card in cards_by_type(data, "link"):
        assert int(card.get("rules", {}).get("strength_bonus", 0)) > 0


def test_card_rules_text_uses_canonical_typography() -> None:
    import re

    data = load_card_file(ROOT / "cards" / "cards.json")
    concepts = re.compile(
        r"\b(?:Subjects?|Links?|Names?|Strength|Fronts?|Frontline|Rear|"
        r"Schemes?|Plots?|Battles?|Pass(?:es|ed)?|Discard(?:ed)?|"
        r"Return(?:ed)?|Move(?:d)?|adjacent|discard pile)\b",
        re.IGNORECASE,
    )

    titles = [card["title"] for card in data["cards"]]
    for card in data["cards"]:
        text = card.get("text", "")

        # Bold spans are the only place defined game terms/actions should occur.
        without_bold = re.sub(r"\*\*[^*]+\*\*", "", text)
        # Italic properties such as *Frontline only.* are deliberately exempt.
        without_markup = re.sub(r"\*[^*]+\*", "", without_bold)
        assert not concepts.search(without_markup), (
            f"{card['title']} has an unformatted game concept: {text}"
        )

        # Any explicit reference to a card title must be italicized.
        text_without_italics = re.sub(r"\*[^*]+\*", "", text)
        for title in titles:
            assert title not in text_without_italics, (
                f"{card['title']} references {title} without italics"
            )
