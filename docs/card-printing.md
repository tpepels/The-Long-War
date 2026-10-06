# Printed cards

The physical-card system now has one renderer.

`web/cards-v2.js` is the canonical physical-card renderer for the Card Lab,
full catalogue, playtest kit, stack proofs and print sheets. `web/cards-v2.css`
owns the shared 68 × 96 mm physical design. `web/v2-heraldry.js` supplies the
functional symbols. The former `print-cards.js` / `print-cards.css` renderer
has been removed so the playtest kit cannot drift into a separate card design.

The visual hierarchy deliberately follows the earlier print-card design: a thin
outer cutting border, a restrained inset accent frame, large EB Garamond title,
compact Gentium classification row, simple framed illustration, straightforward
rule dividers, restrained family color and a quiet footer. The current rules and
mechanics remain V2: formations keep the 10.5 mm exposed battlefield row,
functional SVG symbols, current timing vocabulary, graphical Hero FORCE / NAME
dividers, the bottom-right octagonal Command seal and per-card illustrations.

## Geometry

Cards are **68 × 96 mm**. The exposed formation row is **10.5 mm**. The shared
illustration window is **20 mm** high. Force art is normalized offline to the
shared aperture ratio; runtime artwork is centered by default, with
`art_focus_x` / `art_focus_y` retained only as escape hatches.

Print sheets use **A4 landscape** with 9 mm top/bottom and 12.5 mm side margins.
Four 68 mm cards across and two 96 mm cards down form an exact **272 × 192 mm**
eight-card block with **no gaps between cards**. Adjacent outer borders touch, so
one straight cut separates both cards instead of requiring a trim on each side.
Print cards use square outer corners on the sheet so the shared cut seams remain
continuous; the normal rounded on-screen card shape is unchanged. Print at 100%
/ actual size without browser headers or footers.

`cards.html` prints the complete current V2 catalogue. `playtest-kit.html`
loads `cards/v2/playtest-decks.json`, expands copy counts, and prints those same
card faces. There is no second print-only markup implementation.

Every printable page receives the Pages build revision via
`meta[name="lw-build-version"]`. Each card footer renders that revision as well,
so physical playtest cards can be traced to the exact build.

## Typography and hierarchy

EB Garamond SemiBold is used for titles and numerals, Gentium Book for rules and
classification prose, and Arial only for compact utility labels. Family identity
comes from restrained accent color rather than a different shell per card type.
The exposed row reads as a compact engraved status bar: Strength, intrinsic
classification symbols, placement restrictions and live reminders stay visible
when cards are stacked.

Hero rule modes are section dividers rather than duplicate prose labels:
`FORCE` and `NAME` sit between fine horizontal rules with their functional
symbols. Dense cards tighten rule typography only; they do not move the
illustration or change the physical card skeleton.

## Verify and export

From the repository root, with Chrome/Chromium installed:

```sh
python -m pytest -q tests/test_v2_card_design.py tests/test_browser_card_layout.py
python tools/check_card_layout.py --surface print --require-browser \
  --pdf artifacts/print/cards-v2.pdf
make pages
```

The physical check validates all current V2 cards, formation stack proofs,
numeric-range stress, overflow detection, exact 68 × 96 mm geometry, 10.5 mm
exposed rows and eight-card A4 landscape pagination. The browser play cards are
still a separate in-game surface and are checked by
`python tools/check_card_layout.py --surface browser`.
