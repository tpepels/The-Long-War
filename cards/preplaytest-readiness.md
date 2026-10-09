# Before the next physical playtest: usefulness gate

**9 October 2026 — prospective design audit; not experimental proof.** This review
uses the **131 printed identities** assembled by `tools/print_cards.py`, not the
native/Webgame rules. The card pool and all six standard / four diagnostic
48-card decks stay fixed. The previous pricing audit remains authoritative for
the tariff; this pass tests whether cards can be worth *using*.

Run the repeatable gate:

```bash
python tools/check_preplaytest_readiness.py
python tools/check_preplaytest_readiness.py --inventory > /tmp/tlw-card-opportunities.txt
python tools/check_print_cards.py
python tools/check_physical_combo_decks.py
```

`--inventory` lists **every printed card**, its normal value or absence of
one, printed mode cost, standard and diagnostic deck appearances, whether it has
an individual focus probe, and the complete counterfactuals. Each of the 44
focus cases in [preplaytest-focus.json](preplaytest-focus.json) gives an
**opportunity**, an **alternative use of Command/Actions**, and a **failure
signal**. This is test design, not an assertion that the opportunity has
actually occurred.

## 1. Dominance: inferior choice at the same cost

**Fixed two unambiguous design weaknesses.** No copies or card identities were
added or removed.

| Card | Earlier problem | New physical-only decision |
| --- | --- | --- |
| **All Banners Forward** | 1C King/Captain ACTION shutdown was generally dominated by 1C **They Let Them Through**, which shut down any formation and removed Named Strength too. | 1C leadership-specific disruption: give a King/Captain formation's Force **Shaken**; if Named, apply **−1 Strength** to another opponent in that Front. A different reward, target and counterplay. |
| **The Ilyri** | Its 3C, 2-Strength on-PLAY Move into an adjacent **empty** square could usually be duplicated by deploying it into that square in the first place. | On PLAY, swap with a friendly formation directly ahead/behind, if legal, and give the displaced Force **Guarded**. Swapping with an **occupied** square cannot be reproduced by picking a different placement. Its 2-Strength body remains a deliberate downside. |

**Contrast cases preserved:** the 0C **The Line Was Baited** moves an enemy
only when space exists but inflicts **Depleted** after success; the 1C
**They Had Gone Too Far** has a **Shaken** fallback if movement is blocked.
They are not interchangeable. Similarly, Seven Black Ships has an immediate
attachment-return PLAY trigger while River Raiders pays an ACTION and Command
for repeated opportunities. See the focus probes rather than assuming
textually similar cards are identical.

A heuristic duplicate-wording scan is insufficient to establish semantic
dominance: cards differ by class, target, timing, row and strength floor.
Only the two identified no-op/dominance repairs are changed now; the other
comparisons are explicit choices for the next test, not automatic repricings.

## 2. Effect usefulness: no merely theoretical trigger

For **33 Forces, 24 Bonds, 20 Names and 11 Heroes**, the baseline contribution
is separated from the printed ability. A Force supplies its **Strength and
classes/Attacks**; a Bond can complete the Name requirement and contribute
printed Strength; a Name grants its +1 and completes a Named Formation.
Heroes are evaluated **in both modes**, never as the sum of both. This baseline
can justify playing a card without implying that its special ability is good.

For **14 Tactics, 11 Stratagems, 12 Narratives and 6 Orders** (43 cards)
there is **no permanent Force body** to fall back on. Their effect must
justify the play Action and Command on its own. The checker requires an
operative printed effect; the 44 focus cases demand *meaningful outcomes*,
not merely satisfied conditions.

Examples of questions still requiring tabletop observation:

- **The Ilyri:** does swapping an existing Force and Guarding it change
  deployment priorities, or is 2 Strength too low for 3C?
- **The Field Train, House of Reed, Supplied By, Stayed Behind For:** does
  preparation actually speed up completion after counting *every* Action?
- **The Relief Column / Signal Company:** does their special Maneuver
  permission save more than simply Naming or directly reinforcing the Force?
- **All Banners Forward:** does Shaken plus a conditional second target
  deliver a distinct choice rather than overtaking other 1C Tactics?
- **Watchtowers / Lantern Scouts / hidden-plan counters:** does looking at a
  Stratagem change a later legal play? *Information alone is not proof.*
- **The Lines Held / Ground Was Held:** can a player reasonably choose
  when and where to hold a hidden plan with a viable resolution window?

## 3. Action + Command opportunity cost

Do **two counterfactual trials per focus case** before an ordinary match.
Use exactly the same battlefield, hand and remaining Command:

1. Apply the printed effect and count play Action, any extra ACTION cost,
   Command, setup layers, positions blocked, remaining follow-up options,
   and whether it flips a Front now or next Battle.
2. Rewind. Spend the same Actions/Command on the best ordinary legal
   alternative: a Force, Bond/Name completion, Attack, Maneuver, other
   Tactic, or simply keep the resource.

If the effect is not legal in the proposed state, **do not force it**:
record that the opportunity was unavailable. Then deliberately construct
one *legal* favorable state to check that the card can do something unique.
A conditional effect has failed the static gate when it is illegal even in
the claimed setup, is weaker under **every** legitimate comparison tested,
or has no decision/output beyond what ordinary deployment already does.
When the benefit depends on likely match frequency, mark it **watch**, not
**certified**. Track the same opportunity/play/useful records in
`cards/physical-playtest-evidence.md` during actual games.

**Tempo watchlist:** The Field Train (2 Strength / 3C), Signal Company
(2/3C), Ilyri (2/3C), River Raiders (4/4C plus 1C/ACTION), Black Pursuers
(4/4C plus 1C/ACTION), Watchtowers (3/3C plus ACTION), and delayed
Stratagems. Those are targeted tests, **not measured weak cards**.

## 4. Deck eligibility and encounter rate

All **131/131** physical identities occur in the six standard and four
specialist decks combined. However **20 cards occur only in specialist
decks**, so ordinary mirror matches will never sample them:

| Family | Specialist-only cards |
| --- | --- |
| Force (5) | Grey Riders; Dust Riders; Vardai; Signal Company; Watchtowers of Eren |
| Bond (3) | Marched With; Watched the Skies For; Carried Messages For |
| Name (3) | Iria; Elian; Sela |
| Hero (1) | Neris, the Ferryman |
| Tactic (2) | They Let Them Through; The Scouts Found the Gap |
| Stratagem (3) | The Lines Held; The Flank Was Refused; The Battle Turned East |
| Narrative (3) | The Long March; No Road Was Too Long; They Knew the Ground |

Each appears in **preplaytest-focus.json**, with a favorable use case,
a normal alternative and a failure signal. Keep the four diagnostic decks
for the opening tests, *then* play mirrored standard matches. Do not dilute
the ordinary decks with one-off cards simply to claim coverage:
specialist drills and normal-match incidence are different measurements.

## Decision at the table

- **Keep:** card has a legal, distinctive, understandable use case that
  beats an actual alternative in an appropriate state.
- **Watch:** the effect can matter, but its occurrence rate, setup expense
  or opponent response is unresolved; log opportunities in real games.
- **Replace:** unavoidable dead/no-op text, mechanically unattainable
  prerequisite, or a demonstrably worse choice with no compensating
  price, positioning, strength or synergy advantage.

**Do not stamp all 131 as proven impactful.** The static gate establishes
complete enumeration, operative printed rules, the two concrete repairs,
and explicit tests for 44 uncertain/specialist cards. The next physical
playtest must establish *actual* usefulness and economy. Preserve the
131-card ceiling, replace bad effects rather than merely adding cards,
and avoid copying these printed mechanics into the separate digital runtime.

The prior physical scenario sheet was reconciled with the current
**Swore Again To** effect and Doros's **1C Name-mode** price, and now includes
specific All Banners Forward, Ilyri, tempo and lab-only drills.
