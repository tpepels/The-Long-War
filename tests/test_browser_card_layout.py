from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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


def render_print_cards(cards: list[dict]) -> list[RenderedCard]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to exercise the shared card renderer")
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


def test_shared_renderer_escapes_hostile_text_and_preserves_numbers() -> None:
    hostile = '<img src=x onerror="bad()"> & </script>'
    cards = [
        {
            "id": hostile,
            "title": hostile,
            "type": "force",
            "strength": -1,
            "command_cost": 0,
            "classes": ["human"],
            "unique": True,
            "effects": [{"timing": "action", "text": "Strength " + hostile}],
        }
    ]
    card = render_print_cards(cards)[0]
    assert card.one("card-title")["text"] == hostile
    assert card.one("v2-card")["attrs"]["data-card-id"] == hostile
    assert card.one("effect-text")["text"] == "Strength " + hostile
    assert not any(element["tag"] in {"img", "script"} for element in card.elements)
    assert card.one("cost-gem")["text"] == "0"
    assert card.one("strength-mark")["text"].strip().endswith("-1")


def test_remote_peer_transport_remains_rule_free() -> None:
    source = text("web/remote-peer.mjs")
    assert "RTCPeerConnection" in source
    assert "longwar." not in source
    assert "legal_actions" not in source
    assert "cards" not in source


def test_remote_play_keeps_host_authoritative_session() -> None:
    script = text("web/play.js")
    assert "session.act(command.key, 1)" in script
    assert "session.mulligan(command.indices || [], 1)" in script
    assert "session.view(0)" in script
    assert "session.view(1)" in script
    assert "createRemoteHost" in script
    assert "createRemoteGuest" in script


def _static_checker():
    spec = importlib.util.spec_from_file_location(
        "check_web_static",
        ROOT / "tools" / "check_web_static.py",
    )
    assert spec and spec.loader
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    return checker


def test_web_static_checker_catches_missing_built_data_reference(tmp_path) -> None:
    checker = _static_checker()
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
    checker = _static_checker()
    web = tmp_path / "web"
    web.mkdir()
    (web / "play.html").write_text('<div id="present"></div>', encoding="utf-8")
    (web / "play.js").write_text('$("present"); $("missing");', encoding="utf-8")

    assert checker._play_dom_errors(web) == [
        "web/play.js references missing DOM id #missing"
    ]
