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
and SVG symbols. Formation cards use a **10.5 mm exposed row** so Strength,
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

`cards.html` prints the full 131-card physical playtest pool (print-only overrides applied).
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

### Physical-playtest-only card revisions

`cards/print-overrides.json` now contains **44 physical-print replacements** (including 16 focused new cost/diversity sidegrades), **7 additional cost-only adjustments**, and 2 remaining standalone ACTION-limit corrections; two former standalone corrections were integrated into reworked effects, so all prior once-per-Battle restrictions still apply. `tools/print_cards.py` creates the separate `dist/data/print-cards.json` consumed by both printable Cards and Decks pages. `dist/data/cards.json` and `cards/cards.json` remain unchanged executable input; these printed effects are **not** promises about the webgame. Print-only exports deliberately omit stale executable `design_rules`.

Force/Bond/Name stacks reveal only the top 10.5 mm of each buried card. Thus new PLAY effects resolve immediately and may safely be covered; every new ongoing Force/Bond effect has an explicit exposed-strip reminder. The printed rules text remains the authority. All 20 remaining pre-existing live Force/Bond reminders have updated print-only strip wording to clarify conditions and targets; confirm edge fit in a rendered stack before printing in quantity.

### Rulebook and physical-playtest status

The printed [rulebook](../rules/rulebook.md), [quick reference](../web/playmat.html), [marker sheet](../web/tokens.html), and mechanics page of the deck kit define the **physical 2026 reconciliation**. They use pre-draw voluntary Pass, four Narratives, assigned-Front hidden Stratagems, −1 flanking, and next-Battle lost-Front Exhaustion with Guarded protection. The executable Webgame/AI uses older behavior and is **not a rules reference for these cards**. Rule changes in this phase intentionally do not modify native gameplay code.

### Cost/diversity verification

Use `python tools/check_physical_cost_balance.py` for 15 static tabletop decision checks and [the complete 131-card cost ledger](../cards/physical-cost-review.md). A GitHub Actions advisory build checks the card export, generated Pages, PDF, and rulebook PDF. Full-size browser/card geometry still needs a repaired layout fixture or local print inspection. The build is not a full simulation of the print rules.


## Hero cost seal and icon colour tuning

In `web/physical-cards.css`, near the top of the `:root` block under
**HERO COST SEAL - EDIT THESE VALUES**, tune the diagonal Force/Name Command
seal without changing card data or renderer code:

- `--hero-cost-force-left` / `--hero-cost-force-top` position the upper-left
  Force icon and number together; `--hero-cost-name-right` /
  `--hero-cost-name-bottom` position the lower-right Name pair.
- `--hero-cost-*-symbol-size`, `--hero-cost-*-number-size`, and
  `--hero-cost-*-gap` control the separate glyph and numeral dimensions.
- `--hero-cost-*-symbol-x/y` and `--hero-cost-*-number-x/y` fine-tune each
  part independently; positive X moves right and positive Y moves down.
- `--hero-cost-fraction-inset` adjusts the inner area; `--hero-cost-slash-*`
  controls the diagonal separator. Values use millimetres except the slash
  position (percent), angle (degrees) and opacity (0–1).

All these variables are visual only: the Force and Name Command costs still
come from their separate card-data fields. Inspect all Hero cards at actual
print size after adjustments; `PhysicalCards.inspect()` flags cost pairs
that overlap or leave the seal.

Transparent PNG glyphs now use the **same card-family filter values** as the
decorative frame PNGs (`--card-shell-*` in each `.card-*` selector).
They follow the card family theme automatically. Illustrations, text and SVG
fallback icons are intentionally excluded from that filter.
