# Shared physical-card decoration

These four source PNGs are reusable decoration, initially applied to the Force
approval proof. Card titles, rules, symbols, numbers and illustrations remain
dynamic in `web/physical-cards.js`.

| Asset | Use | Published size cap |
| --- | --- | --- |
| `card-shell.png` | Aged parchment, outer blue-and-gold rim and integrated corners | 1134 px long edge |
| `art-window.png` | Transparent illustration-window rim | 744 px wide |
| `title-divider.png` | Fine engraved line and small central diamond | 640 px wide |
| `command-seal.png` | Empty dark octagonal seal; Command numeral is live text | 160 px square |

Created with the built-in image-generation tool using the supplied King's Spears
mockup as a style reference. No existing card illustration was regenerated.
The PNGs retain their generated alpha channels. `tools/build_pages.py` publishes
lossless WebP derivatives at roughly 300 dpi for their actual printed sizes and
rewrites the physical stylesheet's frame references. Source PNGs and this record
do not deploy. The per-card illustration pipeline is unchanged.

## Prompt set

All four prompts request flat, straight-on production raster assets, antique
gold and deep desaturated blue, no perspective, external shadow, text or numbers.

**Shell:** An empty portrait card, aspect 68:96, filling the canvas without a
margin. Rich aged ivory parchment; worn antique-gold double rim and blue edging;
delicate leafy corner ornament confined to roughly the outer 3% of width. Light,
subtly fibrous parchment throughout the interior. No illustration window,
dividers, icons, seal or internal panels. Only outside rounded corners transparent.

**Art window:** A thin rectangular rim, ratio 2.48:1, filling the canvas. Worn
antique-gold double line, blue at the corners, integrated curled gold leaves.
Border about 1.5% of width. Center and outside corners transparent. No parchment,
illustration or background texture. Intended to overlay a 62 × 25 mm painting.

**Divider:** One delicate antique-gold engraved hairline tapering toward both
ends, a tiny centered diamond and two very small neighboring flourishes.
Restrained aged-gold material, tightly framed wide composition, transparent
surroundings. No large scrollwork, parchment, frame or scene. Intended for a
54 mm wide title divider.

**Seal:** A single symmetrical octagon filling a square canvas. Large empty,
near-black blue matte center; two thin antique-gold beveled rims with slight
wear. Transparent exterior, opaque center. Remove the reference numeral and
all other markings; no surrounding parchment or card.
