"""Read-only inventory of PNG dimensions for canonical card artwork.

Designed to run in CI without Pillow; reads the PNG IHDR directly.
No image assets, game rules or card layouts are changed.
"""
from __future__ import annotations

import json
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "web/art/cards"
CARDS = ROOT / "cards/cards.json"
# Card art viewport is approximately 60 mm wide by 25 mm high (2.4:1).
PRINT_WINDOW_ASPECT = 2.4


def dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != bytes.fromhex("89504e470d0a1a0a") or header[12:16] != b"IHDR":
        raise ValueError(f"Not a valid PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    used = {c.get("art_id", c["id"]) for c in cards}
    grouped: dict[tuple[int, int], list[str]] = defaultdict(list)
    errors: list[str] = []
    for path in sorted(ART.glob("*.png")):
        try:
            size = dimensions(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        grouped[size].append(path.stem)

    print(f"ART_DIMENSIONS: {sum(map(len, grouped.values()))} PNGs, {len(used)} referenced art IDs, {len(grouped)} size groups")
    for (w, h), filenames in sorted(grouped.items(), key=lambda item: (-len(item[1]), -item[0][0])):
        print(f"GROUP: {w}x{h} ratio={w/h:.3f} count={len(filenames)}")
        print("  " + ", ".join(sorted(filenames)))

    flagged = []
    for (w, h), names in sorted(grouped.items()):
        ratio = w / h
        # Classify crop risk, not artistic quality.
        reason = []
        if w < 960 or h < 500:
            reason.append("low-resolution")
        if ratio < 1.3:
            reason.append("square-or-portrait")
        elif ratio < 1.6:
            reason.append("narrow-landscape")
        elif ratio > 2.8:
            reason.append("very-wide")
        if reason:
            flagged.extend((name, w, h, reason) for name in names)
    print("DIMENSION_FLAGS: " + str(len(flagged)))
    for name, w, h, reasons in sorted(flagged):
        print(f"FLAG: {name}.png {w}x{h} ({', '.join(reasons)})")
    missing = sorted(used - {name for names in grouped.values() for name in names})
    unused = sorted({name for names in grouped.values() for name in names} - used)
    print("MISSING: " + (", ".join(missing) if missing else "none"))
    print("UNREFERENCED: " + (", ".join(unused) if unused else "none"))
    if errors:
        print("HEADER_ERRORS: " + "; ".join(errors))
        raise SystemExit(1)
    if missing:
        raise SystemExit("Missing referenced artwork")


if __name__ == "__main__":
    main()
