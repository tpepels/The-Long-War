# Physical stacking and rules-text audit

Generated against 131 card definitions. **No card artwork, layout components, CSS, raster assets, art focus or 10.5 mm overlap geometry was modified.** This is a content-level audit, not a rendered print proof.

## Inventory

- Forces: 33; simple: 12.
- Bonds: 24; simple: 8.
- Names: 20; single printed effect: 8.
- Heroes: 11, dual-mode rules remain deliberately more involved.

## Exposed-strip risk

There are **25** non-PLAY Force/Bond effects, including **22** whose full prose exceeds a rough 65-character readability budget. This is a triage threshold, **not** a measured physical text-fit test. The exposure strip is 10.5 mm. Do not shorten visible rules into misleading mnemonics or silently resize manually positioned layout elements. Review each flagged card against its actual rendered strip; either convert to a one-time PLAY effect with equivalent timing or relocate a complex live ability to a visible Name/Hero.

| Card | Layer | Effect timing | Effect characters | Triage |
|---|---|---|---:|---|
| The White Hands of Elara | force | action | 80 | **Needs rewrite/physical inspection** |
| The Red Shields | force | front | 110 | **Needs rewrite/physical inspection** |
| The House of Reed | force | action | 128 | **Needs rewrite/physical inspection** |
| The Grey Riders | force | mobile | 44 | Inspect exposed strip |
| The Grey Riders | force | tireless | 40 | Inspect exposed strip |
| The Dust Riders | force | bonded | 63 | Inspect exposed strip |
| The Black Pursuers | force | action | 131 | **Needs rewrite/physical inspection** |
| The Thornbow Hunters | force | rear | 122 | **Needs rewrite/physical inspection** |
| The Late Banner | force | bonded | 104 | **Needs rewrite/physical inspection** |
| The Banner Singers | force | while_named | 111 | **Needs rewrite/physical inspection** |
| The Vardai | force | action | 85 | **Needs rewrite/physical inspection** |
| The Serekh | force | front | 134 | **Needs rewrite/physical inspection** |
| The Relief Column | force | middle | 106 | **Needs rewrite/physical inspection** |
| The Field Train | force | action | 117 | **Needs rewrite/physical inspection** |
| The Signal Company | force | middle | 110 | **Needs rewrite/physical inspection** |
| Followed | bond | while_named | 76 | **Needs rewrite/physical inspection** |
| Covered the Withdrawal of | bond | bonded | 95 | **Needs rewrite/physical inspection** |
| Held the Line for | bond | bonded | 66 | **Needs rewrite/physical inspection** |
| Trusted | bond | while_named | 70 | **Needs rewrite/physical inspection** |
| Marched Beneath the Banner of | bond | bonded | 123 | **Needs rewrite/physical inspection** |
| The Lantern Scouts | force | continuous | 111 | **Needs rewrite/physical inspection** |
| The River Raiders | force | action | 167 | **Needs rewrite/physical inspection** |
| The Watchtowers of Eren | force | rear | 107 | **Needs rewrite/physical inspection** |
| Kept the Gate For | bond | bonded | 96 | **Needs rewrite/physical inspection** |
| Supported By | bond | bonded | 112 | **Needs rewrite/physical inspection** |

## Rules inconsistencies still requiring harmonization

- Existing executable card effects include legacy text such as 'flanking cannot Exhaust' even though the proposed core flanking rule no longer applies Exhaustion.
- Some cards still refer to 'temporary negative marker', '-Strength' and old suppression rules. New condition vocabulary is not fully executable.
- `combat_redesign_proposal` contains planned revisions that are not the printed or executable canonical card text; catalogue reflects current executable text only.
- Six-condition print-and-play tracker is specified, not physically printed or validated against each manually designed card.
- Current native runtime has a signed-8-bit card index and a 128-card cap; the 131-card canonical pool is not fully representable until the index format is migrated. Do not raise `MAX_CARDS` alone.

## Preservation requirement

All future fixes must preserve `web/physical-cards.css`, `web/physical-cards.js`, PNG frames, illustration windows, artwork and other approved hand-designed geometry unless individually authorized. Text rewrites must be checked in the existing layout, not used as a reason to redesign it.
