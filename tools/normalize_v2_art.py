#!/usr/bin/env python3
"""Audit canonical V2 card art and normalize Force art to the shared art-window ratio.

The shared V2 card is 68 mm wide with a .42 mm border, 3.45 mm horizontal
card-body padding, -1.05 mm horizontal motif margins, and a fixed 20 mm
illustration height. That yields a 62.36 x 20 mm live art window: 3.118:1.

Force images are cropped once, in pixels, so runtime CSS can stay centered.
Optional art_focus_x/art_focus_y remain renderer escape hatches.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CARDS_JSON = ROOT / "cards" / "v2" / "cards.json"
ART_DIR = ROOT / "web" / "art" / "v2" / "cards"
AUDIT_JSON = ROOT / "web" / "art" / "v2" / "art-audit.json"
AUDIT_CSV = ROOT / "web" / "art" / "v2" / "art-audit.csv"

CARD_WIDTH_MM = 68.0
FRAME_MM = 0.42
BODY_PAD_X_MM = 3.45
MOTIF_MARGIN_X_MM = -1.05
ART_HEIGHT_MM = 20.0

ART_WIDTH_MM = (
    CARD_WIDTH_MM
    - 2 * FRAME_MM
    - 2 * BODY_PAD_X_MM
    - 2 * MOTIF_MARGIN_X_MM
)
ART_RATIO = ART_WIDTH_MM / ART_HEIGHT_MM

# 1248 / 400 = 3.12, within 0.001 of the exact 3.118 shared CSS window.
OUTPUT_WIDTH = 1248
OUTPUT_HEIGHT = 400

# Focus is expressed as a normalized point in the SOURCE image. Most Force art
# uses the former top-biased 28% view baked into the pixels. Portrait-heavy
# compositions get a higher (smaller-y) focus so heads stay in frame.
FORCE_FOCUS_Y = {
    "the-black-company": 0.12,
    "the-old-guard": 0.14,
    "the-red-duelists": 0.16,
    "the-first-spear": 0.18,
    "the-dust-riders": 0.18,
    "the-grey-riders": 0.18,
    "the-iron-boars": 0.18,
    "the-crow-archers": 0.18,
    "the-white-hands-of-elara": 0.20,
}
DEFAULT_FORCE_FOCUS_Y = 0.28
DEFAULT_FOCUS_X = 0.50


def load_cards() -> list[dict]:
    raw = json.loads(CARDS_JSON.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else raw["cards"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def crop_box(width: int, height: int, focus_x: float, focus_y: float) -> tuple[int, int, int, int]:
    source_ratio = width / height
    if source_ratio > ART_RATIO:
        crop_h = height
        crop_w = round(height * ART_RATIO)
    else:
        crop_w = width
        crop_h = round(width / ART_RATIO)

    cx = focus_x * width
    cy = focus_y * height
    left = round(cx - crop_w / 2)
    top = round(cy - crop_h / 2)
    left = max(0, min(left, width - crop_w))
    top = max(0, min(top, height - crop_h))
    return left, top, left + crop_w, top + crop_h


def normalize_force(path: Path, card_id: str) -> dict:
    with Image.open(path) as image:
        image.load()
        original_mode = image.mode
        width, height = image.size
        focus_y = FORCE_FOCUS_Y.get(card_id, DEFAULT_FORCE_FOCUS_Y)
        box = crop_box(width, height, DEFAULT_FOCUS_X, focus_y)
        crop = image.crop(box)
        if crop.mode not in {"RGB", "RGBA"}:
            crop = crop.convert("RGBA" if "A" in crop.getbands() else "RGB")
        crop = crop.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
        crop.save(path, format="PNG", optimize=True)

    return {
        "focus_x": DEFAULT_FOCUS_X,
        "focus_y": focus_y,
        "crop_box": list(box),
        "original_mode": original_mode,
    }


def audit(write: bool) -> dict:
    cards = load_cards()
    by_id = {card["id"]: card for card in cards}
    before: dict[str, dict] = {}

    for path in sorted(ART_DIR.glob("*.png")):
        with Image.open(path) as image:
            width, height = image.size
            before[path.stem] = {
                "width": width,
                "height": height,
                "ratio": round(width / height, 6),
                "sha256": sha256(path),
                "mode": image.mode,
            }

    normalized: dict[str, dict] = {}
    if write:
        for card in cards:
            if card.get("type") != "force":
                continue
            path = ART_DIR / f"{card['id']}.png"
            if not path.is_file():
                continue
            normalized[card["id"]] = normalize_force(path, card["id"])

    rows = []
    for path in sorted(ART_DIR.glob("*.png")):
        card_id = path.stem
        card = by_id.get(card_id, {})
        with Image.open(path) as image:
            width, height = image.size
            post_hash = sha256(path)
            pre = before.get(card_id, {})
            crop = normalized.get(card_id, {})
            rows.append(
                {
                    "id": card_id,
                    "type": card.get("type", ""),
                    "title": card.get("title", ""),
                    "original_width": pre.get("width", width),
                    "original_height": pre.get("height", height),
                    "original_ratio": pre.get("ratio", round(width / height, 6)),
                    "original_sha256": pre.get("sha256", post_hash),
                    "width": width,
                    "height": height,
                    "ratio": round(width / height, 6),
                    "normalized_force": card.get("type") == "force" and write,
                    "focus_x": crop.get("focus_x"),
                    "focus_y": crop.get("focus_y"),
                    "crop_box": crop.get("crop_box"),
                    "sha256": post_hash,
                }
            )

    force_ids = {card["id"] for card in cards if card.get("type") == "force"}
    art_ids = {row["id"] for row in rows}
    report = {
        "shared_window_mm": {
            "width": round(ART_WIDTH_MM, 4),
            "height": ART_HEIGHT_MM,
            "ratio": round(ART_RATIO, 6),
        },
        "normalized_raster": {
            "width": OUTPUT_WIDTH,
            "height": OUTPUT_HEIGHT,
            "ratio": round(OUTPUT_WIDTH / OUTPUT_HEIGHT, 6),
        },
        "canonical_art_count": len(rows),
        "force_art_count": len(force_ids & art_ids),
        "force_missing_art": sorted(force_ids - art_ids),
        "force_focus_overrides": FORCE_FOCUS_Y,
        "images": rows,
    }

    if write:
        AUDIT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        with AUDIT_CSV.open("w", encoding="utf-8", newline="") as handle:
            fields = [
                "id", "type", "title", "original_width", "original_height",
                "original_ratio", "width", "height", "ratio",
                "normalized_force", "focus_x", "focus_y", "crop_box",
                "original_sha256", "sha256",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Normalize Force PNGs and write audit files.")
    args = parser.parse_args()
    report = audit(args.write)
    print(json.dumps({
        "shared_window_mm": report["shared_window_mm"],
        "normalized_raster": report["normalized_raster"],
        "canonical_art_count": report["canonical_art_count"],
        "force_art_count": report["force_art_count"],
        "force_missing_art": report["force_missing_art"],
        "force_focus_overrides": report["force_focus_overrides"],
    }, indent=2))


if __name__ == "__main__":
    main()
