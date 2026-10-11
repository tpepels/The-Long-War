"""Phase 2 physical D6 positional and hidden-Battle-Plan contract.

These examples describe *paper* tactical rules only. They do not simulate a
match and must never be imported by the native engine or any AI.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = (ROOT / "rules/phase2-tactical-audit.md").read_text(encoding="utf-8")
RULES = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
PLAYER = (ROOT / "rules/player-rulebook.md").read_text(encoding="utf-8")
PLANS = (ROOT / "web/tokens.html").read_text(encoding="utf-8")
MAT = (ROOT / "web/playmat.html").read_text(encoding="utf-8")
KIT = (ROOT / "web/playtest-kit.js").read_text(encoding="utf-8")
POOL = json.loads((ROOT / "cards/paper-d6.json").read_text(encoding="utf-8"))["cards"]
CARDS = {card["id"]: card for card in POOL}

PLANS_IN_ORDER = ("Assault", "Hold", "Volley", "Raid")
COUNTERS = {
    "Hold": "Assault",
    "Assault": "Volley",
    "Volley": "Raid",
    "Raid": "Hold",
}


def read_result(ours: str, theirs: str) -> str:
    """A paper plan-table lookup, not a runtime game implementation."""
    if ours == theirs:
        return "Mirror"
    if COUNTERS[ours] == theirs:
        return "Read"
    if COUNTERS[theirs] == ours:
        return "Countered"
    return "Neutral"


@pytest.mark.parametrize(
    ("ours", "theirs", "expected"),
    [
        ("Assault", "Assault", "Mirror"),
        ("Assault", "Hold", "Countered"),
        ("Assault", "Volley", "Read"),
        ("Assault", "Raid", "Neutral"),
        ("Hold", "Assault", "Read"),
        ("Hold", "Hold", "Mirror"),
        ("Hold", "Volley", "Neutral"),
        ("Hold", "Raid", "Countered"),
        ("Volley", "Assault", "Countered"),
        ("Volley", "Hold", "Neutral"),
        ("Volley", "Volley", "Mirror"),
        ("Volley", "Raid", "Read"),
        ("Raid", "Assault", "Neutral"),
        ("Raid", "Hold", "Read"),
        ("Raid", "Volley", "Countered"),
        ("Raid", "Raid", "Mirror"),
    ],
)
def test_all_sixteen_plan_matchups(ours, theirs, expected):
    assert read_result(ours, theirs) == expected
    assert ours in AUDIT and theirs in AUDIT


def test_exact_counter_cycle_and_no_unfair_extra_wins():
    assert len(set(COUNTERS)) == len(set(COUNTERS.values())) == 4
    for own in PLANS_IN_ORDER:
        assert sum(read_result(own, enemy) == "Read" for enemy in PLANS_IN_ORDER) == 1
        assert sum(read_result(own, enemy) == "Countered" for enemy in PLANS_IN_ORDER) == 1
        assert sum(read_result(own, enemy) == "Neutral" for enemy in PLANS_IN_ORDER) == 1
        assert sum(read_result(own, enemy) == "Mirror" for enemy in PLANS_IN_ORDER) == 1
    assert "Hold counters Assault" in PLAYER
    assert "Assault counters Volley" in PLAYER
    assert "Volley counters Raid" in PLAYER
    assert "Raid counters Hold" in PLAYER
    assert "Hold &gt; Assault &gt; Volley &gt; Raid &gt; Hold" in MAT


def test_audit_contains_complete_symmetric_matrix():
    begin = AUDIT.index("| Yours")
    end = AUDIT.index("## Proposed single shared counter rule", begin)
    matrix_lines = [line for line in AUDIT[begin:end].splitlines() if line.startswith("|")]
    assert len(matrix_lines) == 6  # heading, delimiter, four data rows
    for own, line in zip(PLANS_IN_ORDER, matrix_lines[2:]):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert own in cells[0]
        assert len(cells) == 5
        for enemy, cell in zip(PLANS_IN_ORDER, cells[1:]):
            expected = read_result(own, enemy)
            if expected == "Read":
                assert "Counters" in cell
            elif expected == "Countered":
                assert "Countered" in cell
            elif expected == "Mirror":
                assert "Mirror" in cell
            else:
                assert "Neutral" in cell


def test_role_pool_and_face_maps_unchanged_by_positional_rules():
    assert len(POOL) == 44
    roles = {role: sum(c["role"] == role for c in POOL)
             for role in {c["role"] for c in POOL}}
    assert roles["guard"] == 8
    assert roles["archer"] == 3
    assert sum(roles[x] for x in ("raider", "rider", "skirmisher")) == 15
    assert sum(roles[x] for x in ("healer", "steward")) == 4
    assert all(len(c["faces"]) == 6 and len(c["outcomes"]) == 4 for c in POOL)


@pytest.mark.parametrize(
    ("role", "rank", "plan", "special_reach"),
    [
        ("guard", "front", "Hold", "any-friendly-Protect"),
        ("guard", "middle", "Volley", "printed-Protect"),
        ("archer", "middle", "Volley", "any-rank"),
        ("archer", "rear", "Volley", "any-rank"),
        ("archer", "front", "Volley", "foremost"),
        ("raider", "front", "Raid", "middle-rear"),
        ("rider", "middle", "Raid", "middle-rear"),
        ("skirmisher", "rear", "Raid", "foremost"),
        ("healer", "rear", "Assault", "any-friendly-Rescue"),
        ("steward", "middle", "Hold", "printed-Rescue"),
    ],
)
def test_rank_role_permission_examples(role, rank, plan, special_reach):
    # Human-readable table checks: this is deliberately not a new rules engine.
    rule = {
        ("guard", "front"): "any-friendly-Protect",
        ("archer", "middle"): "any-rank",
        ("archer", "rear"): "any-rank",
        ("raider", "front"): "middle-rear",
        ("rider", "middle"): "middle-rear",
        ("healer", "rear"): "any-friendly-Rescue",
    }
    assert rule.get((role, rank), {
        "guard": "printed-Protect",
        "archer": "foremost",
        "skirmisher": "foremost",
        "steward": "printed-Rescue",
    }.get(role)) == special_reach
    assert plan in PLAYER


def test_read_is_optional_and_one_of_two_instead_of_a_free_card_action():
    assert "**one Read per Front where you have Forces**" in RULES
    assert "You may use **at most one** of these two benefits per Front, not both" in RULES
    assert "**Read Strike:**" in RULES and "**Read Protect:**" in RULES
    assert "ignore one Protect" in RULES
    assert "does not name a specific target rank" in RULES
    assert "one extra incoming damaging Strike" in RULES
    assert "no suitable rolled Strike/Protect" in RULES
    assert "cannot bypass Evade or Rescue" in PLAYER
    assert PLANS.count("Read: one Strike targets any rank") == 8
    # Printed fixed-target Specials are unaffected; S outcomes stay as authored.
    assert CARDS["the-crow-archers"]["outcomes"]["S"]["effect"] == "Strike enemy Middle."


@pytest.mark.parametrize(
    ("strike_killed", "protect_cancelled", "rescue_saved", "opportunity"),
    [
        (False, False, False, False),
        (True, False, False, True),
        (False, True, False, True),
        (False, False, True, True),
        (True, True, True, True),
    ],
)
def test_opportunity_triggers(strike_killed, protect_cancelled, rescue_saved, opportunity):
    earned = strike_killed or protect_cancelled or rescue_saved
    assert earned is opportunity
    assert "permanently defeated" in RULES
    assert "cancelled an incoming damaging Strike" in RULES
    assert "prevented a friendly Force's defeat" in RULES


def test_opportunity_movement_limits_and_protections():
    assert "One post-combat move maximum per player per Front" in RULES
    assert "A Force cannot move twice" in RULES
    assert "Pinned Forces cannot move" in RULES
    assert "Assault may make the optional single forward step" in RULES
    assert "The destination must be **empty after casualties**" in RULES
    assert "Printed Special advances first" in PLAYER
    assert "rank never scores extra control" in PLAYER
    assert "never persist to the next Battle" in PLAYER


def test_reference_pages_adhere_to_same_core_rules():
    for doc in (RULES, PLAYER, PLANS, MAT, KIT):
        for plan in PLANS_IN_ORDER:
            assert plan in doc
        assert "Read" in doc
    assert "Opportunity" in PLANS
    assert "Opportunity" in MAT
    assert "OPPORTUNITY" in KIT
    assert "Middle/Rear" in KIT
    assert "One post-combat move per player per Front" in MAT
    assert "20 Command" in PLAYER
    assert "Force-only" in RULES
