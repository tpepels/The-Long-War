from pathlib import Path

import pytest

from longwar.balance import build_report, score_static_formation, validate_command_costs
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
    assert score.static_strength == 7


def test_all_force_bond_name_combinations_are_analyzed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    report = build_report(data)
    forces = [*cards_by_type(data, "force"), *cards_by_type(data, "hero")]
    bonds = cards_by_type(data, "bond")
    printed_names = cards_by_type(data, "name")
    heroes = cards_by_type(data, "hero")
    expected = len(bonds) * (
        len(forces) * (len(printed_names) + len(heroes)) - len(heroes)
    )
    assert report["formation_count"] == expected


def test_static_strength_uses_canonical_rules_not_balance_annotations() -> None:
    cards = card_index(load_card_file(ROOT / "cards" / "cards.json"))
    bond = {
        **cards["followed"],
        "strength_modifier": 2,
        "design_rules": {
            "effects": [
                {
                    "timing": "while_named",
                    "scope": "self",
                    "op": "component_strength",
                    "component": "bond",
                    "amount": 4,
                }
            ],
            "modes": {},
        },
        "balance": {"strength_bonus": 99},
    }
    score = score_static_formation(cards["the-fifty-men"], bond, cards["namar"])
    assert score.static_strength == 11


def test_canonical_command_cost_validation_allows_zero_cost_tactics_and_orders() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    validate_command_costs(data)
    zero_cost = {
        card["id"]
        for card in data["cards"]
        if card["command_cost"] == 0
    }
    assert zero_cost == {
        "they-were-gathering-there",
        "fresh-orders",
        "catch-your-breath",
        "re-form-the-line",
        "bind-the-wound",
        "send-a-runner",
    }


def test_canonical_command_cost_validation_detects_invalid_printed_cost() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    card = next(card for card in data["cards"] if card["id"] == "avaros-the-bronze-king")
    card["command_cost"] = 0
    with pytest.raises(ValueError, match="avaros-the-bronze-king: invalid command_cost=0"):
        validate_command_costs(data)

    tactic = next(card for card in data["cards"] if card["id"] == "they-were-gathering-there")
    tactic["command_cost"] = -1
    with pytest.raises(ValueError, match="they-were-gathering-there: invalid command_cost=-1"):
        validate_command_costs(data)
