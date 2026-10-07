from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from PIL import Image

from tools import build_pages, check_card_layout


@pytest.fixture(scope="module")
def built_site(tmp_path_factory):
    # The runtime has its own build/parity gate. Use an empty runtime here to
    # exercise real static publishing without compiling a wheel in unit tests.
    tmp_path = tmp_path_factory.mktemp("pages-build")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(build_pages, "ensure_browser_runtime", lambda: runtime)
        monkeypatch.setattr(build_pages, "DIST", tmp_path / "dist")
        build_pages.main()
        yield build_pages.DIST


def test_site_publishes_only_current_presentation_assets(built_site):
    files = {path.relative_to(built_site).as_posix() for path in built_site.rglob("*") if path.is_file()}
    assert not any("v2" in name or "candidates" in name or "previews" in name for name in files)
    # Font licenses travel with the fonts; design records do not ship.
    assert not any(name.endswith((".md", ".csv")) for name in files)
    assert all(name.startswith("fonts/") for name in files if name.endswith(".txt"))
    assert not (built_site / "art" / "cards").exists()
    assert (built_site / "data" / "playtest-decks.json").is_file()
    cards = json.loads(build_pages.CARDS.read_text())["cards"]
    for card in cards:
        source = build_pages.WEB / "art" / "cards" / (card["id"] + ".png")
        target = built_site / "art" / "cards-print" / (card["id"] + ".webp")
        assert source.is_file()
        with Image.open(target) as image:
            assert max(image.size) <= build_pages.PRINT_ART_MAX_PX


def test_physical_layout_check_uses_shared_renderer_without_page_controller():
    cards = json.loads(build_pages.CARDS.read_text())["cards"]
    document = check_card_layout.physical_layout_document(cards)
    assert "window.PhysicalCards.cardArticle(card)" in document
    assert "async function main()" not in document
    assert all(card["id"] in document for card in cards)


def test_public_navigation_is_built_from_one_fragment(built_site):
    fragment = (build_pages.WEB / "site-nav.template.html").read_text()
    links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', fragment)
    assert links == [
        ("play.html", "Webgame"), ("cards.html", "Cards"),
        ("playtest-kit.html", "Decks"), ("playmat.html", "Reference"),
        ("rulebook.html", "Rules"), ("balance.html", "Balance Lab"),
    ]
    for page in ("index.html", "cards.html", "playtest-kit.html", "playmat.html", "rulebook.html", "balance.html"):
        source_name = "rulebook.template.html" if page == "rulebook.html" else page
        assert "<!-- SITE_NAV -->" in (build_pages.WEB / source_name).read_text()
        source = (built_site / page).read_text()
        assert "<!-- SITE_NAV -->" not in source
        nav = re.search(r'<nav[^>]+aria-label="(?:Site|Resources)"[^>]*>(.*?)</nav>', source, re.S).group(1)
        assert re.findall(r'>([^<]+)</(?:a|span)>', nav) == [label for _, label in links]
        if page != "index.html":
            current = next(label for href, label in links if href == page)
            assert f'<span aria-current="page">{current}</span>' in nav
    assert not (built_site / "site-nav.template.html").exists()
