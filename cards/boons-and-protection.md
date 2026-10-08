# Boons, protection and support — combat design

> Design specification, **not executable card data yet**. This document records the approved direction for integration with the Attack system. Do not treat proposals as implemented until the card compiler, engine, UI and catalogue agree.

## Universal Boons

Boons are beneficial formation markers. They move with the formation, do not stack with themselves, and **all clear at Battle end** together with Exhausted, Shaken and Depleted.

- **Guarded:** prevent the next affliction that would be applied to this Force, then remove Guarded. It does not prevent movement, attachment loss or direct Command effects.
- **Inspired:** the Force cannot become Shaken. Remove Shaken when it gains Inspired. If Inspired ends, the removed Shaken marker does not return.
- **Empowered:** the Force's next Attack may ignore **screening**; remove Empowered after that Attack. It does not ignore legal target rank, the flanked condition for Rider Attacks, or the once-per-Battle Attack limit.

Boons do not grant an extra Attack or bypass Depleted's prohibition on attacking. Order of resolution: verify eligible attacker and target; apply screening (including Empowered); permit named Reactions; determine the affliction; apply Guarded/Inspired prevention; consume relevant one-use Boons. A prevented affliction is not considered inflicted for follow-up effects.

## Defence roles

**Guards and shields — interception:** Middle Guards screen the Rear Force directly behind from basic Archer Attacks, unless the Guard is Shaken or Depleted. Specialized Shields can intercept an attack on a directly adjacent friendly formation once per Battle; intercepting changes the target, subject to the printed restriction. It does not automatically grant Guarded.

**Strongholds and castles — fixed protection:** positional protection for Rear formations, prepared Bonds/Names and attachment security; use placement restrictions and avoid generic Strength boosts. They should resist Raiders differently from Guards resisting Archers.

**Ships — evasion and transport:** allow limited repositioning, rescue or transfer of a formation; legal position, active-Front and restricted-row rules still apply. A defender relocated by a Reaction can invalidate a declared attack target; the attack still uses its allowance if declared legally.

## Support roles

**Healers:** remove an existing affliction from a formation; stronger versions remove multiple distinct afflictions, once per Battle or by spending an Action.

**Druids:** grant Guarded, Inspired or Empowered, sometimes trading one affliction for another. Druids should not simply duplicate Healers.

**Stewards and suppliers:** prevent or remove Depleted, recover supplies, and move prepared components without granting extra generic actions.

**Carriers and messengers:** reposition prepared Bonds/Names or transfer a Boon between adjacent friendly formations; movement remains orthogonal.

## Proposed reassignments (replace rather than enlarge)

- The Red Shields: intercept one hostile Attack targeting friendly Force directly ahead/behind, once per Battle.
- The Old Guard: retain reliable screening while in Middle, even when afflicted (premium Guard identity).
- The House of Reed: protect attached Bonds and Names of Rear formations from hostile return-to-hand in this Front.
- The Watchtowers of Eren: keep anti-Stratagem scouting; add no generic bonus.
- Seven Black Ships: choose between opportunistic raid and short defensive relocation; do not grant additional Attack.
- The White Hands of Elara: remove any one affliction from a friendly Force directly ahead.
- The Field Train: remove Depleted from the friendly Force directly ahead, once per Battle; retain prepared-card support only if it fits card density.
- The Relief Column: remove Exhausted from a friendly Frontline Force directly ahead.
- Replace weaker numerical Narrative effects with a Druid-inspired protective omen and/or terrain-changing consequence, without increasing the card pool.
- Replace redundant protection Bonds with ones that grant Guarded, Inspired or transfer a Boon, using clear PLAY or once-per-Battle timing.

## Implementation and balance requirements

Do not write rules-only abilities into `cards/cards.json` while leaving the executable `design_rules` empty: canonical cards are compiled by the native runtime and validators require one spec per printed effect. Do not grow beyond the native 128-identity capacity without migrating signed 8-bit card indices first. Track the existing 131-card discrepancy separately. Keep CI advisory during active mechanic development, but do not hide actual native crashes or serialization errors.
