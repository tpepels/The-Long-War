# V2 physical-card visual specification

The cards are physical war-table components. The exposed stack is the battlefield interface.

## Fixed geometry

- Card size: **68 × 96 mm**.
- Force bottom, Bond middle, Name top.
- Each additional card is shifted downward **10.5 mm**.
- The exposed 10.5 mm edge is exactly **one horizontal row**.
- Browser and print use the same renderer.

Nothing may change the top-row baseline: not title length, rules density, card family, or Hero mode. The stat group and classification pictograms keep their full geometry; the live reminder occupies the flexible remainder of the row. The title/meta region also has fixed height so the illustration begins at the same vertical coordinate on every card.

## What belongs in the exposed row

Only information that can still matter while most of the card is covered:

1. card role + Strength;
2. classifications;
3. live buried state/ability;
4. hard row restriction, where one exists.

Do not put title, Command cost, Unique, card ID, finished PLAY text, flavor, or full prose in the exposed edge.

## Symbol grammar

### Card roles

Force = shield. Bond = linked chain. Name = standard/banner.

Hero shows two adjacent role stats: Force shield value and Name banner modifier. Do not compress both into one circle.

### Strength

Strength has its own crossed-weapons symbol. Card role and Strength are separate concepts and separate marks.

### Classifications

The enclosure shape communicates the classification layer:

- Kind = circle: Human, Ship, Stronghold.
- Role = diamond: Archer, Guard, Scout, Rider, Skirmisher, Raider, Healer, Spearman, Steward, Builder, Seer.
- Rank = pennant: King, Captain, Veteran, Heir.

The exposed edge shows classification pictograms only. The full face spells classifications out beneath the title with the same symbols.

Do not turn complete ability semantics into rebus strings. Symbols identify repeated concepts; the live buried reminder remains a very short text fragment such as `ENEMY -1`, `IGNORE TACTIC`, or `ARCHER/SCOUT +1`.

### Rows

Front, Middle and Rear use a three-row diagram with the relevant bar filled.

A hard row restriction is the row diagram plus a small lock, never a long FRONT ONLY label.

### Timing

The exposed edge uses timing pictograms:
- Action = diamond/action mark.
- Reaction = returning arrow.
- Bonded = chain.
- While Named = banner.

If an Action or Reaction is once per Battle, print an empty circular **use socket** beside the timing symbol. Cover the socket after use and clear it for the next Battle.

Once-per-Battle is a limit, never a timing window.

### Command

Command uses the d20/faceted-die symbol in rules and exposed reminder grammar.

The bottom-right printed card cost uses the original dark octagonal Command seal with the numeral centered inside it. There is no visible COMMAND label.

## Full face

The full card returns to words where words are better:

- dominant EB Garamond title;
- classification symbols plus written names below the title;
- generated illustration;
- open rules typography;
- quiet footer.

Symbols support scanning. They do not replace sentence grammar.

## Illustration

The generated illustration is the sole illustration layer.

Where a per-card illustration exists under `web/art/v2/cards/`, use it. The eight family illustrations remain fallbacks for cards that do not yet have individual art.

No vector heraldry, watermark drawing, or second image may sit over the illustration.

All card families, including Force, use the shared **20 mm illustration window** and shared card-body layout. The effective shared art aperture is 62.36 × 20 mm (3.118:1). Force source illustrations are normalized offline to a canonical 1248 × 400 raster matching that aperture, with the subject-preserving crop baked into the PNG. Runtime artwork therefore defaults to centered `50% 50%`. Optional card data fields `art_focus_x` and `art_focus_y` remain available only as escape hatches; they must not be used instead of normalizing inconsistent source dimensions.

## Rules

Rules are printed directly on parchment. There are no beige rule boxes.

Each effect has a timing pictogram, bold sans timing word, optional once-per-Battle use socket and Gentium rules prose.

Separate effects with space and a fine rule.

## Frame and depth

Use one strong outer physical cut line. Do not draw another complete rounded rectangle inside it.

Depth comes from paper variation, subtle edge light/shadow, restrained corner marks, illustration depth, ink/metal contrast on stats and cost, and family-specific accent color.

Never use floating UI panels or card-inside-card boxes.

## Non-stacking card families

Tactics, Orders, Stratagems and Narratives do not waste space on the rigid battlefield strip. They use an expressive family crown while sharing the same frame, typography, illustration treatment, icon vocabulary and cost treatment.

## Acceptance

- one exposed row only;
- symbols, not classification prose, in that row;
- full classification words on the full face;
- Hero Force/Name values separate;
- no need to lift a stack;
- no image overlay;
- no rules/art overlap;
- no Command word at the cost;
- no inner rounded-rectangle document frame;
- print and browser share the component.

## Force layout

Force uses the same shared physical-card renderer as the other card families. It keeps the 10.5 mm exposed formation row through `stackEdge(card)`, then uses the standard identity block, 20 mm illustration window, rules area, footer and Command seal. Force-specific styling is limited to its family color variables and fallback illustration.

Per-card illustrations use the normal filename convention `web/art/v2/cards/<card-id>.png`. Candidate illustrations whose filenames exactly identify a Force card should be promoted to that path rather than wired through special-case CSS or JavaScript.
