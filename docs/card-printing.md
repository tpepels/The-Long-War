# Printed cards

`web/print-cards.js` is the shared catalogue/reference-deck renderer. It consumes
canonical `cards/cards.json` and delegates rules formatting to `CardRules`.
`web/print-cards.css` owns print geometry independently of the website and play
table. The existing Pages build copies these files and `web/fonts/` unchanged.

The reference-deck print page renders all six canonical 40-card decks, one copy of
each. `tools/build_pages.py` publishes them together as `data/reference-decks.json`,
so the page and the repository deck definitions cannot drift apart.

Cards are **63 × 88 mm**, arranged nine per A4 portrait sheet with 8 mm page
margins. Print at **100% / actual size**, without browser headers or footers.
The border is the cutting guide. These are home-print sheets, without commercial
bleed or crop marks. Enable background graphics for the intended paper tints.

Heroes use a single bronze frame, a full-width title, and one integrated bronze
Force/Name strength crest. Corresponding rule groups follow the existing explicit
FORCE and NAME labels; following trigger blocks stay with their preceding mode.
No card-specific rules or rewritten game text live in the renderer.

Command cost uses a compact double-ring medallion with a dominant numeral and an
explicit label. EB Garamond provides display type; Gentium Book provides regular,
bold and italic rules text. Unmodified fonts and their SIL Open Font Licenses are
bundled under `web/fonts/`. Rules use approximately 9.7 pt text, tightening only on the densest cards, while
short cards open up to roughly 10.3 pt. Long titles and timing labels scale or wrap
without stealing unnecessary rule space. Truly vanilla Forces remain textless; their
open area is treated as deliberate composition rather than filled with invented copy. Type names, labels and numbers
remain explicit when printed in grayscale.

## Verify and export

From the repository root, with Chrome/Chromium installed:

```sh
python -m pytest -q tests/test_browser_card_layout.py
python tools/check_card_layout.py --surface print --require-browser \
  --pdf artifacts/print/cards.pdf
```

Use `--browser /path/to/chrome` if Chrome is not on PATH. This export does not
require the game runtime: it uses the actual shared print renderer and canonical
JSON directly, waits for bundled fonts, and checks layout before reporting
success. The default `--surface all` also checks the browser play cards; those
have a separate stylesheet and are outside a print-only design change.

The renderer preserves canonical text and values. The geometry guard detects
region overflow and overlap; still inspect the PDF and test-print a sheet after
typographic changes. Browser PDF output and printer scaling are separate from
browser layout, and tiny metadata should be checked on the intended printer.
