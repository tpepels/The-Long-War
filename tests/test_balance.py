from pathlib import Path

from longwar.balance import build_report, score_static_legend
from longwar.cards import card_index, load_card_file

ROOT = Path(__file__).resolve().parents[1]


def test_fifty_men_followed_namar_static_strength() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = card_index(data)
    score = score_static_legend(
        cards["the-fifty-men"],
        cards["followed"],
        cards["namar"],
    )
    assert score.static_strength == 11


def test_all_current_legend_combinations_are_analyzed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    report = build_report(data)
    assert report["legend_count"] == 6 * 5 * 4
