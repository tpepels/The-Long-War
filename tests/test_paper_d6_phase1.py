"""Phase 1 paper D6 combat contracts.

These checks exercise printed card grammar, documented combat arithmetic and
scenario outcomes. They are NOT a game engine, simulator or AI implementation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "cards/paper-d6.json").read_text(encoding="utf-8"))
CARDS = {card["id"]: card for card in DATA["cards"]}
DETAILED = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
PLAYER = (ROOT / "rules/player-rulebook.md").read_text(encoding="utf-8")
BATTLEFIELD = (ROOT / "web/playmat.html").read_text(encoding="utf-8")
MECHANICS = (ROOT / "web/playtest-kit.js").read_text(encoding="utf-8")


def _kills(
    attackers: tuple[int, ...],
    defender: int,
    *,
    can_defeat_equal_at: frozenset[int] = frozenset(),
) -> bool:
    """Test-only transcription of printed arithmetic, not runtime gameplay."""
    return any(
        strength + len(attackers) - 1 > defender
        or (i in can_defeat_equal_at and strength + len(attackers) - 1 == defender)
        for i, strength in enumerate(attackers)
    )


@pytest.mark.parametrize(
    ("attackers", "defender", "equal_strikers", "defeated"),
    [
        ((5,), 4, frozenset(), True),
        ((4,), 4, frozenset(), False),
        ((3, 4), 4, frozenset(), True),  # printed 4 + one ally = 5
        ((3, 4), 5, frozenset(), False),  # coordinated equality still survives
        ((2, 2), 5, frozenset(), False),  # no automatic two-hit kill
        ((2, 2, 2), 3, frozenset(), True),
        ((3, 4), 5, frozenset({1}), True),  # explicit equal-Force Special
        ((4,), 4, frozenset({0}), True),  # solo equal-Force Special
        ((4,), 5, frozenset({0}), False),
        ((3,), 4, frozenset(), False),  # an uncancelled failed Strike Pins
    ],
)
def test_coordinated_force_threshold(attackers, defender, equal_strikers, defeated):
    assert _kills(attackers, defender, can_defeat_equal_at=equal_strikers) is defeated


def test_protect_cancels_an_individual_strike_not_an_entire_defeat():
    # Two uncancelled attacks 3+4 beat a Force 4, but cancelling Force 4
    # leaves only Force 3 (not 3+1). The remaining hit merely Pins.
    assert _kills((3, 4), 4)
    assert not _kills((3,), 4)
    assert not _kills((4,), 4)
    # Protect cannot remove Pressure, which is resolved before Protect.
    assert DETAILED.index("**Evade, then Pressure.**") < DETAILED.index("**Protect.**")


def test_pressure_is_a_tradeoff_not_an_extra_free_strike():
    assert not _kills((3,), 4)  # solo-ineffective Strike can become Pressure
    assert _kills((3, 4), 4)  # choosing the damaging strike coordinates
    assert not _kills((4,), 4)  # converting Force 3 to Pressure removes +1
    assert "converted Strike no longer damages and gives no +1" in DETAILED
    assert "cancels *that Force's entire rolled support outcome*" in DETAILED
    assert "Multiple Pressure results on one Force do not stack" in DETAILED
    assert "cannot itself be cancelled by Protect" in DETAILED


def test_rescue_saves_the_whole_force_not_just_one_hit():
    assert _kills((4, 4, 5), 5)
    # Rescue is performed once for the whole target after calculating lethal
    # attacks. Its outcome is binary: the target survives, not "one hit left."
    assert "**prevent the entire defeat of one eligible friendly Force**" in DETAILED
    assert "A Force that is **saved by Rescue** was never defeated" in DETAILED
    assert "Rescue never turns into retroactive cancellation" not in DETAILED
    assert "Pressure never turns into retroactive cancellation" in PLAYER


def test_exact_die_faces_for_an_actual_coordinated_front():
    # With a common roll of 6, these two cards both Strike under any Plan.
    assert CARDS["the-red-shields"]["faces"][5] == "A"
    assert CARDS["the-crow-archers"]["faces"][5] == "A"
    assert CARDS["the-red-shields"]["force"] == 4
    assert CARDS["the-crow-archers"]["force"] == 3
    assert _kills((3, 4), 4)
    assert not _kills((3, 4), 5)


def test_every_paper_card_uses_an_existing_mechanical_vocabulary():
    assert len(CARDS) == 44
    assert all(len(card["faces"]) == 6 and len(card["outcomes"]) == 4 for card in CARDS.values())
    for card in CARDS.values():
        outcomes = card["outcomes"]
        assert set(card["faces"]) == set(outcomes), card["id"]
        assert outcomes["F"]["effect"] == "No combat effect.", card["id"]
        assert outcomes["D"]["effect"].startswith(("Evade", "Protect")), card["id"]
        attack_letter = "R" if card["role"] in ("healer", "steward") else "A"
        assert outcomes[attack_letter]["effect"].startswith(("Rescue", "Strike")), card["id"]
        assert outcomes["S"]["effect"].startswith(("Strike", "Protect", "Rescue")), card["id"]
        for outcome in outcomes.values():
            wording = outcome["effect"]
            assert "regardless of Battle Plan" not in wording, card["id"]
            assert "otherwise Frontline" not in wording, card["id"]
            assert "if it defeats an enemy" not in wording, card["id"]
            assert not any(term in wording.lower() for term in
                           ("bond", "named", "strength", "exhausted")), card["id"]


def test_cross_front_effects_have_explicit_permission_only():
    adjacent = [
        card["id"] for card in CARDS.values()
        if any("adjacent active Front" in o["effect"] for o in card["outcomes"].values())
    ]
    assert adjacent == ["avaros-the-bronze-king"]
    assert "Only an individually printed Special" in DETAILED
    assert "explicitly mentioning an adjacent active Front" in DETAILED


def test_movement_and_plan_matrices_are_not_silently_changed():
    for page in (DETAILED, PLAYER, BATTLEFIELD, MECHANICS):
        for plan in ("Assault", "Hold", "Volley", "Raid"):
            assert plan in page
    assert "Pinned Forces cannot move" in DETAILED
    assert "no Force moves more than once" in DETAILED
    assert "freely choose" in PLAYER
    assert "Pressure" in BATTLEFIELD
    assert "Pressure" in MECHANICS
    assert "each uncancelled damaging Strike gains +1" in MECHANICS
    assert "Two Strikes do not automatically kill" in PLAYER
    assert "two or more *uncancelled* Strikes aimed at the same enemy defeat" not in DETAILED


def test_paper_experiment_does_not_import_runtime_components():
    from tools import paper_d6_cards

    source = Path(paper_d6_cards.__file__).read_text(encoding="utf-8")
    assert "from longwar.engine" not in source
    assert "from longwar.ai" not in source
    assert "print-only" in source or "Physical-only" in source
