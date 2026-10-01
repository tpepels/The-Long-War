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


def rendered_rulebook() -> str:
    from tools.build_pages import render_rule_tokens

    return render_rule_tokens(
        text("rules/rulebook.md"),
        GameRules.standard(),
    )


def test_rulebook_uses_manual_columns_and_scan_summary() -> None:
    css = text("web/rules.css")
    rules = rendered_rulebook()
    from tools.build_pages import render_rule_tokens

    standard = GameRules.standard()
    playmat_source = render_rule_tokens(
        text("web/playmat.html"),
        standard,
    )
    playmat = playmat_source.lower()
    recovery_label = ", ".join(
        f"+{standard.command_recovery_for_battle(battle)}"
        for battle in range(1, 6)
    )

    assert "column-count: 2;" in css
    assert "## How the war unfolds {#learn}" in rules
    assert "A Battle has a simple arc:" in rules
    assert "Strength cannot fall below 0" in rules
    assert "player who Passed second counts as active" not in rules
    assert "no generic Draw operation" in rules
    assert (
        f"Base recovery starts at **{standard.command_recovery_start}** in Battle I "
        f"and falls by **{standard.command_recovery_decrement}** each Battle:"
        in rules
    )
    assert "start of every turn" in rules
    assert "both players have Passed at least once" in rules
    assert "player who **Passed first** starts the next Battle" in rules
    assert "<b>start turn:</b> draw 1." in playmat
    assert "reshuffle discard only if deck empties" in playmat_source
    assert "collapse before recovery" in playmat
    assert f"lose {standard.lost_front_command_penalty} command per unprotected front lost" in playmat
    assert f"at or below {standard.command_collapse_threshold}" in playmat
    assert "equal command is a draw" in playmat
    assert "front losses have already reduced command before collapse" in playmat
    assert recovery_label in playmat_source
    assert f"minimum {standard.command_recovery_floor}" in playmat


def test_rulebook_core_values_match_standard_engine() -> None:
    rules_text = rendered_rulebook()
    standard = GameRules.standard()

    assert FRONT_COUNT == 4
    assert f"draw **{standard.opening_hand_size} cards**" in rules_text
    assert f"Command to **{standard.starting_command}**" in rules_text
    assert (
        f"at most **{standard.ongoing_narrative_limit} Ongoing Narratives**"
        in rules_text
    )
    assert (
        "A **Maneuver** is an operation that moves one of your Named Formations."
        in rules_text
    )
    assert f"It costs **{standard.maneuver_command_cost} Command**." in rules_text
    assert "**both players have Passed at least once**" in rules_text
    assert (
        f"at or below **{standard.command_collapse_threshold} Command**"
        in rules_text
    )
    assert (
        f"**{standard.lost_front_command_penalty} Command for each Front you lost**"
        in rules_text
    )
    assert (
        f"Base recovery starts at **{standard.command_recovery_start}** in Battle I "
        f"and falls by **{standard.command_recovery_decrement}** each Battle:"
        in rules_text
    )
    recovery_series = ", ".join(
        str(standard.command_recovery_for_battle(battle))
        for battle in range(1, 6)
    ) + "..."
    assert f"**{recovery_series}**" in rules_text


def test_web_game_rules_summary_uses_snapshot_rule_metadata() -> None:
    play = text("web/play.html")
    script = text("web/play.js")
    api = text("src/longwar/web_api.py")

    assert "configured Command penalty for each unprotected Front lost" in play
    assert "ongoing Narratives" not in play

    assert '"rules": self.engine.rules.as_dict()' in api
    assert "state?.rules" in script
    for field in (
        "starting_command",
        "command_cap",
        "command_collapse_threshold",
        "lost_front_command_penalty",
        "command_recovery_floor",
        "ongoing_narrative_limit",
    ):
        assert f"rules.{field}" in script

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
    assert "WHEN BOTH PLAYERS HAVE PASSED" in page
    assert "BETWEEN BATTLES" in page
    assert "Hero" in page
    assert "max 1 Hero card from hand per Battle" in page
    assert "font-size: 3.1mm;" in css
    assert "page: battlefield-reference" in css


def test_balance_validation_covers_all_reference_decks() -> None:
    from longwar.reference_decks import DECK_CATALOG
    from tools.run_experiments import CANONICAL_DECK_PATHS

    canonical = set(CANONICAL_DECK_PATHS.values())
    catalogued = {
        f"decks/{entry['file']}"
        for entry in DECK_CATALOG
    }
    assert canonical == catalogued
    assert all((ROOT / path).is_file() for path in canonical)


def test_browser_runtime_uses_canonical_engine_composition() -> None:
    from tools.build_browser_runtime import (
        BROWSER_NATIVE_FILES,
        BROWSER_NATIVE_ROOTS,
        cython_include_closure,
    )

    assert "_fast_engine_core.pxi" in BROWSER_NATIVE_ROOTS
    assert set(BROWSER_NATIVE_FILES) == set(
        cython_include_closure(*BROWSER_NATIVE_ROOTS)
    )
    assert "_ismcts_core.pxi" not in BROWSER_NATIVE_FILES
    assert "_mccfr_core.pxi" not in BROWSER_NATIVE_FILES


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
    from longwar.reference_decks import DECK_CATALOG

    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    canonical = {card["id"] for card in cards["cards"]}
    covered: set[str] = set()
    for entry in DECK_CATALOG:
        data = json.loads(
            (ROOT / "decks" / entry["file"]).read_text(encoding="utf-8")
        )
        covered.update(data["cards"])

    assert canonical
    assert covered
    assert covered <= canonical


def test_mccfr_suite_builder_tracks_canonical_decks() -> None:
    from tools.build_mccfr_suite import PROFILES
    from tools.run_experiments import CANONICAL_DECK_PATHS

    profile_decks = {
        deck_path
        for _profile_id, _label, deck_path in PROFILES
    }
    assert profile_decks == set(CANONICAL_DECK_PATHS.values())


def test_web_card_renderers_use_only_canonical_card_types() -> None:
    for surface in ("web/cards.js", "web/playtest-kit.js", "web/play.js", "web/balance.js"):
        source = text(surface)
        assert 'subject: "force"' not in source
        assert 'link: "bond"' not in source
        assert 'plot: "narrative"' not in source
        assert ".veiled" not in source


def test_active_runtime_uses_canonical_card_vocabulary() -> None:
    effects = text("src/longwar/_fast_engine_effects.pxi")
    costs = text("src/longwar/_fast_engine_costs.pxi")
    heuristic = text("src/longwar/_heuristic_core.pxi")
    play_style = text("web/play.css")
    compiled_runtime = "\n".join(
        text(path)
        for path in (
            "src/longwar/_fast_constants.pxi",
            "src/longwar/_fast_engine_class.pxi",
            "src/longwar/_fast_engine_cards.pxi",
            "src/longwar/_fast_engine_effects.pxi",
            "src/longwar/_fast_engine_pending.pxi",
            "src/longwar/_fast_engine_hashing.pxi",
            "src/longwar/_fast_engine_actions.pxi",
            "src/longwar/_fast_engine_battleflow.pxi",
            "src/longwar/_fast_engine_resolution.pxi",
            "src/longwar/_fast_engine_state_io.pxi",
            "src/longwar/_fast_engine_strength.pxi",
            "src/longwar/_fast_engine_costs.pxi",
            "src/longwar/_heuristic_core.pxi",
        )
    )

    assert "_fe_remove_link" not in effects
    assert "_fe_recover_recent_link_fast" not in costs
    assert "needs_link" not in heuristic
    assert ".play-card.card-link" not in play_style
    assert ".play-card.card-bond" in play_style

    for legacy in (
        "ongoing_narrative_limit",
        "narrative_slot",
        "STORY_CHOICE_",
        "narrative_choice_kind",
        "strat_cancel_narrative",
        "_fe_pre_narrative_cancel",
        "_fe_compact_ongoing_stories",
        "_fe_discard_narrative_by_card",
        "recover_narrative_on_completion_name",
        "narrative_discard_count",
        "narrative_discard_gain_command",
        "strat_narrative_lock",
        "strat_global_narrative_lock",
        "_fe_clear_narrative_targets_at_slot",
        "_fe_narrative_locked",
        "CONSTRAINT_DISCARD_SOURCE_STORY",
    ):
        assert legacy not in compiled_runtime

    assert "ongoing_narrative_limit" in compiled_runtime
    assert "_fe_pre_narrative_cancel" in compiled_runtime
    assert "NARRATIVE_CHOICE_FRONT" in compiled_runtime


def test_progression_surfaces_do_not_restore_terminal_collapse_compatibility() -> None:
    progression = text("src/longwar/progression.py")
    dashboard = text("web/balance.js")
    active = progression + "\n" + dashboard

    for legacy in (
        "equal_low_continuations",
        "zero_zero_continuations",
        "zero_zero_recovered",
        "equal_low_streak_length",
        "first_equal_low_continuation_battle",
        "longest_equal_low_streak",
        "zero_vs_positive_collapses",
        "zero_command_start_battles",
        "censored_zero_command_matches",
        "both_zero_command_battle_starts",
        "zero_command_battle_starts",
    ):
        assert legacy not in active

    assert "simultaneous_collapse_draws" in progression
    assert "unequal_collapse_terminations" in progression
    assert "collapse_point_battle_starts" in progression
    assert "censored_at_collapse_point_matches" in progression


def test_cards_are_scan_first_and_all_current_copy_blocks_are_labeled() -> None:
    data = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    cards = data["cards"]
    assert cards
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
    assert "PASS ACTIVE" in page
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



def test_rulebook_markdown_and_sections_have_generated_wrappers() -> None:
    from tools.build_pages import group_rulebook_sections

    rules = text("rules/rulebook.md")
    builder = text("tools/build_pages.py")
    css = text("web/rules.css")
    rendered = markdown.markdown(
        rules,
        extensions=["extra", "sane_lists", "attr_list"],
    )
    rendered = group_rulebook_sections(rendered)

    assert "rulebook-opening" not in rules
    assert '"md_in_html"' not in builder
    assert "<strong>The Long War</strong>" in rendered
    assert "**The Long War**" not in rendered
    assert '<section class="rule-section">' in rendered
    assert ".rule-section" in css
    assert "break-inside: avoid-column;" in css
    assert "break-inside: auto;" in css


def test_balance_lab_hides_dynamic_evidence_from_other_rulesets() -> None:
    builder = text("tools/build_lab_report.py")
    script = text("web/balance.js")
    fingerprint = text("src/longwar/fingerprint.py")

    assert "current_game_fingerprint" in builder
    assert '"stale_evidence": sorted(stale_files)' in builder
    assert 'data.get("game_fingerprint") != game_fingerprint' in builder
    assert "Solver evidence needs a fresh run for this ruleset" in script
    assert '".pxi"' in fingerprint
