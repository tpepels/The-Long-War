# V2 physical-card visual specification

The design must work first as a printed tabletop component and second as a browser preview.

## Stack geometry

Cards are 68 × 96 mm.

Force is the bottom card, Bond the middle card, Name the top card. Each additional card is shifted down by exactly 10.5 mm.

The exposed 10.5 mm edge is **one horizontal row only**. Do not split it into a heading row plus a reminder row.

The row contains, from left to right:

1. Strength/stat crest or type emblem;
2. classifications / compact identity;
3. only the live buried reminder or row restriction that must remain readable.

The type symbol and family treatment already identify Force/Bond/Name. Do not cram redundant labels into the strip.

Hero Force and Name values remain separate adjacent stat marks. Never combine them into one circle.

## No-lifting rule

A player must never lift the Name to inspect the Bond or lift the Bond to inspect the Force.

PLAY text may disappear after resolving. Any ACTION, REACTION, BONDED, or WHILE NAMED rule that can still matter while a Force or Bond is buried must be represented completely in the exposed row.

## Illustration

The recovered generated family image is the illustration.

There must be **one image layer only** in the art field.

Do not place the old vector heraldry motif on top of the generated image. Heraldry remains useful for small type/stat symbols, but not as a second illustration.

The image receives only very light paper/edge grading. It should remain visibly detailed and should be the main visual focus of the card.

Rules text is a separate layout region below the image and may never overlap it.

Sparse cards may devote more height to art. Dense cards may reduce art height, but not by allowing rules to invade the image.

## Frame

Use one strong physical outer cut line.

Do not put a second complete rounded rectangle inside it. Interior structure comes from restrained corner marks, the exposed-edge rule, the illustration boundary, and the footer rule.

The frame should feel like a game component, not a slide, UI panel, or bordered document.

## Title and rules

Title: EB Garamond, dominant and left aligned.

Rules: Gentium Book, open on the parchment.

Utility/timing/classification labels: Arial.

Separate multiple effects with spacing and a fine rule. Do not put effects inside beige boxes.

## Command cost

The bottom-right cost is one integrated faceted seal with only the numeral. No visible COMMAND label and no product/version wording competing with it.

## Density

The component may use sparse / normal / dense / very-dense interior layouts.

Those variants may change art height and rules type size. They may **not** change:

- card dimensions;
- exposed-edge height;
- stack-row baseline;
- stat placement;
- classification baseline;
- cost anchor.

## Acceptance criteria

- one exposed row;
- generated image unobstructed by vector art;
- no rule text over image;
- no complete inner rounded-rectangle outline;
- all stack combinations remain readable without lifting;
- Hero Force and Name stats remain distinct;
- print and browser use the same renderer.
