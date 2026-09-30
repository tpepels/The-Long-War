# The Long War

*Fight now. Live with it later.*

**The Long War** is a two-player card game played over a series of rounds. In each round, you commit cards to four contested areas, build groups that can survive into later rounds, and decide how much of a limited resource you are willing to spend.

When both players are ready to stop, the four areas are resolved separately. Some groups hold their ground, some fall back, and some disappear. Then the next round begins from whatever survived.

Nothing resets just because a round ended. A position you fought hard to build can become the foundation of the next round, while resources you spend now may leave you vulnerable later. The game ends when one side has exhausted the resource that keeps it fighting while the other side still has some left.

> The central question is rarely "Can I win this round?" It is "How much can I afford to spend on it?"

## How the war unfolds {#learn}

A round of the game is called a **Battle**.

Each of the four contested areas is called a **Front**.

The resource you spend to play cards and move established groups is called **Command**. Each player begins the war with **{{STARTING_COMMAND}} Command**.

A Battle follows a simple rhythm:

1. Players alternate turns, adding cards, moving established groups, or choosing not to act.
2. When both players choose not to act one after the other, the Battle ends.
3. Resolve the four Fronts separately.
4. Some cards survive into the next Battle; others are removed or pushed back.
5. Check whether either side has exhausted its Command.
6. If the war continues, recover some Command, refill hands, and begin the next Battle.

A war may last several Battles. The board you build and the Command you preserve matter from one Battle to the next.

## The battlefield

Each Front has two positions on each player's side.

The position nearest the centre is the **Frontline**. The position behind it is the **Rear**.

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

**Strength** is the number used to compare the two sides of a Front.

At the end of a Battle, total the Strength that counts at each Front.

- Higher total wins that Front.
- Equal totals tie.
- There is no overall Battle winner.

Winning or losing a Front changes what survives and how much Command you recover. You can therefore give up ground in one place to preserve resources for the rest of the war.

## Force, Bond, and Name {#cards}

Most of the battlefield is built from three kinds of cards.

A **Force** gives a position its body. A Force has printed Strength.

A **Bond** is attached to a Force and helps define the group around it.

A **Name** gives that group an identity.

A **formation** is a Force together with any Bond and/or Name in the same position.

A **Named Formation** is a complete formation containing all three:

**Force + Bond + Name**

Named Formations are important because they can survive from one Battle to the next.

Force, Bond, and Name may be played in **any order**.

If a Bond or Name is played into a position without a Force, it is **prepared**. It stays face-up, but has no Strength and no Force-dependent effect until a Force arrives.

A Force with a Bond but no Name has an **open Bond**.

A Force may have a Name without being a Named Formation. Force + Name without a Bond is still incomplete.

For example:

**The Fifty Men - Followed - Namar**

### Force

Play a Force into any position without a Force, subject to any deployment restriction printed on the card.

A Force supplies its printed Strength and makes the cards in that position a formation.

### Bond and Name

A prepared Bond or Name becomes part of a formation as soon as a Force is present.

Every printed Name is **Unique**.

Text beginning **When you play...** happens only when that card itself is played.

Text beginning **When this formation becomes Named...** happens when the position first contains Force + Bond + Name, whichever card completed it.

### Persistence

Named Formations persist between Battles unless they are removed or driven off.

Anything incomplete is cleared at Battle end.

### Deployment restrictions

**Deploy - Frontline only** and **Deploy - Rear only** restrict where a Force enters play. They do not prevent later movement unless the card also says so.

## Labels, Unique cards, and Heroes

Words such as *Swordsman*, *Archer*, *Human*, *King*, or *Ship* are classifications. They have no hidden rules. If a classification matters mechanically, a card will say so.

**Adjacent** means one Front left or right in the same rank.

**In front of** and **behind** mean the other rank in the same Front.

A card marked **Unique** may appear only once in your deck. Unique is not a shared battlefield limit: both players may control their own copy of the same Unique card.

A **Hero** is a Unique card that can be played as either a Force or a Name. Use the matching text on the card.

You may play at most **one Hero from hand per Battle**.

A Hero already on the battlefield does not use the next Battle's Hero allowance.

## Setup {#setup}

1. Each player takes a deck of **at least 34 cards**.
2. Set each player's Command to **{{STARTING_COMMAND}}**.
3. Shuffle and draw **{{OPENING_HAND_SIZE}} cards**.
4. You may shuffle up to 2 cards from your hand back into your deck, then draw the same number.
5. Randomly choose the first player.

Hands and decks are hidden.

Battlefield cards, discard piles, hand size, deck size, Command, and any face-up cards outside the battlefield are public.

The first player's first turn is normal. If their opening hand is already at the hand limit, they discard 1 before drawing 1.

---

## Your turn {#turn}

At the start of every turn, **draw 1 card**.

Your hand limit is **{{HAND_LIMIT}}**. If you would draw while holding {{HAND_LIMIT}} cards, discard 1 card first, then draw.

After drawing, take exactly **one operation**. An operation is the one thing you choose to do on that turn:

1. **Play one card** and pay its Command cost.
2. **Maneuver** - move one Named Formation for {{MANEUVER_COMMAND_COST}} Command.
3. **Pass** - spend 0 Command and take no other operation.

You cannot spend more Command than you have. Command never goes below 0.

A cost reduction cannot reduce a card below 1 Command unless the card explicitly says it costs 0.

There is no generic Draw operation, Advance, or attack step.

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

You cannot normally Maneuver between Battles or change rank with a Maneuver.

## Narratives and Stratagems {#stories}

A **Narrative** is a card that represents something the war has made true beyond a single formation.

Narrative is the umbrella term for **Legend, Saga, Myth, Omen, Warning, Prophecy,** and **Conspiracy**. The specific form is printed on the card.

Narratives are always face-up.

- A Narrative marked **Ongoing** stays in play until its text ends it.
- Any other Narrative resolves when played, then is discarded.
- You may have at most **{{ONGOING_NARRATIVE_LIMIT}} Ongoing Narratives** in play.

The individual Narrative forms have no hidden rules of their own.

A **Stratagem** is a public plan for the current Battle. Play it face-up in your Stratagem area. Playing it is your operation and you pay its Command cost.

You may play at most **one Stratagem from hand per Battle**.

Discard Stratagems at Battle end unless a card says otherwise.

## Passing {#passing}

To **Pass** is to spend 0 Command and take no other operation.

Normally, you cannot Pass until both players have completed at least one operation. If you have no other legal operation, you may Pass.

Passing does not remove you from the Battle. The opponent takes a normal turn.

- If the opponent also Passes, the Battle ends.
- If the opponent does anything else, your Pass is cleared.

A Battle therefore ends after **two consecutive Passes**.

The player who made the **first** of those two Passes starts the next Battle.

---

## Ending a Battle {#scoring}

When a Battle ends, resolve all four Fronts.

For each Front, apply card text and total the Strength that counts there.

- Higher total wins.
- Equal totals tie.
- Prepared cards without a Force count 0 Strength.
- Strength cannot fall below 0 unless a card says otherwise.

The margin of victory has no effect unless a card says otherwise.

## Retreat {#retreat}

When you lose a Front, a surviving Named Formation may be forced backward. That movement is called a **Retreat**.

After all four Front results are known:

1. Discard every Force, Bond, or Name that is not part of a Named Formation.
2. In each lost Front, drive off the Rear Named Formation, if any.
3. Then Retreat the Frontline Named Formation into the Rear, if any.

A driven-off formation is discarded as Force + Bond + Name.

A tie does nothing. Formations in a won Front stay where they are.

## After the Battle {#after-battle}

After Retreats are complete:

1. Resolve Battle-end card effects.
2. Discard Stratagems and effects that last only for this Battle.
3. Leave Ongoing Narratives in play if their text has not ended them.
4. Check for Command Collapse using each player's current Command.
5. If the war continues, recover Command.
6. Draw until you have {{HAND_LIMIT}} cards.
7. Reset the Hero and Stratagem allowances.
8. Start the next Battle with the player who made the first of the two consecutive Passes.

Keep your hand, draw pile, and discard pile between Battles.

Do not reshuffle just because a Battle ended. If you must draw from an empty deck, shuffle your discard pile into a new draw pile.

There is **no between-Battle Maneuver**.

## Command and winning the war {#command}

Command carries from one Battle to the next and stays between **0 and {{COMMAND_CAP}}**.

For this playtest, base recovery starts at **{{RECOVERY_START}}** in Battle I and falls by **{{RECOVERY_DECREMENT}}** every Battle:

**{{RECOVERY_SERIES_PLAIN}}**

Subtract **1 for each Front you lost**.

Your actual recovery is never less than **{{RECOVERY_FLOOR}}** while the war continues.

Add the result to your current Command, to a maximum of {{COMMAND_CAP}}.

### Command Collapse

**Command Collapse** is the check that can end the war.

After Battle resolution, cleanup, Retreats, and relevant Battle-end effects - but **before Command recovery** - check current Command.

- If exactly one player is at **{{COLLAPSE_THRESHOLD}} Command**, that player loses the war.
- If both players are at **{{COLLAPSE_THRESHOLD}} Command**, the war continues.
- Only a continuing war receives Command recovery.

Because surviving recovery is at least {{RECOVERY_FLOOR}}, a {{COLLAPSE_THRESHOLD}}-{{COLLAPSE_THRESHOLD}} continuation begins the next Battle at at least {{RECOVERY_FLOOR}}-{{RECOVERY_FLOOR}}.

This is the long-war pressure behind almost every decision: spending Command may win a Front now, but preserving even a little Command may be what keeps you alive after the Battle.

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

- at least **34 cards**;
- at least **14 Force-type cards**;
- at least **6 printed Names**;
- at most 2 copies of any non-Unique title;
- at most 1 copy of any Unique title.

Heroes count toward the Force minimum even though they may be played as Names.

> **Fight the war, not the Battle.** A Front can be won and still cost too much.
