from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_browser_hand_cards_use_one_fixed_internal_geometry() -> None:
    css = text("web/play.css")
    assert "flex: 0 0 204px;" in css
    assert "width: 204px;" in css
    assert "height: 286px;" in css
    assert "grid-template-rows: 20px 48px 30px 160px 24px;" in css
    assert "scale(var(--inspect-scale));" in css
    assert "card-density-" not in css


def test_print_pages_load_the_shared_v2_renderer_and_styles() -> None:
    for page, renderer in (
        ("web/cards.html", "cards.js"),
        ("web/playtest-kit.html", "playtest-kit.js"),
    ):
        source = text(page)
        assert 'href="cards-v2.css' in source
        assert source.index('src="v2-heraldry.js') < source.index('src="cards-v2.js')
        assert source.index('src="cards-v2.js') < source.index(f'src="{renderer}')
        assert "V2Cards.cardArticle" in text("web/" + renderer)
        assert "print-cards.css" not in source
        assert "print-cards.js" not in source
    assert not (ROOT / "web" / "print-cards.css").exists()
    assert not (ROOT / "web" / "print-cards.js").exists()


class RenderedCard(HTMLParser):
    """Collect decoded text and structure without introducing a DOM dependency."""

    def __init__(self, markup: str) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[dict] = []
        self.stack: list[dict] = []
        self.feed(markup)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = {
            "tag": tag,
            "attrs": dict(attrs),
            "text": "",
            "ancestors": self.stack.copy(),
        }
        self.elements.append(element)
        if tag not in {"br", "hr", "img", "input", "meta", "link"}:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            assert self.stack[-1]["tag"] == tag
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        for element in self.stack:
            element["text"] += data

    def all(self, class_name: str) -> list[dict]:
        return [
            element
            for element in self.elements
            if class_name in element["attrs"].get("class", "").split()
        ]

    def one(self, class_name: str) -> dict:
        elements = self.all(class_name)
        assert len(elements) == 1, (class_name, elements)
        return elements[0]


def v2_effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [
            *card.get("modes", {}).get("force", {}).get("effects", []),
            *card.get("modes", {}).get("name", {}).get("effects", []),
        ]
    return card.get("effects", [])


def render_print_cards(cards: list[dict]) -> list[RenderedCard]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the shared V2 renderer")
    script = """
const fs = require("node:fs");
global.window = {};
eval(fs.readFileSync("web/v2-heraldry.js", "utf8"));
eval(fs.readFileSync("web/cards-v2.js", "utf8"));
const input = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(input.cards.map(card => window.V2Cards.cardArticle(card, "print-card"))));
"""
    result = subprocess.run(
        [node, "-e", script],
        input=json.dumps({"cards": cards}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [RenderedCard(markup) for markup in json.loads(result.stdout)]


def test_print_renderer_preserves_current_v2_content_and_modes() -> None:
    cards = json.loads(text("cards/cards.json"))["cards"]
    rendered = render_print_cards(cards)
    for card, output in zip(cards, rendered, strict=True):
        assert output.one("v2-card")["attrs"]["data-card-id"] == card["id"]
        assert output.one("card-title")["text"] == card["title"]
        assert output.one("footer-id")["text"] == card["id"]
        assert output.one("footer-version")["text"] == "vdev"
        assert bool(output.one("footer-mark")["text"].strip()) == bool(card.get("unique"))
        assert [node["text"] for node in output.all("effect-text")] == [
            effect["text"] for effect in v2_effects(card)
        ]
        formation = card["type"] in {"force", "bond", "name", "hero"}
        assert bool(output.all("stack-edge")) is formation
        assert bool(output.all("event-crown")) is (not formation)
        if card["type"] == "hero":
            headings = [node["text"].strip() for node in output.all("mode-heading")]
            assert headings[0].endswith("Force")
            assert headings[1].endswith("Name")
        assert output.one("cost-gem")["text"] == str(card["command_cost"])


def test_shared_renderer_escapes_hostile_text_and_preserves_numeric_values() -> None:
    hostile = '<img src=x onerror="bad()"> & </script>'
    cards = [
        {
            "id": hostile, "title": hostile, "type": "force", "strength": -1,
            "command_cost": 0, "classes": ["human"], "unique": True,
            "effects": [{"timing": "action", "text": "Strength " + hostile}],
        },
        {
            "id": "zero-hero", "title": "Zero Hero", "type": "hero",
            "force_strength": 0, "name_strength_modifier": -2, "command_cost": 0,
            "classes": ["human"], "unique": False,
            "modes": {"force": {"effects": []}, "name": {"effects": []}},
        },
    ]
    first, hero = render_print_cards(cards)
    assert first.one("card-title")["text"] == hostile
    assert first.one("v2-card")["attrs"]["data-card-id"] == hostile
    assert first.one("effect-text")["text"] == "Strength " + hostile
    assert not any(element["tag"] in {"img", "script"} for element in first.elements)
    assert first.one("cost-gem")["text"] == "0"
    assert first.one("strength-mark")["text"].strip().endswith("-1")
    hero_stats = [value["text"].strip() for value in hero.all("hero-stat")]
    assert hero_stats[0].endswith("0")
    assert hero_stats[1].endswith("-2")
    assert hero.one("cost-gem")["text"] == "0"


def test_playtest_kit_uses_current_v2_decks_and_expands_copies() -> None:
    decks = json.loads(text("cards/v2/playtest-decks.json"))["decks"]
    script = text("web/playtest-kit.js")
    html = text("web/playtest-kit.html")
    css = text("web/cards-v2.css")
    assert 'id="mechanics-reference"' in html
    assert "position_vocabulary" in script
    assert "MOVE UP TO N" in script
    assert "SWAP" in script
    assert "MOVES / MOVED" in script
    assert "ROW RESTRICTIONS" in script
    assert "OUTMATCHED" in script
    assert "TIRELESS" in script
    assert "EXHAUSTION" in script
    assert "COMMAND MODIFIERS" in script
    assert "TAX MARKERS" in script
    assert "TEMPORARY NEGATIVE" in script
    assert ".mechanics-reference" in css
    page = text("web/playtest-kit.html")
    assert decks
    assert 'data/cards.json' in script
    assert 'data/v2-playtest-decks.json' in script
    assert "function expandDeck(deck)" in script
    assert "window.V2Cards.cardArticle" in script
    assert "chunk(expanded,8)" in script
    assert "Print all decks" in page
    assert "chunk(cards,8)" in text("web/cards.js")
    assert 'class="print-sheet card-sheet"' in text("web/cards.js")


def test_print_card_sheets_fit_eight_68x96_cards_on_a4_landscape() -> None:
    css = text("web/cards-v2.css")
    assert "@page v2cards{size:A4 landscape;margin:9mm 12.5mm}" in css
    assert "width:272mm;height:192mm" in css
    assert "grid-template-columns:repeat(4,68mm)" in css
    assert "grid-template-rows:repeat(2,96mm)" in css
    assert "gap:0" in css
    assert "break-after:page" in css
    assert 4 * 68 == 272
    assert 2 * 96 == 192
    assert 272 == 297 - 2 * 12.5
    assert 192 == 210 - 2 * 9
    assert ".print-card{border-radius:0}" in css
    assert ".print-card::before{border-radius:0}" in css


def test_physical_print_surfaces_share_v2_renderer_while_browser_play_stays_separate() -> None:
    assert "card-rules.js" in text("web/play.html")
    for page in ("web/cards.html", "web/playtest-kit.html"):
        source = text(page)
        assert "cards-v2.js" in source
        assert "v2-heraldry.js" in source
        assert "card-rules.js" not in source
    assert "V2Cards?.inspect" in text("web/cards.js")
    assert "V2Cards?.inspect" in text("web/playtest-kit.js")


def test_browser_cards_always_reserve_the_properties_row() -> None:
    js = text("web/play.js")
    assert '<div class="play-card-properties">' in js
    assert "propertyMarkup" in js
    assert "data-card-id=" in js


def test_runtime_overflow_checks_match_each_surface() -> None:
    assert "card-layout-guard.js" in text("web/play.html")
    assert "card-layout-guard.js" not in text("web/cards.html")
    assert "card-layout-guard.js" not in text("web/playtest-kit.html")
    guard = text("web/card-layout-guard.js")
    assert "scrollHeight > element.clientHeight" in guard
    assert "layout-overflow" in guard
    assert "function inspect(root=document)" in text("web/cards-v2.js")


def test_print_build_version_is_stamped_everywhere() -> None:
    builder = text("tools/build_pages.py")
    renderer = text("web/cards-v2.js")
    card_css = text("web/cards-v2.css")
    site_css = text("web/style.css")
    assert "GITHUB_SHA" in builder
    assert "PRINTABLE_PAGES" in builder
    assert 'name="lw-build-version"' in builder
    assert 'class="print-version"' in builder
    for page in ("cards.html", "playtest-kit.html", "rulebook.html", "playmat.html", "tokens.html"):
        assert f'"{page}"' in builder
    assert 'meta[name="lw-build-version"]' in renderer
    assert "footer-version" in renderer
    assert ".print-version" in card_css
    assert ".print-version" in site_css


def test_rulebook_print_is_typst_and_separate_from_web_layout() -> None:
    page_builder = text("tools/build_pages.py")
    pdf_builder = text("tools/build_rulebook_pdf.py")
    template = text("web/rulebook.template.html")

    assert 'TYPST_SOURCE = DIST / "rulebook.typ"' in pdf_builder
    assert 'OUTPUT = DIST / "rulebook.pdf"' in pdf_builder
    assert "#columns(2, gutter: 9mm)[" in pdf_builder
    assert "PdfReader" in pdf_builder
    assert "TLW print v" in pdf_builder
    assert "build_rulebook_print_pages" not in page_builder
    assert "{{RULEBOOK_PRINT}}" not in template
    assert "rulebook-print-shell" not in template
    assert 'href="rulebook.pdf?v={{PRINT_VERSION}}"' in template


def test_rulebook_uses_generated_pdf_for_printing() -> None:
    pyproject = text("pyproject.toml")
    workflow = text(".github/workflows/pages.yml")
    template = text("web/rulebook.template.html")
    generator = text("tools/build_rulebook_pdf.py")

    assert "WeasyPrint" not in pyproject
    assert "pypdf" in pyproject
    assert "typst-community/setup-typst@v5" in workflow
    assert "typst-version: 0.15.1" in workflow
    assert "python tools/build_rulebook_pdf.py" in workflow
    assert 'href="rulebook.pdf?v={{PRINT_VERSION}}"' in template
    assert "window.print()" not in template
    assert 'OUTPUT = DIST / "rulebook.pdf"' in generator
    assert '"compile"' in generator
    assert "MAX_PAGES = 6" in generator
    assert "2 <= len(reader.pages) <= MAX_PAGES" in generator
    assert "blank or nearly blank" in generator

def test_stale_build_legends_copy_is_gone() -> None:
    for path in (
        "web/play.html",
        "web/play.js",
        "web/index.html",
        "rules/rulebook.md",
    ):
        assert "Build Legends" not in text(path)


def test_play_client_loads_published_reference_deck_catalog() -> None:
    script = text("web/play.js")
    assert 'data/reference-decks.json' in script
    assert 'data/reference-deck.json' not in script
    assert "deckCatalog.decks?.[0]" in script
    assert '"Game failed to load"' in script


def test_remote_peer_transport_is_rule_free_webrtc_token_exchange() -> None:
    source = text("web/remote-peer.mjs")
    assert "RTCPeerConnection" in source
    assert 'createDataChannel("the-long-war"' in source
    assert "inviteToken" in source
    assert "answerToken" in source
    assert "...endpoint" not in source
    assert source.count("return endpoint;") == 2
    assert "get connected()" in source
    assert "longwar." not in source
    assert "cards" not in source
    assert "legal_actions" not in source


def test_play_setup_exposes_remote_host_and_join_token_controls() -> None:
    page = text("web/play.html")
    style = text("web/play.css")
    assert 'value="remote-host"' in page
    assert 'value="remote-join"' in page
    assert 'id="remote-input"' in page
    assert 'id="remote-output"' in page
    assert 'id="remote-copy-token"' in page
    assert 'id="remote-reset"' in page
    assert "Direct WebRTC uses STUN" in page
    assert ".remote-connect" in style
    assert "#remote-reset" in style


def test_remote_play_routes_actions_through_host_authoritative_session() -> None:
    script = text("web/play.js")
    assert "mode: GAME_MODE.REMOTE" in script
    assert "session.act(command.key, 1)" in script
    assert "session.mulligan(command.indices || [], 1)" in script
    assert "session.view(0)" in script
    assert "session.view(1)" in script
    assert "type: REMOTE_MESSAGE_TYPE.SNAPSHOT" in script
    assert "createRemoteHost" in script
    assert "createRemoteGuest" in script


def test_pages_cache_busts_remote_peer_module() -> None:
    builder = text("tools/build_pages.py")
    assert '("browser-engine.mjs", "remote-peer.mjs")' in builder


def test_browser_verify_checks_all_authored_and_built_static_assets() -> None:
    makefile = text("Makefile")
    workflow = text(".github/workflows/pages.yml")
    checker = text("tools/check_web_static.py")

    assert "$(PYTHON) tools/check_web_static.py" in makefile
    assert "$(PYTHON) tools/check_web_static.py --dist dist" in makefile
    assert "python tools/check_web_static.py" in workflow
    assert "python tools/check_web_static.py --dist dist" in workflow
    assert '"--check", "--input-type=module"' in checker
    assert "DATA_REF_RE" in checker
    assert "requests missing built data asset" in checker


def test_web_static_checker_catches_missing_built_data_reference(tmp_path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_web_static",
        ROOT / "tools" / "check_web_static.py",
    )
    assert spec and spec.loader
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "play.js").write_text(
        'fetch(dataUrl("data/reference-deck.json"));',
        encoding="utf-8",
    )

    errors = checker._dist_reference_errors(dist)
    assert any(
        "data/reference-deck.json" in error
        and "missing built data asset" in error
        for error in errors
    )


def test_web_static_checker_catches_missing_play_dom_id(tmp_path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_web_static_dom",
        ROOT / "tools" / "check_web_static.py",
    )
    assert spec and spec.loader
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    web = tmp_path / "web"
    web.mkdir()
    (web / "play.html").write_text('<div id="present"></div>', encoding="utf-8")
    (web / "play.js").write_text(
        '$("present"); $("missing");',
        encoding="utf-8",
    )

    errors = checker._play_dom_errors(web)
    assert errors == ["web/play.js references missing DOM id #missing"]


def test_browser_hand_uses_available_width_at_readable_resting_scale() -> None:
    script = text("web/play.js")
    style = text("web/play.css")

    assert "Math.min(.9, Math.max(.5" in script
    assert "150 * scale" in script
    assert "hand.clientWidth - 204 * scale - 24" in script
    assert "padding: 0 clamp(14px, 2vw, 30px);" in style
    assert "--inspect-scale: 1.15;" in style


def test_remote_invite_creation_has_visible_progress_and_errors() -> None:
    script = text("web/play.js")
    peer = text("web/remote-peer.mjs")
    style = text("web/play.css")

    assert 'remoteStatus("Creating invite…")' in script
    assert "remoteSetupPhase = REMOTE_SETUP_PHASE.CREATING" in script
    assert "remoteSetupPhase === REMOTE_SETUP_PHASE.CREATING" in script
    assert "setupMode === PLAY_SETUP_MODE.REMOTE_HOST" in script
    assert "setupMode === PLAY_SETUP_MODE.REMOTE_JOIN" in script
    assert 'remoteStatus(error?.message || "Remote connection failed.", true)' in script
    assert "timeoutMs = 10000" in peer
    assert "Could not finish gathering network candidates" in peer
    assert 'typeof RTCPeerConnection === "undefined"' in peer
    assert "armRemoteConnectTimeout" in script
    assert '"remote-reset"' in script
    assert "Direct connection failed" in script
    assert "#remote-status.remote-error" in style


def test_battle_resolution_banner_uses_rules_active_front_count() -> None:
    script = text("web/play.js")
    assert '"Four Fronts resolved"' not in script
    assert "renderedState.active_fronts?.length" in script
    assert '" Front resolved"' in script
    assert '" Fronts resolved"' in script


def test_public_navigation_has_only_six_surfaces() -> None:
    index = text("web/index.html")
    labels = ("Webgame", "Cards", "Decks", "Reference", "Rules", "Balance Lab")
    for label in labels:
        assert f">{label}</a>" in index
    assert "V2 card lab" not in index
    assert "V2 Force style lab" not in index
    assert "Physical markers" not in index
    assert "Print playtest kit" not in index
    assert 'href="cards.html">Cards</a>' in index
    assert 'href="playtest-kit.html">Decks</a>' in index
    assert 'href="playmat.html">Reference</a>' in index
