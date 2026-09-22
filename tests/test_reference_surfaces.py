from __future__ import annotations

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
