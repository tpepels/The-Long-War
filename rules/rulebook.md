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

A card has one **Force** value, mainly its ability to withstand Strikes. A single uncancelled Strike defeats a target only if its attacking Force is **strictly greater** than the target's Force. Equal Force is a stalemate, unless the card's own Special explicitly defeats equal Force. Force values are **never totaled across a Front** and no Battle Plan modifies dice or Force.

Every card has four individually authored outcomes arranged across six die faces. Each player rolls **one D6 per Front containing any of their Forces**; all of that player's Forces in that Front read their own corresponding face. Both players roll independently. **Every Force's rolled effect participates once** in the simultaneous exchange, even if that Force is later defeated. No individual Attack action exists during turns.

### Shared combat words

- **Falter:** no effect.
- **Strike:** choose one legal opposing target under your revealed Battle Plan; one Strike can target only one Force. The printed Special may override its target or the equal-Force stalemate rule.
- **Protect:** cancel **one incoming damaging Strike** against one eligible friendly Force. “Protect two different friendly Forces” cancels one damaging Strike against each of up to two separate eligible Forces. “Protect all friendly Forces” cancels one Strike per friendly Force. “Against every Strike” is an explicit exception that cancels all damaging Strikes at one chosen Force.
- **Evade:** cancel **every incoming damaging Strike or Pressure** against this Force.
- **Rescue:** after lethal attacks have been calculated, **prevent the entire defeat of one eligible friendly Force**, even if many Strikes caused it. Rescue does not cancel individual Strikes and cannot be counted in coordination; a two-target Rescue saves at most two *different* Forces.
- **Pressure:** a declared alternative to a weak Strike, defined below. It suppresses support or prevents post-combat movement. It never defeats or adds Force.
- **Special:** follow its printed Strike, Protect, Evade, Rescue or post-combat movement variant. Special text does not add a separate timing step.

### Coordinated Strike

After Evade, Pressure and Protect have resolved, count only **uncancelled damaging Strikes aimed at the same target**. If there are *n* such Strikes, **each attacker's effective Force is its printed Force + (n − 1)**. A target is defeated if **any** effective Force is greater than the target's printed Force. An equal-Force Special defeats only when *its own* effective Force equals the target's Force. Each cancelled or converted-to-Pressure Strike adds **nothing** to coordination.

Example: Force 3 and Force 4 attack Force 4 together. Their effective Forces are 4 and 5, so the defender is defeated. Against Force 5, effective 5 is an ordinary stalemate: the defender survives, even though the two attackers coordinated. No “two hits always kill” rule remains.

### A failed Strike still matters: Pressure or Pin

**When declaring targets**, a Strike whose printed Force is **not high enough to defeat its chosen target on its own** (including any explicit equal-Force Special) may instead be declared **Pressure**. This is a real choice: the converted Strike no longer damages and gives no +1 to any coordinated attack.

Resolve Pressure **after Evade and before Protect**. Pressure against a Force showing **Protect or Rescue** cancels *that Force's entire rolled support outcome* for this Battle (including all targets it could have protected). Otherwise Pressure **Pins** the target. Pressure cannot cancel Evade, cannot cross Fronts unless printed text explicitly permits it, and cannot itself be cancelled by Protect. Multiple Pressure results on one Force do not stack.

Any **uncancelled damaging Strike that fails to defeat its target** also Pins the target automatically. Pin means **that specific Force cannot perform post-combat movement this Battle**, including a printed advance or Assault. Pin does not affect attacks, ordinary combat support, control or the next Battle. There are **no Pin markers** and nothing persists to remember: finish the Battle's movement step, then forget Pin.

This distinction prevents circular timing: you decide whether to Pressure **before** allocating protection; you never go back and undo already resolved Protect effects. An ineffective damaging Strike Pins only **after** lethal checks. If an attacking Force dies in the same exchange, its already declared attack or Pressure still resolves.

### Targets, positions and roles

In every Front, each rank holds at most one Force per player. **Foremost** is the occupied enemy/friendly rank nearest the battle line: Frontline, otherwise Middle, otherwise Rear. Under Assault or Hold, an ordinary Strike may target only the foremost enemy; Volley and Raid open additional eligible ranks for the specified roles. **Players freely choose among the eligible enemy Forces** rather than automatically assigning targets. An explicit printed Special target takes precedence over the Plan; if its named rank is empty and no fallback is printed, the Strike does nothing.

“Frontline,” “Middle,” “Rear,” “ahead” and “behind” normally refer to **the owner's ranks in the current Front**. “Nearest friendly behind/ahead” searches occupied ranks in order, excluding the source. A Force counts as friendly to itself unless the card says “another.” No Force or effect reaches another Front by default. **Only an individually printed Special explicitly mentioning an adjacent active Front** may cross the Front boundary; it must have an eligible target when it resolves.

**Role** is a printed classification, not an additional triggered ability. Raider, Rider and Skirmisher may use Raid movement and targeting; Archer may use Volley targeting. Healer, Steward and other roles simply use their printed D6 results.

### Universal timing of a Special

Classify a rolled Special by what it **actually does**, not by the letter S. A Special Strike declares targets with ordinary Strikes. A Special Protect operates with other protection. A Special Rescue waits until after lethal checks. A Special advance happens after casualties. A multi-part Special is split into its corresponding steps. **No card invents its own resolution priority.**

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

**All active Fronts are one simultaneous exchange.** Read the dice in each Front, but do not discard one Front's casualties before resolving adjacent-Front Rescues. Nothing here changes the timing of deployment, turns or Command scoring.

1. **Reveal Plans; move.** Both players reveal their single army-wide Plan, simultaneously declare legal **pre-combat** Hold/Raid moves, and execute them. Destinations must be empty *before* those moves.
2. **Roll.** Each player rolls one D6 for each Front containing their Forces; all their Forces in that Front use the corresponding result on their own cards.
3. **Declare targets and intentions.** Both players declare all eligible Strikes **simultaneously**, freely choosing legal targets within their Plan. A Strike that cannot defeat its chosen target alone may be announced as **Pressure** instead of damage. Printed fixed-target Specials override Plans. Target choice is locked for this Battle.
4. **Evade, then Pressure.** Evade cancels incoming damaging Strikes and Pressure. Uncancelled Pressure cancels one target's entire rolled Protect/Rescue support outcome, or Pins it if it was not providing those outcomes. Multiple Pressure on the same target do not stack.
5. **Protect.** Both players allocate remaining Protect effects after targets are visible. Cancel one damaging Strike per applicable protection, or the explicitly printed number. Hold can retarget Protect *within the same Front* but does not increase capacity. Specials that ignore one Protect bypass one assigned Protect against their Strike, **not** Evade or Rescue.
6. **Coordinated damage and failed attacks.** For each target, let *n* be its remaining uncancelled damaging Strikes. Each of those attackers has **effective Force = printed Force + (n − 1)** for *that target only*. If any is greater than the target's printed Force, defeat it (or equal if that attacking Special explicitly permits equality). Otherwise the target survives but is **Pinned** if at least one Strike remained. No card is removed yet.
7. **Rescue.** Each remaining Rescue effect saves its allowed number of different, otherwise-defeated friendly Forces. **One Rescue saves an entire Force**, regardless of how many attacks would defeat it. Printed adjacent-Front Rescue may be assigned after all Fronts' lethal attacks are known.
8. **Discard and advance.** Permanently discard defeated Forces. Resolve surviving Forces' printed **after-combat Special movement**, then Assault advances; **Pinned Forces cannot move**, and no Force moves more than once during this Battle. Moves obey printed legal ranks and empty destinations.
9. **Control.** Count surviving occupied positions in each Front (0–3 per player). **More Forces controls** that Front; equal headcounts are contested. Continue to Command loss, Collapse check and recovery below.

**Timing clarifications:** Damage, Pressure, Protect and Rescue are declared/executed even if their source is later destroyed in the same exchange. A Force that is **saved by Rescue** was never defeated and cannot trigger “if this Strike defeats an enemy” advance text as the victim. A Force must itself survive to move. Cross-Front effects require their own printed permission; sharing the same Battle Plan does not grant cross-Front targeting or support. Failed Pressure and Pin leave **no persistent state**.

## Command, casualties and continuation

After control is scored, each player **loses 1 Command for every Front controlled by the opponent**. A contested Front costs neither player Command. Check for **Command Collapse at 0 or below before recovery**. If both collapse simultaneously, the player with lower Command loses; if tied, the player who Passed loses.

If neither collapsed, compare the **number of controlled Fronts**:
- The player controlling **fewer** Fronts recovers **8 Command**.
- The player controlling **more** Fronts recovers **6 Command**.
- If equal, each recovers **7 Command**.

Command cannot exceed **20**. Both players draw back up to **10 cards**, reshuffling only ordinary discards when necessary. All surviving Forces remain in their current squares; all Battle Plans return to their owners for reuse. Open the next Front on schedule, if any.

**Prototype limit:** after **Battle VIII**, if neither player has collapsed, the player controlling more Fronts wins. If tied, the player with more Command wins. If also tied, the war is a draw. This is a test stop condition, not a claim about ideal game length.

## Fully worked combat example (actual card faces)

Your **Red Shields (Force 4)** hold Frontline, **Crow Archers (Force 3)** Middle and **White Hands of Elara (Force 3)** Rear. The opponent has **Fifty Men (Force 5)** in Frontline, **River Raiders (Force 4)** in Middle and **Tovan, the Quartermaster (Force 2)** in Rear. You choose **Volley**; the opponent chooses **Raid**. No legal Raid movement is available.

**Your die = 2:** Red Shields show **Special** (Protect two different friendly Forces), Crow Archers show **Strike**, White Hands show **Special** (Rescue any one friendly Force).

**Opponent die = 1:** Fifty Men show **Strike**, River Raiders show **Strike**, Tovan shows **Protect** (friendly Frontline).

1. You freely target Tovan with the Archers under Volley. Archers' Force 3 is greater than Tovan's Force 2.
2. Fifty Men Strike your Red Shields (Force 5 vs 4), and Raiders Strike your Archers under Raid (Force 4 vs 3). Tovan's rolled Protect may cover only the opposing Frontline, so cannot protect Tovan.
3. Red Shields Protect Archers and White Hands, cancelling the Raiders' Strike. White Hands Rescue Red Shields against the lethal Fifty Men Strike.
4. All attacks are simultaneous. Tovan receives no protection or Rescue and is permanently discarded. You control the Front **3 surviving Forces to 2**.

**Coordination instead of automatic two-hit kills:** Suppose Force 3 and Force 4 both legally Strike an opposing Force 4. Their effective Forces are **4 and 5**, defeating it. If one attack is cancelled by Protect, the remaining Force 4 alone only **ties** and fails, **Pinning** the defender. Against Force 5, both coordinated Strikes only reach effective Forces 4 and 5: **no defeat**, but the target is Pinned.

**Pressure against a Guard:** A Force 3 Strike cannot defeat an opposing Guard (Force 4) alone. At declaration you may instead designate that Strike **Pressure**. If that Guard rolled Protect, its entire Protect result is suppressed **before** it can protect another Force in its Front. Your Force 3 contributes **no** coordinated Strike bonus that exchange. If the Guard instead rolled Strike, the Pressure Pins it (preventing an after-combat advance), but **does not cancel its Strike**. These outcomes require no status counter after movement is finished.

## Playtest failure tests

Record each player's plan, each Front's two die results, attacks cancelled, fatalities, surviving headcount, final control and post-Battle Command. Test these before changing the entire 44-identity pool:

- Do **two weak coordinated Strikes** defeat strong defenders too reliably?
- Does **Force** remain dominant because high-Force troops are always safer and can kill lower Force?
- Are **Protect** and **Rescue** sufficiently different?
- Can players read and resolve a **full twelve-Force side** quickly without persistent markers?
- Do **Volley** and **Raid** have credible alternatives to **Assault** and **Hold** in several deck matchups?
- Does majority control reward three inexpensive Forces over a stronger mixed formation?

No digital match, AI win rate or historical balance result validates these paper rules. They require physical playtesting.
