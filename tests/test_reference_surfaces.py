from __future__ import annotations

import json
import re

import markdown
from pathlib import Path

from longwar.game.model import FRONT_COUNT
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rulebook_uses_manual_columns_and_scan_summary() -> None:
    css = text("web/rules.css")
    rules = text("rules/rulebook.md")

    assert "column-count: 2;" in css
    assert "rulebook-at-a-glance" in rules
    assert "Final Force Strength cannot fall below 0." in rules
    assert "player who Passed second counts as active" not in rules
    assert "no generic Draw operation" in rules
    assert "| I | 10 |" in rules
    assert "start of every turn" in rules
    assert "two consecutive Passes" in rules
    assert "first of the two consecutive Passes" in rules
    assert "draw 1 card automatically" in text("web/playmat.html").lower()
    assert "reshuffle discard only if deck empties" in text("web/playmat.html")


def test_rulebook_core_constants_match_standard_engine() -> None:
    rules_text = text("rules/rulebook.md")
    standard = GameRules.standard()

    assert FRONT_COUNT == 4
    assert standard.opening_hand_size == 10
    assert standard.starting_command == 20
    assert standard.command_cap == 20
    assert standard.hand_limit == 10
    assert standard.ongoing_story_limit == 2
    assert standard.maneuver_command_cost == 1
    assert standard.command_recovery_schedule == (10, 7, 5, 4, 3, 2, 1)
    assert standard.command_collapse_threshold == 5
    assert standard.cycle_enabled is False

    assert "**four Fronts**" in rules_text
    assert "draw **10 cards**" in rules_text
    assert "Command to **20**" in rules_text
    assert "at most **2 ongoing Stories**" in rules_text
    assert "Maneuver is an operation that costs **1 Command**" in rules_text
    assert "**two consecutive Passes**" in rules_text
    assert "fewer than 5 Command" in rules_text


def test_rulebook_healer_language_matches_engine_semantics() -> None:
    rules = text("rules/rulebook.md")
    assert (
        "| *Healer* | While in the Rear, the friendly Force directly in front "
        "of it gets +2 Strength. |"
    ) in rules


def test_battlefield_reference_is_one_readable_practical_sheet() -> None:
    page = text("web/playmat.html")
    css = text("web/rules.css")

    assert "reference-v3" in page
    assert "Battlefield & turn order" in page
    assert "WHERE CARDS GO" in page
    assert "ROLE BONUSES" in page
    assert "AFTER TWO CONSECUTIVE PASSES" in page
    assert "BETWEEN BATTLES" in page
    assert "Hero" in page
    assert "only 1 Hero per side per Battle" in page
    assert "font-size: 3.1mm;" in css
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
    assert len(canonical) == 51


def test_mccfr_suite_builder_covers_all_four_profile_policies() -> None:
    builder = text("tools/build_mccfr_suite.py")
    for profile in ("reference", "avaros", "mara", "sera"):
        assert f'("{profile}",' in builder
    assert 'mccfr-policy-{profile_id}.json' in builder
    assert 'mccfr-{profile_id}-vs-heuristic.json' in builder
    assert 'heuristic-vs-mccfr-{profile_id}.json' in builder


def test_cards_are_scan_first_and_all_current_copy_blocks_are_labeled() -> None:
    data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    cards = data["cards"]
    allowed_labels = {
        "PLAY",
        "TRAIT",
        "DUAL",
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
        "FACE-DOWN",
        "WHEN PLAYED",
        "DURING THIS BATTLE",
    }

    assert len(cards) == 51
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
    rules_style = re.search(r"\.play-card-rules\s*\{([^}]+)\}", play_style).group(1)
    typography = re.search(r"font:\s*([\d.]+)px/([\d.]+)\s+Georgia\s*,\s*serif", rules_style)
    assert typography is not None
    assert float(typography.group(1)) >= 11
    assert float(typography.group(2)) >= 1.15
    assert "Frontline +1 if Rear occupied" in card_rules
    assert "Rear: Force in front +2" in card_rules
    for surface in ("web/card-rules.js", "web/cards.js", "web/playtest-kit.js", "web/balance.html", "web/balance.js", "web/tokens.html"):
        assert "Subject" not in text(surface)


def test_physical_playtest_markers_cover_visible_state_without_leaking_hidden_bonus() -> None:
    page = text("web/tokens.html")
    css = text("web/tokens.css")
    kit = text("web/playtest-kit.html")

    assert "ACTIVE" in page
    assert "FIRST" in page and "TO PASS" in page
    assert "PASS PENDING" in page
    assert "BATTLE WIN" not in page
    assert "STRATAGEM USED" in page
    assert page.count("HERO USED") == 2
    assert "DRAW USED" not in page
    assert "FINAL</strong><span>OPERATION" not in page
    assert "COMMAND · NEXT BATTLE" not in page
    assert "There is no overall Battle winner." in page
    for modifier in ("+1", "+2", "+3", "-1", "-2", "-3"):
        assert modifier in page
    assert "Ongoing Stories and Stratagems are public." in page
    assert "stay face-up and visible to both players" in page
    assert "@page tracker" in css
    assert 'href="tokens.html"' in kit



def test_rulebook_opening_renders_markdown_and_sections_have_column_wrappers() -> None:
    from tools.build_pages import group_rulebook_sections

    rules = text("rules/rulebook.md")
    builder = text("tools/build_pages.py")
    css = text("web/rules.css")
    rendered = markdown.markdown(
        rules,
        extensions=["extra", "sane_lists", "attr_list", "md_in_html"],
    )
    rendered = group_rulebook_sections(rendered)

    assert '<div class="rulebook-opening" markdown="1">' in rules
    assert '"md_in_html"' in builder
    assert "<strong>The Long War</strong>" in rendered
    assert "**The Long War**" not in rendered
    assert '<section class="rule-section">' in rendered
    assert ".rule-section" in css
    assert "break-inside: avoid-column;" in css


def test_balance_lab_hides_dynamic_evidence_from_other_rulesets() -> None:
    builder = text("tools/build_lab_report.py")
    script = text("web/balance.js")
    fingerprint = text("src/longwar/fingerprint.py")

    assert "current_game_fingerprint" in builder
    assert '"stale_evidence": sorted(stale_files)' in builder
    assert 'data.get("game_fingerprint") != game_fingerprint' in builder
    assert "Solver evidence needs a fresh run for this ruleset" in script
    assert '".pxi"' in fingerprint
