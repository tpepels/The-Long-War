# V2 visual specification

The card face returns to the earlier Long War/Astra design language.

- 68 × 96 mm.
- Four by two on A4 landscape.
- Strong double frame and muted family-specific wash.
- Decorative geometric motif field so the card feels like a game object, not a document.
- No beige effect textboxes.
- Each effect is open typography separated by a fine rule.
- Timing words use compact bold sans labels; events have a small arrowhead, states an underline, and limits italic serif. No filled ability panels.
- Force and Bond expose a fixed 10.5 mm live-information edge.
- Hero Force and Name values use two separate crests. Never compress both into one circle.
- Command cost is an unlabeled faceted gem in the bottom-right. No visible word "COMMAND".
- Header geometry is fixed across all density classes so stacked edges align.

The exposed heading fixes the Strength position and classification baseline.
Complete live reminders start at the same second-row position, using up to two
lines; longer future text must be flagged rather than truncated or shrunk.
The Hero edge always prints shield Strength, “or”, and banner modifier as
separate values. Its live edge is explicitly labelled FORCE. The printed face
never changes when a Hero is used as a Name.

The Card Lab includes actual overlapping Force + Bond, Force + Name,
Force + Bond + Name, Hero-as-Force and Hero-as-Name proofs. These use the same
card component and dimensions as the catalogue and print export. No underlying
body is hidden or shortened to make the examples appear to fit.

Class references are secondary “Involves” bylines, never intrinsic classes or
an assumed target declaration. Battle-limited Narrative duration is explicit.
See `docs/card-printing.md` for reproduction and verification commands.


## Recovered family artwork

The interrupted Astra/Codex pass produced seven coherent engraved landscape images. They are integrated as **card-family vignettes**, not as arbitrary per-card illustrations:

- Force - `web/art/v2/force-march.png`
- Bond - `web/art/v2/bond-bound-spears.png`
- Name - `web/art/v2/name-tattered-banner.png`
- Hero - `web/art/v2/hero-helmet-laurel.png`
- Tactic - `web/art/v2/tactic-archer-volley.png`
- Stratagem - `web/art/v2/stratagem-war-map.png`
- Narrative - `web/art/v2/narrative-roadside-memorial.png`

The renderer desaturates and blends these into the parchment, then keeps the vector heraldry as a restrained overprint. The art may add character but must never carry rules information or alter fixed stack geometry.
