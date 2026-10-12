# Physical D6 cards — visual hierarchy and cooperative rolls

This is an **authoring audit** for the paper-only edition, not additional gameplay rules. The existing short rulebook and visible Command/Battle Plan cards remain canonical.

## The printed face

One card should read in this order:

1. **Name and artwork:** recognize the Force first, without reducing the illustration to a token-sized thumbnail.
2. **Force, role, allowed rows and Command cost:** see where it belongs and how expensive it is.
3. **Four roll-to-effect rows:** read the D6 **number** beside the result in one movement of the eye. No letter key, separate die strip or wordy repeated outcome heading.
4. **Exceptions:** the individual Special has discreet contrast and the same plain-language grammar as ordinary results.

In print, the effect panel uses a warm neutral surface and fine rules; action pictograms are secondary to a larger printed die number and the readable effect sentence. Blank/Falter-style results remain visible, not hidden or crossed out. The artwork window is preserved at **19.2 mm** and font sizes are checked by the headless layout test.

## The meaning of a die assignment

Each player rolls **one D6 per occupied Front**. Different friendly Forces therefore read **the same number** on their own cards. This creates *natural combinations without another combo keyword*. Dice are independent between opposing players. There is no globally better roll, reroll, combo counter, or special bonus.

All **44 card effect frequencies are unchanged**: rearranging a six-character face string changes *which* rolls trigger an outcome, not the chance of that outcome for any individual card. Force values, prices, art, permitted ranks, the 44 outcomes and deck composition remain unchanged.

### Intentionally authored lineups

| Roll | Formation (in the same Front) | What cooperates |
| --- | --- | --- |
| **2** | Red Shields + Crow Archers + White Hands of Elara | Shields' double Defend, Archers' Attack and White Hands' Save appear together |
| **6** | Red Shields + Crow Archers + White Hands of Elara | Two ordinary Attacks can coordinate against the same foremost target while the healer Saves |
| **4** | Fifty Men + Thirty Spears + First Spear | Two ordinary Attacks and a Guard's all-Attack Defend |
| **2** | Grey Riders + Dust Riders + Aradai | Rider's advancing Attack and two ordinary Attacks on the same foremost enemy |
| **5** | Grey Riders + Dust Riders + Aradai | Grey Riders and Aradai can combine on the foremost target; Dust Riders attack Middle instead |
| **4** | Fifty Men + First Spear + Relief Column | One Attack, an all-Attack Defend and a successful Save *if threatened* |

These are **possible** formations, not guaranteed outcomes: placement restrictions, target eligibility, defending choices and the actual opponent still matter. A Save result does nothing if no friendly Force is threatened. A successful Attack is not guaranteed to defeat a target.

### Starter-deck activity audit

Number of cards, **counting copies in the 24-card sample deck**, whose result is an Attack on each die face (not a predicted number of attacks in play):

| Starter deck | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shield & Volley | 7 | 13 | 8 | 12 | 7 | 14 |
| Riders & Raids | 12 | 15 | 11 | 12 | 16 | 12 |
| Sustain & Control | 5 | 6 | 5 | 6 | 3 | 9 |

No deck has a die face where all 24 cards Attack or where none can Attack. The combat probabilities and the balance of simultaneous permanent casualties **have not** been validated by physical games. Preserve this visible variety and retest after any edits to dice assignments.

## Editorial guardrails

- Never shrink the artwork to compensate for growing card text without a visual review.
- Keep the rule text readable at **actual 68 × 96 mm card size**; do not hide overflow or rely on zoom.
- Give the die number prominence, then the actual effect; pictograms are supplemental.
- Avoid matching every Force of a role to identical dice outcomes. A deck should have several tactical rhythms rather than a universal “good roll.”
- Do not add universal exceptions or new rules on the Force cards. If a genuinely new mechanic needs explaining elsewhere, question the mechanic first.

Run `python tools/check_paper_d6_synergy.py` and `python tools/check_paper_d6_layout.py` before printing.
