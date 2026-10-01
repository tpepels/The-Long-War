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


def test_print_pages_load_the_shared_renderer_and_styles() -> None:
    for page, renderer in (
        ("web/cards.html", "cards.js"),
        ("web/playtest-kit.html", "playtest-kit.js"),
    ):
        source = text(page)
        assert 'href="print-cards.css"' in source
        assert source.index('src="card-rules.js"') < source.index('src="print-cards.js"')
        assert source.index('src="print-cards.js"') < source.index(f'src="{renderer}"')
        assert "PrintCards.markup(" in text("web/" + renderer)


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


def render_print_cards(cards: list[dict], deck_label: str | None = None) -> list[RenderedCard]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the shared print renderer")
    script = """
const fs = require("node:fs");
global.window = {};
eval(fs.readFileSync("web/card-rules.js", "utf8"));
eval(fs.readFileSync("web/print-cards.js", "utf8"));
const input = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(input.cards.map(card => window.PrintCards.markup(card, input.deckLabel))));
"""
    result = subprocess.run(
        [node, "-e", script],
        input=json.dumps({"cards": cards, "deckLabel": deck_label}),
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [RenderedCard(markup) for markup in json.loads(result.stdout)]


def test_print_renderer_preserves_catalogue_content_and_hero_modes() -> None:
    cards = json.loads(text("cards/cards.json"))["cards"]
    rendered = render_print_cards(cards)
    for card, output in zip(cards, rendered, strict=True):
        assert output.one("game-card")["attrs"]["data-card-id"] == card["id"]
        assert output.one("card-title")["text"] == card["title"]
        assert output.one("card-id")["text"] == card["id"]
        assert output.one("card-version")["text"] == "vdev"
        assert bool(output.all("unique")) == bool(card.get("unique"))
        properties = output.one("card-properties")["text"].lower()
        for value in card.get("classes", []):
            if value != "hero":
                assert value.replace("-", " ").replace("_", " ") in properties
        if card["type"] == "force" and card.get("role"):
            assert output.one("card-role")["text"].lower() == card["role"].replace("-", " ").replace("_", " ")
        region_classes = ["card-meta", "card-title"]
        if card.get("hero") or isinstance(card.get("strength"), int):
            region_classes.append("card-stats")
        region_classes.extend(["card-properties", "card-rule", "card-footer"])
        regions = [output.one(name) for name in region_classes]
        assert [output.elements.index(region) for region in regions] == sorted(
            output.elements.index(region) for region in regions
        )
        for block, rendered_block in zip(card["rule_blocks"], output.all("rule-block"), strict=bool(card["rule_blocks"])):
            assert block["text"].replace("*", "") in rendered_block["text"]
            assert block["label"] in rendered_block["text"]
        if card.get("hero"):
            modes = output.all("hero-mode")
            assert len(modes) == 2
            assert "Force" in modes[0]["text"]
            assert "Name" in modes[1]["text"]
            values = output.all("stat-value")
            for mode, expected in zip(modes, (card["strength"], card["hero_name_strength"]), strict=True):
                assert [value["text"] for value in values if mode in value["ancestors"]] == [str(expected)]
        elif isinstance(card.get("strength"), int):
            assert output.one("card-stats") in output.one("strength")["ancestors"]
            assert output.one("strength")["text"] == str(card["strength"])
        else:
            assert not output.all("strength")
        if isinstance(card.get("command_cost"), int):
            assert output.one("card-meta") in output.one("command-cost")["ancestors"]
            assert output.one("command-cost") in output.one("command-seal")["ancestors"]
            assert re.findall(r"-?\d+", output.one("command-cost")["text"]) == [str(card["command_cost"])]
        else:
            assert not output.all("command-cost")
        if not card["rule_blocks"] and not card.get("text"):
            assert not output.all("rule-block")
            assert "No special rules" not in output.one("card-rule")["text"]


def test_print_renderer_keeps_zero_negative_values_and_escapes_content() -> None:
    hostile = '<img src=x onerror="bad()"> & </script>'
    cards = [
        {
            "id": hostile, "title": hostile, "type": "force", "strength": -1,
            "command_cost": 0, "role": "swordsman", "classes": ["human"],
            "unique": True,
            "rule_blocks": [{"kind": "effect", "label": hostile, "text": "**Strength** " + hostile}],
        },
        {
            "id": "zero-hero", "title": "Zero Hero", "type": "force", "hero": True,
            "strength": 0, "hero_name_strength": -2, "command_cost": 0,
            "classes": ["hero"], "rule_blocks": [],
        },
    ]
    deck_label = "Deck " + hostile
    first, hero = render_print_cards(cards, deck_label)
    assert first.one("card-title")["text"] == hostile
    assert first.one("game-card")["attrs"]["data-card-id"] == hostile
    assert first.one("card-id")["text"] == deck_label
    assert first.one("rule-label")["text"] == hostile
    assert first.one("rule-text")["text"] == "Strength " + hostile
    assert deck_label in first.one("card-footer")["text"]
    assert not any(element["tag"] in {"img", "script"} for element in first.elements)
    assert re.findall(r"-?\d+", first.one("command-cost")["text"]) == ["0"]
    assert first.one("strength")["text"] == "-1"
    assert [value["text"] for value in hero.all("stat-value") if hero.one("card-stats") in value["ancestors"]] == ["0", "-2"]
    assert re.findall(r"-?\d+", hero.one("command-cost")["text"]) == ["0"]


def test_print_kit_publishes_and_renders_reference_decks() -> None:
    from longwar.reference_decks import DECK_CATALOG

    builder = text("tools/build_pages.py")
    script = text("web/playtest-kit.js")
    page = text("web/playtest-kit.html")

    assert DECK_CATALOG
    assert "REFERENCE_DECKS" in builder
    assert 'data/reference-decks.json' in script
    assert 'decks.map(' in script
    assert 'window.PrintCards.markup(index[id], label)' in script
    assert "Print all reference decks" in page
    assert "chunk(deck.cards, 9)" in script
    assert 'class="deck-card-grid card-sheet"' in script
    assert 'data/reference-deck.json' not in builder
    assert 'data/reference-deck.json' not in script
    assert "chunk(cards, 9)" in text("web/cards.js")
    assert 'class="card-sheet"' in text("web/cards.js")


def test_print_card_sheets_fit_inside_a4_with_tolerance() -> None:
    css = text("web/print-cards.css")
    assert "@page cards { size: A4 portrait; margin: 12mm 8mm 10mm; }" in css
    assert "width: 193mm;" in css
    assert "height: 272mm;" in css
    assert "grid-template-columns: repeat(3, 63mm);" in css
    assert "grid-auto-rows: 88mm;" in css
    assert "gap: 4mm 2mm;" in css
    assert "break-after: page;" in css
    assert "page-break-after: always;" in css
    assert "break-inside: avoid-page;" in css
    assert "overflow: hidden;" in css
    assert "width: 210mm;" not in css[css.index("@media print"):]
    assert "height: 297mm;" not in css[css.index("@media print"):]

    # The 3x3 grid is smaller than the printable content box in both axes.
    assert 3 * 63 + 2 * 2 == 193
    assert 3 * 88 + 2 * 4 == 272
    assert 193 < 210 - 2 * 8
    assert 272 < 297 - 12 - 10


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




def test_print_build_version_is_stamped_everywhere() -> None:
    builder = text("tools/build_pages.py")
    renderer = text("web/print-cards.js")
    card_css = text("web/print-cards.css")
    site_css = text("web/style.css")

    assert "GITHUB_SHA" in builder
    assert "PRINTABLE_PAGES" in builder
    assert 'name="lw-build-version"' in builder
    assert 'class="print-version"' in builder
    for page in ("cards.html", "playtest-kit.html", "rulebook.html", "playmat.html", "tokens.html"):
        assert f'"{page}"' in builder

    assert 'meta[name="lw-build-version"]' in renderer
    assert "card-version" in renderer
    assert "v' + esc(BUILD_VERSION)" in renderer
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
    assert ".remote-connect" in style


def test_remote_play_routes_actions_through_host_authoritative_session() -> None:
    script = text("web/play.js")
    assert 'mode: "remote"' in script
    assert "session.act(command.key, 1)" in script
    assert "session.mulligan(command.indices || [], 1)" in script
    assert "session.view(0)" in script
    assert "session.view(1)" in script
    assert 'type: "snapshot"' in script
    assert "createRemoteHost" in script
    assert "createRemoteGuest" in script


def test_pages_cache_busts_remote_peer_module() -> None:
    builder = text("tools/build_pages.py")
    assert '("browser-engine.mjs", "remote-peer.mjs")' in builder


def test_browser_verify_checks_all_authored_and_built_static_assets() -> None:
    makefile = text("Makefile")
    workflow = text(".github/workflows/pages.yml")
    checker = text("tools/check_web_static.py")

    assert "python tools/check_web_static.py" in makefile
    assert "python tools/check_web_static.py --dist dist" in makefile
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
    assert 'remoteSetupPhase = "creating"' in script
    assert 'remoteSetupPhase === "creating"' in script
    assert 'setupMode.startsWith("remote-")' in script
    assert 'remoteStatus(error?.message || "Remote connection failed.", true)' in script
    assert "timeoutMs = 6000" in peer
    assert 'typeof RTCPeerConnection === "undefined"' in peer
    assert "#remote-status.remote-error" in style
