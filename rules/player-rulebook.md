# The Long War — D6 paper playtest

*Two-player experimental physical edition. The digital engine uses different rules.*

## Goal

Control Fronts with surviving Forces. Destroyed Forces never return. Lose the war if Command reaches 0 after a Battle (before recovery). If nobody collapses after Battle VIII, more controlled Fronts wins; then more Command; otherwise a draw.

## Set up

Each player needs one **24-card D6 deck**, **20 Command**, four reusable secret **Battle Plans** (Assault, Hold, Volley, Raid), and one D6. Draw 10 cards; optionally reshuffle up to two back and replace them. Choose the starting player at random.

There are four **Fronts**, each with **Frontline, Middle and Rear** positions per player. One Force (or Force-mode Hero) per position. Only Fronts 2 and 3 start open; open Front 1 at Battle II and Front 4 at Battle III. **No Bonds, Names, Tactics, Orders, Stratagems, Narratives or old Opening Orders** in this test.

## On your turn

Before drawing, you may **Pass**. Otherwise draw 1 (hand limit 10), then take up to **two Actions**:

- **Play** a Force into an empty legal position, paying its printed Command cost. Maximum one Hero played per Battle, always as a Force.
- **Maneuver** a Force one orthogonally adjacent legal position for **1 Command**, or swap adjacent friendly Forces if both positions remain legal. No diagonals or inactive Fronts.
- **Cycle** two cards from hand into your ordinary discard pile to draw one.

You may end with unused Actions; that is not Pass. Passing skips the draw and actions. After the first Pass, the opponent gets one complete turn, then the passer gets one complete turn. Neither can Pass again. Then both choose secret Battle Plans.

You cannot voluntarily spend Command below 0.

## Hidden Battle Plans (one per army)

Both players secretly select one reusable plan and reveal together:

| Plan | What it changes |
| --- | --- |
| **Assault** | Strike foremost enemy; after combat advance one surviving Force one empty rank forward per Front |
| **Hold** | Before combat withdraw one Force one empty rank backwards per Front; Protect may cover any ally in its own Front |
| **Volley** | Archers may Strike any occupied enemy rank in their Front; other Strikes target foremost |
| **Raid** | Before combat redeploy one Raider/Rider/Skirmisher per Front into a vacant same-rank space in an adjacent active Front; these mobile roles may Strike enemy Middle/Rear if occupied, otherwise foremost |

Under Hold/Raid, unless stated otherwise, all ordinary Strikes target the foremost occupied enemy rank. Printed Specials with an explicit target override plan targeting. A Force can move at most once in a Battle resolution. Declare simultaneous plan movement into **originally empty, distinct destinations**, obeying printed allowed ranks.

## Dice and outcomes

Each player rolls **one D6 per Front containing their Forces**. All their Forces in that Front use the result on their own six-face strip. Each Force has four distinct outcomes spread across six faces; **all Force outcomes happen**, even if the Force dies in the same exchange. No individual Attack Action.

- **Strike:** one eligible enemy target. Higher Force than target defeats; equal/lower Force does not.
- **Concentrate:** two or more *uncancelled* Strikes at the same target defeat it regardless of Force.
- **Protect:** cancel one incoming Strike on an eligible ally. If printed as protecting multiple distinct Forces, cancel at most one against each.
- **Evade:** cancel all incoming Strikes against that Force.
- **Rescue:** after checking lethal hits, prevent one eligible friendly Force's defeat, even from concentration.
- **Falter:** nothing. **Special:** follow the short instruction on the card. It may override targeting or allow a Strike against equal Force.

“Foremost” means Frontline if occupied, otherwise Middle, otherwise Rear. “Behind/ahead” refers to another Force in the same Front. A Force counts as friendly to itself when an effect permits it. Printed rank restrictions still apply.

## Resolve every Battle in this order

1. Reveal both Plans, then make permitted **pre-combat movements**.
2. Each player rolls **one D6 per occupied Front**. Read every surviving Force's result.
3. Declare all **Strikes and targets simultaneously**.
4. Assign and resolve **Evade, then Protect** after targets are visible. A piercing Special ignores one Protect but not Evade or Rescue.
5. Determine lethal Strikes and **two-Strike concentration**. Then allocate **Rescue** to cancel otherwise-lethal defeats.
6. Discard defeated Forces permanently into **casualty piles**. Execute Special post-combat moves and then Assault advances.
7. Count surviving Forces per Front (0–3 each). **More occupied positions controls**; equal counts are contested.
8. Lose **1 Command per Front controlled by the opponent**, check Collapse at 0, then recover **8 Command if behind in controlled Fronts, 6 if ahead, 7 each if tied**, capped at 20. Refill hands to 10. Survivors stay in place.

Recycle only the **ordinary discard pile** when drawing; **casualties never re-enter decks**. If there are no cards to draw, skip the draw. The player who did not Pass starts the next Battle.

For edge cases and a worked example see the [detailed physical rules](rulebook.md). This version is provisional and has not been validated in a tabletop game.
