# The Long War

*Fight now. Live with it later.*

**The Long War** is a two-player card game fought across successive Battles. Your formations survive from one Battle to the next. Losing a Front costs Command and leaves defenders Exhausted; it does not remove them. **A player loses the war when their Command collapses.**

## The shape of the war {#learn}

You fight over up to four **Fronts**, opening from the centre outward:

- **Battle I:** Fronts 2 and 3.
- **Battle II:** add Front 1.
- **Battle III:** add Front 4.
- **Battle IV onward:** all four remain active.

Inactive Fronts cannot be used. In each Battle, players take turns until someone Passes. Both players then get a final turn before each active Front is scored. Formations stay in place for the next Battle.

## The battlefield {#battlefield}

Each Front has **three positions per player**: Frontline nearest the opponent, then Middle and Rear. Fronts run from left to right.

A position holds at most **one Force, one Bond, and one Name**. Together they form a **formation**; all three layers make a **Named Formation**. Stack Force at the bottom, Bond in the middle, and Name on top, leaving the exposed strips visible. Each Force's row symbols restrict where it may stand.

## What you need {#components}

- One deck per player (published playtest decks contain **48 cards**).
- Two **Command tracks (0–20)** and four Front markers.
- Condition markers: **Exhausted, Shaken, Depleted, Guarded, Inspired, Empowered**.
- Used-Attack and once-per-Battle reminders; other markers when cards require them.

A playmat is optional. Lay out four Fronts with three rows on each player's side.

## Setup {#setup}

1. Shuffle your decks and set both Command totals to **20**.
2. Each draw **10 cards**. You may return up to **2** to your deck, shuffle, and replace them.
3. Randomly choose who plays first.
4. Open Fronts **2 and 3**.

Hands, decks and face-down Stratagem identities are hidden. Command, card counts, battlefield, discard piles and a Stratagem's assigned Front are public.

## Your turn {#turn}

Before drawing, you may **Pass** (see *Passing*). Otherwise, take your normal turn:

1. **Draw 1 card.**
2. Take **up to 2 Actions**, in any combination:

- **Play** a card, paying its Command cost.
- Use a printed **ACTION** ability, paying any stated cost.
- **Maneuver** a legal formation for **1 Command**.
- **Attack** with a Force that has not attacked this Battle.
- **Cycle:** discard 2 cards to draw 1.

Each choice uses one Action unless a card says otherwise. You may end a normal turn with Actions unused; doing so is not Pass. If your hand exceeds **10**, discard down to 10 before continuing. If a deck runs out, shuffle its discard pile to draw again.

A printed **1/BATTLE** ability can be used once per physical card per Battle, even if the card leaves play and returns. Mark it as used; reset between Battles. Free plays or Attacks granted by card text still follow their normal legality and limits unless explicitly overridden.

## Playing cards and building formations {#cards}

You may play a **Force, Bond or Name** in any order into its empty layer slot, in a legal active position. Playing a card normally costs **one Action plus its printed Command**.

A Force anchors a formation. Add a Bond to make it **Bonded**; add both a Bond and Name to make it **Named**. A Name alone does not make it Named; a Bond without a Name is an **open Bond**.

A Bond or Name placed without a Force is **prepared**: face-up, with no Strength. Its PLAY text works when played, but other abilities wait until attached to a Force; WHILE NAMED still requires all three layers. It attaches when a legal Force arrives. You cannot simply replace an existing Bond or Name; a card effect must remove, return or exchange it.

**PLAY** abilities happen when a card is played, including a prepared layer. **BECOMES NAMED** happens when a formation gains its missing layer and becomes Named. Resolve PLAY first, then the new completion effects. Prepared cards do not repeat their old PLAY effects when attached later.

If an ACTION ability tells you to play a card, that play is part of the spent Action; pay the played card's cost unless the ability discounts it.

### Row and placement restrictions

Only use **active Fronts** and legal positions. Every resulting Force, Bond and Name must meet its restrictions, including after a Move or swap. On a card in play, **here** means **in this Front**, not only its position.

### Strength {#strength}

Add a Force's Strength, attached Bond/Name modifiers and active effects. A Hero uses the figures printed for its chosen mode. Penalties are cumulative:

| Condition | Strength change |
| --- | --- |
| **Exhausted** | −1 |
| **Depleted** | −1 |
| **Shaken** | −2 |
| **Flanked** | −1 |

A formation contributes **at least 0** Strength. Prepared layers contribute none. At Battle end, sum all friendly formations across a Front's three rows. Higher total wins that Front; a tie costs neither side anything. Score **each Front separately**.

> **Example:** Force 3 + Bond 1 + Name 1 = **5 Strength**. Exhausted and Shaken bring it to **2**.

### Classifications {#classifications}

Classifications come from the **Force and attached Name together**. They determine basic Attacks and which card effects apply. When a card asks you to choose one classification, choose it once and apply the effect once per qualifying formation. A Force with several Attack classifications still attacks only **once per Battle**, choosing one Attack. **Guard** grants its screening rule. Other classifications do only what card text says.

## Maneuver and card movement {#maneuver}

**Any formation**, Named or not, may Maneuver for **one Action and 1 Command**: move one position forward/back in the same Front or left/right to an adjacent active Front in the same rank. No diagonals.

Move the complete formation and its markers. It can enter a position without a Force and attach compatible prepared layers. It may instead **swap** with a friendly formation if both positions remain legal; only the initiator must qualify. An **Exhausted** Force cannot initiate a normal Maneuver unless a card permits it, but can be swapped by another formation.

Printed **Move** and **swap** effects are different from Maneuver: they usually cost no Maneuver Command, and can move Exhausted Forces. Follow their stated range and targets. A two-step Move takes two legal adjacent steps, never jumping over an occupied or inactive position. A free *Maneuver* remains a Maneuver with its normal restrictions.

**Empty** means no Force (prepared layers may be present); **completely empty** means no cards. A movement cannot duplicate layers, violate a row restriction or enter an inactive Front.

## Attacking {#attacking}

An **Attack** uses **one Action**, normally costs no Command, and each Force gets **one Attack per Battle**. It need not be Named. Mark it used. A **Depleted** Force cannot Attack.

Choose a legal opposing Force, check target and screening, allow eligible responses, then apply the effect:

| Attacker | Legal target | Result |
| --- | --- | --- |
| **Archer** | Opposing Rear in same Front | Shake |
| **Skirmisher** | Opposing Middle in same Front | Shake |
| **Raider** | Opposing Middle or Rear in same Front, with a successful Incursion | Deplete |
| **Rider** from Frontline/Middle | Flanked opposing Frontline in adjacent active Front | Shake |

**Incursion:** A Raider in your Frontline succeeds if its current Strength is greater than the opposing Frontline formation's Strength, or if that opposing position has no Force. A tie holds the line. The Raider stays on your side; the Incursion is its normal Attack, not another Action.

An **ATTACK** ability modifies or extends that one Attack; it does not grant another unless explicitly stated. Only a **card effect** can combine a Move or Maneuver with a free Attack. A friendly **Guard in Middle** screens the Rear Force directly behind it from basic Archer Attacks; Shaken or Depleted Guards cannot screen. Other Attacks and effects are not automatically screened.

### Flanking

A Frontline Force is **flanked** if the opponent has a Frontline Force in an adjacent active Front **and you have none there**. It suffers **−1 Strength**, even if flanked on both sides. Recheck after movement. A Force that *cannot be flanked* suffers no flank penalty and is not a legal basic Rider target.

## Conditions and protection {#conditions}

A Force can have one marker of each condition. Identical conditions do not stack; different penalties do. Markers travel with their Force.

- **Exhausted:** −1 Strength; cannot initiate ordinary Maneuver. It may still Attack and use abilities.
- **Shaken:** −2 Strength; Guard screening stops.
- **Depleted:** −1 Strength; cannot Attack or activate **any ACTION** printed on its formation. Passive and triggered effects still work.

Only actual negative markers on Forces (such as Exhausted, Shaken and Depleted) can be removed by marker-removal effects. Temporary Strength penalties, ignored text and ACTION locks are not removable markers unless the card says to place one. Conditions otherwise leave only through card effects or Battle-end cleanup; there is **no generic recovery Action**. Removing Exhaustion does not reset a spent Attack.

### Boons

- **Guarded:** cancel the next affliction, then remove Guarded. This includes lost-Front Exhaustion.
- **Inspired:** remove Shaken and prevent it while Inspired.
- **Empowered:** the next Attack ignores screening, then remove Empowered (not range or Attack limits).

Boons do not stack with themselves. Guarded stops one affliction, not a sequence of separate ones. All temporary conditions and Boons normally clear during Battle-end cleanup. An unspent Tax marker also expires at Battle end.

## Special cards {#stories}

**Tactics** target the opponent; **Orders** help you. Play each for one Action and its printed cost, resolve PLAY, then discard. Targeting a Force also targets its formation for Tactic protections and costs. A Tactic or Order that selects a target or Front counts as played in that Front; global cards do not. Choose the Front and target before paying any Tax.

**Narratives** stay face-up until Battle end (up to **4** at a time). Resolve PLAY when you play one; CONTINUOUS text operates while it remains, and ACTION text costs an Action when used.

**Stratagems** are hidden plans. You may set **one per Battle** for an Action and its cost (or through a card that saves the Action). Place it face-down beside a publicly chosen **active Front**. When its condition is met, you may reveal it. It resolves once, then is discarded; unrevealed plans leave at Battle end. Opposing plans with the same trigger reveal simultaneously.

**Heroes** are Unique cards played as **Force or Name**. Their Command seal has two centred prices: **Force on top, Name below**. Choose the mode when played, pay that price and use only its corresponding Strength and abilities. You may play **one Hero as Force and one as Name from hand per Battle**; Heroes remaining from earlier Battles do not use those allowances.

## Command {#command}

You start at **20 Command**, cannot exceed 20, and cannot voluntarily spend below 0. Apply cost increases before reductions. A positive printed cost cannot fall below **1** unless an effect explicitly allows 0.

Effects that steal Command normally cannot reduce the opponent below **1 during a Battle**, unless they say otherwise. **Command Collapse** is checked only when resolving the Battle, after Command loss for defeated Fronts.

## Passing and ending a Battle {#passing}

**Pass** is an entire turn, chosen **before drawing**. You draw nothing and take no Actions. You may Pass even when actions are available.

The first Pass begins the closing sequence:

1. The **other player** takes a full turn (draw 1, up to 2 Actions).
2. The **passer** takes a full turn (draw 1, up to 2 Actions).
3. Both players reveal their **Opening Orders**, then **resolve the Battle**.

Neither closing turn may Pass. If the war continues, the player **who did not Pass** starts the next Battle.

## Opening Orders {#opening-orders}

After the two closing turns, each player secretly writes **two Opening Orders**, numbered 1 and 2. You may repeat a type:

- **Maneuver:** Maneuver one friendly formation one legal step. No Action or Command cost. An Exhausted Force still cannot initiate.
- **Commit:** Pay **1 Command** to give **+2 Strength** to one active Front containing one of your Forces this Battle. This adds to the **Front total**, not an individual Force; it counts only while you have a Force there.
- **Strike:** Make one legal **basic Attack** with a chosen Force against a chosen target. It uses that Force's normal once-per-Battle Attack.
- **Hold:** Do nothing.

**Reveal all four orders together.** First reveal any Stratagem triggered by that reveal; it may alter only what its own text permits. Pay for valid Commit orders, then resolve Maneuvers followed by Strikes in numbered order. Opposing orders at the same step happen simultaneously. Check legal positions and targets after earlier steps; an impossible order does nothing. **Other Stratagems may react to a Move or Attack as usual**, but resolution Stratagems wait until Opening Orders are complete. Two Commits may reinforce the same Front. All Opening Orders are **free Actions**; only Commit spends Command.

The procedure is **identical in every Battle, including Battle I**. Players play their cards during their normal turns before the Pass and closing turns. Opening Orders happen **once**, after those turns and before Stratagems are revealed.

## Resolving a Battle {#scoring}

After the Opening Orders have resolved, follow these six steps **in order**.

### 1. Reveal Stratagems

Check unrevealed Stratagem eligibility against the **initial** board and provisional Strength, including *would tie* and *would lose by exactly 1*. Both players decide privately and reveal simultaneously. Apply effects; **do not open another reveal window**.

### 2. Settle Fronts

For each active Front, add each player's formation Strength and any **Commit** bonus. Higher Strength wins. A tie defeats neither player. Record each lost Front and its **Strength difference**; formations stay on the field.

### 3. Lose Command

Resolve Battle-end card effects, then for **each lost Front lose Command equal to the difference in Strength** (for example, 8 against 5 loses **3 Command**), unless prevented by card text. Add losses across Fronts; a tie costs nothing. Loss can take Command to 0 or below.

### 4. Check Collapse

Check **before recovery**. A player at 0 or less loses the war. If both collapse, the **lower total** loses; if equal, the **passer** loses. If Command falls below 0, write the negative total beside the track for this comparison.

### 5. Clean up and Exhaust defenders

Choose **one Force in each lost Front**, if any. Its Guarded may prevent Exhaustion; if it does, do not choose a replacement. Then:

1. Clear old afflictions, Boons, use markers, unspent Tax markers, temporary effects and Narratives; discard unrevealed Stratagems.
2. Apply **one new Exhaustion token** to each chosen, unprotected Force (at most one per lost Front).

New Exhaustion lasts through the next Battle unless removed by a card. Layers remain in play. An Exhausted Force still contributes Strength and may Attack.

### 6. Recover and continue

If neither player collapsed, recover **12, 9, 6, 3, then 1 Command per subsequent Battle**, to a maximum of 20. Refill hands to **10** and reset once-per-Battle uses. Open the next scheduled Front, then the player who did not Pass begins the next Battle.

## Reference {#reference}

### Timing words

| Card text | Meaning |
| --- | --- |
| **PLAY** | Resolve when played, even if prepared. |
| **BECOMES NAMED** | Resolve on a real change to a Named Formation. |
| **ACTION / ACTION · 1/BATTLE** | Spend an Action; for 1/BATTLE, once per physical card per Battle. |
| **ATTACK** | Changes that Force's one Attack. |
| **FRONT / MIDDLE / REAR** | Active in the named row. |
| **BONDED / WHILE NAMED / CONTINUOUS** | Active while the condition and card remain in play. |
| **TRIGGER / REACTION** | Resolve when the stated event occurs. |
| **HIDDEN / REVEAL** | Hidden Stratagem, optionally revealed on its trigger. |

Resolve instructions in printed order. A free basic Attack after a Move still needs an unused Attack and a legal target. A card with no legal target for its PLAY effect has no effect from that instruction. For multiple friendly triggers at the same time, their controller chooses the order, except simultaneous opposing Stratagems.

### Removing layers

| Event | What remains |
| --- | --- |
| **Force discarded** | Discard its attached Bond and Name and conditions. |
| **Bond discarded** | Keep Force; return attached Name to hand. |
| **Bond returned** | Keep Force and any Name in position; no longer Named. |
| **Name returned or discarded** | Keep Force and Bond; Bond becomes open. |
| **Force moves / swaps** | Move attached layers and markers together; attach compatible prepared layers. |
| **Battle ends** | Ordinary Force/Bond/Name layers stay. |

### Deck construction

A deck needs **at least 34 cards**. Use at most **4 copies** of a non-Unique title and **1 copy** of a Unique title. There are **no Force or printed-Name minimums**. Heroes are Unique.

More unusual interactions—including attached-card transfers, simultaneous Stratagem conflicts, forced movement, suppression, Tax markers and specific card examples—are in the **Detailed Reference** on the website.

> The battlefield grows. Your commitments remain. A lost Front matters next Battle.
