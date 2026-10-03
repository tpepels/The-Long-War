# V2 mechanics and card grammar

## Formation states

- **Formation** - Force present.
- **Unbonded Formation** - Force present, Bond absent.
- **Bonded Formation** - Force + Bond. It may also have a Name.
- **Named Formation** - Force + Bond + Name. Every Named Formation is also Bonded.
- Force + Name without a Bond is not Named.
- **Prepared Bond / Prepared Name** - that card is in a position with no Force.

**BONDED** is a state. It remains active while Force + Bond are present.

**WHILE NAMED** is a state. It remains active while Force + Bond + Name are present.

**BECOMES NAMED** is an event. Resolve it when a Formation transitions from not Named to Named.

## No-lifting rule

A Named Formation must be fully playable without lifting, sliding or fanning any card.

Force is bottom, Bond middle, Name top. Force and Bond each leave a 10.5 mm top edge exposed.

A buried rule may exist only if it was a PLAY effect that has finished, or its complete live meaning is printed in the exposed edge.

## Card-type grammar

**Force** - base Strength and battlefield identity. No rule, PLAY, 1/BATTLE, BONDED or WHILE NAMED. Never TRIGGER.

**Bond** - compact middle-layer support. PLAY, 1/BATTLE, BONDED or WHILE NAMED. Never TRIGGER.

**Name** - visible top card. BECOMES NAMED, ACTION, TRIGGER, CONTINUOUS or WHILE NAMED.

**Hero** - Force mode follows Force grammar; Name mode follows Name grammar.

**Tactic** - immediate hostile interaction. Every Tactic affects the opponent.

**Stratagem** - hidden support for your own side.

**Narrative** - face-up support for your own troops, classifications or formation states.

There are deliberately no RESOLUTION effects in the V2 pool.

## Classifications

Classifications have no intrinsic rules.

- **Kind** - Human, Ship, Stronghold.
- **Role** - Archer, Guard, Scout, Rider, Skirmisher, Raider, Healer, Spearman, Steward, Builder, Seer.
- **Rank** - King, Captain, Veteran, Heir.

The pool, not the glossary, gives those labels personality.

## Typography

Exactly three font families:
1. EB Garamond SemiBold - titles and large numerals.
2. Gentium Book - rules and italics.
3. Arial - timings, classifications and utility labels.

Each effect starts on a new line. Timing is a compact bold sans label; an arrowhead marks events, an underline marks states, and italic text marks limits. Prose sits directly on parchment rather than inside a textbox.
