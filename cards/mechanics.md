# mechanics and card grammar

> Canonical card definitions live only in `cards/cards.json`. This directory contains design notes, playtest lists, and physical-card documentation.

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

## Position and support vocabulary

The three ranks in a Front are **Front**, **Middle**, and **Rear**.

- **directly ahead** - the adjacent position in the same Front one rank toward Front. A Front-row Formation has no position directly ahead.
- **directly behind** - the adjacent position in the same Front one rank toward Rear. A Rear-row Formation has no position directly behind.
- **MOVE 1 / move one position** - move the Formation to one orthogonally adjacent active position: one Front left/right in the same rank, or one rank forward/back in the same Front. Never diagonal. The destination must be empty unless the card explicitly says to swap. Move is a card effect, not a Maneuver: it does not require the Formation to be Named, costs no Maneuver Command, and Exhaustion does not stop it.
- **Move up to N positions** - make up to N legal one-position Moves, one at a time. Every intermediate destination must be legal and empty.
- **SWAP** - exchange the complete contents of the two specified friendly positions. Both positions must contain a Formation unless the card says otherwise. Swap is a card effect, not a Maneuver: it costs no Maneuver Command and Exhaustion does not stop it.
- **moves / moved** - a Formation counts as moving whenever it changes battlefield position by Maneuver, Move, or Swap, regardless of which player or effect caused the relocation. This is the event used by cards that react after a Formation moves.
- **SUPPORT +N** - the friendly Formation directly ahead has +N Strength while the support effect is active.
- **SUPPLY** - Bonds played onto the friendly Formation directly ahead cost 1 less Command, to a minimum of 0; Names played onto it cost 1 less Command, to a minimum of 1.
- **OUTMATCHED** - an opposing Formation occupies the same rank in the same Front and has greater current Strength after continuous Strength modifiers are applied. A tie is not OUTMATCHED. This is only a local card condition; it does not decide the Front.
- **RESERVE +N** - this Formation has +N Strength while the friendly Formation directly ahead is OUTMATCHED.
- **PRESS +N** - this Formation has +N Strength while at least one opposing Force in this Front is Exhausted.
- **SUPPLY RAID** - a card may check whether an opposing Formation in its Front currently provides SUPPLY; the raid's payoff is printed on that card and does not remove SUPPLY unless stated.
- **STEAL N COMMAND** - the opponent loses up to N Command, never below 1, and you regain exactly the amount lost. It does not itself cause Collapse during the Battle.
- **MOBILE** - this Force may initiate a Maneuver without being Named. It still pays the Maneuver Command cost and obeys adjacency, row, destination, and Exhaustion restrictions.
- **TIRELESS** - this Force may initiate a Maneuver while Exhausted. TIRELESS ignores only the Exhaustion restriction: the Formation must still satisfy every other Maneuver requirement, including being Named unless another effect says otherwise, paying any Command cost, using an adjacent legal destination, and obeying movement restrictions. It keeps its Exhaustion token, so other cards may still care that it is Exhausted. TIRELESS is boolean: multiple sources do not grant any additional benefit.
- **EXHAUSTION** - after a Front is lost, every Force that player has in that Front receives one Exhaustion token, to a maximum of one. Exhaustion persists between Battles, moves with the Force, and normally prevents that Force from initiating a Maneuver. If the Force leaves the battlefield, its Exhaustion token leaves with it. Tied Fronts exhaust neither player.
- **EXHAUSTED** as a timing label is a continuous state active while that Force has an Exhaustion token.
- **FRONT / MIDDLE / REAR** as a timing label is a continuous positional state. The text is active only while that Formation occupies that rank.
- Multiple active **SUPPORT +N**, **RESERVE +N**, and **PRESS +N** effects add together. Multiple active **SUPPLY** effects each reduce the cost by 1.
- **Command modifiers** stack. Add all applicable increases, then apply all applicable reductions. If at least one applicable reduction explicitly says "minimum 0", the final reduced cost may reach 0; otherwise reductions cannot take a positive printed cost below 1 unless a card explicitly says otherwise.
- Each **Tax marker** is separate. If the next card played satisfies more than one Tax marker, all matching increases apply and all matching "next card" markers are consumed. A marker with an expiry such as "before your next turn" expires when its own text says it does.
- A **-Strength marker** is a temporary negative marker recording a Battle-long Strength penalty created by card text such as "gets -2 Strength this Battle".
- A **temporary negative marker** is any adverse marker on a Formation created by a card effect with a finite duration, including -Strength, text-suppression, or ability-lock markers. It does **not** include Exhaustion or a Tax marker on a Front. When a card removes a temporary negative marker, remove one such adverse marker and end that marker's effect.

Positional and Exhaustion text should normally be one short line. The rank, token, and relationship should carry the idea; Forces should not become paragraphs that need rereading every time Strength is counted.

A Force with an allowed-row restriction may list more than one legal rank. This is a **hard occupancy restriction**, not only a deployment restriction: the Force may be played only in those ranks and may not Maneuver, Move, or Swap into a forbidden rank. In particular, former Rear-only support Forces may occupy **Middle or Rear**; their **REAR** text simply does nothing in Middle.

## No-lifting rule

A Named Formation must be fully playable without lifting, sliding or fanning any card.

Force is bottom, Bond middle, Name top. Force and Bond each leave a 10.5 mm top edge exposed.

A buried rule may exist only if it was a PLAY effect that has finished, or its complete live meaning is printed in the exposed edge.

## Timing and real decisions

**Once per Battle is a limit, not a timing window.**

A card never says merely `1/BATTLE - do something`. A limited ability still says what kind of decision it is:

- **ACTION · 1/BATTLE** - spend one of the turn's Actions; the limit prevents repetition.
- **REACTION · 1/BATTLE** - when the stated event occurs, decide whether to spend the limited response.
- **TRIGGER · once per Battle** - only on a visible Name/Hero, and only where choosing which trigger to spend or limiting repetition matters.

A limited-use wrapper must change a real decision. An automatic `1/BATTLE - +1 Strength`, automatic free Command gain, or automatic free card filtering is not an ability; write it as a stat/state or give it an Action, reaction window, or cost.

Avoid invisible "the first X each Battle/turn" bookkeeping when the same identity can be expressed as a visible continuous rule.

## Card-type grammar

**Force** - base Strength and one simple battlefield identity. Prefer no rule, PLAY, a short positional/state rule, or a repeatable ACTION whose complete instruction fits in the exposed edge. Regular Forces do not use once-per-Battle abilities.

**Bond** - compact middle-layer support. Use PLAY for one-shot choices and BONDED / WHILE NAMED / positional state text for live effects. Bonds do not carry ACTION or REACTION abilities while buried.

**Name** - visible top card. BECOMES NAMED, ACTION, REACTION, TRIGGER, CONTINUOUS or WHILE NAMED.

**Hero** - Force mode follows Force grammar; Name mode follows Name grammar.

**Tactic** - immediate hostile interaction. Every Tactic affects the opponent.

**Order** - immediate self-support instruction. Playing it spends one Action exactly like any other card play; resolve it, then discard it. A 0-Command Order must require a class, board state, position, or other real eligibility condition.

**Stratagem** - hidden support for your own side.

**Narrative** - face-up support for your own troops, classifications or formation states. A Narrative may have a visible ACTION ability when spending an Action is the point of the choice.

There are deliberately no RESOLUTION effects in the pool.

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

Each effect starts on a new line. Timing is visually distinct. Prose sits directly on parchment rather than inside a textbox.


## Zero-Command cards

A printed Command cost of **0** removes only the Command payment. Playing the card still consumes an Action and the card itself still leaves the player's hand. Zero-Command Orders are never unrestricted: each requires a class, position, board state, or other real eligibility condition. Their value budget still includes spending half a normal two-Action turn.
