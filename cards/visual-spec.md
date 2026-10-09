# Physical-card visual specification

The cards are physical war-table components. Their exposed strips remain the
battlefield interface when formations are stacked.

## Shared face

All eight families use `web/physical-cards.js`, `web/physical-cards.css` and
`web/card-symbols.js` in the catalogue and playtest kit. Force, Bond, Name, Hero,
Tactic, Order, Stratagem and Narrative share the same aged parchment shell,
blue-and-gold ornament, dark ink and octagonal Command seal. The runtime webgame
has its own presentation.

The face order is **exposed strip → illustration → centered title → rules →
written classifications → footer**. Decoration comes from four reusable raster
assets; artwork, text, numbers and functional symbols remain live elements.
All eight families use the same four decorative frame rasters: `card-shell.png`,
`art-window.png`, `title-divider.png` and `command-seal.png`. Force keeps their
original sand/blue-gold treatment; the other families may apply one shared CSS
filter across all four frame PNGs. These per-family controls live together in the
`CARD FRAME COLOUR - TUNING PANEL` in `web/physical-cards.css`. Text, SVG symbols
and the card illustration itself remain unfiltered.

## Geometry and typography

- Cards measure **68 × 96 mm**.
- Formation layers shift down **10.5 mm**; their exposed strips never grow.
- Legal deployment/occupancy ranks use one three-bar row glyph. Every allowed rank
  is filled in that single glyph, so a Middle/Rear Force shows the middle and rear
  bars filled rather than two separate row icons. The glyph is only a summary:
  the rules body repeats the legal-row restriction in words.
- Nothing on the exposed top row may be rules-exclusive. Positional/state reminders
  are repeated in self-contained body prose using "While...", "If...", or "When..."
  rather than relying on terse labels alone.
- Illustrations are **25 mm** high, or **20 mm** when rules need more room.
- The identity-height variables remain **19 mm**, **18 mm** for dense faces, and
  **15 mm** for Heroes. When a written classification row is present, its **4 mm**
  is reclaimed from that identity allocation so the rules region becomes taller.
  The footer identity row itself lives inside the footer band and is vertically
  aligned with the Command seal, leaving the body space available to rules text.
  Every card begins that row with its family symbol and written family name, then
  a centred dot before any classifications the card itself has. No card family
  prints reference metadata as an "Involves" footer. Referenced classes belong
  in the rule text when relevant, **as words rather than repeated inline symbols**.
  Effect prose reserves at most two inline symbols for conditions and explicitly
  quantified Strength/Command impacts. Card types, classifications, ranks,
  movement verbs and ordinary references remain plain text.
- The footer reserves **15 mm** for the ID, revision, family identity,
  authored classifications, Unique label when applicable, and a **12.5 mm**
  raster Command seal.
- A4 landscape sheets hold **4 × 2 cards**: exactly **272 × 192 mm**, without gaps.

EB Garamond supplies titles and numerals. Titles range from 5.3 mm to 3.9 mm for
long Hero titles. Gentium supplies rules at **3.25 mm**, or **2.85 mm (8.1 pt)** on
dense faces. Placement text counts as a real rule block for density; a restricted
Force with another rule therefore receives the dense layout rather than relying
only on raw character count. Heroes retain both Force and Name rules, with mode and timing labels
inline to save vertical space. Vanilla cards leave their rules area empty.

## Exposed information and symbols

The exposed strip uses one fixed three-zone layout on every card: **left,
middle, right**. Left holds the family/Strength information, middle holds only
functional classification and row icons, and right holds only the exposed reminder
or status text. The three zones keep the same boundaries on every card, including
Heroes and cards with an empty middle zone.

All top-row text uses one font size and all primary top-row icons use one icon size.
Long reminders wrap within the right zone at that same size; there is no compact or
very-compact typography fallback. The strip keeps fixed outer padding and clips
nothing outside its own zone. Heroes show separate Force and Name values in the
left zone.

Human uses a profile medallion; remaining kinds retain circular outlines,
while roles and ranks use unframed silhouettes. The classification line repeats the symbols alongside their words.
Action uses a circled cross. These are functional SVGs, not decorative frames.

The exposed strip uses a single **2.45 mm** text scale and a single **3.8 mm**
primary icon scale. The fixed zones are **14 mm / 19 mm / remaining width** after
3 mm outer padding. Long reminders wrap in the right zone without shrinking.
Timing words and once-per-Battle sockets remain visible; hard row restrictions are
represented by same-size row icons in the middle zone. Full rules stay in the body.
The reference's sample wording does not replace the current card's wording or
classifications.

Non-formation strips use the same three zones: family symbol at left, family name
in the middle and status text such as “Played face-down” or “This Battle” at right.
The footer retains the authored card ID and build revision.

## Raster assets and artwork

The four authoring PNGs in `web/art/card-frame/` are `card-shell.png`,
`art-window.png`, `title-divider.png` and `command-seal.png`. They provide the
integrated corners/parchment, aperture, divider and cost seal. No semantic glyph
or additional scene is overlaid on the illustration.

Canonical illustrations remain under `web/art/cards/`; retained originals remain
in `cards/art-sources/`. Default focus is centered. Existing `art_focus_x` and
`art_focus_y` escape hatches accept percentages from 0% to 100%; invalid values
fall back to the center. No artwork is regenerated for this extension. The complete 128-card review found
16 portraits whose available faces were lost by the shorter window. Those cards
use `art_focus_y: "0%"` through the existing escape hatch; the other 112 remain
centered. These presentation fields do not alter any card wording or mechanics.
The canonical PNGs and retained originals are unchanged.

Some illustrations already cut subjects in their source images, including The
First Spear, The Old Guard, The Dust Riders, The Black Pursuers, The Iron Boars,
Elian and Mara. Focus cannot restore missing image content; those remain artwork
review debt.

The build publishes optimized per-card art and lossless, alpha-preserving WebP
frame derivatives. Frame sizes target roughly 300 dpi: shell 1134 px long edge,
art window 744 px wide, divider 640 px wide and seal 160 px square. Source PNGs
remain in the repository. Frame contents participate in asset hashes and the
source-archive print version; built URLs receive the stylesheet's cache version.

## Review

The optional print audit checks the current pool, stacked formations, long titles,
dense rules, numeric extremes, visible status/reminders and overlap detection.
Review the actual catalogue and selected deck PDFs as well: fitting geometry alone
does not establish readable typography or a good illustration crop.
