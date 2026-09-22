from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_gameplay_is_bound_to_one_viewport_scene() -> None:
    css = text("web/play.css")
    assert "width: 100vw;" in css
    assert "height: 100dvh;" in css
    assert "body.game-body" in css
    assert "overflow: hidden;" in css
    assert "position: sticky" not in css


def test_gameplay_secondary_information_is_overlayed_not_document_flow() -> None:
    html = text("web/play.html")
    css = text("web/play.css")

    game_start = html.index('<section id="game"')
    game_end = html.index("</section>\n    </main>", game_start)
    tools_index = html.index('<aside class="game-tools"', game_start)

    assert game_start < tools_index < game_end
    assert ".game-tools {" in css
    assert "position: absolute;" in css
    assert "campaign-drawers" not in html


def test_table_and_hand_never_request_browser_scrollbars() -> None:
    css = text("web/play.css")
    assert ".digital-hand {" in css
    assert ".war-table {" in css
    assert "overflow-x: auto" not in css
    assert "scrollbar-width" not in css
    assert "grid-template-columns: 1fr;" not in css[css.index("/* Width-driven recomposition"):]


def test_game_layout_checker_covers_standard_desktop_sizes() -> None:
    checker = text("tools/check_game_layout.py")
    for viewport in ("1920, 1080", "1440, 900", "1366, 768", "1024, 768"):
        assert viewport in checker
    assert "root-scroll" in checker
    assert "hand-card-" in checker
    assert "shell-outside-viewport" in checker
