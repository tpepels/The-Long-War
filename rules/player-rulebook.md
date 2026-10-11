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

Roll **one D6 per player per occupied Front**. Every Force on that player's side of the Front performs its own printed result for the rolled face, even if defeated in the same exchange. Every Force has four differently arranged outcomes. No separate Attack action.

- **Strike:** choose an enemy permitted by your Battle Plan. Players freely choose among eligible targets; printed Special targets override the Plan.
- **Coordinated Strike:** each additional **uncancelled damaging Strike at the same target adds +1 effective Force to every Strike at that target**. If any effective Force is **greater** than the defender's Force, it is defeated. Equal Force is a stalemate unless that Strike's Special says otherwise. **Two Strikes do not automatically kill.**
- **Pressure:** when declaring a Strike that **cannot defeat its target alone**, choose to use it as Pressure instead of damage. After Evade, Pressure suppresses **all Protect/Rescue from the targeted Force** for this Battle; if it rolled neither, Pressure Pins it instead. Pressure gives **no** coordination bonus.
- **Pin:** a Force hit by an uncancelled **failed damaging Strike**, or applicable Pressure, **cannot move after combat this Battle**. It still attacks, supports and holds territory. No persistent Pin marker.
- **Protect:** cancels **one** incoming damaging Strike (or the exact capacity stated on its card). **Evade** cancels all Strikes and Pressure against itself.
- **Rescue:** prevents **one Force's entire defeat**, regardless of how many Strikes would have killed it. It operates **after** lethal attacks, not as an individual hit cancellation.
- **Falter:** nothing. **Special:** use its printed combat operation at the normal universal timing.

A Special explicitly naming an adjacent active Front is the **only** way a Force can affect another Front. “Foremost” is Frontline if occupied, otherwise Middle, otherwise Rear. “Ahead/behind” refers to ranks within the same Front, and a Force is friendly to itself unless stated otherwise. Printed rank restrictions still apply.

## Resolve every Battle in this order

1. **Reveal** one secret Plan per army; execute eligible pre-combat **Hold/Raid movement**.
2. Both players **roll one D6 per occupied Front** and read every Force's own result.
3. **Declare all Strike targets simultaneously**. Freely choose eligible enemies; optionally convert a solo-ineffective Strike into **Pressure**.
4. Resolve **Evade**, then **Pressure** (suppress rolled Protect/Rescue or Pin), then allocate **Protect** after targets are known.
5. Calculate **effective Force = each surviving attacking Force + (uncancelled damaging Strikes against that same target − 1)**. Defeat only where an attack exceeds the defender or an eligible Special permits equality. Any unsuccessful uncancelled Strike **Pins** its defender.
6. Assign **Rescue** to otherwise-lethal casualties. Each Rescue saves its entire permitted Force.
7. Discard remaining casualties permanently; apply **Special post-combat movement**, then **Assault** advances. Pinned Forces cannot advance.
8. Count surviving Forces (0–3 per side) in each Front: higher count **controls**, equal counts are contested.
9. Lose **1 Command per enemy-controlled Front**, check Collapse at 0, then recover **8 if behind** in controlled Fronts, **6 if ahead**, **7 each if tied** (cap 20). Refill hands to 10.

Every Force contributes its rolled effect **once**, even if that Force will be defeated. Protection and Rescue are distinct; Pressure never turns into retroactive cancellation. Cross-Front Specials resolve together with their corresponding universal operation.

Recycle only the **ordinary discard pile** when drawing; **casualties never re-enter decks**. If there are no cards to draw, skip the draw. The player who did not Pass starts the next Battle.

For edge cases and a worked example see the [detailed physical rules](rulebook.md). This version is provisional and has not been validated in a tabletop game.
