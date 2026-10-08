# Physical print implementation — cohesion sidegrades

**Implemented for print only:** physical card catalogue and 48-card deck sheets use `cards/print-overrides.json` over the existing 131-card pool. This is not an engine rules update. See `tools/print_cards.py` for the export. Webgame, native code, and `cards/cards.json` remain unchanged.

## Card changes (16 replacements)

| Card | Type | New Command cost (or unchanged) | New Strength (or unchanged) | Printed effect |
|---|---|---|---|---|
| The Damar | force | unchanged | Force 3 | PLAY - You may move another friendly formation in this Front one row toward its Frontline into an empty legal position. |
| The Crow Archers | force | unchanged | unchanged | ATTACK - If the opposing Frontline in this Front is empty, this Force's basic Archer Attack may target an opposing Middle Force. |
| The Ilyri | force | unchanged | Force 2 | PLAY - You may move this formation one position into an adjacent active empty position, if legal. |
| The Old Guard | force | unchanged | unchanged | MIDDLE - While in the Middle row, this Force screens the friendly Rear Force from basic Archer Attacks even while Shaken, but not while Depleted. |
| The King's Spears | force | unchanged | Force 3 | PLAY - If played into an empty Middle position, you may swap this formation with the friendly Frontline formation here, if both placements are legal. |
| The Wolf Skirmishers | force | unchanged | Force 4 | PLAY - You may move an opposing Frontline formation in this Front one row toward its Rear if that position is empty and legal. |
| Blocked the Road for | bond | unchanged | Bond +0 | BONDED - While this formation is Bonded, opposing card effects cannot move it. |
| Seized the Standard of | bond | unchanged | Bond +0 | PLAY - You may choose an opposing Bonded Formation in this Front. Return its Bond to its owner's hand. |
| Swore Again To | bond | unchanged | Bond +0 | PLAY - If playing this Bond completes a Named Formation, you may immediately Maneuver it once without spending another Action or Command. |
| Endured With | bond | unchanged | Bond +0 | PLAY - If this position contains a Force, give that Force Guarded. |
| Carried the Oath of | bond | unchanged | Bond +0 | BONDED - While this formation is Bonded, its Name text cannot be suppressed. |
| Had Been Ordered Forward | bond | unchanged | Bond +0 | BONDED - While this formation is Bonded, it may Maneuver without being Named. |
| Watched the Skies For | bond | unchanged | unchanged | PLAY - Draw 1 card, then put 1 card from your hand on top of your deck. |
| Mara | name | unchanged | unchanged | BECOMES_NAMED - Look at your opponent's hand. You may then move this formation one position into an adjacent active empty position, if legal. |
| The Lines Held | stratagem | 2 | unchanged | HIDDEN - Reveal before Strength is compared in this Front. If your Frontline here is empty, move a friendly Middle formation into it, if legal. It gets +2 Strength this Battle. |
| Fresh Orders | order | unchanged | unchanged | PLAY - Choose one of your Kings or Captains. You may move another friendly formation in its Front to an adjacent active empty position, if legal. |

## Printed-limit corrections (4)

- **The Crows Came Down** — its ACTION timing now visibly says **1/BATTLE**, matching the existing executable limit.
- **No Road Was Too Long** — its ACTION timing now visibly says **1/BATTLE**, matching the existing executable limit.
- **No One Would Be First to Leave** — its ACTION timing now visibly says **1/BATTLE**, matching the existing executable limit.
- **The King Had Given the Order** — its ACTION timing now visibly says **1/BATTLE**, matching the existing executable limit.

## Stacking and legibility

A Named Formation stacks **Force → Bond → Name**. The Force and Bond are behind the Name, leaving **10.5 mm each** visible. The print build and CSS now use that same overlap. The playable part of a buried Force/Bond is its exposed title-free header and rule strip; the full rule must not require lifting the Name or Bond.

- New one-shot **PLAY** effects occur immediately and need no reminder after the card is covered.
- Five newly revised Force/Bond rules remain live: **The Crow Archers** (expanded Archer Attack), **The Old Guard** (Shaken screening), **Blocked the Road for** (movement protection), **Carried the Oath of** (Name-text protection), and **Had Been Ordered Forward** (Unnamed Maneuver). All have explicit exposed-strip wording.
- **25 additional existing live Force/Bond effect reminders** have been clarified in the print export, without changing what those effects do.
- A separate print-only mechanics sheet now lists the current **four basic Attacks**, flanking, screening, Exhausted, Shaken, Depleted, and the three Boons.
- The print-only catalogue intentionally omits old executable `design_rules`; never feed it into the native engine or the Webgame.

## Layout and validation

The physical card dimensions remain **68 × 96 mm**, with the 10.5 mm exposed strip and original artwork/frames. Top-edge padding was adjusted to make room for up to three lines of reminder text. The dedicated printed-card checks are:

```sh
python tools/check_print_cards.py
python tools/check_card_layout.py --surface print --require-browser
```

For an actual printable site build:

```sh
TLW_PAGES_INSPECTION_ONLY=1 python tools/build_pages.py
```

`dist/data/cards.json` remains the canonical executable pool; `dist/data/print-cards.json` is the separate printed pool read by **Cards** and **Decks**.

**Validation status:** the print-only data has been checked against 131 card identities and every new/old live effect has an exposed reminder. JavaScript physical renderer smoke-check: 131 faces and six stack compositions rendered. The repository-native Python command and pixel-level Chromium layout/PDF check have **not** been run in this environment; local print proof remains required before physical production.

## Playtest focus

- Try the Wolf Skirmishers → Raider Attack breach and Crow Archers' new support targeting.
- Use Swore Again To to complete and instantly reposition a Named Formation.
- Test Old Guard + Endured With + Blocked the Road for against different kinds of disruption.
- Test whether The Lines Held's surprise movement is fair in both early and late Battles.
- Count how often the new 0-Command Fresh Orders movement matters, rather than merely improving hand quality.
- Watch for the most compressed exposed reminders in actual printed three-layer stacks. If any are not readable, change the corresponding text/ability rather than requiring card lifting.

**Next work must stay print-only unless engine work is explicitly authorized.**
