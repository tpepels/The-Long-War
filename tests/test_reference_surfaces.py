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


def test_battlefield_reference_is_one_readable_practical_sheet() -> None:
    page = text("web/playmat.html")
    css = text("web/rules.css")

    assert "reference-v3" in page
    assert "Battlefield & turn order" in page
    assert "WHERE CARDS GO" in page
    assert "ROLE BONUSES" in page
    assert "WHEN BOTH PASS" in page
    assert "BETWEEN BATTLES" in page
    assert "font-size: 2.95mm;" in css
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


def test_cards_are_scan_first_and_all_48_copy_blocks_are_labeled() -> None:
    data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    cards = data["cards"]
    allowed_labels = {
        "PLAY",
        "TRAIT",
        "WHILE",
        "WHEN",
        "BONUS",
        "NAMED",
        "TARGET",
        "EFFECT",
        "MOVE",
        "VEILED",
        "REVEAL",
        "WHILE REVEALED",
    }

    assert len(cards) == 48
    for card in cards:
        for block in card.get("rule_blocks", []):
            assert block.get("label") in allowed_labels
            assert block.get("text", "").strip()
        player_copy = " ".join(
            [card.get("text", "")]
            + [block.get("text", "") for block in card.get("rule_blocks", [])]
        ).lower()
        assert " link " not in f" {player_copy} "
        assert " plot " not in f" {player_copy} "
        assert " scheme " not in f" {player_copy} "

    style = text("web/style.css")
    play_style = text("web/play.css")
    card_rules = text("web/card-rules.js")
    assert "font: 3.55mm/1.18 Georgia,serif;" in style
    assert "font: 11.2px/1.16 Georgia, serif;" in play_style
    assert "Frontline +1 if Rear occupied" in card_rules
    assert "Rear: Subject in front +2" in card_rules


def test_physical_playtest_markers_cover_visible_state_without_leaking_hidden_bonus() -> None:
    page = text("web/tokens.html")
    css = text("web/tokens.css")
    kit = text("web/playtest-kit.html")

    assert "ACTIVE" in page
    assert "FIRST" in page and "TO PASS" in page
    assert page.count("BATTLE WIN") == 4
    assert "STRATAGEM USED" in page
    for modifier in ("+1", "+2", "+3", "-1", "-2", "-3"):
        assert modifier in page
    assert "Do not place a public Strength marker for a face-down" in page
    assert "opaque sleeves or identical card backs" in page
    assert "@page tracker" in css
    assert 'href="tokens.html"' in kit



def test_rulebook_opening_renders_markdown_and_sections_have_column_wrappers() -> None:
    rules = text("rules/rulebook.md")
    builder = text("tools/build_pages.py")
    css = text("web/rules.css")

    assert '<div class="rulebook-opening" markdown="1">' in rules
    assert '"md_in_html"' in builder
    assert "group_rulebook_sections" in builder
    assert ".rule-section" in css
    assert "break-inside: avoid-column;" in css
