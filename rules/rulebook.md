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

Each rank holds at most one Force per player. **Foremost** is the occupied rank nearest the battle line: Frontline, otherwise Middle, otherwise Rear. Under Assault and Hold, ordinary Strikes target only the foremost opposing Force. Volley and Raid open additional **eligible** ranks for specific roles and positions. **Players freely choose among their eligible enemy targets**. A printed Special that explicitly names a target rank overrides the Plan and role restrictions; if that rank is empty and no fallback is printed, it cannot Strike.

“Ahead” and “behind” refer to adjacent directions within the **same Front**, and nearest occupied friendly Forces exclude the source. A Force counts as friendly to itself unless text states otherwise. No Force or effect reaches another Front by default. **Only an individually printed Special explicitly mentioning an adjacent active Front** can target or Rescue there.

**Roles matter by rank**, using four shared interactions rather than triggers or bonuses:

- **Guard in Frontline — Screen:** when it rolls **Protect**, it may choose any friendly Force in **its own Front** as a recipient, regardless of the rank restriction printed on that Protect. Its Protect still cancels only the *printed number of Strikes*. A Guard that rolled Falter, Strike or Rescue does not Screen, and a Guard in Middle/Rear follows its ordinary printed Protect reach.
- **Archer in Middle or Rear — Volley:** only from these ranks may an Archer use Volley's permission to select **any** occupied enemy rank. An Archer in Frontline must target the foremost enemy with an ordinary Strike. A printed fixed-target Special remains usable.
- **Raider, Rider or Skirmisher in Frontline or Middle — Raid:** only from these ranks may a mobile Force use Raid's permission to choose opposing Middle/Rear targets. A mobile Force in Rear targets the foremost enemy with ordinary Strikes, but may still make Raid's normal **same-rank lateral move**. Printed fixed-target Specials remain usable.
- **Healer or Steward in Rear — Sustain:** a rolled **Rescue** may save any one otherwise-defeated friendly Force **in its own Front**, even if the printed Rescue normally says “foremost.” This never increases how many Forces a Rescue can save. Explicitly printed adjacent-Front Rescue reach remains available regardless of rank.

These interactions apply equally to both players based on their **actual positions after pre-combat movement**. All other roles and ranks use their normal printed effects. No role gives passive damage, automatic protection, extra dice or extra movement.

### Universal timing of a Special

Classify a rolled Special by what it **actually does**, not by the letter S. A Special Strike declares targets with ordinary Strikes. A Special Protect operates with other protection. A Special Rescue waits until after lethal checks. A Special advance happens after casualties. A multi-part Special is split into its corresponding steps. **No card invents its own resolution priority.**

## Hidden army-wide Battle Plans

Each player secretly selects **one reusable Plan for their entire army** after the closing turns. Reveal simultaneously **before** any dice roll. A Plan controls targeting and movement, never the D6 face or Force statistic. It applies across all active Fronts; you cannot select a different Plan for an individual Front.

| Plan | Before rolling | Normal Strike targets | Post-combat movement |
| --- | --- | --- | --- |
| **Assault** | No plan move | Foremost enemy in the Front | One optional forward step per Front, whether or not an Opportunity was earned |
| **Hold** | Withdraw up to one Force one empty rank backward per Front | Foremost enemy; a Protect may cover any friendly Force in its own Front without adding capacity | One optional forward step per Front **only after an Opportunity** |
| **Volley** | No plan move | Archer in **Middle/Rear** may choose any enemy rank; other ordinary Strikes target foremost | One optional forward step per Front **only after an Opportunity** |
| **Raid** | Redeploy up to one Raider/Rider/Skirmisher from each Front to an originally empty same-rank position in an adjacent active Front | Mobile Force in **Frontline/Middle** may choose enemy Middle/Rear if occupied; otherwise foremost; other ordinary Strikes target foremost | One optional forward step per Front **only after an Opportunity** |

Movement is optional and must obey the moved Force's legal printed ranks. Before-combat moves are declared simultaneously into **originally empty and distinct** destinations. No pre-combat swap through occupied squares. The moved Force may still act on its D6 face, but cannot move a second time during Battle resolution.

A **printed Special that names an enemy rank** keeps that fixed targeting even if a Plan would permit more or fewer targets. A printed Special with a fallback chooses the first **occupied** target in its listed order. Plan rules do not grant a cross-Front Strike or Rescue.

### Plan counters: one Tactical Read

A correct prediction grants a strong but conditional **Tactical Read**. There is a single shared counter cycle:

**Hold counters Assault → Assault counters Volley → Volley counters Raid → Raid counters Hold.**

If your revealed Plan **counters** your opponent's, you may use **one Read per Front where you have Forces**, after the dice are rolled. Each Read chooses **one** of your rolled Strike or Protect outcomes in that Front, using its normal combat timing:

- **Read Strike:** a Strike whose printed effect **does not name a specific target rank** may choose **any occupied enemy rank in that Front** and **ignore one Protect assigned against it**. Its printed Force, damage, coordination and equal-Force exceptions do not change. Read cannot bypass Evade or Rescue. If instead you declare that Strike as **Pressure**, it gains no protection bypass or damage/coordination bonus.
- **Read Protect:** one Protect cancels **one extra incoming damaging Strike** against an otherwise **eligible friendly target** in that Front. It gains no additional reach and cannot cancel Pressure. A rolled Protect can lose its Read benefit if Pressure suppresses that Protect before allocation.

You may use **at most one** of these two benefits per Front, not both. Announce a Read on the selected Force when Strikes/Pressure are declared, and allocate Read Protect with normal Protect effects. A Read is lost if there is no suitable rolled Strike/Protect or no legal target. **No Read marker, reroll, automatic attack, or new timing step exists.**

A Plan does **not** counter itself. The other two unordered plan pairs, **Assault versus Raid** and **Hold versus Volley**, are **neutral in either direction**. With four Plans, this four-edge cycle has a clear predator for each Plan rather than unbalanced always-winning pairwise rankings.

| Your Plan \\ Opponent's | Assault | Hold | Volley | Raid |
| --- | --- | --- | --- | --- |
| **Assault** | Mirror | Countered | **Read** | Neutral |
| **Hold** | **Read** | Mirror | Neutral | Countered |
| **Volley** | Countered | Neutral | Mirror | **Read** |
| **Raid** | Neutral | **Read** | Countered | Mirror |

### Opportunities: advance after winning an exchange

After casualties are removed, you may **advance one surviving, unpinned Force one empty rank forward in its Front** if you earned an **Opportunity in that same Front**. An Opportunity is earned when **at least one** of these occurred during the current Battle:

1. One of your damaging Strikes **permanently defeated** an enemy Force in this Front (a Force that is **saved by Rescue** was never defeated).
2. One of your Protect or Evade effects actually **cancelled an incoming damaging Strike** in this Front.
3. One of your Rescue effects **prevented a friendly Force's defeat** in this Front.

Pressure, failed damaging Strikes, unused protection, merely choosing a counter Plan, and watching an opponent retreat do **not** earn Opportunities.

**One post-combat move maximum per player per Front**—including a printed after-combat Special advance and a Plan/Opportunity advance. Resolve printed Special advances first. A special advance must satisfy its printed condition; it also uses that Front's one post-combat move. Assault may make the optional single forward step **without** an Opportunity, but does not gain a second move for earning one. Hold/Volley/Raid require an Opportunity for an ordinary forward step. The destination must be **empty after casualties**, immediately ahead in the same Front and legal for that card; no swap, jump, opposing-side crossing or movement into a closed Front. A Force that moved before combat or is **Pinned** cannot move again. **Pinned Forces cannot move** after combat, and **no Force moves more than once** during a Battle. All unused Opportunities disappear at Battle end.

Neither an Opportunity nor a Tactical Read adds Command or a territorial point. **Fronts remain controlled by the majority of surviving Forces, with no rank bonus.**

## Resolution order — every Battle

**All active Fronts resolve as one simultaneous exchange.** No Front's defeated cards are discarded before all Rescues, including printed adjacent-Front Rescues, have been checked.

1. **Reveal Plans and move.** Both players reveal their single hidden army-wide Plan. Declare and execute any Hold/Raid **pre-combat movement**, obeying original vacancy and rank restrictions.
2. **Roll.** Each player rolls one D6 for each occupied Front on their side; all their Forces there use their own corresponding result. Positions after movement determine **role-by-rank** permissions.
3. **Declare Strikes, Pressure and Reads.** Players freely choose simultaneous legal targets under their Plan and rank-role permissions. A solo-ineffective Strike may become Pressure instead of damage. If your Plan counters the enemy's, you may designate **one Tactical Read** on an eligible rolled Strike or Protect **per Front**. Read Strike may target any occupied rank unless its printed Special fixes a target.
4. **Evade, then Pressure.** Evade cancels all incoming damaging Strikes and Pressure against that Force. Pressure suppresses its target's entire rolled Protect/Rescue outcome, or Pins it if it rolled neither. A suppressed Read Protect is lost.
5. **Protect.** Allocate remaining Protect effects after declarations. A Frontline Guard can Screen any friendly Force in that Front when its Protect is rolled; Hold also widens Protect reach within its Front. **Read Protect** cancels one extra damaging Strike against an already-eligible friendly target. **Read Strike** ignores one Protect against itself (not Evade/Rescue).
6. **Damage, coordination and Pin.** Against each target with *n* uncancelled damaging Strikes, each attacking Force has effective Force **printed Force + (n − 1)**. If any attack exceeds target Force (or permits equality through its printed Special), that Force would be defeated. A remaining nonlethal damaging Strike Pins its target. Keep the exchange simultaneous.
7. **Rescue.** Allocate rolled Rescue effects to otherwise-defeated eligible friendly Forces. A Rear Healer/Steward can Sustain any friendly Force in its own Front (without adding Rescue capacity). Resolve printed adjacent-Front Rescues after checking all Fronts' threatened casualties.
8. **Discard, Special advances and Opportunities.** Permanently discard unrescued casualties. For each Front determine whether each player **earned an Opportunity** through an actual defeated enemy, cancelled damaging Strike or successful Rescue. Resolve eligible printed Special moves first, then at most one forward rank step in that Front under Assault or an earned Opportunity. A Force cannot move twice or while Pinned.
9. **Score control.** Compare surviving occupied positions (0–3 each) in each Front. More Forces wins control, equal counts are contested. Apply existing Command loss, Collapse check and recovery unchanged.

All rolled outcomes participate even when their source would be defeated in this exchange. Any one of your Forces can execute only its own rolled outcome once. Reads and Opportunities require no markers and never persist between Battles.

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

### Example: a predicted Plan changes a full Front

Your **Red Shields** (Guard, Frontline), **Crow Archers** (Archer, Middle), and **White Hands of Elara** (Healer, Rear) oppose a Frontline **Fifty Men**, a Middle **River Raiders**, and Rear **Tovan the Quartermaster**. **Volley counters Raid**, so when you reveal Volley against Raid you earn a Tactical Read in this Front. With your D6 **2**, the Guard rolls **Special Protect**, the Archer rolls **ordinary Strike**, and the Healer rolls **Special Rescue**; your opponent's D6 **1** produces two Strikes and Tovan's Protect.

You may nominate the Archer's **Read Strike**, giving it permission to target any enemy rank and ignore one Protect (though here Tovan's Protect only covers Frontline, so the protection bypass is redundant). The Guard's Special Protect cancels one enemy Strike against Archers, while the Healer can Rescue the Guard. The Archer defeats Tovan (Force 3 vs Force 2), so your Volley army earns an **Opportunity** in this Front and may advance one *unpinned* survivor into an empty forward rank **if one exists**. This is not an automatic second attack, free card or immediate control point.

Under the same rolls with **Assault against Raid**, neither army has a counter Read. The Archer's ordinary Strike can target only the foremost enemy (Fifty Men, Force 5) instead of Rear Tovan. With a sole Force-3 Strike, it cannot defeat Fifty Men; it may remain a nonlethal damaging Strike and Pin them, or become Pressure at declaration. Assault retains its unconditional post-combat forward step if a legal square exists. **The roll, Force values and number of actions are identical**; prediction and role placement change what can happen.

For detailed sixteen-matchup reasoning, see [Phase 2 tactical audit](phase2-tactical-audit.md).

## Playtest failure tests

Record each player's plan, each Front's two die results, attacks cancelled, fatalities, surviving headcount, final control and post-Battle Command. Test these before changing the entire 44-identity pool:

- Do **two weak coordinated Strikes** defeat strong defenders too reliably?
- Does **Force** remain dominant because high-Force troops are always safer and can kill lower Force?
- Are **Protect** and **Rescue** sufficiently different?
- Can players read and resolve a **full twelve-Force side** quickly without persistent markers?
- Do **Volley** and **Raid** have credible alternatives to **Assault** and **Hold** in several deck matchups?
- Does majority control reward three inexpensive Forces over a stronger mixed formation?

No digital match, AI win rate or historical balance result validates these paper rules. They require physical playtesting.
