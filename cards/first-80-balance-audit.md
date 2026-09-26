# First 80 - balance audit

Status: active playtest audit.

## Applied conservative balance changes

The following changes are now in the approved card data:

- **The Long March** - reduced from one free qualifying Maneuver every turn to one Command refund on the first qualifying Maneuver each Battle.
- **Iven** - discount now applies only to the first card played in Iven's Front each turn.
- **Trusted** - recurring Battle-end Command generation replaced by a one-time +1 Command when the formation becomes Named.
- **Sorin** - base cost 2; costs 1 when played on a Force that already has a Bond.
- **Tovan, the Quartermaster** - Name-mode discount changed from once each turn to once each Battle.
- **Before Sunset, the Ford Would Be Ours** - cost increased from 1 to 2.
- **Arel** - only the formation's first Maneuver each Battle is free while the empty-Front condition holds.
- **The Battle Turned East** - cost increased from 2 to 3; the per-formation once tracking was removed in favor of free Maneuvers only in the chosen direction.


## Pool and deck snapshot

The approved first-80 pool currently contains:

- 17 regular Forces
- 9 Heroes (all Unique and counted as Force-type cards)
- 17 Bonds
- 16 printed Names (all Unique)
- 10 narrative cards
- 11 Stratagems

That is 80 designed cards total, of which 28 are Unique.

Current deck construction requires:

- at least 34 cards;
- at least 14 Force-type cards;
- at least 6 printed Names;
- maximum 2 copies of a non-Unique title;
- maximum 1 copy of a Unique title;
- Heroes count among Force-type cards and may instead be played as Names.

Because all printed Names are Unique, the six required Name slots are always six different Names.

## Highest balance concerns

### The Long March

Current:
> **Ongoing.** Your first **Maneuver** each turn costs 0 Command if it moves into an empty position instead of swapping.

Concern: a 2-Command persistent card can save one Command on many turns and across multiple Battles. The ceiling is far above most other Command cards.

Possible direction:
> **Ongoing.** The first time each Battle you **Maneuver** into an empty position, regain 1 Command.

This keeps the narrative/Command identity but caps the return at one Command per Battle.

### Iven

Current:
> While you have less Command than your opponent, the first card you play each turn costs 1 less Command (minimum 1).

Concern: persistent global discount every turn. Being behind in Command may produce several points of savings per Battle and continue across Battles.

Possible direction: scope the discount to Iven's Front, or make it once per Battle.

### Tovan, the Quartermaster - Name mode

Current:
> While this formation is Named, the first card you play in this Front each turn costs 1 less Command (minimum 1).

Concern: repeated discount from a persistent Hero. Less dangerous than Iven because it is local and Tovan costs 3, but the long-run ceiling is still high.

Possible direction: first card in this Front **each Battle**, not each turn.

### Trusted

Current:
> At Battle end, if this formation wins its Front, regain 1 Command.

Concern: a 1-Command Bond can become a recurring Command engine for every later Battle in which the persistent formation keeps winning.

This is especially notable because narrative cards were deliberately given Command generation as their shared identity while normally paying for it with a condition and/or self-discard.

Possible direction: raise its cost, make the reward conditional on a new event that Battle, or make the effect one-shot in a way that does not require long-term memory.

### Sorin

Current:
> If you play this Name on a Force that already has a Bond, it costs 0 Command.

Concern: completing a persistent Named Formation is already a major reward. Sorin also adds +1 Strength and can make that completion entirely free.

Possible direction: base cost 2; if played on a Force that already has a Bond, cost 1.

### Arel

Current:
> While one of your Fronts has no Force, this formation's **Maneuvers** cost 0 Command.

Concern: having at least one empty Front is likely to be common, especially early and after losses. This can become effectively unlimited free self-Maneuver from a 1-Command Name.

Possible direction: only the first Maneuver each Battle is free while the condition is true.

### The Battle Turned East

Current:
> Choose left or right. **During this Battle**, each of your Named Formations may Maneuver once for 0 Command if that Maneuver moves it in the chosen direction.

Concern: at 2 Command the card can save several Command on a developed battlefield. It also requires remembering which formations have already used their free Maneuver.

Possible direction:
> Choose left or right. **During this Battle**, your Named Formations may Maneuver in that direction for 0 Command.

Then price the cleaner, bounded directional effect around 3-4 Command. Direction and board edges naturally cap how far formations can travel.

## Strong cards to watch, not immediate nerfs

### Avaros, the Bronze King

Force mode is effectively 6 Strength in Frontline for 3 Command and can chain a free adjacent Maneuver after Avaros Maneuvers. This is intentionally Hero-level, but it is substantially above the baseline Force rate.

Test possibility: base Strength 4 rather than 5 if Avaros dominates Hero choices.

### Rovan, the Gatebreaker

5 Strength for 3 plus the ability to ignore an opposing Rear Force can create very large Front swings. Name mode also upgrades a win into a drive-off condition.

Test possibility: Force Strength 4 if the suppression effect proves too reliable.

### Before Sunset, the Ford Would Be Ours

1 Command can become 2 Command plus a card by choosing a Front the player expects to win. The condition is visible and interruptible, but the successful swing is large.

Test possibilities:
- cost 2; or
- keep cost 1 and remove the draw; or
- regain 1 Command plus draw 1.

### They Lived to Tell It

A safe persistent Named Formation can make the survival condition relatively easy. At cost 1, success refunds the Command and draws a card.

Watch whether players simply attach this to the safest Rear formation for low-risk card advantage.

### No Road Was Too Long

A persistent Unique Myth can generate 1 Command and a movement benefit in every Battle. The ongoing Story-slot cost may balance it, but its value grows with war length.

### The Center Must Hold

Combining two Fronts can turn one concentrated Strength advantage into two Front wins, which also affects Retreat and Command recovery. This is appropriately dramatic for a Stratagem, but 3 Command may prove cheap.

Test at 3 first; 4 is the obvious adjustment if it dominates.

## Unique cards

### Current count

28 / 80 cards are Unique:

- 16 printed Names
- 9 Heroes
- 2 narratives
- 1 Stratagem

This is not automatically too many. Most of the count follows directly from the rule that every printed Name is Unique and every Hero is Unique.

### Printed Names

At least 6 printed Names are required, and all 16 available Names are Unique.

Consequences:

- every deck has six distinct printed Names;
- Name-heavy combos cannot be made consistent by running duplicate copies;
- deck identity comes partly from which 6 of the 16 Names are selected;
- in a minimum 34-card deck containing exactly six printed Names, an opening 10-card hand has about a 90% chance of seeing at least one printed Name; larger decks or higher Name counts change that consistency.

This looks healthy.

### Heroes

There are 9 Heroes. They count toward the minimum 14 Force-type cards, can instead be played as Names, and only one Hero card may be played from hand each Battle.

There is currently **no Hero deck-building cap**.

That creates two issues if a player loads up on Heroes:

1. Heroes partially bypass the intended Force/Name composition because they occupy Force slots but can function as Names.
2. Multiple Heroes in hand can conflict with the one-Hero-from-hand-per-Battle rule.

Opening-hand pressure for a 10-card opening hand:

- 3 Heroes in deck: about 20% chance to draw 2 or more
- 4 Heroes: about 33%
- 5 Heroes: about 47%
- 6 Heroes: about 58%
- 9 Heroes: about 83%

A Hero cap remains an open balance question. Do not impose one yet; first test Hero-heavy decks under the minimum-size deck rules.

Four keeps Heroes important, forces a real choice among the nine available designs, and avoids making the Force/Name split mostly cosmetic.

### Unique on the battlefield

Current rules use Unique as a deck-construction restriction: maximum one copy of a Unique title per deck.

There is no reason to add a global battlefield uniqueness rule. With separate player decks, preventing both players from controlling the same Unique title would make mirror matches awkward and create first-player ownership problems.

Recommended interpretation:

> **Unique means maximum one copy of that title in your deck. It does not prevent both players from having a copy of the same title in play.**

A player's own duplicate battlefield copy is already impossible under normal play because only one physical copy exists in that player's deck.

### Non-character Unique cards

Three Unique cards are not Names or Heroes:

- **All Banners Forward**
- **Before Sunset, the Ford Would Be Ours**
- **No Road Was Too Long**

If **Unique** is purely a mechanical singleton label, this is consistent.

If Unique is intended to mean a singular person/entity in the fiction, these should instead use a separate one-per-deck rule. Adding a second label is probably unnecessary; the simpler first-set rule is to let **Unique mean singleton deck card regardless of type**.

## Recommended next balance pass

Before changing many Strength values, test the Command economy first.

Priority order:

1. repeated free/discounted actions;
2. recurring Command generation across Battles;
3. Hero density in deck construction;
4. Battle-wide Stratagem swing;
5. raw Strength rates.

The first three can distort the whole game even when individual Front combat still appears balanced.
