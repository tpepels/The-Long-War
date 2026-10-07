# Printed cards

`web/physical-cards.js` is the shared renderer for the catalogue, playtest kit,
stack proofs and print sheets. `web/physical-cards.css` owns appearance and
geometry; `web/card-symbols.js` supplies functional symbols. The runtime webgame
remains a separate presentation surface.

## Card design

All eight card families share an aged parchment shell, blue-and-gold ornament,
a landscape illustration above the centered title, written classifications,
readable rules, and a large raster Command seal. A subtle type-specific wash
distinguishes Force, Bond, Name, Hero, Tactic, Order, Stratagem and Narrative
without changing the shared frame assets. The exposed strip uses bold silhouettes
and serif reminders, with slightly more breathing room above the live content.
Heroes keep both Force and Name modes; dense faces reclaim space from artwork and
identity spacing before reducing rules to 2.85 mm (8.1 pt). Vanilla cards have no
placeholder rules text.

See [`cards/visual-spec.md`](../cards/visual-spec.md) for the dimensions and
presentation contract. Card text, numbers, classifications and rules come from
`cards/cards.json`; the reference illustration is a style guide, not a replacement
source for game content.

## Assets and versions

The reusable authoring PNGs live in `web/art/card-frame/`: `card-shell.png`,
`art-window.png`, `title-divider.png` and `command-seal.png`. Their README records
provenance. CSS composites these pieces rather than drawing an ornamental frame.

`tools/build_pages.py` preserves the originals and publishes lossless WebP frame
derivatives with transparency under `dist/art/card-frame/`. Sizes target roughly
300 dpi: **1134 px shell long edge**, **744 px art-window width**, **640 px divider
width** and **160 px square seal**. Built CSS references those derivatives with
cache versions. Frame content contributes to the asset digest and source-archive
print version.

Canonical per-card PNGs remain under `web/art/cards/`; deployed card art uses the
optimized derivatives under `dist/art/cards-print/`. Raw originals remain in
`cards/art-sources/`. Do not replace high-resolution sources with deployed images.
Sixteen existing `art_focus_y` overrides keep available portrait faces in the
shorter windows; all other art remains centered. No PNGs were regenerated or
recropped. Source images that already cut heads remain an artwork-review issue.
Every printable page and card footer carries the build revision.

## Print geometry

Cards are **68 × 96 mm**. Four across and two down form a **272 × 192 mm** block,
with no gaps, leaving **9 mm above and below** and **12.5 mm at each side** on A4
landscape. The CSS bottom page margin is 6 mm, reserving 3 mm below the cards for
the revision stamp. Square cut boxes share straight seams; rounded raster corners
remain inside those boxes. Print at **100% / actual size**, with browser headers
and footers disabled.

`cards.html` prints the catalogue. `playtest-kit.html` expands copy counts from
`cards/playtest-decks.json` and renders the same faces. Both wait for their
optimized assets before enabling printing.

## Optional review and export

Evolving visual design is reviewed through local proofs, not a release gate based
on frozen typography. With Chrome/Chromium installed:

```sh
make pages
python tools/check_card_layout.py --surface print --require-browser
```

The diagnostic covers the current pool, formation stacks, numeric extremes,
long titles, dense rules, raster assets, live reminders and event status labels.
An intentionally oversized example verifies that overflow is detected.

Use the built Cards and Decks pages to export print PDFs. Review the full
catalogue and two selected decks: page counts, eight cards per sheet, copies,
visible revision stamps, typography and every artwork crop. Local proofs and
review reports belong under `artifacts/`; they are not authored sources.
