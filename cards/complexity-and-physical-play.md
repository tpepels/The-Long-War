# Physical play and complexity budget

This is a design constraint for the card pool, not a substitute for compiling and playtesting card effects.

## Card complexity targets

- **Forces:** 12/33 currently have no printed special effect. Inherent classification Attacks are not counted as printed effects. These are meaningful basic combatants or stable defensive bodies.
- **Bonds:** 8/24 have no printed special effect. These remain valuable as the required middle layer of a Named Formation and should not be burdened with rules for the sake of having text.
- **Names:** 8/20 now have one visible becomes-Named effect; the remaining 12 retain two effects. These eight Names still complete a Named Formation and enable Maneuver, but their one-time value must be tested against more powerful Names.
- **Heroes, Narratives, Stratagems:** reserve exceptional complexity for visible, limited, or one-shot choices; major battlefield transformations must be priced for how many Fronts they can affect.

## Physical stacking is authoritative

Stack order is Force (bottom) > Bond (middle) > Name (top). Only the top 10.5 mm of the buried Force and Bond remains exposed. Their persistent effects are legal designs **only when the entire ongoing effect is readable from that visible strip**. A short mnemonic that requires lifting cards to decode the full rule is insufficient. Effects that completely resolve when played may be hidden afterward. A card cannot require turning or lifting a stack to learn an exception during play.

Guard/Archer/Raider/Rider classifications can carry **intrinsic** basic attacks without printed text; the reference sheet, not buried effect prose, teaches those attacks.

## One compact condition tracker

Avoid separate piles of six bespoke condition tokens. Use one **six-cell condition strip per affected formation**, immediately beside its position (not over the Force/Bond/Name stack), and six checkmarks or generic small cubes. The strip labels **E / S / D / G / I / P** for Exhausted, Shaken, Depleted, Guarded, Inspired, Empowered. Every condition is binary and clears at Battle end. A Force may have more than one simultaneously. An ordinary coin/cube marks that a Force has used its Attack this Battle; this is **not** an affliction or Boon.

A print-and-play reference can supply one reusable condition track per battlefield position, preprinted on a playmat or on small movable paper strips. A paperclip-on-edge alternative works only if it doesn't cover active rules text. No physical flanking marker is required: flanking is evaluated from neighboring active Frontlines and has no intrinsic penalty.

## Command pricing rubric

- 1: modest conditional cards, simple Bonds and utility.
- 2: straightforward Forces, ordinary tactical specialists.
- 3: stronger Force bodies, meaningful tactical disruption or flexible movement.
- 4: powerful persistent Names/Heroes or whole-Front rearrangements.
- 5: exceptional multi-Front effects only after playtest evidence.

Price expected value, repeatability, persistence and opportunity cost, **not word count**. The changes reprice Grey Riders (3), Black Pursuers (4), Namar (4), Iven (4), Rovan (4), No Road Was Too Long (4), The King Had Given the Order (3), The Lines Held (3), The Trap Closed (3). Plain Iron Boars remain cost 3 and Strength 5. Check late-war Command affordability before further increases.

## Canonical/data integration caveat

The common Attack/affliction/Boon rules have been designed, but several proposed powers are stored as `combat_redesign_proposal` in card data and are **not executable**. Do not swap these into printed `effects` without matching executable `design_rules` and runtime/UI support. The deck and catalogue need regeneration when executable effects are integrated. The native 128-card-identity limit versus 131 card entries remains unresolved; **do not raise MAX_CARDS while card indices are signed int8**.
