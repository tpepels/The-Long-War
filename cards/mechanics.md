# Mechanics and card grammar

> Canonical card definitions live only in `cards/cards.json`. This file defines the design grammar the card pool should follow.

## Design direction

The battlefield should create the interesting decisions. Card text should mostly move, expose, protect, exhaust, recover, steal, attach, exchange, redirect or otherwise change the board rather than repeatedly adding small numerical bonuses.

Use as little special vocabulary as possible. A player should normally be able to understand a card from ordinary language plus the core game terms.

The old shorthand mechanics **SUPPORT**, **SUPPLY**, **OUTMATCHED**, **RESERVE**, **PRESS**, **STEAL COMMAND**, **MOBILE** and **TIRELESS** are retired as player-facing keywords. Their useful ideas may still exist, but cards must say what actually happens.

Examples:

- not “SUPPORT +1”, but “The friendly formation directly ahead has +1 Strength.”
- not “TIRELESS”, but “This Force may Maneuver while Exhausted.”
- not “MOBILE”, but “This Force may Maneuver while Unnamed.”
- not “STEAL 1 COMMAND”, but “Your opponent loses 1 Command, then you regain 1 Command.”
- not “SUPPLY”, but an explicit logistical action such as moving a prepared Bond or Name forward.

Strength modifiers remain useful as simple glue, but they are not the primary identity of an archetype.

## Formation states

- **Formation** - a position containing a Force.
- **Unbonded Formation** - a Formation without a Bond.
- **Bonded Formation** - Force + Bond. It may also contain a Name.
- **Named Formation** - Force + Bond + Name.
- Force + Name without a Bond is not Named.
- **Prepared Bond / Prepared Name** - that card is in a position with no Force.
- **Exhausted Force** - a Force with an Exhaustion token.

“Bonded” and “Named” are ordinary game states, not ability keywords. Card text should use normal conditional language such as “While this formation is Named...” or “When this formation becomes Named...”.

## Battlefield position

The three ranks in a Front are **Front**, **Middle**, and **Rear**.

- **directly ahead** - the adjacent position in the same Front one rank toward Front.
- **directly behind** - the adjacent position in the same Front one rank toward Rear.
- **adjacent position** - one active Front left/right in the same rank, or one rank forward/back in the same Front. Never diagonal.
- **move one position** - move the complete Formation to one orthogonally adjacent legal empty position. This is a card effect, not a Maneuver, so it costs no Maneuver Command and does not require the Formation to be Named.
- **swap** - exchange the complete contents of two specified friendly positions. This is a card effect, not a Maneuver.
- A Formation counts as having **moved** whenever its battlefield position changes through Maneuver, a card move, or a swap.

Cards should normally say these things as sentences rather than as uppercase shorthand.

## Attacks and afflictions

Attacking is an Action: once per Force per Battle, no Command by default, legal without a Name. Depleted Forces cannot Attack. Attacks have no automatic health damage and a used Attack is not refreshed by recovery. Multi-class Forces choose one Attack.

| Classification | Basic Attack |
|---|---|
| Archer | Exhaust opposing Rear Force in same Front |
| Skirmisher | Shake opposing Middle Force in same Front |
| Raider | Deplete opposing Middle/Rear Force in same Front, if the opposing Frontline is empty |
| Rider | Shake flanked opposing Frontline Force in adjacent active Front |

Guards in Middle screen the Rear Force directly behind against basic Archer Attacks, unless the Guard is Shaken or Depleted.

There are exactly three core afflictions: **Exhausted** prevents initiating Maneuvers; **Shaken** reduces formation Strength by 2 at Front resolution (minimum zero); **Depleted** prevents Attacks and printed ACTION abilities on the formation. Duplicate markers do not stack. All three clear at Battle end; recovery is card-specific, with no generic Recover Action.

## Boons and protection

Boons are temporary beneficial markers. Like afflictions, they do not stack with themselves, move with the Force, and all clear at Battle end.

- **Guarded:** Prevent the next affliction that would affect this Force, then remove Guarded. It does not protect against forced movement, attachment removal or Command loss.
- **Inspired:** Remove Shaken from this Force and prevent it becoming Shaken while Inspired.
- **Empowered:** The next Attack this Force makes ignores screening. Remove Empowered after that Attack. All other range, flanking and eligibility restrictions still apply.

A Depleted Force cannot Attack even if Empowered. A prevented affliction does not count as inflicted for card effects that refer to an enemy becoming afflicted. There is no generic Action to gain a Boon: cards grant them.

Protection and support are different roles. Middle Guards screen Rear Forces from basic Archer Attacks. Strongholds may protect attachments and prepared cards; Ships may move friendly formations out of danger; Healers remove afflictions; Druids grant and transform Boons; Stewards remove Depletion; and Carriers move components or transfer Boons. These roles grant no universal bonuses unless explicitly stated on a card.

## Flanking

A Frontline Force is flanked if an enemy Frontline Force occupies an immediately adjacent active Front and its controller has no Frontline Force in that neighboring Front. This applies in **both directions** between any active adjacent Fronts. Inactive Fronts and the outside edges of the active battlefield never create a flank. A flank is only a tactical condition; it **does not automatically apply an affliction**. Rider Attacks and specific card effects exploit it.

## Open lines and support positions

Do not create another keyword for “exposed”, “breakthrough”, “supply line”, or similar ideas unless repeated play proves that one is necessary.

Cards should instead use explicit board conditions:

- “if there is no friendly Force directly ahead...”
- “if the opposing Front row is empty...”
- “choose an opposing Exhausted Force...”
- “choose a prepared Bond or Name in this Front...”
- “when the friendly Formation directly ahead moves or leaves play...”

This makes Front, Middle and Rear matter without forcing players to memorize another glossary.

Middle-only Forces are second-line specialists. Their purpose is not extra Strength. They should do things such as:

- relieve or replace the line ahead;
- move prepared components forward;
- let the Force ahead reposition;
- intercept Tactics;
- remove afflictions;
- react when the Front row opens.

Rear specialists should feel safer and more logistical, but should become vulnerable once the line in front of them opens.

## Row restrictions

A printed row restriction is a **hard occupancy restriction**, not merely a deployment restriction.

A restricted Force may be played only in its legal rows and may not Maneuver, move or swap into a forbidden row. The top-row rank glyph is only a reminder; the same restriction must appear in the rules text.

## No-lifting rule

A Named Formation must remain playable without lifting, sliding or fanning cards.

Force is bottom, Bond middle, Name top. Force and Bond each leave a 10.5 mm top edge exposed.

A buried rule may exist only if:

- it resolves when the card is played and then no longer matters; or
- its complete live meaning is also visible in the exposed strip.

## Conditions and timing

Conditions must read as conditions. Do not use a bare label such as “REAR”, “BONDED” or “NAMED” as if the label itself were the rule.

Prefer:

- “While this formation is in the Rear row...”
- “If the opposing Front row is empty...”
- “When this formation becomes Named...”
- “When an opposing Tactic targets...”

The timing label helps scanning, but the sentence must remain self-contained.

**Once per Battle is a limit, not a timing window.**

A limited ability still needs a real decision:

- **ACTION · once per Battle** - spend an Action to use it.
- **REACTION · once per Battle** - decide whether to use it when the stated event occurs.
- **TRIGGER · once per Battle** - use only where limiting the visible trigger creates a meaningful choice.

Avoid invisible “first X each Battle” bookkeeping when a visible state or explicit Action can create the same identity.

## Mechanical roles

Classifications should create recognizable play patterns.

- **Rider** - creates or closes flanks through movement.
- **Guard** - intercepts interaction, holds gaps, protects the line behind.
- **Raider** - attacks exhausted troops, prepared cards and support positions.
- **Skirmisher** - forces movement, opens holes and exploits unstable lines.
- **Archer** - reaches formations behind an open Front row and pressures support positions.
- **Scout** - reveals plans, finds openings and enables precise movement.
- **Healer** - removes Exhaustion and other attrition.
- **Steward** - moves components, prepares reserves and creates battlefield infrastructure.
- **Captain / King** - coordinates movement, replacement and timing.
- **Seer** - bends hidden information, timing, adjacency or other assumptions.
- **Ship / Stronghold** - retain distinct identities through card text rather than intrinsic glossary rules.

Classifications grant the basic Attacks and Guard screening defined in the rulebook; no other automatic abilities are implied. Additional class-dependent effects must be specified by card text.

## Card-type grammar

**Force** - the battlefield body. Prefer one clear positional identity. A regular Force may move, protect, exploit Exhaustion, support the line or create pressure; avoid stacking several unrelated clauses on one Force.

**Bond** - the relationship beneath a Name. PLAY effects may be more dramatic because they resolve before being buried. Live Bond text must fit the exposed strip and should usually change the relationship of the formation to the position ahead/behind rather than add generic Strength.

**Name** - visible personality and repeatable decision layer. Names are a good home for Actions, Reactions, movement, transfers, targeted disruption and odd exceptions.

**Hero** - the highest-complexity formation card. Force mode should remain readable when buried; Name mode may carry the stranger ability.

**Tactic** - immediate hostile interaction. Tactics should change the opponent's position, resources, components, Exhaustion or options. Avoid using “gets -2 Strength” as the default hostile effect.

**Order** - immediate friendly reorganization or recovery. Orders should feel like issuing an instruction: move, swap, relieve, attach, recover, redeploy.

**Stratagem** - hidden reversal or trap. A Stratagem should create a memorable consequence when revealed, not merely a small Strength surprise.

**Narrative** - the main home for “magic”. Narratives may temporarily bend the rules of the battlefield: geography, adjacency, ownership of Bonds/Names, what counts as a legal movement, which Fronts matter, or how a particular event resolves. Strange effects are welcome when their duration and consequences remain explicit.

## Strange effects and “magic”

The setting's magic should feel like history, omen and battlefield reality becoming unreliable rather than generic spell damage.

Good examples:

- two Fronts exchange their complete positions;
- a Name moves from one Bonded Formation to another;
- two Bonds exchange formations;
- the outer active Fronts count as adjacent for a Battle;
- a discarded Force returns Exhausted in an empty Rear position;
- a Formation is moved because “the road was elsewhere”;
- a Tactic is redirected to a different legal target;
- a Front's support positions become reachable because its Front row is empty.

These effects should usually replace bland arithmetic cards rather than expand the pool indefinitely.

## Balance guardrails

The overhaul should create more consequences without turning the game into unchecked snowballing.

- **Flanking itself causes no affliction.** It creates a vulnerability for Rider Attacks and card effects, without automatically losing Command or discarding cards.
- Returning an attached Bond or Name to hand normally costs a card/Action and requires a positional or Exhaustion condition.
- Forced movement is usually one position. Moving multiple positions belongs on a Hero, Narrative, or expensive/conditional effect.
- Repeated disruption should usually cost an Action and/or Command.
- A card that changes adjacency, swaps whole Fronts, revives a Force or otherwise bends a core rule should normally last only for the current Battle or resolve once.
- Permanent denial of an opponent's card text is avoided.
- Broad Strength bonuses should be rare and modest.
- Command theft remains capped by the normal rule that mid-Battle effects cannot cause immediate Collapse.
- Avoid automatic trigger chains that can recursively move or exhaust the battlefield without a player decision.

The target is not maximum complexity. The target is **consequential decisions with readable cards**.

## Typography

Exactly three font families:
1. EB Garamond SemiBold - titles and large numerals.
2. Gentium Book - rules and italics.
3. Arial - timings, classifications and utility labels.

Each effect starts on a new line. Timing is visually distinct. Prose sits directly on parchment rather than inside a textbox.

## Zero-Command cards

A printed Command cost of **0** removes only the Command payment. Playing the card still consumes an Action and the card leaves the player's hand.

A 0-Command Order must require a class, position, board state or other real eligibility condition. Its value budget still includes spending half a normal two-Action turn.
