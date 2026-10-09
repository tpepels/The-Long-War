# Combat and conditions — physical quick reference

> **Print version, not native/Webgame rules.** The definitive rules are in [the rulebook](../rules/rulebook.md). Cards use the printable overlay in `cards/print-overrides.json`.

## Turn and Pass

Before drawing, either **Pass** (a complete turn with no draw and no Actions) or draw **1** and take up to **2 Actions**: play a card, use a printed ACTION ability, Maneuver (1 Command), Attack, or cycle two cards into one. Passing voluntarily starts exactly two closing turns: opponent (draw, up to 2 Actions), then passer (draw, up to 2 Actions), then Battle resolution.

## Formation Strength and classifications

Force Strength + printed Bond modifier + printed Name modifier (including Hero-as-Name) + applicable effects, then subtract **1 for Exhausted**, **1 for Depleted**, **2 for Shaken**, and **1 if flanked**. Apply a minimum of **0 per formation**. Separate conditions stack; duplicate markers of one type do not. Add all formations across a Front. Attachments contribute no Strength without a Force. An attached Name contributes all its classifications to the Force; multiple Attack types still allow **one Attack per Force per Battle**. Separate card effects stack; one effect is applied only once per formation.

| Classification | Basic Attack target | Result |
| --- | --- | --- |
| Archer | Opposing Rear Force in same Front | Exhaust |
| Skirmisher | Opposing Middle Force in same Front | Shake |
| Raider | Opposing Middle or Rear Force if opposing Frontline empty | Deplete |
| Rider (attacking from Frontline or Middle) | Opposing flanked Frontline Force in adjacent active Front | Shake |

A Middle Guard screens the Rear from a basic Archer Attack unless Shaken or Depleted, except when a card grants explicit screening while Shaken.

## Flanking and markers

A Frontline Force is flanked when its opponent has a Frontline Force in an adjacent active Front but it has no matching friendly Frontline Force there. **−1 Strength while flanked** (only once even if threatened on two sides). The penalty disappears when the flank closes; **no flank marker**.

| Marker | Meaning |
| --- | --- |
| Exhausted | **−1 Strength**; cannot initiate ordinary Maneuvers. Can still Attack unless also Depleted. |
| Shaken | −2 Strength to this formation and loses basic Guard screening. |
| Depleted | **−1 Strength**; cannot Attack or use ACTION on Force, Bond or Name in its formation; loses basic Guard screening. |
| Guarded | Prevent next affliction, including defeat Exhaustion, then remove. |
| Inspired | Remove and prevent Shaken while present. |
| Empowered | Next Attack ignores screening, but not range or flanking rules. |

## End of Battle

1. Eligible pre-comparison and tie-related Stratagems are chosen **secretly and revealed simultaneously** in a single window, checked against the state before reveals.
2. Resolve independent effects, prevent prevented actions, cancel contradictory movement, then compare each Front.
3. Resolve Battle-end effects, lose 1 Command per lost Front, and check Collapse at 0 or less **before** recovery.
4. Before clearing Boons, Guarded can prevent loss-based Exhaustion. Clear old afflictions and Boons, then apply **one new Exhaustion token** to each unprotected Force in each lost Front. These tokens last **through the next Battle**, unless removed early.
5. Discard Battle-duration Narratives and unused Stratagems, clear used Attack/once-per-Battle markers, recover Command, refill hands to 10, open the next Front, and let the non-passer start.

## Card-timing reminders

PLAY resolves when played (also when prepared), not when the prepared card later attaches. Bonds with a legal other-formation target can resolve PLAY even when prepared. House of Reed may attach two prepared layers one at a time with one ACTION, and completion rewards follow BECOMES NAMED triggers. BECOMES NAMED can retrigger upon rebuilding after a genuine loss of Named status. Attached Force/Name classifications combine. ACTION takes a turn Action. ATTACK modifies an existing Attack. Move into compatible prepared cards to attach them; don't overwrite an occupied Bond/Name layer. Printed once-per-Battle use stays spent even if a card is returned and replayed. Narratives stay face-up until Battle end (max **4**). A set Stratagem is publicly assigned to an active Front and optionally revealed when eligible.

A condition tracker alongside a formation should not obscure buried live reminders on the exposed 10.5 mm edges.
