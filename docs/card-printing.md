# Printed cards

The physical-card system has one canonical renderer.

`web/physical-cards.js` renders the full catalogue, playtest decks and print
sheets. `web/physical-cards.css` owns the shared 68 × 96 mm design, and
`web/card-symbols.js` supplies the functional symbols. There is no separate old
or V2 card presentation to maintain.

## Card design

All card families use the same four decorative frame rasters from
`web/art/card-frame/`: `card-shell.png`, `art-window.png`,
`title-divider.png` and `command-seal.png`. Force keeps the original sand
treatment; the other families use CSS filters on all four frame rasters so their
colours can be tuned without recolouring text, symbols or illustrations.

The face combines those raster assets with live per-card artwork, rules, numbers
and SVG symbols. Formation cards use a **12 mm exposed row** so Strength,
classifications, legal-rank restrictions and live reminders remain visible when
cards are stacked. Tactic, Order, Stratagem and Narrative use a centred event
header. The footer identifies the card family and, for formation cards, its
classifications.

The exposed row is a reminder, not a second rules source. Placement restrictions
and state conditions shown there are also written explicitly in the body.

Normal cards use a **30 mm** illustration region. Dense cards reclaim space with a
**25 mm** region and smaller rule type; Heroes use their own compact geometry.
Placement text counts as a real rule block when density is determined.

See [`cards/visual-spec.md`](../cards/visual-spec.md) for the complete layout
contract and the CSS tuning panels.

## Artwork

Canonical card illustrations live in `web/art/cards/`. Cards may temporarily
reuse another canonical illustration through an explicit `art_id`; both the
catalogue and playtest-kit preload that resolved artwork ID.

The Pages build publishes optimized WebP derivatives under
`dist/art/cards-print/`. Raw illustration sources remain in
`cards/art-sources/`. Do not replace authoring PNGs with deployed derivatives.

`tools/build_pages.py` also publishes lossless WebP versions of the four frame
rasters and rewrites built CSS to use them. Frame assets participate in the build
digest, so changing the shell or ornament changes the printed revision.

## Print geometry

Cards are **68 × 96 mm**. Four across and two down form a **272 × 192 mm** block
on A4 landscape, with no gaps between cards. Print at **100% / actual size** with
browser headers and footers disabled.

`cards.html` prints the complete canonical catalogue.
`playtest-kit.html` expands copy counts from `cards/playtest-decks.json` and
renders the same card faces. Every printable page and card footer carries the
Pages build revision.

## Verify and export

From the repository root, with Chrome/Chromium installed:

```sh
make pages
python tools/check_card_layout.py --surface print --require-browser
```

The layout checker is diagnostic: it checks physical dimensions, stacking,
overflow, long titles, dense rules, raster assets and representative print
pagination. The built Cards and Decks pages are the final visual review surface.
