"""Checks that authored card PNGs are actually used by the card renderer.

This is a small asset-contract check, not a freeze on icon appearance or rules.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "web" / "art" / "icons" / "sizes" / "128"
RENDERER = ROOT / "web" / "card-symbols.js"


def test_every_existing_png_is_enabled() -> None:
    source = RENDERER.read_text(encoding="utf-8")
    match = re.search(r"PNG_ICONS\s*=\s*new Set\(\s*\[([\s\S]*?)\]\s*\)", source)
    assert match is not None
    enabled = re.findall(r'"([a-z0-9_-]+)"', match.group(1))
    assert len(enabled) == len(set(enabled))
    assert set(enabled) == {p.stem for p in ICON_DIR.glob("*.png")}


@pytest.mark.skipif(shutil.which("node") is None, reason="Node needed for browser renderer smoke check")
def test_png_by_default_and_svg_only_on_request() -> None:
    runner = r'''
    const fs = require("node:fs");
    const assert = require("node:assert/strict");
    const source = fs.readFileSync(process.argv[1], "utf8");
    const render = (search) => {
      const window = {location: {search}};
      eval(source);
      return window.CardSymbols;
    };
    const png = render("");
    const svg = render("?icons=svg");

    const checks = [
      ["Family", () => png.symbol("force"), "force"],
      ["Class", () => png.classification("archer"), "archer"],
      ["New class", () => png.classification("spearman"), "spearman"],
      ["Timing", () => png.timing("trigger"), "trigger"],
      ["Play", () => png.timing("play"), "play"],
      ["Named trigger", () => png.timing("becomes_named"), "becomes_named"],
      ["Move", () => png.utility("move"), "move"],
      ["Card", () => png.utility("card"), "card"],
      ["Clear", () => png.utility("clear"), "clear"],
      ["Lock", () => png.utility("lock"), "lock"],
      ["Enemy", () => png.utility("enemy"), "enemy"],
      ["Strength", () => png.strength(), "strength"],
      ["Front row", () => png.row(["front"]), "front"],
      ["Middle row", () => png.row(["middle"]), "middle"],
      ["Rear row", () => png.row(["rear"]), "rear"],
      ["Middle/rear row", () => png.row(["middle", "rear"]), "middle-rear"],
    ];
    for (const [label, make, name] of checks) {
      const html = make();
      assert.match(html, /<img /, label + " still SVG");
      assert.ok(html.includes("/" + name + ".png"), label + " has wrong source");
    }
    assert.match(png.row(["front", "rear"]), /<svg /,
      "Unsupported row combinations must remain composited SVG");
    assert.match(svg.symbol("force"), /<svg /, "Explicit comparison override");
    assert.match(svg.strength(), /<svg /, "Strength comparison override");
    assert.match(svg.row(["middle", "rear"]), /<svg /, "Row comparison override");
    assert.match(svg.utility("lock"), /<svg /, "Utility comparison override");
    console.log("Card PNG rendering smoke test passed (" + checks.length + " cases).");
    '''
    result = subprocess.run(
        ["node", "-e", runner, str(RENDERER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
