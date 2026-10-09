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

Each Front has **three positions per player**: **Frontline**, **Middle**, and **Rear**. Frontline faces the opponent; adjacent Fronts sit to the left and right.

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

Before drawing, choose whether to **Pass** (see *Passing*). Otherwise:

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

A Force anchors a formation. A Force with a Bond is **Bonded**; with both Bond and Name it becomes **Named**. A Name alone does not make a Force Named. A Bond without a Name is an **open Bond**.

A Bond or Name placed without a Force is **prepared**: face-up, with no Strength. It attaches when a legal Force arrives. You cannot simply replace an existing Bond or Name; a card effect must remove, return or exchange it.

**PLAY** abilities happen when a card is played, including a prepared layer. **BECOMES NAMED** happens when a formation gains its missing layer and becomes Named. Resolve PLAY first, then the new completion effects. Prepared cards do not repeat their old PLAY effects when attached later.

If an ACTION ability tells you to play a card, that play is part of the spent Action; pay the played card's cost unless the ability discounts it.

### Row and placement restrictions

Only use **active Fronts** and legal positions. Every resulting Force, Bond and Name must meet its restrictions, including after a Move or swap.

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

Classifications come from the **Force and attached Name together**. They determine basic Attacks and which card effects apply. A Force with several Attack classifications still attacks only **once per Battle**, choosing one Attack. **Guard** grants its screening rule. Other classifications do only what card text says.

## Maneuver and card movement {#maneuver}

A **Named Formation** may Maneuver for **one Action and 1 Command**: move one step forward/back in its Front or left/right to an active adjacent Front in the same row. No diagonals.

Move the complete formation and its markers. It can enter a position without a Force and attach compatible prepared layers. It may instead **swap** with a friendly formation if both positions remain legal; only the initiator must qualify. An **Exhausted** Force cannot initiate a normal Maneuver unless a card permits it, but can be swapped by another formation.

Printed **Move** and **swap** effects are different from Maneuver: they do not require a Name, usually cost no Maneuver Command, and can move Exhausted Forces. Follow their stated range and targets. A two-step Move takes two legal adjacent steps, never jumping over an occupied or inactive position. A free *Maneuver* remains a Maneuver with its normal restrictions.

**Empty** means no Force (prepared layers may be present); **completely empty** means no cards. A movement cannot duplicate layers, violate a row restriction or enter an inactive Front.

## Attacking {#attacking}

An **Attack** uses **one Action**, normally costs no Command, and each Force gets **one Attack per Battle**. It need not be Named. Mark it used. A **Depleted** Force cannot Attack.

Choose a legal opposing Force, check target and screening, allow eligible responses, then apply the effect:

| Attacker | Legal target | Result |
| --- | --- | --- |
| **Archer** | Opposing Rear in same Front | Exhaust |
| **Skirmisher** | Opposing Middle in same Front | Shake |
| **Raider** | Opposing Middle or Rear in same Front, if opposing Frontline is empty | Deplete |
| **Rider** from Frontline/Middle | Flanked opposing Frontline in adjacent active Front | Shake |

An **ATTACK** ability modifies or extends that one Attack; it does not grant another unless explicitly stated. A friendly **Guard in Middle** screens the Rear Force directly behind it from basic Archer Attacks; Shaken or Depleted Guards cannot screen. Other Attacks and effects are not automatically screened.

### Flanking

A Frontline Force is **flanked** if the opponent has a Frontline Force in an adjacent active Front **and you have none there**. It suffers **−1 Strength**, even if flanked on both sides. Recheck after movement. A Force that *cannot be flanked* suffers no flank penalty and is not a legal basic Rider target.

## Conditions and protection {#conditions}

A Force can have one marker of each condition. Identical conditions do not stack; different penalties do. Markers travel with their Force.

- **Exhausted:** −1 Strength; cannot initiate ordinary Maneuver. It may still Attack and use abilities.
- **Shaken:** −2 Strength; Guard screening stops.
- **Depleted:** −1 Strength; cannot Attack or activate **any ACTION** printed on its formation. Passive and triggered effects still work.

Conditions are removed only by card effects or Battle-end cleanup; there is **no generic recovery Action**. Removing Exhaustion does not reset a spent Attack.

### Boons

- **Guarded:** cancel the next affliction, then remove Guarded. This includes lost-Front Exhaustion.
- **Inspired:** remove Shaken and prevent it while Inspired.
- **Empowered:** the next Attack ignores screening, then remove Empowered (not range or Attack limits).

Boons do not stack with themselves. Guarded stops one affliction, not a sequence of separate ones. All temporary conditions and Boons normally clear during Battle-end cleanup.

## Special cards {#stories}

**Tactics** target the opponent; **Orders** help you. Play each for one Action and its printed cost, resolve PLAY, then discard.

**Narratives** stay face-up **until Battle end**. You can have at most **4** in play. Resolve PLAY immediately; CONTINUOUS and ACTION abilities work while present. Playing an ACTION later costs its own Action.

**Stratagems** are hidden plans. Play at most **one from hand per Battle**, face-down beside a publicly chosen **active Front**, for one Action and its printed cost. When their REVEAL condition occurs, you may reveal and resolve them. Unless specified otherwise, their effects refer to that Front. Each revealed Stratagem resolves once and is discarded; unrevealed ones are discarded at Battle end. Opposing reveals at the same event are simultaneous.

**Heroes** are Unique cards played as **Force or Name**. Choose the mode when played and use only its corresponding Strength and abilities. You may play **one Hero as Force and one as Name from hand per Battle**; Heroes remaining from earlier Battles do not use those allowances.

## Command {#command}

You start at **20 Command**, cannot exceed 20, and cannot voluntarily spend below 0. Apply cost increases before reductions. A positive printed cost cannot fall below **1** unless an effect explicitly allows 0.

Effects that steal Command normally cannot reduce the opponent below **1 during a Battle**, unless they say otherwise. **Command Collapse** is checked only when resolving the Battle, after Command loss for defeated Fronts.

## Passing and ending a Battle {#passing}

**Pass** is an entire turn, chosen **before drawing**. You draw nothing and take no Actions. You may Pass even when actions are available.

The first Pass begins the closing sequence:

1. The **other player** takes a full turn (draw 1, up to 2 Actions).
2. The **passer** takes a full turn (draw 1, up to 2 Actions).
3. **Resolve the Battle** immediately.

Neither closing turn may Pass. If the war continues, the player **who did not Pass** starts the next Battle.

## Resolving a Battle {#scoring}

Resolve these six steps **in order** after the last closing turn.

### 1. Reveal Stratagems

Check unrevealed Stratagem eligibility against the **initial** board and provisional Strength, including *would tie* and *would lose by exactly 1*. Both players decide privately and reveal simultaneously. Apply effects; **do not open another reveal window**.

### 2. Settle Fronts

For each active Front, add the final Strength of each side's formations. Higher Strength wins. A tie defeats neither player. Record Fronts lost; **formations stay on the field**.

### 3. Lose Command

Resolve Battle-end card effects, then lose **1 Command per lost Front**, unless prevented by card text. This loss can take Command to 0 or below.

### 4. Check Collapse

Check **before recovery**. A player at 0 or less loses the war. If both collapse, the **lower total** loses; if equal, the **passer** loses.

### 5. Clean up and Exhaust defenders

First let **Guarded** prevent lost-Front Exhaustion. Then:

1. Clear old afflictions, Boons, use markers, temporary effects and Narratives; discard unrevealed Stratagems.
2. Apply **one new Exhaustion token** to every unprotected Force in a lost Front.

New Exhaustion lasts through the next Battle unless removed by a card. Layers remain in play. An Exhausted Force still contributes Strength and may Attack.

### 6. Recover and continue

If neither player collapsed, recover **12, 9, 6, 3, then 1 Command per subsequent Battle**, to a maximum of 20. Refill hands to **10**, reset once-per-Battle uses, open the next scheduled Front, and let the non-passer begin.

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

Resolve instructions in printed order. For multiple friendly triggers at the same time, their controller chooses the order, except simultaneous opposing Stratagems.

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
