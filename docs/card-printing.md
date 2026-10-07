# Printed cards

`web/physical-cards.js` is the shared physical-card renderer for the catalogue,
playtest kit, stack proofs and print sheets. `web/physical-cards.css` owns their
geometry and appearance; `web/card-symbols.js` supplies functional symbols.
The runtime webgame remains a separate presentation surface.

## Force approval checkpoint

The current design proof covers **Force only**. All 30 Forces have been reviewed;
the full 128-card art audit and extensions to other families wait for Force
approval. The 128 canonical card records and 128 per-card illustrations remain
unchanged.

Force cards use an aged parchment, blue and gold raster shell. Their face order
is a **10.5 mm exposed strip**, **25 mm illustration**, **19 mm centered title and
classification region**, rules, and a **15 mm footer** with a **12.5 mm Command
seal**. The Force shield sits left of the Strength number. Classification words
appear beneath the title; pictograms and live reminders stay visible in the
exposed strip. EB Garamond supplies titles and numerals, and Gentium supplies
rules at **3.25 mm**, or **2.85 mm** for dense Force layouts. Vanilla Forces leave
the rules area empty without adding placeholder text.

All other families retain their current identity-before-art layouts, **20 mm
illustration windows**, typography and cost treatment pending approval. See
[`cards/visual-spec.md`](../cards/visual-spec.md) for the visual contract.

## Assets and versions

The reusable authoring PNGs are in `web/art/card-frame/`: `card-shell.png`,
`art-window.png`, `title-divider.png` and `command-seal.png`. These frame elements
are the only decorative overlays. Functional symbols and additional scene
imagery must not cover the card illustration.

`tools/build_pages.py` keeps the originals and generates lossless WebP frame
derivatives with transparency in `dist/art/card-frame/`. Sizes target roughly
300 dpi at print scale: **1134 px shell long edge**, **744 px art-window width**,
**640 px divider width** and a **160 px square seal**.
Local proof CSS uses the PNGs; built CSS rewrites only these frame URLs to WebP
and adds the existing static asset hash version. Frame content contributes to
that digest and the source-archive print version. Existing HTML asset version
tokens are refreshed during the build.

Per-card PNGs remain under `web/art/cards/`; deployed card art uses the existing
optimized derivatives in `dist/art/cards-print/`. All Force focus is centered
at `50% 50%`. Optional focus overrides accept 0–100% values and otherwise fall
back to the center. No artwork was recropped for this checkpoint: The First
Spear, The Old Guard, The Dust Riders and The Black Pursuers retain source crops
whose originals already cut subject heads.

Every printable page receives `meta[name="lw-build-version"]`, and each card
footer shows that revision so physical copies can be traced to their build.

## Print geometry

Cards are **68 × 96 mm**. Their A4 landscape cut block leaves **9 mm above and
below** and **12.5 mm at each side**. The CSS page bottom margin is 6 mm, reserving
3 mm below the cards for the page revision stamp. Four cards across and two down
make an exact **272 × 192 mm** block with **no gaps**. Square cut boxes share straight seams; rounded
raster corners may remain visible inside those boxes. Print at **100% / actual
size**, without browser headers or footers.

`cards.html` prints the complete catalogue. `playtest-kit.html` expands the copy
counts in `cards/playtest-decks.json` and prints the same card faces. There is no
second print-only markup implementation.

## Verify and export

From the repository root, with Chrome/Chromium installed:

```sh
python -m pytest -q tests/test_physical_card_design.py tests/test_browser_card_layout.py tests/test_pages_build.py
python tools/check_card_layout.py --surface print --require-browser \
  --pdf artifacts/print/cards.pdf
make pages
```

The physical check covers all current cards, formation stacks, numeric stress,
overflow detection, Force hierarchy, exact card geometry, exposed strips and
eight-card A4 pagination. The runtime browser cards are checked separately with
`python tools/check_card_layout.py --surface browser`.
