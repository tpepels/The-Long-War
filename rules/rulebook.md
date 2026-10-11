# The Long War — Force-only D6 tabletop prototype

*Paper rules, 11 October 2026. Experimental; not implemented in the digital engine.*

Two players contest up to four Fronts over successive Battles. Forces hold territory, suffer permanent casualties, and execute one secret **Battle Plan** per army. The winning condition is **Command Collapse** or the eight-Battle limit.

This prototype deliberately uses **Forces and Force-mode Heroes only**. Set aside Bonds, Names, Tactics, Stratagems, Narratives, Orders, their markers and their effects. The old Opening Orders are replaced by the four Battle Plans below. No Strength totals, Attack/Defence pairs, Health, wounds, Exhaustion, afflictions or triggered legacy Force powers are used. Only the Force value, roles, costs, positions and six-face combat strips printed for this prototype count.

## Components and setup

- Two **24-card D6 playtest decks**, one per player. Each deck follows its published card list, with no more than four copies of any non-Unique title and one of any Unique Hero.
- Four Fronts, numbered left to right, each with a **Frontline, Middle, and Rear position on each player's side** (maximum twelve Forces per player). The nearest rank to the enemy is Frontline.
- One D6 per player (or reuse the same die), a 0–20 Command track per player, and a set of four **Battle Plan cards** per player: Assault, Hold, Volley and Raid. Plans are reusable; they do not come from your deck.
- A face-down draw deck, a discard pile for cycled cards, and a separate **casualty pile** for destroyed Forces.

Each player starts at **20 Command**, draws **10 cards**, and may shuffle up to two cards back into their deck and draw replacements. Randomly choose the first player. Initially only **Fronts 2 and 3** are open. In Battle II open Front 1, in Battle III open Front 4; all four remain open from Battle III onward.

Only open Fronts can receive Forces or be entered by movement.

## Turns and ending deployment

Instead of a normal turn, you may **Pass before drawing**. Otherwise draw one card (maximum hand size 10; immediately discard excess to the ordinary discard pile), then take up to **two Actions**:

1. **Deploy:** pay a card's printed Command cost to play a Force or Hero to a vacant, legal position in an open Front.
2. **Maneuver:** pay **1 Command** to move a Force to one adjacent legal empty position: one rank forward/back in the same Front or left/right to an adjacent open Front in the same rank. Instead of entering an empty square, you may swap with an adjacent friendly Force if both placements are legal.
3. **Cycle:** discard two cards from hand into the ordinary discard pile to draw one.

A normal turn may end with unused Actions. You cannot spend Command below zero. A Force may be placed only in a rank allowed by its card. A Hero is always a Force and may be played **at most once per player per Battle**; its former Name mode does not exist.

The first Pass starts the closing sequence: the opponent takes one complete normal turn, then the passer takes one complete normal turn. Neither closing player can Pass. Both then choose one hidden Battle Plan. The non-passer starts the next Battle.

When a draw is needed and the draw pile is empty, shuffle only the **ordinary discard pile** into a new draw pile. Casualties are permanently removed from the game and never reshuffled. If both piles are empty, skip that draw.

## Force, roles and combat strip

A Force has just one statistic, **Force**, used as its resistance and for breaking opposing Forces. There are no cumulative Front totals. Higher Force defeats lower Force on a valid Strike; **equal or lower Force does not**. Two or more *uncancelled* Strikes aimed at the same enemy defeat it regardless of Force (Concentrated Attack). A printed Special may explicitly defeat equal Force.

Every Force has a **six-face combat strip**. Each die face maps to one of **four distinct outcomes** listed on that card. Face order and frequencies differ by card. Each player rolls **one D6 for each occupied Front on their side**, and **every Force in that Front uses that player's same result**. The opponent rolls independently.

Every Force executes **exactly its rolled outcome once**, even if it is subsequently defeated during the same exchange. No Force takes a separate Attack action during normal turns. Every effect completes this Battle, except permanent removal of casualties and movement.

The small common vocabulary:

- **Falter:** no effect.
- **Strike:** declare one legal opposing Force as target; this attack may defeat it. Unless the combat strip explicitly names a different target, legal targets come from the Battle Plan.
- **Protect:** cancel **one incoming Strike** against a permitted friendly Force. If the effect lists multiple friendly Forces, it cancels at most one Strike against each. A Protect that has no eligible target does nothing.
- **Evade:** cancel **all incoming Strikes against this Force**.
- **Rescue:** after checking otherwise-lethal attacks, **save one permitted friendly Force from defeat**, regardless of how many Strikes hit it. A Rescue for two different Forces can save each once.
- **Special:** carry out exactly the printed text, built from these same operations with a limited exception such as special targeting, equal-Force breakthrough or post-combat movement.

An unqualified **Protect** acts only in its Front. “Frontline,” “Middle,” “Rear,” “foremost,” “ahead,” and “behind” refer to **the owner's positions within that Front**, unless the text explicitly says otherwise. The **foremost** is the occupied friendly or enemy rank nearest the battle line: Frontline, otherwise Middle, otherwise Rear. “Nearest friendly Force behind/ahead” searches ranks in order and excludes the source Force. An effect may Protect its own Force only if it says “self,” “any friendly Force,” or names a rank including itself. A Force is friendly to itself unless the text says “another.”

**Role** appears on the physical card. Roles govern plan targeting or movement, but do not add automatic triggers. Under Raid, **Raider, Rider and Skirmisher** are mobile roles. Under Volley, only **Archer** gains open-rank targeting. Other roles have exactly their printed combat outcomes, including Healer and Steward Rescues.

## Hidden army-wide Battle Plans

After the two closing turns, **each player secretly chooses one reusable plan for their entire army**. Reveal both simultaneously. The same plan applies across all active Fronts; players cannot pick different plans per Front. Plans alter only target permissions, protection reach and movement. They **never change the die roll or Force value**.

| Plan | Before combat | Targeting / protection | After casualties |
| --- | --- | --- | --- |
| **Assault** | No plan movement | Ordinary Strikes target the foremost enemy in their Front | Move up to one surviving Force one empty rank **forward** in each Front |
| **Hold** | Withdraw up to one friendly Force one empty rank **back** in each Front | Ordinary Strikes target the foremost enemy; Protect may cover **any friendly Force in that Front** | No plan movement |
| **Volley** | No plan movement | Archers may Strike **any occupied enemy rank** in their Front; all other Strikes target foremost | No plan movement |
| **Raid** | Move up to one mobile Force from each Front into an empty position at the **same rank in an adjacent open Front** | Raider, Rider and Skirmisher Strikes may choose enemy Middle or Rear, if occupied; otherwise foremost; other Strikes target foremost | No plan movement |

Plans do not expand the reach of a Special that already defines its own target. When a Special says “regardless of Battle Plan,” its printed target takes priority. If its named target is empty and no fallback is printed, it has no legal Strike. A printed “Strike foremost enemy” always targets the foremost enemy, even under Volley or Raid. An unqualified “Strike” uses the plan's target permission.

Plan movements on opposing sides happen simultaneously. For simultaneous movement on one side, declare all intended sources and destinations first, using only squares that were empty before those movements; destinations must be distinct. Each Force may move **at most once during Battle resolution**, including moves from a Special. Movement must obey its original rank restrictions and never cross into inactive Fronts.

## Resolution order — every Battle

**Treat all active Fronts as one simultaneous exchange.** In particular, do not finish and discard the casualties of Front 1 before processing possible cross-Front Rescues for Front 2.

1. **Reveal Plans.** Each player shows their one chosen Plan.
2. **Before-combat movement.** Both players declare and execute their legal Hold/Raid movements simultaneously.
3. **Roll.** Each player rolls one D6 for each Front containing any of their Forces. Announce the result and read all surviving Forces' face results.
4. **Declare Strikes.** Both players declare all legal targets simultaneously. Ordinary Strike targeting is defined by the Plan. A Force produces at most one Strike, except when a Special explicitly says otherwise; each combat result is used once.
5. **Assign protection.** Both players allocate their rolled Protect/Evade outcomes after seeing announced targets. Apply Evade, then Protect, cancelling declared Strikes; a Strike marked as ignoring one Protect bypasses one assigned Protect, but not Evade or Rescue.
6. **Find lethal attacks.** For each target, a surviving, uncancelled Strike defeats it if the attacking Force is **strictly higher Force**, or if a printed Special explicitly permits an **equal-Force defeat**. Also defeat a target with **two or more uncancelled Strikes** aimed at it, regardless of Force. Resolve every Force's own result before removing anybody.
7. **Apply Rescue.** Allocate Rescue results to eligible otherwise-defeated friendly Forces and cancel their defeat. Each Rescue effect has the capacity stated on its card. It can save a Force from concentrated attacks.
8. **Discard casualties.** Send every defeated Force permanently to its owner's casualty pile. Resolve printed after-combat Special movement, then any Assault movement, subject to the one-movement-per-Force limit.
9. **Score territory.** For each Front, count occupied positions remaining on each side (0–3). **More surviving Forces controls the Front**; equal counts mean contested. Ranks determine who can attack or move, but do not add points. Uncontested empty Fronts (0 vs 0) are tied.

All attacks and support apply even when their source Force is destroyed by that same exchange. If multiple Protect results could cancel a Strike, the defender chooses which Protect is spent; each available Protect effect is used at most once, except where its text covers multiple targets. An ignored Protect does not cancel its Strike; it is still consumed. Two Strikes cannot count as concentrated if one was cancelled.

## Command, casualties and continuation

After control is scored, each player **loses 1 Command for every Front controlled by the opponent**. A contested Front costs neither player Command. Check for **Command Collapse at 0 or below before recovery**. If both collapse simultaneously, the player with lower Command loses; if tied, the player who Passed loses.

If neither collapsed, compare the **number of controlled Fronts**:
- The player controlling **fewer** Fronts recovers **8 Command**.
- The player controlling **more** Fronts recovers **6 Command**.
- If equal, each recovers **7 Command**.

Command cannot exceed **20**. Both players draw back up to **10 cards**, reshuffling only ordinary discards when necessary. All surviving Forces remain in their current squares; all Battle Plans return to their owners for reuse. Open the next Front on schedule, if any.

**Prototype limit:** after **Battle VIII**, if neither player has collapsed, the player controlling more Fronts wins. If tied, the player with more Command wins. If also tied, the war is a draw. This is a test stop condition, not a claim about ideal game length.

## Fully worked combat example

Your **Guard (Force 4)** is in Frontline, **Archer (Force 2)** in Middle, and **Healer (Force 3)** in Rear. Opposing **Heavy Infantry (Force 5)** occupies Frontline, **Raider (Force 3)** Middle, and **Steward (Force 2)** Rear. You secretly choose **Volley**; they choose **Raid**. Assume no legal pre-combat Raid movement.

You roll a die face that produces **Protect** on Guard, **Strike** on Archer, and **Rescue** on Healer. The opponent rolls a face that produces **Strike** on Heavy Infantry, **Strike** on Raider, and **Falter** on Steward.

Your Archer targets the opposing Steward because Volley permits Archers to target Rear. The Heavy Infantry targets your Guard as foremost. The Raider targets your Archer because Raid allows Middle. Your Guard Protects the Archer, cancelling the Raider's Strike. Your Healer Rescues the Guard from Heavy Infantry's lethal Strike. The Archer's Force 2 Strike defeats the Steward's Force 2 **only if a printed equal-Force Special allows it or another uncancelled Strike joins it**; otherwise it stalemates. Under the ordinary Strike defined here, this attack is **not lethal**, so all six Forces survive and the Front remains contested.

Changing the opposing Steward to **Force 1** makes the Archer's Strike lethal. The Steward is discarded and you control the Front **3 to 2**. This distinction is intentional: Force comparisons remain exact, and equal-Force attacks do not secretly turn into kills.

## Playtest failure tests

Record each player's plan, each Front's two die results, attacks cancelled, fatalities, surviving headcount, final control and post-Battle Command. Test these before changing the entire 44-identity pool:

- Do **two weak coordinated Strikes** defeat strong defenders too reliably?
- Does **Force** remain dominant because high-Force troops are always safer and can kill lower Force?
- Are **Protect** and **Rescue** sufficiently different?
- Can players read and resolve a **full twelve-Force side** quickly without persistent markers?
- Do **Volley** and **Raid** have credible alternatives to **Assault** and **Hold** in several deck matchups?
- Does majority control reward three inexpensive Forces over a stronger mixed formation?

No digital match, AI win rate or historical balance result validates these paper rules. They require physical playtesting.
