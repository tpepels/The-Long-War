# Physical-card visual specification

The cards are physical war-table components. The exposed stack is the battlefield interface.

## Current checkpoint

The raster design is a **Force-only proof awaiting approval**. All 30 Forces have
been reviewed. Bonds, Names, Heroes, Tactics, Orders, Stratagems and Narratives
retain their current layouts and 20 mm illustration windows until that approval.
The full 128-card art audit and extensions to other families follow the Force review.

All families still use `web/physical-cards.js` and `web/physical-cards.css` for the
catalogue, playtest kit, stack proofs and print sheets. The runtime webgame has its
own presentation; this work does not change game semantics or canonical card data.

## Fixed geometry

- Card size: **68 × 96 mm**.
- Stack order: Force below Bond below Name, with each layer shifted down **10.5 mm**.
- Force face order: **10.5 mm exposed strip → 25 mm art → 19 mm centered identity region → rules → 15 mm footer**.
- The Force Command seal is **12.5 mm** square at the bottom right.
- A4 landscape sheets hold **4 × 2 cards**, a **272 × 192 mm** block with no gaps.

The exposed strip stays fixed regardless of title length or rules density. It
contains the role and Strength, classification pictograms, live buried reminders
and any hard row restriction. Reminders may wrap within the strip. Titles,
Command cost, Unique, card ID and completed PLAY effects belong on the full face.

Print cut boxes remain square and meet at shared seams. Rounded corners within
the raster shell are decorative and may remain visible inside those boxes.

## Force face and symbols

The Force uses an aged parchment shell with blue and gold ornament. Its shield
sits to the left of the Strength numeral; the Force face does not add a separate
crossed-weapons mark. Other families retain their current stat treatments,
including separate Force and Name values on Heroes.

The illustration precedes the centered EB Garamond title. Classification words
and their symbols sit beneath the title and divider. The exposed strip uses only
classification pictograms: circles for kind, diamonds for role and pennants for
rank. Front, Middle and Rear restrictions use row diagrams with a small lock.

Gentium rules prose is **3.25 mm**, or **2.85 mm** for dense Force layouts. Timing
labels, functional symbols and any once-per-Battle use socket remain live markup.
Vanilla Forces have an empty rules area; they do not gain a printed “No special
rules” placeholder. The Command numeral is live text over the raster seal, with
no visible COMMAND label. The footer keeps the card ID and build revision.

## Raster assets and artwork

Four reusable PNG authoring assets live in `web/art/card-frame/`:
`card-shell.png`, `art-window.png`, `title-divider.png` and `command-seal.png`.
They supply the shell, aperture ornament, title divider and cost seal. These are
the only decorative overlays; no semantic glyph, watermark or extra scene may
be composited over the illustration.

Every card still uses `web/art/cards/<card-id>.png`. The **128 canonical cards and
128 per-card illustrations are unchanged** at this checkpoint. All Force art
uses centered `50% 50%` focus. Optional `art_focus_x` and `art_focus_y` values
accept percentages from 0% through 100%; invalid values fall back to the center.

The Force review found existing subject-head crops on The First Spear, The Old
Guard, The Dust Riders and The Black Pursuers (`the-black-company`). Their
retained originals already cut those heads; no recrops were made for this proof.

The Pages build preserves the PNG sources and publishes lossless, alpha-preserving
WebP frame derivatives under `dist/art/card-frame/`, sized near 300 dpi at their
printed dimensions: shell 1134 px long edge, art window 744 px wide, divider
640 px wide and seal 160 px square. Only the built CSS switches these frame URLs
to WebP. Frame content participates in the
static asset digest and source-archive print version; built frame URLs receive
the same cache version as the stylesheet.

## Acceptance

- Exposed information remains readable with the next stack layer in place.
- Force art precedes its centered title and written classifications.
- Rules remain complete, readable and clear of art, footer and cost seal.
- Shared raster ornament preserves its transparency without covering scene content.
- Catalogue, deck sheets and stack proofs use the same renderer.
- Other card families remain at their current presentation until Force approval.
