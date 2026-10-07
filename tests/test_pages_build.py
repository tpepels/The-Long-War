from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
from PIL import Image

from tools import build_pages, build_rulebook_pdf, check_card_layout


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


def test_shared_frame_art_is_resized_without_losing_transparency(tmp_path, monkeypatch):
    web = tmp_path / "web"
    frames = web / "art" / "card-frame"
    frames.mkdir(parents=True)
    card_art = web / "art" / "cards"
    card_art.mkdir()
    data = json.loads(build_pages.CARDS.read_text())
    data["cards"] = data["cards"][:1]
    cards = tmp_path / "cards.json"
    cards.write_text(json.dumps(data))
    Image.new("RGB", (8, 8), "white").save(card_art / (data["cards"][0]["id"] + ".png"))
    names = ("card-shell", "art-window", "title-divider", "command-seal")
    for name in names:
        image = Image.new("RGBA", (2000, 1000) if name == "card-shell" else (8, 8), (50, 80, 120, 255))
        image.putpixel((0, 0), (0, 0, 0, 0))
        image.putpixel((3, 3), (60, 90, 130, 128))
        image.save(frames / (name + ".png"))
    originals = {path.name: path.read_bytes() for path in frames.iterdir()}
    dist = tmp_path / "dist"
    dist.mkdir()
    css = dist / "physical-cards.css"
    css.write_text("\n".join([
        '.shell{background:url("art/card-frame/card-shell.png")}',
        ".window{background:url('art/card-frame/art-window.png')}",
        ".title{background:url(art/card-frame/title-divider.png)}",
        '.seal{background:url( "art/card-frame/command-seal.png" )}',
        '.other{background:url("art/other/card-shell.png")}',
        '.literal{content:"art/card-frame/card-shell.png"}',
    ]))
    monkeypatch.setattr(build_pages, "WEB", web)
    monkeypatch.setattr(build_pages, "DIST", dist)
    monkeypatch.setattr(build_pages, "CARDS", cards)

    build_pages.build_print_art()

    targets = dist / "art" / "card-frame"
    assert {path.name for path in targets.glob("*")} == {name + ".webp" for name in names}
    assert {path.name: path.read_bytes() for path in frames.iterdir()} == originals
    for name in names:
        with Image.open(targets / (name + ".webp")) as image:
            assert image.size == ((1134, 567) if name == "card-shell" else (8, 8))
            if name != "card-shell":
                assert image.getpixel((0, 0))[3] == 0
                assert image.getpixel((3, 3)) == (60, 90, 130, 128)
    assert not list(dist.rglob("*.png"))
    rewritten = css.read_text()
    for name in names:
        assert f"art/card-frame/{name}.webp" in rewritten
    assert 'url("art/other/card-shell.png")' in rewritten
    assert 'content:"art/card-frame/card-shell.png"' in rewritten


def test_frame_pixels_invalidate_static_version_and_css_image_urls(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    frames = dist / "art" / "card-frame"
    frames.mkdir(parents=True)
    asset = frames / "command-seal.webp"
    Image.new("RGBA", (8, 8), (50, 80, 120, 128)).save(asset, lossless=True)
    original_css = '.seal{background:url("art/card-frame/command-seal.webp")} .other{background:url("unrelated.png")}'
    original_html = '<link href="physical-cards.css?v=stale"><script src="physical-cards.js"></script>'
    css = dist / "physical-cards.css"
    page = dist / "cards.html"
    css.write_text(original_css)
    page.write_text(original_html)
    monkeypatch.setattr(build_pages, "DIST", dist)

    before = build_pages.version_static_assets()

    assert f'url("art/card-frame/command-seal.webp?v={before}")' in css.read_text()
    assert 'url("unrelated.png")' in css.read_text()
    assert f'href="physical-cards.css?v={before}"' in page.read_text()
    css.write_text(original_css)
    page.write_text(original_html)
    Image.new("RGBA", (8, 8), (150, 80, 120, 128)).save(asset, lossless=True)

    after = build_pages.version_static_assets()

    assert after != before
    assert f'url("art/card-frame/command-seal.webp?v={after}")' in css.read_text()


def test_frame_pixels_invalidate_source_archive_print_version(tmp_path, monkeypatch):
    source_root = build_pages.ROOT
    paths = [
        "rules/rulebook.md", "cards/cards.json", "cards/playtest-decks.json", "src/longwar/rules.py",
        "web/physical-cards.css", "web/physical-cards.js", "web/card-symbols.js", "web/rules.css",
        "web/style.css", "web/tokens.css", "web/playtest-kit.js", "web/cards.js",
        "web/site-nav.template.html", "web/playmat.html", "web/tokens.html",
    ]
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / name, target)
    frames = tmp_path / "web" / "art" / "card-frame"
    frames.mkdir(parents=True)
    for name in ("card-shell", "art-window", "title-divider", "command-seal"):
        Image.new("RGBA", (8, 8), (50, 80, 120, 128)).save(frames / (name + ".png"))
    monkeypatch.setattr(build_pages, "ROOT", tmp_path)
    monkeypatch.setattr(build_pages, "WEB", tmp_path / "web")
    monkeypatch.setattr(build_pages, "RULEBOOK", tmp_path / "rules/rulebook.md")
    monkeypatch.setattr(build_pages, "CARDS", tmp_path / "cards/cards.json")
    monkeypatch.setattr(build_pages, "PLAYTEST_DECKS", tmp_path / "cards/playtest-decks.json")
    monkeypatch.setattr(build_pages, "REFERENCE_DECKS", ())
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    def no_git(*args, **kwargs):
        raise OSError("Source archive has no Git metadata")

    monkeypatch.setattr(build_pages.subprocess, "check_output", no_git)
    before = build_pages.print_build_version()
    Image.new("RGBA", (8, 8), (150, 80, 120, 128)).save(frames / "command-seal.png")

    after = build_pages.print_build_version()

    assert before.startswith("local-") and after.startswith("local-")
    assert after != before


def test_site_publishes_versioned_frame_derivatives(built_site):
    css = (built_site / "physical-cards.css").read_text()
    page = (built_site / "cards.html").read_text()
    version = re.search(r'physical-cards\.css\?v=([a-f0-9]+)', page).group(1)
    expected_caps = {"card-shell": 1134, "art-window": 744, "title-divider": 640, "command-seal": 160}
    for name, max_px in expected_caps.items():
        source = build_pages.WEB / "art" / "card-frame" / (name + ".png")
        target = built_site / "art" / "card-frame" / (name + ".webp")
        assert source.is_file()
        assert not target.with_suffix(".png").exists()
        assert f"art/card-frame/{name}.webp?v={version}" in css
        assert f"art/card-frame/{name}.png" not in css
        with Image.open(source) as original, Image.open(target) as published:
            assert max(published.size) <= max_px
            if original.convert("RGBA").getchannel("A").getextrema()[0] < 255:
                assert "A" in published.getbands()
                assert published.getchannel("A").getextrema()[0] < 255


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


def test_rulebook_markdown_does_not_substitute_historical_battlefield_art():
    rendered = build_rulebook_pdf.markdown_to_typst("```\nBATTLE LINE\n```", "test")
    assert "assets/rulebook-battlefield.svg" not in rendered
    assert '#raw(block: true, "BATTLE LINE")' in rendered


def test_rulebook_images_use_authored_path_without_legacy_decoder():
    rendered = build_rulebook_pdf.markdown_to_typst("![Example](assets/example.jpg)", "test")
    assert '#image("assets/example.jpg"' in rendered
