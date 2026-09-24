from pathlib import Path

from longwar.balance import build_report, score_static_legend
from longwar.cards import card_index, cards_by_type, load_card_file

ROOT = Path(__file__).resolve().parents[1]


def test_fifty_men_followed_namar_static_strength_before_position_bonus() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = card_index(data)
    score = score_static_legend(
        cards["the-fifty-men"],
        cards["followed"],
        cards["namar"],
    )
    assert score.static_strength == 9


def test_all_subject_bond_name_combinations_are_analyzed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    report = build_report(data)
    assert report["legend_count"] == (
        len(cards_by_type(data, "subject"))
        * len(cards_by_type(data, "link"))
        * len(cards_by_type(data, "name"))
    )


def test_static_strength_uses_canonical_rules_not_balance_annotations() -> None:
    cards = card_index(load_card_file(ROOT / "cards" / "cards.json"))
    link = {**cards["followed"], "rules": {"strength_bonus": 2, "named_strength_bonus": 4}, "balance": {"strength_bonus": 99}}
    score = score_static_legend(cards["the-fifty-men"], link, cards["namar"])
    assert score.static_strength == 12
