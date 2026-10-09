# Full physical-card coherence audit — Opening Orders pass

**Paper game, 9 October 2026.** Reviewed all **131 printed card identities**:
33 Forces, 24 Bonds, 20 Names, 11 Heroes, 14 Tactics, 11 Stratagems,
12 Narratives and 6 Orders. This pass does not alter the native game
engine or claim to have measured actual win rates.

Full per-card inventory and test-deck locations:
[`full-card-coherence-audit.json`](full-card-coherence-audit.json).
Every identity is present in the **six standard and four diagnostic
decks**, each containing 48 cards. There are **no exact duplicates**
among the printed rules texts. The existing Force tariff remains
`1 + ceil(Strength / 2) + premium`: 17 Forces cost 3C, 13 cost
4C and 3 cost 5C, totalling 118C for one copy of each Force.
All 11 Hero mode prices and the full 131 identity count are unchanged.

## The three replacements (already in physical test decks)

| Card | Existing place in decks | Distinct decision |
| --- | --- | --- |
| **Had Been Ordered Forward** (1C Bond) | Broken Oaths ×2 | Its Bonded formation, when selected to make an Opening Maneuver, can Move **one additional adjacent legal step**. Public investment, one order, no extra Attack or permanent Unnamed Maneuver exemption. |
| **Every Bow Was Strung** (1C Narrative) | Crown of Crows ×2 | **One** Bonded Archer chosen for Opening **Strike** can target opposing **Middle** instead of Rear. Still exactly one normal basic Attack; no passive Strength aura. |
| **The Scouts Had Warned Them** (1C Stratagem) | Broken Oaths ×1; Seer & Hidden Plans Lab ×2 | At the simultaneous **Opening Order reveal**, a Scout/Seer in the assigned Front may let you **change the destination** of one already-chosen Opening Maneuver starting there. No third order, no changed initiator or order type. |

No new artwork or identities are required because the existing card
titles, illustrations and deck IDs remain unchanged. These effects
replace the prior text, including the now-obsolete printed references
to passive Archer Strength and scouting an enemy Stratagem when set.

## Which effects happen when?

Every Battle, **including Battle I**:

1. Normal play continues until someone **Passes**.
2. The opponent takes a closing turn; the passer takes a closing turn.
3. Both commanders secretly write **two Opening Orders each** and
   reveal **all four together**.
4. Reveal any Stratagem triggered by this order reveal (*The Scouts
   Had Warned Them*) and resolve permitted order redirection.
5. Pay **Commit**, perform numbered simultaneous **Maneuvers**
   (including movement-triggered effects), then numbered simultaneous
   **Strikes** (including Attack prevention and counterattacks).
6. Resolve eligible end-of-Battle **Stratagems** in the one existing
   resolution reveal window, using the provisional board **after**
   Opening Orders. Settle Fronts, lose Command by **Strength deficit**,
   check Collapse, then clean up and recover.

The full 11-Stratagem timing matrix is
[`stratagem-opening-interactions.json`](stratagem-opening-interactions.json).

### Stratagem interaction inventory

| Stratagem | Trigger / response | How it differs from Opening Orders |
| --- | --- | --- |
| **The Scouts Had Warned Them** | Immediately after opening reveal | Change a chosen Maneuver destination after seeing the opponent's revealed plan |
| **The Battle Turned East** | After Rider movement, including Opening Maneuver | One extra Rider Move and Strength, not another Maneuver order; hidden, narrower than public Bond |
| **There Was No Road Back** | Named completion, including movement onto prepared layers | Attachment-reward movement or enemy Bond return, not an opening privilege |
| **No Step Back** | Attack affliction or hostile Tactic | Prevent harm from an Opening Strike; no new Attack |
| **The Archers Were Ready** | After an opposing Attack, including Opening Strike | Make an unused Archer basic Attack; a later assigned Strike with that Archer cannot also occur |
| **The Trap Closed** | After Raider/Skirmisher applies a negative marker | Return an affected enemy attachment; persistent economic threat |
| **The Ground Was Held** | Final Front resolution only | Unique tie/one-point-deficit condition calculated after opening orders |
| **The Lines Held** | Final Front resolution only | Late generic Move and conditional +2 |
| **The Center Must Hold** | Final Front resolution only | Captain/King directs another ally's Move and +2 |
| **The Flank Was Refused** | Final Front resolution only | Outer-Front Archer/Guard/Stronghold defensive Move and +2 |
| **Every Banner Turned Toward Them** | Final Front resolution only | Larger cross-Front Human Strength reinforcement, without movement |

**Reactions are not the final resolution window.** Normal trigger-based
Stratagems can still reveal when their trigger occurs during the
Opening Orders: this does not create a second *Front-resolution*
reveal window. Simultaneous Strikes check eligibility before either
side's attack consequences, so an attack-triggered Depletion does not
retroactively undo the opposing legal Strike.

## Overlap audit: what is genuinely different?

**The three Opening cards do not dominate one another.**
One changes distance, one changes legal Attack targets, and one
changes a secret *choice* in light of enemy orders.

- **Had Been Ordered Forward vs The Battle Turned East:** both can
  extend movement, but the Bond is face-up, requires a chosen Opening
  Maneuver by its Bonded formation, and does not boost Strength.
  The Stratagem is hidden, Rider-specific and reacts to a Move
  in/out of its assigned Front at any qualifying time. They can
  combine to produce multiple legal steps; the Stratagem resolves
  only once. This stacking is **a playtest watch**, not an infinite
  chain or a second Opening Order.
- **Every Bow Was Strung vs The Crow Archers:** Crow Archers can
  reach Middle with their printed basic Attack **when the opposing
  Frontline is empty**. The Narrative works **only for one
  Bonded Archer chosen for an Opening Strike**, but also when
  enemy Frontline is occupied. Neither adds a second Attack.
- **The Scouts Had Warned Them vs The Lantern Scouts,
  The Watchtowers of Eren, Iria and Before Sunset:** ordinary
  scouting reveals an enemy **face-down Stratagem** or affects
  cards and Strength during card-playing turns. The changed
  Stratagem instead reacts to the opponent's **revealed Opening
  Orders**, and can redirect only a Maneuver already chosen.

**Meaningful near-overlaps remain elsewhere, and should not be
misrepresented as proof of uniqueness.**

- **The Lines Held / The Center Must Hold / The Flank Was Refused:**
  all potentially produce late movement plus +2 Strength. Their
  generic, leader-dependent and outer-Front/class-dependent
  prerequisites do differ, but their *result* may feel too similar.
  Keep each as a **watch**, comparing actual uses before rewriting
  more cards.
- **They Had Gone Too Far / The Line Was Baited:** both push an
  opposing Frontline/Middle Force toward Rear, but the former
  costs 1C, works with a Scout or Skirmisher, and Shakes if
  unable to move; the latter costs 0C, needs a Skirmisher and
  Depletes only if a legal Move occurs. Their common successful
  position change overlaps; measure how often the different
  fallback/condition genuinely creates a separate choice.
- **Covered the Withdrawal Of / Kept the Gate For:** mirrored
  ahead/behind permission for Exhausted Maneuvers. These are
  deliberate spatial counterparts, although both suffer a
  rare-setup risk.
- **Held the Line For / Supported By:** both tax hostile
  Tactics, but protect different targets; the latter needs
  Middle positioning and shields the Rear behind, not itself.

## Overall assessment

Of 131 identities, **101** have coherent paper-game roles without
a special concern in this pass, **3** received new Opening Order
abilities, and **27** have *concrete playtest watches* rather than
claims of verified balance. These include 17 previous non-Force
watch cases and ten additional Force, Stratagem and Tactic risks
amplified by simultaneous orders or full-margin Command loss.

Main systemic risks are **uncapped Strength-margin losses** on
undefended Fronts; whether Commit×2 becomes the default over
Maneuver and Strike; several inexpensive late Move/+2 surprises;
and permanent attachment removal immediately increasing the
loser's Strength deficit. Another concern is how often the special
opening abilities actually activate when they compete against
two ordinary Opening Orders.

All **27 watch cases** and all **three new Opening Order cards** have
specific opportunity/alternative/failure prompts in the **77-case**
[focused playtest sheet](preplaytest-focus.json).

No additional identities, counters, global keywords, new Battle I
timing, or Hero prices were introduced. Printed cards, rulebook,
decks and timing tests were updated consistently, but **there is
no native-automated paper-game simulation**, and human playtesting
is still needed to establish usefulness, non-dominance and comeback
viability.
