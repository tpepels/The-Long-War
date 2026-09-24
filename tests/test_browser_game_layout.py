from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_gameplay_is_bound_to_one_viewport_scene() -> None:
    css = text("web/play.css")
    compact = re.sub(r"\s+", "", css)
    assert "width:100%;" in compact
    assert "height:100dvh;" in compact
    assert "body.game-body" in css
    assert "overflow:hidden;" in compact
    assert "position:sticky" not in compact


def test_gameplay_secondary_information_uses_a_game_drawer() -> None:
    html = text("web/play.html")
    css = text("web/play.css")

    assert 'id="game-drawer"' in html
    for destination in ("menu", "rules", "log", "piles"):
        assert f'data-open-drawer="{destination}"' in html + text("web/play.js")
    assert "<details" not in html[html.index('id="game"'):]
    assert "game-masthead" not in html
    assert ".game-drawer" in css
    compact = re.sub(r"\s+", "", css)
    assert "position:fixed;" in compact or "position:absolute;" in compact


def test_table_and_hand_never_request_browser_scrollbars() -> None:
    css = text("web/play.css")
    assert ".digital-hand {" in css
    assert ".war-table {" in css
    assert "overflow-x: auto" not in css
    assert "--fan-x" in css
    assert "--fan-scale" in css


def test_game_layout_checker_covers_standard_desktop_sizes() -> None:
    checker = text("tools/check_game_layout.py")
    for viewport in ("1920, 1080", "1440, 900", "1366, 768", "1280, 720"):
        assert viewport in checker
    assert "root-scroll" in checker
    assert "hand-card-" in checker
    assert "shell-outside-viewport" in checker


def test_live_player_loads_canonical_engine_without_a_javascript_rules_copy() -> None:
    play = text("web/play.js")
    engine = text("web/browser-engine.mjs")
    build = text("tools/build_pages.py")

    assert 'BrowserSession' in play
    assert 'browser-engine.mjs' in play
    assert 'new Worker(' not in play
    assert 'initializeBrowserEngine()' in play
    assert 'longwar.web_api' in engine
    assert 'loadPyodide' in engine
    assert 'class BrowserEngine' not in engine
    assert 'class LightweightAgent' not in engine
    assert not (ROOT / "web" / "play-worker.js").exists()
    assert "python-bundle.json" not in build
    assert "version_static_assets" in build


def test_start_match_is_covered_by_real_browser_interaction_smoke() -> None:
    checker = text("tools/check_play_start.py")
    workflow = text(".github/workflows/ci.yml")
    play = text("web/play.js")

    assert "form.requestSubmit()" in checker
    assert 'confirm.click()' in checker
    assert '.play-card.playable[data-hand-card]' in checker
    assert '.digital-slot.targetable, .scheme-marker.targetable' in checker
    assert 'data-play-smoke="pass"' in checker
    assert '<button type="button" class="' in play
    assert "legal-target-cue" in play
    assert "check_browser_engine.mjs" in workflow
    assert "check_play_start.py --require-browser" in workflow


def test_start_overlay_obeys_hidden_attribute() -> None:
    css = text("web/play.css")
    checker = text("tools/check_play_start.py")

    compact = re.sub(r"\s+", "", css)
    assert ".game-body[hidden]{display:none!important;}" in compact
    assert 'getComputedStyle(setup).display !== "none"' in checker
    assert "start overlay remains visible after match start" in checker


def test_battlefield_has_minimum_visual_scale_and_public_card_inspection() -> None:
    css = text("web/play.css")
    play = text("web/play.js")
    html = text("web/play.html")
    checker = text("tools/check_game_layout.py")
    smoke = text("tools/check_play_start.py")

    assert "battlefield-too-small" in checker
    assert "board-title-" in checker and "-clipped" in checker
    assert "presentation_snapshots" in checker
    assert "qa-engine.mjs" in checker
    assert 'data-inspect-card="' in play
    assert "bindCardInspectors" in play
    assert "openCardInspector" in play
    assert 'id="card-inspector"' in html
    assert ".card-inspector .play-card" in css
    assert ".opponent-army [data-inspect-card]" in smoke
    assert "public battlefield card did not open inspector" in smoke


def test_first_playtest_ui_exposes_draw_paced_actions_and_term_help() -> None:
    html = text("web/play.html")
    play = text("web/play.js")
    css = text("web/play.css")
    engine = text("web/browser-engine.mjs")
    smoke = text("tools/check_play_start.py")

    assert 'id="draw-button"' in html
    assert 'id="action-banner"' in html
    assert 'id="term-hint"' in html
    assert "actionForDraw" in play
    assert "scheduleAiStep" in play
    assert 'type: "ai_step"' in play
    assert "TERM_HINTS" in play
    assert 'class="game-term"' in play
    assert "mulligan-confirm" in play
    assert "aiStep()" in engine
    assert '"needs_ai":' in text("src/longwar/web_api.py")
    assert ".action-banner" in css
    assert ".term-hint" in css
    assert ".draw-button" in css
    assert "human action did not produce a visible action banner" in smoke
    assert "opponent action was not shown before returning control" in smoke
    assert "openingAnnouncementShown" in play
    assert "+1 opening card" in play
    assert '"opening_player":' in text("src/longwar/web_api.py")


def test_desktop_fixtures_cover_crowded_and_interrupting_states() -> None:
    from tools.check_game_layout import SCENARIOS, presentation_snapshots

    assert set(SCENARIOS) == {"battle", "targeting", "inspector", "ai", "choose-first", "complete", "mulligan", "drawer"}
    snapshots = presentation_snapshots()
    crowded = snapshots["battle"]
    assert len(crowded["hand"]) >= 18
    assert all(slot["subject"] and slot["link"] and slot["name"] for side in crowded["board"] for slot in side)
    assert all(scheme["hidden"] and scheme["card_id"] is None for scheme in crowded["schemes"][1])
    assert crowded["stratagems"][1]["hidden"]
    assert crowded["stratagems"][1]["card_id"] is None
    assert snapshots["ai"]["needs_ai"]
    assert snapshots["choose-first"]["phase"] == "choose_first"
    assert snapshots["complete"]["winner"] == 0


def test_desktop_motion_respects_user_preference_and_exposes_visible_state() -> None:
    assert "prefers-reduced-motion" in text("web/play.css")
    play = text("web/play.js")
    assert "render_game_to_text" in play
    assert "advanceTime" in play
