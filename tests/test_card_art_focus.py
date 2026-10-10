"""Top-first illustration framing, shared by browser cards and print cards.

This checks the stable default, not the individual visual composition of an image.
A deliberate per-card art_focus_y override remains supported.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_default_artwork_crop_is_top_aligned() -> None:
    css = (ROOT / "web/physical-cards.css").read_text(encoding="utf-8")
    assert "background-size: cover;" in css
    assert "background-position: var(--art-x, 50%) var(--art-y, 0%);" in css


def test_shared_renderer_defaults_to_top_in_screen_and_print() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to exercise the shared card renderer")

    # A card with no explicit focus, one with invalid focus, and one with an
    # intentional custom focus. Print and catalogue must use the same grammar.
    examples = [
        {"id": "top-default", "title": "No explicit focus", "type": "force",
         "strength": 3, "command_cost": 2, "classes": [], "effects": []},
        {"id": "top-invalid", "title": "Invalid focus", "type": "force",
         "strength": 3, "command_cost": 2, "classes": [], "effects": [],
         "art_focus_y": "beyond"},
        {"id": "explicit-override", "title": "Intentional override", "type": "force",
         "strength": 3, "command_cost": 2, "classes": [], "effects": [],
         "art_focus_y": "25%"},
    ]
    script = """
const fs = require("node:fs");
global.window = {};
eval(fs.readFileSync("web/card-symbols.js", "utf8"));
eval(fs.readFileSync("web/physical-cards.js", "utf8"));
const cards = JSON.parse(fs.readFileSync(0, "utf8"));
const result = cards.flatMap(c => [false,true].map(printArt => ({
  id: c.id, printArt,
  markup: window.PhysicalCards.cardArticle(c, "", {printArt})
})));
process.stdout.write(JSON.stringify(result));
"""
    proc = subprocess.run(
        [node, "-e", script], input=json.dumps(examples), text=True,
        capture_output=True, cwd=ROOT, timeout=15, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    for entry in json.loads(proc.stdout):
        expected_focus = "25%" if entry["id"] == "explicit-override" else "0%"
        assert f"--art-y:{expected_focus}" in entry["markup"]
        assert "--art-x:50%" in entry["markup"]
        art_dir = "art/cards-print/" if entry["printArt"] else "art/cards/"
        ext = ".webp" if entry["printArt"] else ".png"
        assert art_dir + entry["id"] + ext in entry["markup"]


def test_illustration_urls_match_preloader_and_include_asset_revision() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to verify shared artwork URLs")

    script = """
const fs = require("node:fs");
global.window = {location: {href: "https://example.org/cards.html"}};
global.document = {currentScript: {src: "https://example.org/physical-cards.js?v=artwork123"}};
eval(fs.readFileSync("web/card-symbols.js", "utf8"));
eval(fs.readFileSync("web/physical-cards.js", "utf8"));
const card = JSON.parse(fs.readFileSync("cards/cards.json", "utf8")).cards[0];
const url = window.PhysicalCards.cardArtURL(card.art_id || card.id, true);
const rendered = window.PhysicalCards.cardArticle(card, "print-card", {printArt: true});
process.stdout.write(JSON.stringify({url, rendered}));
"""
    result = subprocess.run(
        [node, "-e", script], cwd=ROOT, capture_output=True,
        text=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["url"].endswith(".webp?v=artwork123")
    assert data["url"] in data["rendered"]
    assert 'cardArtURL(id,true)' in (ROOT / "web/cards.js").read_text(encoding="utf-8")
    assert 'cardArtURL(id,true)' in (ROOT / "web/playtest-kit.js").read_text(encoding="utf-8")
