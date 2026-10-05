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


def test_rulebook_uses_manual_columns_and_playtest_summary() -> None:
    css = text("web/rules.css")
    rules = rendered_rulebook()
    from tools.build_pages import render_rule_tokens

    standard = GameRules.standard()
    playmat_source = render_rule_tokens(
        text("web/playmat.html"),
        standard,
    )
    playmat = playmat_source.lower()

    assert "column-count: 2;" in css
    assert "## The shape of the war {#learn}" in rules
    assert "Battle I: middle 2" in playmat_source
    assert "Battle II: add left outer" in playmat_source
    assert "Battle III+: all 4" in playmat_source
    assert playmat_source.count("Middle / Support") == 8
    assert f"take up to {standard.actions_per_turn} actions" in playmat
    assert "cycle (discard 2, draw 1)" in playmat
    assert "only when no legal action remains after your draw" in playmat
    assert "opponent takes one full closing turn" in playmat
    assert "the battlefield itself does not move or clear" in playmat
    assert "player who did not pass starts the next battle" in playmat
    assert "face-down" in playmat
    assert "identity hidden until revealed" in playmat
    assert f"lose {standard.lost_front_command_penalty} command per unprotected front lost" in playmat
    assert "collapse before recovery" in playmat

def test_rulebook_core_values_match_standard_engine() -> None:
    rules_text = rendered_rulebook()
    standard = GameRules.standard()

    assert FRONT_COUNT == 4
    assert f"draw **{standard.opening_hand_size} cards**" in rules_text
    assert f"Each player begins with **{standard.starting_command} Command**" in rules_text
    assert f"at most **{standard.ongoing_narrative_limit} Ongoing Narratives**" in rules_text
    assert "Take **up to 2 Actions**" in rules_text
    assert "A **Maneuver** is an Action" in rules_text
    assert f"A Maneuver costs **{standard.maneuver_command_cost} Command**." in rules_text
    assert "**Pass is a turn, not an Action.**" in rules_text
    assert "You may end your turn after zero, one, or two Actions." in rules_text
    assert "player who **did not Pass** starts the next Battle" in rules_text
    assert "Winning or losing a Front does **not** move, Retreat, or discard any battlefield cards." in rules_text
    assert f"Lose **{standard.lost_front_command_penalty} Command for each Front you lost**" in rules_text
    assert "Check for Command Collapse before anyone recovers Command." in rules_text
    assert "at most **4 copies** of any non-Unique title" in rules_text
    assert "There is no required minimum number of Forces or printed Names." in rules_text

    effective_recovery = [
        max(
            standard.command_recovery_floor,
            standard.command_recovery_for_battle(battle),
        )
        for battle in range(1, 7)
    ]
    assert effective_recovery == [12, 9, 6, 3, 1, 1]

def test_canonical_card_copy_and_design_schema_use_actions_not_operations() -> None:
    payload = json.loads(text("cards/cards.json"))
    for card in payload["cards"]:
        visible = [str(card.get("text", ""))]
        for block in card.get("rule_blocks", []):
            visible.extend([str(block.get("label", "")), str(block.get("text", ""))])
        assert "operation" not in " ".join(visible).lower(), card["id"]
        assert "operation" not in json.dumps(card.get("design_rules", {})).lower(), card["id"]

    protocol = text("src/longwar/protocol.py")
    assert "NEXT_ACTION_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE" in protocol
    assert "NEXT_OPERATION_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE" not in protocol


def test_web_game_rules_summary_uses_snapshot_rule_metadata() -> None:
    play = text("web/play.html")
    script = text("web/play.js")
    api = text("src/longwar/web_api.py")

    assert "take up to 2 Actions" in play
    assert "Cycle by discarding 2 cards and drawing 1" in play
    assert "Pass is not an Action" in play
    assert "Stratagems are set face-down" in play
    assert "The battlefield persists" in play
    assert "did not Pass start" in play

    assert '"rules": self.engine.rules.as_dict()' in api
    assert '"active_front_mask": active_front_mask' in api
    assert '"actions_this_turn": state.actions_this_turn' in api
    assert '"closing_turns_remaining": state.closing_turns_remaining' in api
    assert 'result.get("kind") == "PlayStratagem"' in api
    assert "EndTurn" in api

    assert "ACTION_KIND.END_TURN" in script
    assert "actionForTurnEnd" in script
    assert "Face-down Stratagem" in script
    assert "Battle I uses the two middle Fronts" in script
    assert "Pass appears only when no legal Action remains" in script

def test_rulebook_roles_are_labels_not_hidden_rules() -> None:
    rules = text("rules/rulebook.md")
    assert "They have no rule of their own unless a card refers to them." in rules

def test_battlefield_reference_is_one_readable_practical_sheet() -> None:
    from tools.build_pages import render_rule_tokens

    standard = GameRules.standard()
    page = render_rule_tokens(text("web/playmat.html"), standard)
    css = text("web/rules.css")

    assert "reference-v3" in page
    assert "Battlefield & turn order" in page
    assert "Active Fronts" in page
    assert "YOUR TURN" in page
    assert f"take up to {standard.actions_per_turn} Actions" in page
    assert "end your turn early" in page
    assert "AFTER THE TWO CLOSING TURNS" in page
    assert "The battlefield itself does not move or clear." in page
    assert "face-down" in page
    assert "identity hidden until revealed" in page
    assert (
        f"Play at most {standard.hero_force_play_limit_per_battle} Hero as Force "
        f"and {standard.hero_name_play_limit_per_battle} Hero as Name"
        in page
    )
    assert "the player who did not Pass starts" in page
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
    assert "_ismcts_core.pxi" in BROWSER_NATIVE_FILES
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
        assert 'plot: "story"' not in source
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
    assert ".board-attachment.link" not in play_style
    assert ".board-attachment.bond" in play_style

    for legacy in (
        "ongoing_story_limit",
        "story_slot",
        "STORY_CHOICE_",
        "story_choice_kind",
        "strat_cancel_story",
        "_fe_pre_story_cancel",
        "_fe_compact_ongoing_stories",
        "_fe_discard_story_by_card",
        "recover_story_on_completion_name",
        "story_discard_count",
        "story_discard_gain_command",
        "strat_story_lock",
        "strat_global_story_lock",
        "_fe_clear_story_targets_at_slot",
        "_fe_story_locked",
        "CONSTRAINT_DISCARD_SOURCE_STORY",
    ):
        assert legacy not in compiled_runtime

    assert "ongoing_narrative_limit" in compiled_runtime
    assert "_fe_pre_narrative_cancel" in compiled_runtime
    assert "NARRATIVE_CHOICE_FRONT" in compiled_runtime


def test_story_schema_is_fully_removed_from_active_surfaces() -> None:
    active_paths = (
        "cards/cards.json",
        "src/longwar/cards.py",
        "src/longwar/game/model.py",
        "src/longwar/game/actions.py",
        "src/longwar/game/engine.py",
        "src/longwar/web_api.py",
        "src/longwar/_fast_engine_cards.pxi",
        "src/longwar/_fast_engine_state_io.pxi",
        "web/play.js",
        "web/play.css",
        "web/style.css",
        "web/print-cards.js",
        "web/print-cards.css",
        "web/balance.js",
        "web/balance.html",
    )
    active = "\n".join(text(path) for path in active_paths)

    for legacy in (
        '"story"',
        "'story'",
        "StoryState",
        "PlayStory",
        ".stories",
        '"stories"',
        "'stories'",
        "story:",
        "story_form",
        "story_limit",
        "discard_source_story",
        "card-story",
        "first_story_each_battle_discount_1_min_1",
        "return_one_story_from_discard_to_hand",
    ):
        assert legacy not in active

    assert '"narrative"' in text("cards/cards.json")
    assert "NarrativeState" in active
    assert "PlayNarrative" in active
    assert ".narratives" in active
    assert "narrative:" in active
    assert "card-narrative" in active


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

    assert "simultaneous_collapse_terminations" in progression
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
    assert "ACTION" in page and "1 / 2" in page
    assert "PASSER" in page and "CLOSING" in page
    assert "PASS ACTIVE" not in page
    assert "STRATAGEM USED" in page
    assert page.count("FORCE USED") == 2
    assert page.count("NAME USED") == 2
    assert "Stratagem identities are hidden" in page
    assert "face-down until its own trigger reveals it" in page
    assert "Battle I: middle two" in page
    assert "Battle II: add left outer" in page
    assert "Battle III+: all four" in page
    for modifier in ("+1", "+2", "+3", "-1", "-2", "-3"):
        assert modifier in page
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


def test_historical_design_reports_cannot_masquerade_as_current_rules() -> None:
    first80 = text("cards/first-80-design.md")
    audit = text("cards/first-80-balance-audit.md")
    pass_report = text("reports/pass-rule-experiments.md")
    force_report = text("reports/force-availability-draw-candidate.md")

    assert "**Historical design record.**" in first80
    assert "Do not promote those statements back into the engine" in first80

    assert "Status: **historical audit**" in audit
    assert "Those quotas are superseded." in audit
    assert "no Force or printed-Name minimum" in audit

    assert "later superseded by the 2026-10-04 overhaul" in pass_report
    assert "permanent Pass is canonical" not in pass_report

    assert "At the time of this experiment" in force_report
    assert "Current runtime vocabulary uses **Force**." in force_report


def test_balance_lab_has_no_parallel_engine_sync_status_channel() -> None:
    page = text("web/balance.html")
    script = text("web/balance.js")
    canonical_cards = text("cards/cards.json")

    assert "mechanics_pending" not in page
    assert "engine_sync" not in script
    assert "mechanics_pending_cards" not in script
    assert '"engine_sync"' not in canonical_cards
