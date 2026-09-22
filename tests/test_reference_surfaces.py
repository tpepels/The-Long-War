from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rulebook_uses_manual_columns_and_scan_summary() -> None:
    css = text("web/rules.css")
    rules = text("rules/rulebook.md")

    assert "column-count: 2;" in css
    assert "rulebook-at-a-glance" in rules
    assert "Final Subject Strength cannot fall below 0." in rules
    assert "No Fires Burned" in rules
    assert "gives +2" in rules
    assert "player who Passed second counts as active" not in rules


def test_rulebook_healer_language_matches_engine_semantics() -> None:
    rules = text("rules/rulebook.md")
    assert (
        "| *Healer* | While in the **Rear**, the friendly Subject directly in front "
        "of it gets +2 Strength. Current Healer cards are printed *Rear only*. |"
    ) in rules


def test_battlefield_reference_is_one_practical_sheet() -> None:
    page = text("web/playmat.html")
    css = text("web/rules.css")

    assert "battle-reference-sheet" in page
    assert "What can go where?" in page
    assert "Role bonuses" in page
    assert "When both players Pass" in page
    assert "reference-turn-strip" in page
    assert "page: battlefield-reference" in css


def test_balance_lab_is_human_first_and_collapsible() -> None:
    page = text("web/balance.html")
    script = text("web/balance.js")
    css = text("web/style.css")

    assert 'id="attention-summary"' in page
    assert page.count('class="dashboard-disclosure"') >= 5
    assert "renderAttention(lab)" in script
    assert "mccfr_suite" in script
    assert "card-health-table" in page
    assert "min-width: 0 !important;" in css
    assert "row-evidence" in script


def test_mccfr_profiles_cover_the_entire_current_card_pool() -> None:
    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    canonical = {card["id"] for card in cards["cards"]}
    covered: set[str] = set()
    for deck in (
        "decks/reference.json",
        "decks/avaros-line.json",
        "decks/mara-rear.json",
        "decks/sera-support.json",
    ):
        data = json.loads((ROOT / deck).read_text(encoding="utf-8"))
        covered.update(data["cards"])

    assert covered == canonical
    assert len(canonical) == 48


def test_manual_mccfr_workflow_builds_all_four_profile_policies() -> None:
    workflow = text(".github/workflows/mccfr.yml")
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    for profile in ("reference", "avaros", "mara", "sera"):
        assert f"mccfr-policy-{profile}.json" in workflow
    assert "tools/build_mccfr_suite.py" in workflow
