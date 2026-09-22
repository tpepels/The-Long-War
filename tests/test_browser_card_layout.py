from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_browser_hand_cards_use_one_fixed_internal_geometry() -> None:
    css = text("web/play.css")
    assert "flex: 0 0 204px;" in css
    assert "width: 204px;" in css
    assert "height: 286px;" in css
    assert "grid-template-rows: 22px 54px 16px 42px 124px 24px;" in css
    assert "card-density-" not in css


def test_print_cards_use_six_fixed_internal_zones() -> None:
    css = text("web/style.css")
    assert "grid-template-rows: 7mm 15mm 6mm 17mm minmax(0, 1fr) 6.5mm;" in css

    for renderer in ("web/cards.js", "web/playtest-kit.js"):
        source = text(renderer)
        assert 'class="card-meta"' in source
        assert 'class="card-title"' in source
        assert 'class="card-properties"' in source
        assert 'class="card-rule"' in source
        assert 'class="card-footer"' in source


def test_semantic_rule_renderer_is_shared_by_all_card_surfaces() -> None:
    helper = text("web/card-rules.js")
    assert "rule-block rule-" in helper
    assert "card.rule_blocks" in helper

    for page in ("web/play.html", "web/cards.html", "web/playtest-kit.html"):
        assert "card-rules.js" in text(page)


def test_browser_cards_always_reserve_the_properties_row() -> None:
    js = text("web/play.js")
    assert '<div class="play-card-properties">' in js
    assert "propertyMarkup" in js
    assert "data-card-id=" in js


def test_card_pages_load_runtime_overflow_guard() -> None:
    for page in ("web/play.html", "web/cards.html", "web/playtest-kit.html"):
        assert "card-layout-guard.js" in text(page)

    guard = text("web/card-layout-guard.js")
    assert "scrollHeight > element.clientHeight" in guard
    assert "scrollWidth > element.clientWidth" in guard
    assert "layout-overflow" in guard
    assert "-overlap" in guard
    assert "-outside" in guard


def test_stale_build_legends_copy_is_gone() -> None:
    for path in (
        "web/play.html",
        "web/play.js",
        "web/index.html",
        "rules/rulebook.md",
    ):
        assert "Build Legends" not in text(path)
