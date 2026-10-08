"""Icon-size tunability of the physical cards (content-level contract)."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "web" / "physical-cards.css"
SYMBOLS = ROOT / "web" / "card-symbols.js"

# Sizes belong to independent *visual slots*, not to the overall card geometry.
REQUIRED_SLOT_CONTROLS = (
    "edge-type", "edge-hero-force", "edge-hero-name", "edge-class",
    "edge-row", "edge-event", "classification", "family",
    "rule-timing", "rule-placement", "inline-class", "mode-heading",
    "hero-mode", "footer-mark", "command-seal", "used-marker",
    "hero-used",
)


def test_each_icon_slot_can_be_sized_from_top_of_stylesheet() -> None:
    source = CSS.read_text(encoding="utf-8")
    panel = source.split("CARD ICON SIZES — TUNING PANEL", 1)[1]
    root = panel.split("body {", 1)[0]
    for role in REQUIRED_SLOT_CONTROLS:
        name = f"--icon-{role}-size"
        # The default value is deliberately not locked by this test.
        assert re.search(rf"{re.escape(name)}\s*:\s*[^;]+;", root), name
        assert f"var({name})" in source, name


def test_individual_glyph_scales_are_exposed_for_png_and_svg() -> None:
    css = CSS.read_text(encoding="utf-8")
    symbols = SYMBOLS.read_text(encoding="utf-8")
    # Existing elements must expose a stable name across the PNG and SVG paths.
    assert "data-icon" in symbols
    assert "transform: scale(var(--icon-symbol-scale, 1))" in css
    for name in ("force", "bond", "name", "guard", "archer",
                 "play", "trigger", "row", "command"):
        css_name = name.replace("_", "-")
        assert f"--icon-scale-{css_name}:" in css
        assert f'[data-icon="{name}"]' in css


def test_card_layout_dimensions_are_not_part_of_icon_tuning() -> None:
    css = CSS.read_text(encoding="utf-8")
    # The icon panel must not resize the physical card or stacking overlap.
    assert "--card-width: 68mm;" in css
    assert "--card-height: 96mm;" in css
    assert "--exposed-edge: 10.5mm;" in css
