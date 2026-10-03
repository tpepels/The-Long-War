# V2 card mechanics and physical grammar

This is the design contract for the new 95-card proposal. It is intentionally separate from the engine and current decks.

## Formation states

- **Formation** - a battlefield position containing a **Force**. A Bond and/or Name may also be present.
- **Unbonded Formation** - a Formation with no Bond.
- **Bonded Formation** - a Formation containing **Force + Bond**. It may also contain a Name.
- **Named Formation** - a Formation containing **Force + Bond + Name**.
- Every **Named Formation is also Bonded**.
- **Force + Name** without a Bond is a Formation with a Name, but it is **not Named**.
- **Prepared Bond** - a Bond in a position with no Force.
- **Prepared Name** - a Name in a position with no Force.
- A Formation **becomes Named** whenever it changes from not having all three cards to having Force + Bond + Name.

These are states, not classifications.

## The no-lifting rule

A completed formation must be fully playable without lifting, sliding, or fanning any card.

Cards stack **Force -> Bond -> Name**. Force and Bond each leave a 9.6 mm top edge exposed.

The Force edge always shows:
- Force symbol;
- base Strength;
- classifications;
- any Front/Middle/Rear restriction;
- the complete reminder for any 1/BATTLE effect.

The Bond edge always shows:
- Bond symbol;
- Strength modifier;
- the complete reminder for any 1/BATTLE effect.

The Name is on top, so all of its live rules remain readable.

**PLAY text on Forces and Bonds may disappear after resolving. No other information that still matters may be hidden.**

## Card-type grammar

### Force

Forces establish base Strength and battlefield identity.

Allowed:
- **PLAY**
- **1/BATTLE**

Not allowed:
- TRIGGER
- CONTINUOUS prose
- recurring text that is not completely readable in the exposed strip

A Force may have no special rule. Hard row restrictions are exceptional.

### Bond

Bonds are compact support cards in the middle of the stack.

Allowed:
- **PLAY**
- **1/BATTLE**

Not allowed:
- TRIGGER
- CONTINUOUS prose
- hidden recurring rules

A Bond's persistent numeric Strength modifier is always printed in its exposed edge.

### Name

Names are the visible top card and therefore the main home for rules a player must repeatedly check.

Allowed:
- **NAMED**
- **ACTION**
- **TRIGGER**
- **RESOLUTION**
- **CONTINUOUS**

A Name may have more than one effect. Each effect is printed as its own block.

### Hero

A Hero played as a Force follows Force grammar. A Hero played as a Name follows Name grammar.

### Tactic

A Tactic always:
1. uses **PLAY**;
2. resolves immediately;
3. affects the **opponent** or the opponent's battlefield/hidden information;
4. is discarded afterward.

Pure self-buffs do not belong on Tactics.

### Stratagem

A Stratagem is face-down and helps **your own side** when its reveal condition occurs.

The face-down card is the reminder that something is waiting.

### Narrative

A Narrative is face-up and supports **your own troops**, classifications, or formation states.

Narratives are the natural home for broad effects such as:
- your Archers have +1 Strength;
- your Guards and Strongholds have +1 Strength;
- your Bonded Human Formations have +1 Strength.

## Classification system

Classifications have **no inherent rules**. A player never needs a glossary to learn what Archer or Scout mechanically means.

Instead, the card pool gives each classification a recognizable personality:

- **Human** - Broadest people classification. Human support is common but deliberately modest.
- **Ship** - Long-range support and unusual Front interaction.
- **Stronghold** - Static support, protection, and staying power.
- **Archer** - Ranged pressure, Strength reduction, and support from a distance.
- **Guard** - Protection, interception, and resistance to hostile Tactics.
- **Scout** - Information: hands, hidden Stratagems, and advance knowledge.
- **Rider** - The main home for the game's deliberately scarce movement effects.
- **Skirmisher** - Harassment, temporary suppression, and small Strength penalties.
- **Raider** - Pressure on prepared cards, Command costs, and the opponent's build-up.
- **Healer** - Removal of temporary negative state.
- **Spearman** - Simple, dependable battlefield Strength, especially in the Front.
- **King** - Command, broad coordination, and high-impact Named payoffs.
- **Captain** - Local formation-building, Bonds, Names, and action efficiency.
- **Veteran** - Reliability, marker removal, and once-per-Battle resilience.
- **Seer** - Deep information and deck/hidden-plan manipulation.
- **Steward** - Command efficiency, card filtering, and resource management.
- **Builder** - Bonds, prepared cards, and Stronghold-style development.
- **Hero** - A special dual-use card that may be played as Force or Name.
- **Heir** - Succession and access to King synergies once fully established.

Abstract tags such as movement, pressure, focus, identity, necessity, or defence are not classifications.

## Timing and memory

- **PLAY** - resolve when played.
- **NAMED** - resolve when the Formation becomes Named.
- **ACTION** - spend one of the turn's Actions.
- **TRIGGER** - a visible Name reacts to the stated event.
- **RESOLUTION** - checked while a Front is being settled.
- **CONTINUOUS** - visible rule that remains true while its source is active.
- **1/BATTLE** - mark the source after use and clear the marker when the next Battle begins.

If an effect survives after its source is gone or buried, use a physical marker. If a player could reasonably ask "is that still active?", the table must answer without memory.

## Typography

Exactly three font families are used:

1. **EB Garamond SemiBold** - card titles, large Strength numerals, large Command numerals.
2. **Gentium Book** - rules text and italics.
3. **Arial** - timing labels, classifications, metadata, compact reminders.

## Rule-block layout

Every separate effect starts on a new line.

- timing label: bold uppercase sans serif;
- rules prose: serif;
- reminder/usage text: italic serif where needed;
- each effect has a subtle tinted field and accent rule;
- no multi-effect paragraph soup.

## Command cost

Command cost is not part of the exposed stack edge.

It lives in a faceted Command badge integrated into the bottom-right card frame, so:
- it is easy to find while the card is in hand;
- it disappears naturally when cards are stacked;
- it cannot be confused with Strength.

## Design limits

- Maximum movement-related cards in this proposal: **12**.
- Current movement-related cards: **10**.
- Maximum hard row-restricted Forces: **4**.
- Current hard row-restricted Forces: **3**.
- Force/Bond TRIGGER effects: **forbidden**.
- Tactics that do not target the opponent: **forbidden**.
- Stratagems/Narratives whose primary scope is not your own side: **forbidden**.
