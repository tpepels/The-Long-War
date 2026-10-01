# The Long War

*Fight now. Live with it later.*

**The Long War** is a two-player card game about fighting a war that does not reset after each round.

You play across four contested areas. During a round, both players build up positions with cards, shift established groups, and decide how much of a limited resource they are willing to spend.

When both players are ready to stop, the four areas are settled separately. Some groups survive into the next round, some are pushed back, and some disappear entirely. The resource you spent does not simply come back.

That makes every round part of a longer argument. You may give up ground now to preserve resources for later, or spend heavily to hold a position that matters. Eventually one side can no longer sustain the war.

> If you remember one idea before learning the vocabulary, remember this: what you spend and what you leave standing now will shape the next round.

## How the war unfolds {#learn}

A round in The Long War is called a **Battle**.

The battlefield is divided into four contested areas called **Fronts**.

Each player begins the war with **{{STARTING_COMMAND}} Command**. **Command** is the resource used to play cards and move established groups. It carries from one Battle to the next.

A Battle has a simple arc:

1. Players alternate turns, drawing a card and then doing one thing.
2. They build positions, move established groups, or choose to do nothing.
3. Once both players have chosen to stop at least once, the Battle ends.
4. Resolve the four Fronts separately.
5. Some groups survive, while incomplete positions are cleared and losing positions may be pushed back.
6. Check whether either side has exhausted its Command.
7. If the war continues, recover some Command, refill hands, and begin another Battle.

A war may last several Battles. The board you preserve and the Command you save matter later.

![A Battle moves from alternating turns until both players have Passed, then through four separate Front resolutions, Retreat, the collapse check, and recovery.](assets/rulebook-battle-flow.svg)

> **REMEMBER** Winning more Fronts is useful, but there is no single Battle victory. The war ends through Command Collapse.

## The battlefield

Each Front has two positions on each player's side.

The position nearest the centre is the **Frontline**. The position behind it is the **Rear**. The four Frontline positions form one rank; the four Rear positions form the other.

```
                         OPPONENT

              FRONT 1   FRONT 2   FRONT 3   FRONT 4
                Rear      Rear      Rear      Rear
             Frontline Frontline Frontline Frontline
        =================================================
                       BATTLE LINE
        =================================================
             Frontline Frontline Frontline Frontline
                Rear      Rear      Rear      Rear
              FRONT 1   FRONT 2   FRONT 3   FRONT 4

                           YOU
```

Cards can contribute a number called **Strength**. At the end of a Battle, compare the Strength on the two sides of each Front.

- Higher total Strength wins that Front.
- Equal totals tie.
- There is no overall Battle winner.

What survives at a Front matters more than the margin by which it was won.

## Setup {#setup}

1. Each player takes a deck of **at least {{MINIMUM_DECK_SIZE}} cards**.
2. Set each player's Command to **{{STARTING_COMMAND}}**.
3. Shuffle and draw **{{OPENING_HAND_SIZE}} cards**.
4. You may shuffle up to **{{MULLIGAN_MAX_CARDS}} cards** from your hand back into your deck, then draw the same number.
5. Randomly choose the first player.

Hands and decks are hidden.

Battlefield cards, discard piles, hand size, deck size, Command, and any face-up cards outside the battlefield are public.

The first player's first turn is normal. If their opening hand is already at the hand limit, they discard 1 before drawing 1.

## Playing a Battle

Players alternate turns. A turn always starts with a draw, then gives that player exactly one chosen action.

You are not required to keep spending until you run out of useful plays. Choosing to stop can be part of the strategy: once both players have an active Pass, the Battle ends and the four Fronts are resolved.

After that resolution, the board is not wiped clean. Complete established groups can remain in place for the next Battle. That is why building something that lasts can be more valuable than winning one Front cheaply for a moment.

## Your turn {#turn}

At the start of every turn, **draw 1 card**.

Your hand limit is **{{HAND_LIMIT}}**. If you would draw while holding {{HAND_LIMIT}} cards, discard 1 card first, then draw.

After drawing, take exactly **one operation** - one chosen action for the turn:

1. **Play one card** and pay its Command cost.
2. **Maneuver** - pay {{MANEUVER_COMMAND_COST}} Command to move one eligible established group sideways. The exact kind of group that can do this is defined below.
3. **Pass** - spend 0 Command and take no other operation.

You cannot spend more Command than you have. Command never goes below 0.

A cost reduction cannot reduce a card below 1 Command unless the card explicitly says it costs 0.

There is no generic Draw operation, Advance, or attack step.

## Building a position {#cards}

At each position you can build a stack using three kinds of cards.

A **Force** supplies the group's printed Strength.

A **Bond** can connect to that Force.

A **Name** gives the group its identity.

A position can hold at most one Force, one Bond, and one Name.

Any stack containing a Force is a **formation**. A formation containing **Force + Bond + Name** is a **Named Formation**.

Named Formations matter because they can survive from one Battle to the next and can Maneuver. Unless they are removed or driven off, Named Formations remain on the battlefield when a Battle ends.

Force, Bond, and Name may be played in **any order**.

![A position can begin with prepared cards, become a formation when a Force arrives, and becomes a Named Formation only when Force, Bond, and Name are all present.](assets/rulebook-formation.jpg)

> **EXAMPLE** You may play a Bond and a Name first. They wait face-up without Strength. When a Force later enters that position, the three cards immediately form a Named Formation.

### Prepared cards

If a Bond or Name is played into a position without a Force, it is **prepared**. It stays face-up, but it has no Strength and no Force-dependent effect until a Force arrives.

As soon as a Force is present, the prepared card becomes part of the formation.

### Open and incomplete formations

A Force with a Bond but no Name has an **open Bond**.

A Force may also have a Name without a Bond. Force + Name is a formation, but it is not a Named Formation.

Anything short of Force + Bond + Name is incomplete and will normally be cleared at Battle end.

### Completing a Named Formation

Text beginning **When you play...** happens only when that card itself is played.

Text beginning **When this formation becomes Named...** happens when the position first contains Force + Bond + Name, whichever card completed it.

Every printed Name is marked **Unique**. Unique means that at most one copy of that title may be included in your deck; it does not prevent the other player from using their own copy.

### Deployment restrictions

**Deploy - Frontline only** and **Deploy - Rear only** restrict where a Force enters play. They do not prevent later movement unless the card also says so.

## Maneuver {#maneuver}

A **Maneuver** is an operation that moves one of your Named Formations. It costs **{{MANEUVER_COMMAND_COST}} Command**.

Choose one of your Named Formations and move it:

- one Front left or right;
- in the same rank.

If the destination is empty, move there.

If the destination contains one of your formations, swap the two positions. Only the formation starting the Maneuver must be Named.

During the resolution of a single operation, each formation may initiate at most one Maneuver.

When formations swap, only the formation chosen to Maneuver is considered to have Maneuvered. The other formation is displaced by the swap.

Move every Bond and Name with its Force.

![A Maneuver moves one Named Formation one Front left or right without changing rank; an occupied friendly destination causes a swap.](assets/rulebook-maneuver.jpg)

> **REMEMBER** A Maneuver moves the whole formation. Bond and Name never stay behind when their Force moves.

You cannot normally Maneuver between Battles or change rank with a Maneuver.

## Passing {#passing}

To **Pass** is to spend 0 Command and take no other operation.

Normally, you cannot Pass until both players have completed at least one operation in the Battle. If you have no other legal operation, you may Pass.

Once you Pass, that Pass remains active for the rest of the Battle. The opponent takes a normal turn, and you continue taking normal turns too.

You may still take non-Pass operations later. They do **not** remove your Pass.

As soon as the other player also Passes, the Battle ends. After the first Pass has been made, the other player may Pass on any later turn.

A Battle therefore ends when **both players have Passed at least once**.

![A Pass remains yours while play continues; the Battle ends once both players have Passed.](assets/rulebook-pass-flow.jpg)

> **REMEMBER** Passing costs one operation once. After that, your Pass cannot be cleared during that Battle.

The player who **Passed first** starts the next Battle.

## Resolving the four Fronts {#scoring}

When a Battle ends, resolve all four Fronts separately.

For each Front, apply card text that matters to its result and total the Strength that counts there.

- Higher total wins.
- Equal totals tie.
- Prepared cards without a Force count 0 Strength.
- Strength cannot fall below 0 unless a card says otherwise.

The margin of victory has no effect unless a card says otherwise.

## Losing ground {#retreat}

After all four Front results are known, clear incomplete positions first.

Discard every Force, Bond, or Name that is not part of a Named Formation.

Then deal with each Front you lost. A surviving Named Formation may be forced backward; that forced movement is called a **Retreat**.

For each lost Front:

1. Drive off the Rear Named Formation, if there is one.
2. Then Retreat the Frontline Named Formation into the Rear, if there is one.

![When a Front is lost, its Rear Named Formation is driven off first; only then does its Frontline Named Formation Retreat into the Rear.](assets/rulebook-retreat.jpg)

> **REMEMBER** The order matters. Clear the Rear first, then move the Frontline group backward.

A driven-off formation is discarded as Force + Bond + Name.

A tie does nothing. Named Formations in a won Front stay where they are.

This is the main way the battlefield carries history forward: complete groups can survive, but losing ground can force them back or remove them.

## After the Battle {#after-battle}

After Retreats are complete:

1. Resolve Battle-end card effects.
2. Discard effects that last only for this Battle.
3. Check whether either player has exhausted their Command.
4. If the war continues, recover Command.
5. Draw until you have {{HAND_LIMIT}} cards.
6. Reset allowances that apply once per Battle.
7. Start the next Battle with the player who Passed first.

Keep your hand, draw pile, and discard pile between Battles.

Do not reshuffle just because a Battle ended. If you must draw from an empty deck, shuffle your discard pile into a new draw pile.

There is **no between-Battle Maneuver**.

## Command and ending the war {#command}

Command carries from one Battle to the next and stays between **0 and {{COMMAND_CAP}}**.

Winning every Front is not automatically worth the cost. Command spent to secure one Battle may leave you unable to survive the check that follows it.

### Recovery

If the war continues, each player recovers Command.

Base recovery starts at **{{RECOVERY_START}}** in Battle I and falls by **{{RECOVERY_DECREMENT}}** each Battle:

**{{RECOVERY_SERIES_PLAIN}}**

Before the Collapse check, lose **{{LOST_FRONT_COMMAND_PENALTY}} Command for each Front you lost** in that Battle, to a minimum of 0. Card effects can protect you from this loss.

If the war continues, recover the base amount above. Your recovery is never less than **{{RECOVERY_FLOOR}}**, and Command never rises above {{COMMAND_CAP}}.

> **EXAMPLE** If you end a Battle on 3 Command after losing two Fronts, subtract the configured lost-Front penalty twice before the Collapse check. If you survive, you then receive that Battle's normal recovery.

The recovery numbers above are generated from the same rules configuration used by the game engine.

### The collapse check

The check that can end the war is called **Command Collapse**. It happens after Front resolution, cleanup, Retreats, relevant Battle-end effects, and Front-loss Command attrition, but **before Command recovery**.

- If either player is at or below **{{COLLAPSE_THRESHOLD}} Command**, compare their current Command.
- The player with lower Command loses the war.
- If both players are at or below **{{COLLAPSE_THRESHOLD}} Command** with equal Command, the war ends in a **draw**.
- Only a continuing war receives Command recovery.

## Special card types {#narratives}

Some cards sit outside the Force-Bond-Name structure or bend it in a defined way.

### Narratives

A **Narrative** represents something the war has made true beyond a single formation.

Narrative is the umbrella term for **Legend, Saga, Myth, Omen, Warning, Prophecy,** and **Conspiracy**. The specific form is printed on the card.

Narratives are always face-up.

- A Narrative marked **Ongoing** stays in play until its text ends it.
- Any other Narrative resolves when played, then is discarded.
- You may have at most **{{ONGOING_NARRATIVE_LIMIT}} Ongoing Narratives** in play.

The individual Narrative forms have no hidden rules of their own.

### Stratagems

A **Stratagem** is a public plan for the current Battle. Play it face-up in your Stratagem area. Playing it is your operation and you pay its Command cost.

You may play at most **one Stratagem from hand per Battle**.

Discard Stratagems at Battle end unless a card says otherwise. The allowance resets for the next Battle.

### Heroes

A **Hero** is a Unique card that can be played as either a Force or a Name. Use the matching text on the card.

You may play at most **one Hero from hand per Battle**.

A Hero already on the battlefield does not use the next Battle's Hero allowance. The allowance resets for each Battle, and there is no separate cap on Heroes already in play.

Heroes count toward the Force minimum when building a deck.

### Labels and position words

Words such as *Swordsman*, *Archer*, *Human*, *King*, or *Ship* are classifications. They have no hidden rules. If a classification matters mechanically, a card will say so.

**Adjacent** means one Front left or right in the same rank.

**In front of** and **behind** mean the other rank in the same Front.

Unique is not a shared battlefield limit: both players may control their own copy of the same Unique card.

---

## Card movement and removal {#reference}

Unless a card says otherwise:

| Event | Result |
| --- | --- |
| Force is discarded | Discard its Bond and Name too. |
| Bond is discarded | Force stays; return its Name to its owner's hand. |
| Bond is returned | Force stays; put the Bond in its owner's hand. |
| Name is returned or discarded | Force and Bond stay; the Bond becomes open. |
| Force moves | Its Bond and Name move with it. |
| Named Formation Maneuvers or Retreats | Move Force, Bond, and Name together. |
| Rear Named Formation is driven off | Discard Force, Bond, and Name together. |

## First-game reminders {#reminders}

These are the rules most worth checking during a first game:

- **Draw first**, then take exactly one operation.
- Once you **Pass**, it remains active for the rest of that Battle, even if you later act.
- Only **Force + Bond + Name** persists normally from one Battle to the next.
- A Maneuver goes **one Front sideways in the same rank**.
- On a lost Front, **drive off the Rear first**, then Retreat the Frontline formation.
- Check **Command Collapse before recovery**.
- If Command Collapse is triggered while both players have equal Command, the war ends in a **draw**.

## Timing

There is no reaction stack.

When you play a card, choose anything the card asks you to choose, pay its cost, then follow its text in order.

For a Maneuver, choose the formation and destination, pay {{MANEUVER_COMMAND_COST}} Command, then move or swap.

Effects that mention Battle end, a Front result, or Retreat happen when that event occurs.

Some cards require a later operation to do something **if possible**.

An operation **affects a Front** if it does at least one of these things:

- plays a Force, Bond, or Name in that Front;
- plays a card that chooses that Front;
- Maneuvers a formation into or out of that Front.

If several effects require your next operation to do particular things, satisfy all of them together if one legal operation can do so.

If no legal operation can satisfy all requirements, choose one requirement that can be satisfied.

If none can be satisfied, take your turn normally.

## Deck construction

A legal playtest deck has:

- at least **{{MINIMUM_DECK_SIZE}} cards**;
- at least **{{MINIMUM_FORCE_COUNT}} Force-type cards**;
- at least **{{MINIMUM_PRINTED_NAME_COUNT}} printed Names**;
- at most **{{NON_UNIQUE_COPY_LIMIT}}** copies of any non-Unique title;
- at most **{{UNIQUE_COPY_LIMIT}}** copy of any Unique title.

Heroes count toward the Force minimum even though they may be played as Names.

> Fight the war, not the Battle. A Front can be won and still cost too much.
