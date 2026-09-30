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
    assert "Strength cannot fall below 0" in rules
    assert "player who Passed second counts as active" not in rules
    assert "no generic Draw operation" in rules
    assert "Base recovery = max(0, X - Y × (Battle - 1))" in rules
    assert "start of every turn" in rules
    assert "two consecutive Passes" in rules
    assert "first of the two consecutive Passes" in rules
    playmat = text("web/playmat.html").lower()
    assert "<b>start turn:</b> draw 1." in playmat
    assert "reshuffle discard only if deck empties" in text("web/playmat.html")
    assert "collapse before recovery" in playmat
    assert "+12, +9, +6, +3, +0" in text("web/playmat.html")
    assert "minimum 1" in playmat
    assert "below 5" not in playmat
    assert "+10, +7, +5" not in text("web/playmat.html")


def test_rulebook_core_constants_match_standard_engine() -> None:
    rules_text = text("rules/rulebook.md")
    standard = GameRules.standard()

    assert FRONT_COUNT == 4
    assert standard.opening_hand_size == 10
    assert standard.starting_command == 20
    assert standard.command_cap == 20
    assert standard.hand_limit == 10
    assert standard.ongoing_narrative_limit == 2
    assert standard.maneuver_command_cost == 1
    assert standard.command_recovery_start == 12
    assert standard.command_recovery_decrement == 3
    assert standard.command_recovery_floor == 1
    assert standard.command_collapse_threshold == 0

    assert "**four Fronts**" in rules_text
    assert "draw **10 cards**" in rules_text
    assert "Command to **20**" in rules_text
    assert "at most **2 Ongoing Narratives**" in rules_text
    assert "A Maneuver is one operation and costs **1 Command**" in rules_text
    assert "**two consecutive Passes**" in rules_text
    assert "exactly one player is at **0 Command**" in rules_text
    assert "X = 12" in rules_text
    assert "Y = 3" in rules_text


def test_web_game_rules_summary_matches_current_command_model() -> None:
    play = text("web/play.html")
    script = text("web/play.js")

    assert "check Command Collapse before recovery" in play
    assert "Ongoing Narratives" in play
    assert "ongoing Stories" not in play

    assert "exactly one player at 0 loses; 0-0 continues" in script
    assert "max(1, base recovery minus Fronts lost)" in script
    assert "below 5" not in script
    assert "Choose one of your two Ongoing Narrative slots" not in script
    assert "first open Narrative slot is assigned automatically" in script


def test_rulebook_roles_are_labels_not_hidden_rules() -> None:
    rules = text("rules/rulebook.md")
    assert "They have no hidden rules." in rules


def test_battlefield_reference_is_one_readable_practical_sheet() -> None:
    page = text("web/playmat.html")
    css = text("web/rules.css")

    assert "reference-v3" in page
    assert "Battlefield & turn order" in page
    assert "WHERE CARDS GO" in page
    assert "CARD TEXT" in page
    assert "AFTER TWO CONSECUTIVE PASSES" in page
    assert "BETWEEN BATTLES" in page
    assert "Hero" in page
    assert "max 1 Hero card from hand per Battle" in page
    assert "font-size: 3.1mm;" in css
    assert "page: battlefield-reference" in css


def test_balance_validation_covers_all_reference_decks() -> None:
    from tools.run_experiments import CANONICAL_DECK_PATHS

    shipped = {
        f"decks/{path.name}"
        for path in (ROOT / "decks").glob("*.json")
    }
    assert set(CANONICAL_DECK_PATHS.values()) == shipped
    assert "six shipped reference deck templates" in text("README.md")


def test_browser_runtime_copies_every_fast_search_include() -> None:
    from tools.build_browser_runtime import BROWSER_NATIVE_FILES

    fast_includes = {
        path.name
        for path in (ROOT / "src" / "longwar").glob("_fast_*.pxi")
    }
    assert fast_includes <= set(BROWSER_NATIVE_FILES)


def test_balance_lab_is_human_first_and_collapsible() -> None:
    page = text("web/balance.html")
    script = text("web/balance.js")
    css = text("web/style.css")

    assert 'id="attention-summary"' in page
    assert page.count('class="dashboard-disclosure"') >= 5
    assert "renderAttention(lab)" in script
    assert "renderProgression(lab)" in script
    assert 'id="progression-title"' in page
    assert 'id="progression-source-note"' in page
    assert "Unobserved" in page
    assert "unobserved = no self-play exposure" in script
    assert "Is the battlefield developing?" in page
    assert "Are Battles staying contestable?" in page
    assert "Are players retaining mechanical choice?" in page
    assert "Are resources progressing correctly?" in page
    assert "progression.html" not in page
    assert "mccfr_suite" in script
    assert "card-health-table" in page
    assert "min-width: 0 !important;" in css
    assert "row-evidence" in script
    assert "In hand at match end" in script
    assert "all_legends" not in script
    assert "health.legends" not in script
    assert 'cache: "no-store"' not in script
    assert "dashboard_telemetry" in script


def test_mccfr_profiles_use_only_current_cards() -> None:
    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    canonical = {card["id"] for card in cards["cards"]}
    covered: set[str] = set()
    for deck in (
        "decks/mobility-open-bonds.json",
        "decks/persistent-elite-heroes.json",
        "decks/narrative-command.json",
        "decks/battlefield-control-stratagems.json",
        "decks/momentum-orders.json",
        "decks/necessity-attrition.json",
    ):
        data = json.loads((ROOT / deck).read_text(encoding="utf-8"))
        covered.update(data["cards"])

    assert len(canonical) == 95
    assert len(covered) == 94
    assert canonical - covered == {"covered-the-withdrawal-of"}


def test_mccfr_suite_builder_covers_all_six_profile_policies() -> None:
    builder = text("tools/build_mccfr_suite.py")
    for profile in (
        "mobility",
        "elite",
        "narrative",
        "control",
        "momentum",
        "necessity",
    ):
        assert f'("{profile}",' in builder
    assert 'mccfr-policy-{profile_id}.json' in builder
    assert 'mccfr-{profile_id}-vs-heuristic.json' in builder
    assert 'heuristic-vs-mccfr-{profile_id}.json' in builder


def test_web_card_renderers_use_only_canonical_card_types() -> None:
    for surface in ("web/cards.js", "web/playtest-kit.js", "web/play.js", "web/balance.js"):
        source = text(surface)
        assert 'subject: "force"' not in source
        assert 'link: "bond"' not in source
        assert 'plot: "story"' not in source
        assert ".veiled" not in source


def test_cards_are_scan_first_and_all_current_copy_blocks_are_labeled() -> None:
    data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    cards = data["cards"]
    assert len(cards) == 95
    for card in cards:
        for block in card.get("rule_blocks", []):
            assert block.get("label", "").strip()
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
    assert "Frontline +1 if Rear occupied" not in card_rules
    assert "Rear: Force in front +2" not in card_rules
    assert "roleHint" not in card_rules
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
    assert "Ongoing Narratives and Stratagems are public." in page
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
