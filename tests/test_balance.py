from pathlib import Path

import pytest

from longwar.balance import (
    build_report,
    score_static_formation,
    validate_command_costs,
)
from longwar.cards import card_index, cards_by_type, load_card_file

ROOT = Path(__file__).resolve().parents[1]


def test_fifty_men_followed_namar_static_strength_before_position_bonus() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    cards = card_index(data)
    score = score_static_formation(
        cards["the-fifty-men"],
        cards["followed"],
        cards["namar"],
    )
    assert score.static_strength == 8


def test_all_force_bond_name_combinations_are_analyzed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    report = build_report(data)
    assert report["formation_count"] == (
        len(cards_by_type(data, "force"))
        * len(cards_by_type(data, "bond"))
        * len(cards_by_type(data, "name"))
    )


def test_static_strength_uses_canonical_rules_not_balance_annotations() -> None:
    cards = card_index(load_card_file(ROOT / "cards" / "cards.json"))
    bond = {
        **cards["followed"],
        "rules": {"strength_bonus": 2, "named_strength_bonus": 4},
        "balance": {"strength_bonus": 99},
    }
    score = score_static_formation(
        cards["the-fifty-men"],
        bond,
        cards["namar"],
    )
    assert score.static_strength == 11


def test_command_cost_validation_accepts_canonical_printed_costs() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    validate_command_costs(data)
    card = next(
        card
        for card in data["cards"]
        if card["id"] == "avaros-the-bronze-king"
    )
    card["command_cost"] = 0
    with pytest.raises(ValueError, match="Invalid Command costs"):
        validate_command_costs(data)
