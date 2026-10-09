# Final physical card balancing audit — 9 October 2026

**Scope:** all **131** printed cards (canonical identities plus the physical
`print-overrides.json` overlay). The current native/Webgame engine uses
different gameplay and card definitions, so its historical AI matches cannot
establish physical tabletop win rates.

## Verdict

The underlying costs and ability roles are broadly coherent, but a static
audit found two remaining comparative imbalances: several passive supports
were priced as significant 3C specialist Forces despite a weak 2-Strength
floor, and five Hero Name modes cost more than comparable ordinary Names.

This pass makes **nine narrow print-only corrections**. None changes an
effect, classification, placement restriction, Hero Force cost, card identity
or rulebook mechanic. These are price/Strength judgments rather than measured
win-rate corrections.

## Family coverage and economics

| Family | Count | Result |
| --- | ---: | --- |
| Forces | 33 | Retain 1 + ceil(Strength / 2) plus assessed premium; four weak-floor supports normalized |
| Bonds | 24 | All 1C, but slot opportunity cost and different immediate/persistent utility prevent a simple dominance conclusion |
| Names | 20 | 1–4C; no defensible pool-wide change |
| Heroes | 11 | Independent Force/Name costs retained; five Name prices corrected |
| Tactics | 14 | 0–2C; require a relevant opposing target or setup |
| Stratagems | 11 | 1–2C, assigned to one Front, maximum one from hand per Battle |
| Narratives | 12 | 1–3C, Battle-only duration and Action costs |
| Orders | 6 | Five free-Command Orders still consume an Action and have eligibility conditions |

Force printed Command distribution remains **1 at 2C, 17 at 3C, 12 at
4C and 3 at 5C**. Significant even-Strength abilities retain their premiums.
No Force, Bond or Hero effects were altered.

## Four Forces: improve minimum on-board value

All remain **3C** and have exactly the same text and classifications.

| Force | Strength | Why the old value was poor |
| --- | --- | --- |
| The White Hands of Elara | **2 → 3** | Middle/Rear healer cannot make an offensive basic Attack; healing requires an afflicted Force directly ahead and another Action |
| The Relief Column | **2 → 3** | Middle-only; helps only an Exhausted Force directly ahead that can otherwise initiate a Maneuver |
| The Banner Singers | **2 → 3** | Tactic tax operates only while Named in Middle and only on *another* formation, requiring several preparations and an eligible opposing Tactic |
| The Lantern Scouts | **2 → 3** | Same-Front hidden-plan reaction is intermittent and requires being in Middle/Rear when the plan is set |

At 3 Strength they each pay the odd-Strength baseline of 3C, with the modest
or conditional ability covered by the rounding margin (premium 0).
The proactive **Field Train** and **Signal Company** remain 2 Strength / 3C;
they provide attachment tempo or repeatable unnamed mobility respectively.

## Five Hero Name-mode repricings

Hero Force prices, Force Strength and both sets of abilities stay unchanged.

| Hero | Name cost | Basis |
| --- | --- | --- |
| Kael, the Roadless | **2 → 1** | Narrow hidden-Stratagem peek relative to 1C Lysa's hand information |
| Alda, Keeper of the Ford | **3 → 2** | Conditional one-time cleansing/redirecting nearer the protection-Name tier |
| Yara, the Chronicler | **3 → 2** | Narrative recursion needs a populated discard pile and subsequent plays |
| Serai, Queen of Crows | **3 → 2** | Temporary Archer buff and 1C/Action paid debuff compared with 2C Corin's persistent Archer synergy |
| Doros, the Last Spear | **2 → 1** | Limited Tactic Strength protection and regain-1 compare to Edrin's 1C regain and once-per-Battle general affliction prevention |

Each still contributes only +1 as a Name and counts against the one
Hero-as-Name-per-Battle limit. This avoids paying a Force-mode premium for
effects that are not used in Name mode.

## War economy and deck exposure

There are six published 48-card decks, each with **16–18 Force cards** and
three flexible Heroes. An unmodified opening draw of 10 has less than a
1.1% chance of containing no Force in any deck. That says nothing about the
quality or affordability of the full opening hand.

| Deck | Force copies | Command to play *every Force copy* |
| --- | ---: | ---: |
| Banner & Blood | 16 | 61 |
| Crown of Crows | 16 | 59 |
| Oathforge | 16 | 56 |
| Blood & Spoils | 17 | 72 |
| The Last Watch | 17 | 50 |
| Broken Oaths | 18 | 64 |

Those are full-deck accounting totals, **not expected expenditures**.
Battle I starts at 20 Command with six available formation positions.
The Front expansion eventually opens twelve positions, but recovery declines
through 12, 9, 6, 3 and then 1 Command per surviving Battle. The
Battle-specific Action cost still competes with attacking, finishing
formations and reacting. The expensive Blood & Spoils Force curve is the
biggest risk of early Command starvation versus the much cheaper Last Watch.

## No-change decisions and watchlist

- **Tovan (4C Name):** continuous discounting and a 2C completion refund
  can snowball, but require a completed formation and further layers to be
  played. Count actual future Command saved before increasing this unusual
  economy engine's price.
- **The Ilyri (2 Strength / 3C):** moving itself on PLAY has limited value
  on an empty board, but offers a Skirmisher basic Attack and can Move into
  compatible prepared layers. Its *useful-play rate* needs observation before
  rewriting the ability.
- **The Battle Had Chosen Them, They Knew the Ground, The Long March:**
  can multiply a modest payment over many eligible formations in one Battle.
  The front/Named/Seer/Rider gates and Action opportunity cost matter.
  Measure actual Strength contributed, number of Maneuvers and Front flips.
- **Saturated Fronts:** after Battle III, strong Forces drawn late may be
  unplayable. Track occupancy and remaining Command before reworking card
  cost formulas or adding more retreat effects.
- **Conditional Tactics and Stratagems:** no additional general discounts
  justified without evidence of actual failed opportunities or deployment
  choices. Orders use an Action even when their Command cost is 0.

## Verification and evidence needed

Run `python tools/check_final_balance.py`, the existing Force/Hero pricing
checks, physical scenarios, printable-card validation and site/PDF build.
These checks can establish that the printed costs, effects, deck legality
and formatting are **consistent**. They cannot establish game balance.

To assess real relative strength, record mirrored physical-rule matches:
whether each card was drawn and could legally improve the next two Actions,
actual Hero Force/Name selection, Command consumed/recouped, ability activations,
number of targets or affected formations, Front outcomes genuinely changed,
Battle number, occupied positions, and final war result. Do not interpret the
old native/Webgame tournament results as evidence for this printed ruleset.
