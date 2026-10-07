# Physical-card visual specification

The cards are physical war-table components. Their exposed strips remain the
battlefield interface when formations are stacked.

## Shared face

All eight families use `web/physical-cards.js`, `web/physical-cards.css` and
`web/card-symbols.js` in the catalogue and playtest kit. Force, Bond, Name, Hero,
Tactic, Order, Stratagem and Narrative share the same aged parchment shell,
blue-and-gold ornament, dark ink and octagonal Command seal. The runtime webgame
has its own presentation.

The face order is **exposed strip → illustration → centered title → written
classifications → rules → footer**. Decoration comes from four reusable raster
assets; artwork, text, numbers and functional symbols remain live elements.
All families still use the same renderer and raster furniture, but the parchment
receives a restrained family tint so card types can be distinguished at a glance:
Force umber, Bond teal, Name cobalt, Hero violet, Tactic crimson, Order olive,
Stratagem slate and Narrative burgundy.

## Geometry and typography

- Cards measure **68 × 96 mm**.
- Formation layers shift down **10.5 mm**; their exposed strips never grow.
- Illustrations are **25 mm** high, or **20 mm** when rules need more room.
- The centered identity region is **19 mm**, **18 mm** for dense faces, and
  **15 mm** for Heroes.
- The footer reserves **15 mm** for the ID, revision, family mark, Unique label
  when applicable, and a **12.5 mm** raster Command seal.
- A4 landscape sheets hold **4 × 2 cards**: exactly **272 × 192 mm**, without gaps.

EB Garamond supplies titles and numerals. Titles range from 5.3 mm to 3.9 mm for
long Hero titles. Gentium supplies rules at **3.25 mm**, or **2.85 mm (8.1 pt)** on
dense faces. Heroes retain both Force and Name rules, with mode and timing labels
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

Human uses a profile medallion, Spearman an upright spearpoint, and Veteran
double chevrons. Kinds retain circular outlines; roles and ranks use unframed
silhouettes. The classification line repeats the symbols alongside their words.
Action uses a circled cross. These are functional SVGs, not decorative frames.

Strength is 6.4 mm. Exposed reminders are 2.7 mm, reduced to 2.35 mm for longer
or multiple reminders. Timing words, once-per-Battle sockets and hard row
restrictions remain visible; full rules stay in the body. The reference's sample
wording does not replace the current card's wording or classifications.

Non-formation strips show the family name. “Played face-down” and “This Battle”
appear at the right of those strips, where they remain visible independently of
title length. The strip content sits slightly lower within the fixed 10.5 mm
exposed edge to give the top ornament more breathing room. The footer retains the
authored card ID and build revision.

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
