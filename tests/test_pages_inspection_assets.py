"""Guard the Pages inspection build against shipping broken Webgame JS."""

from tools import build_pages
from tools.check_web_static import _dist_reference_errors


def test_inspection_site_excludes_webgame_runtime_scripts(tmp_path, monkeypatch):
    web = tmp_path / "web"
    dist = tmp_path / "dist"
    web.mkdir()

    (web / "play.html").write_text(
        '<div id="battlefield"></div><script src="play.js"></script>',
        encoding="utf-8",
    )
    (web / "cards.html").write_text(
        '<script src="card-symbols.js"></script>', encoding="utf-8"
    )
    (web / "play.js").write_text(
        'document.getElementById("battlefield");', encoding="utf-8"
    )
    for filename in ("browser-engine.mjs", "remote-peer.mjs"):
        (web / filename).write_text("export const ready = true;", encoding="utf-8")
    (web / "card-symbols.js").write_text("const ok = true;", encoding="utf-8")
    (web / "art").mkdir()
    (web / "art" / "original.png").write_bytes(b"source-only")

    monkeypatch.setattr(build_pages, "WEB", web)
    monkeypatch.setattr(build_pages, "DIST", dist)
    build_pages.copy_web_sources(inspection_only=True)

    for filename in build_pages.WEBGAME_RUNTIME_SCRIPTS:
        assert (web / filename).is_file(), "Inspection must preserve authored code"
        assert not (dist / filename).exists(), f"{filename} is not deployable"

    assert (dist / "cards.html").is_file()
    assert (dist / "card-symbols.js").is_file()
    assert not (dist / "art").exists()

    # The actual build replaces the Webgame with a placeholder.
    (dist / "play.html").write_text(
        '<p>Webgame temporarily unavailable.</p>'
        '<a href="cards.html">Inspect cards</a>',
        encoding="utf-8",
    )
    assert _dist_reference_errors(dist) == []


def test_full_site_keeps_webgame_runtime_scripts(tmp_path, monkeypatch):
    web = tmp_path / "web"
    dist = tmp_path / "dist"
    web.mkdir()

    for filename in (*build_pages.WEBGAME_RUNTIME_SCRIPTS, "cards.html"):
        (web / filename).write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(build_pages, "WEB", web)
    monkeypatch.setattr(build_pages, "DIST", dist)
    build_pages.copy_web_sources(inspection_only=False)

    for filename in build_pages.WEBGAME_RUNTIME_SCRIPTS:
        assert (dist / filename).is_file()


def test_changed_card_art_changes_static_asset_version(tmp_path, monkeypatch):
    """A new source PNG generates a new WebP, and thus a new card URL version."""
    dist = tmp_path / "dist"
    art = dist / "art" / "cards-print"
    art.mkdir(parents=True)
    (dist / "physical-cards.js").write_text("const updated = true;")
    (dist / "cards.html").write_text(
        '<script src="physical-cards.js"></script>', encoding="utf-8"
    )
    (art / "arel.webp").write_bytes(b"first print artwork")
    monkeypatch.setattr(build_pages, "DIST", dist)

    initial = build_pages.version_static_assets()
    assert f'physical-cards.js?v={initial}' in (dist / "cards.html").read_text()

    # The card definitions, JS and CSS did not change: only the illustration.
    (art / "arel.webp").write_bytes(b"regenerated print artwork")
    changed = build_pages.version_static_assets()
    assert changed != initial
    page = (dist / "cards.html").read_text()
    assert f'physical-cards.js?v={changed}' in page
    assert f'physical-cards.js?v={initial}' not in page
