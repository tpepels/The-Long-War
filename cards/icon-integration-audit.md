# Heraldic PNG icon integration — batches 1–3

**Scope:** Icon-source substitution only. The physical card layout, 4 mm icon slots, 10.5 mm stack exposure, fonts, decorations, art crops and all card data remain unchanged.

The repository retains 30 transparent candidate PNGs from batches 1–3. The current card symbol module uses 26 of those names as 128 px PNGs in its existing slots and leaves every unmatched active symbol as the original inline SVG. The four retired classification PNGs remain as unused source assets. The approved art packs are stored under `web/art/icons/`, with `web/art/icons/sizes/128/` copied into the Pages deployment.

## Counts and exclusions

| Group | Integrated PNG names |
|---|---|
| Card types | force, bond, name, hero, tactic, order, stratagem, narrative |
| Classifications | human, ship, stronghold, archer, guard, scout, rider, skirmisher, raider, healer, steward, seer, king, captain |
| Timings/states | action, reaction, bonded, while_named |

**26 active PNG-backed names.** The old SVGs for active classes are retained as a reversible fallback. `reaction` is currently a defined but infrequently used timing symbol. The rest are referenced by the card pool.

**Excluded:** all art from batches 4–5; all rank indicators, utility icons without batch 1–3 PNGs, and the setup battlefield illustration. No unapproved image is in use.

## Inspect and compare

- `icon-preview.html?icons=png`: all 26 currently active icons shown at 8 mm, 4 mm (actual card-edge target) and 16 px.
- `icon-preview.html?icons=svg`: same gallery using original SVG glyphs.
- `cards.html`: existing card views with PNG marks.
- `cards.html?icons=svg`: existing card views with original SVG marks.
- `playtest-kit.html?icons=svg`: use original SVG marks when checking printable card layouts.

The `icons=svg` query is a comparison/rollback switch, not a styling change; URLs without the query use PNG.

## Preliminary visual observations

- **Force and Guard:** imagery is very similar (shield silhouette); these should be revisited before the icons are approved for final print production.
- **16 px and smaller:** intricate heraldic detail may merge. These designs are easier to distinguish at 4 mm / about 47 px at 300 dpi, but still require a real printer check.
- **Character:** several detailed badges are recognizably ornate, but less immediately semantic than the former flat silhouettes. Inspect recognition speed, not just appearance.

No decisions are made here about generating more icons. Evaluate batches 1–3 in context first.

## Technical notes

The shared `CardSymbols` API still returns HTML strings with the same glyph CSS class names. SVG implementations remain available, while approved PNG calls return `<img>` tags in the existing slots. Only CSS selectors were widened from `svg` to `svg, img.glyph-png`; physical sizing variables are unchanged. The Pages builder copies only the 128 px icon derivatives, not the 1254 px authoring masters. Static browser checks assert the referenced PNGs are present in both the source tree and deployed build.

**Not covered:** Game engine, AI, gameplay rules, card balancing, full raster print proofing or replacing any other icon family.
