# Printed cards

`web/print-cards.js` is the shared catalogue/reference-deck renderer. It consumes
canonical `cards/cards.json` and delegates rules formatting to `CardRules`.
`web/print-cards.css` owns print geometry independently of the website and play
table. The existing Pages build copies these files and `web/fonts/` unchanged.

The reference-deck print page renders all six canonical 40-card decks, one copy of
each. `tools/build_pages.py` publishes them together as `data/reference-decks.json`,
so the page and the repository deck definitions cannot drift apart.

Cards are **63 × 88 mm**, arranged nine per A4 portrait sheet. Printed sheets
reserve **12 mm at the top, 10 mm at the bottom, and at least 8 mm at each side**
so ordinary home printers do not need borderless output. Print at **100% / actual
size**, without browser headers or footers. The border is the cutting guide.
These are home-print sheets, without commercial bleed or crop marks. Enable
background graphics for the intended paper tints.

Every printed card and every printable page carries the exact Pages build
revision as `v<commit>`. Treat that printed revision as the authoritative way
to tell two physical playtest builds apart.

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

## V2 physical cards and Card Lab

The separate V2 proposal uses `web/cards-v2.js` and `web/cards-v2.css` for both
Card Lab and print. It reads `cards/v2/cards.json`; it does not replace the
canonical engine pool described above. V2 cards are **68 × 96 mm**, eight per
A4 landscape sheet with 6 mm page margins. The complete 120-card proposal uses
15 sheets. Print at actual size with background graphics and no browser headers.

The shared `V2Cards.cardArticle` also renders the six physical stack proofs.
Cards really overlap at 10.5 mm offsets: underlying bodies remain intact and
are covered by the next card. A Hero's face is identical in both roles, including
two separate exposed values and its Force-only live reminder. The mode attribute
records the example's role; it cannot change the printed face.

`web/v2-heraldry.js` supplies vector symbols and family artwork.
`web/v2-reminders.js` contains display-only compact reminders keyed by the exact
source effect text. These retain target, range, condition, amount, cost, duration
and consequence. A new or changed source sentence falls back to its full text,
so stale summaries cannot silently survive rule changes. An oversized fallback
is flagged in Card Lab and fails the layout check; review the presentation copy
rather than shrinking type or rewriting a mechanic.

Exactly three families are used: EB Garamond SemiBold for titles/numerals,
Gentium Book for rules/italics, and Arial for utility information. Rules are
9.35 pt (10.2 pt on sparse cards); exposed reminder prose is 7.51 pt. Event labels
have a small vector-like arrowhead, states use underlining, and limits are italic.
References are labelled "Involves" because they can be enablers or targets,
whereas intrinsic classifications stay on the exposed edge.

```sh
python -m pytest -q tests/test_v2_card_design.py tests/test_browser_card_layout.py
python tools/check_card_layout.py --surface v2 --require-browser \
  --pdf artifacts/print/cards-v2.pdf
make pages
```

The V2 check covers all 120 cards, six stack compositions, live-edge visibility,
footer collisions, dimensions and oversized-reminder detection. With `pdftotext`
installed it also rejects blank PDF pages and missing card IDs. Visually inspect
representative exported pages as well. The 7.5 pt reminders and fine engraving
still need an actual-size paper proof on the intended printer; these home-print
sheets do not provide commercial bleed. `make pages` also builds the unrelated
canonical rulebook and requires Typst 0.15.1.


The V2 family vignettes are production assets under `web/art/v2/`. They came from the recovered generated-image cache and are intentionally reused by card family rather than pretending the pool has 120 unique illustrations. Their source mapping is documented in `web/art/v2/README.md`.
