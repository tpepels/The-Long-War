from pathlib import Path

from longwar.cards import cards_by_type, load_card_file

ROOT = Path(__file__).resolve().parents[1]


def test_card_file_is_valid() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert len(data["cards"]) == 18


def test_every_name_is_unique() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    assert all(card["unique"] for card in cards_by_type(data, "name"))
