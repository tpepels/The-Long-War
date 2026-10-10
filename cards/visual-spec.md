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
- The **full rules** use icons only for an explicit reference to another
  card family or classification, at most two distinct referents per effect.
  Strength, Command, outcomes, timing labels, and Force/Name Hero mode labels
  remain prose. All other structural icons stay on the exposed edge,
  footer, Command seal and legal-position strip.
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
  in rule text when relevant, using selective card-family or classification
  symbols only when another card is referenced. Do not iconize routine words.
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

The exposed strip retains **left, middle, right** order on every card. Left
holds family/Strength information; middle holds functional classifications and
legal-row icons; right holds a short visible reminder or status. For formations,
left and middle take the width their actual contents require, and the right
uses the remaining width. The zones do not have fixed boundaries across cards.
The strip itself remains **10.5 mm** high, so physical stacking is unchanged.

All top-row text uses one font size and all primary top-row icons use one icon size.
Long reminders wrap in the available right space at that same size; there is no
compact or very-compact typography fallback. The zones must not cut off their
contents at arbitrary column boundaries. Text remains confined to the fixed
physical strip height. Heroes show separate Force and Name values in the left
zone.

Human uses a profile medallion; remaining kinds retain circular outlines,
while roles and ranks use unframed silhouettes. The classification line repeats the symbols alongside their words.
Action uses a circled cross. These are functional SVGs, not decorative frames.

The exposed strip uses a single **2.45 mm** text scale and a single **3.8 mm**
primary icon scale. Formation zone widths are **content / content / remaining**.
Event family labels occupy their intrinsic width while the side columns share
remaining room. Long reminders wrap in the right zone without shrinking.
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
in `cards/art-sources/`. **Every card now defaults to top-aligned artwork**:
`art_focus_y: "0%"` shows the source image’s upper edge in the illustration
window, cropping the bottom when `background-size: cover` needs to crop vertically.
Horizontal alignment remains centered by default. The `art_focus_x` and
`art_focus_y` fields remain available for intentional per-card exceptions and
accept percentages from 0% to 100%; invalid or absent values fall back to the
respective horizontal (50%) or vertical (0%) default.
The illustration retains the existing fixed-height window and 68 × 96 mm card
geometry; changing the default does not regenerate assets, change rules or modify
manual card layout settings. Top alignment cannot reveal material already absent
from the original illustration.

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
