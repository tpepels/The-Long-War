# The Long War - Card Mechanics V2

Status: mechanical redesign proposal. This deliberately ignores the current engine and deck files.

## Design premise

The battlefield is persistent. A card can remain in play for many Battles, so persistent state must be readable directly from the table.

**Hard rule:** if a player must remember an effect after its source is hidden, either expose it on the stack or represent it with a marker.

The old 95-card mechanics are not being migrated. Titles and flavour are reused where useful, but every mechanic is designed for the new game.

## Battlefield assumptions used by this card set

- Each active Front has three rows on each player's side: **Front, Middle, Rear**.
- An inactive Front cannot be entered, targeted, or chosen.
- A **Formation** is any position containing a Force.
- A **Named Formation** is exactly **Force + Bond + Name**.
- Bonds remain mandatory for becoming Named.
- Formation cards stay in play between Battles unless card text moves or removes them.
- A standard one-position move is one orthogonal step:
  - one active Front left or right in the same row; or
  - one row forward or backward in the same Front.
- Hard row-placement restrictions are intentionally rare. Most Forces can enter any row.

## Classifications

Classifications have **no inherent rules**.

Archer, Rider, Guard, Scout, Human, King, Ship, and every other classification are labels only. They matter when another card explicitly refers to them.

Examples:

- “Every formation containing an Archer gets +1 Strength.”
- “Choose a Scout you control.”
- “Move one Rider one position.”

A player never needs to know a hidden rule for “Archer” or “Guard”.

## Card types

### Force

Persistent battlefield body. Supplies base Strength.

A Force may have:
- a **PLAY** effect that happens once and can then be buried;
- one very simple persistent property that remains legible in the exposed Force strip;
- rarely, a hard row restriction.

### Bond

Persistent middle layer of a formation and mandatory for becoming Named.

A Bond should usually be compact enough to communicate through its exposed strip:
- a Strength modifier;
- a protection symbol;
- a NAMED payoff;
- a simple PLAY effect.

A buried Bond must never require a player to remember a paragraph of recurring text.

### Name

Persistent top card of a Named Formation and therefore the main home for richer recurring abilities.

Names may use ACTION, TRIGGER, RESOLUTION, CONTINUOUS, and NAMED effects because their rules remain visible.

Completing Force + Bond + Name is meant to be a major power jump.

### Hero

A Unique dual-mode card played as either a Force or a Name.

The existing Battle allowance remains the design assumption:
- at most one Hero from hand as a Force per Battle;
- at most one Hero from hand as a Name per Battle.

### Tactic

Immediate card.

- Play as an Action during the normal building/formation play of a Battle.
- Pay its Command cost.
- Resolve it immediately.
- Discard it.

Tactics are the main home for immediate interference: volleys, scouts, feints, sudden movement, suppression, hand filtering, and prepared-card disruption.

### Stratagem

Hidden delayed interaction.

- Play face-down.
- Pay its cost when set.
- Its existence is public; its identity is hidden.
- Reveal only when its printed condition occurs.
- Resolve honestly by trust.
- Discard at Battle end unless text says otherwise.

The face-down card itself is the memory aid.

### Narrative

Visible broad rule.

Narratives are the natural home for:
- class-wide effects;
- symmetric battlefield rules;
- Front-wide conditions.

In this proposal, Narratives are intentionally Battle-scoped unless stated otherwise. Their source remains face-up, so players do not need to memorize their effect.

### Front Story

Front Stories remain a separate prototype system, not part of these 95 player cards. They can later give individual Fronts public terrain/story rules.

## Timing vocabulary

### PLAY

Resolve once when the card is played.

No marker is needed unless PLAY creates a temporary effect that outlives the card.

### NAMED

Resolve once when Force + Bond + Name is completed.

### ACTION

Spend one of the player's Actions to use the ability.

### TRIGGER

Resolve when the stated event occurs.

Recurring triggers are allowed only when their source remains visible.

### RESOLUTION

Resolve when the relevant Front is being compared/settled.

Use sparingly. Resolution should not become an arithmetic audit.

### CONTINUOUS

Always true while the source remains in the required state.

If the card can be buried, the complete continuing state must fit in its exposed strip.

### Once per Battle

A modifier for ACTION or TRIGGER.

Use a standard **used marker**. Remove all used markers when the next Battle begins.

## Temporary state and markers

Use a marker whenever the source no longer makes the state obvious.

Examples:
- `+1 Strength this Battle` -> +1 marker
- `-2 Strength this Battle` -> -2 marker
- `Bond suppressed this Battle` -> suppression marker
- `cannot move this Battle` -> no-move marker

Do not create bespoke memory rules when a token can show the state.

## Physical stack grammar

The intended stack is:

1. **Force** on the bottom
2. **Bond**
3. **Name** on top

Each buried card leaves an exposed strip.

### Force strip

Must show:
- base Strength;
- classifications relevant to interaction;
- any continuing icon/property that remains active while buried.

### Bond strip

Must show:
- `+Strength`, if any;
- compact continuing property;
- NAMED icon if the Bond has a completion effect.

### Name

The Name is the readable top card.

Show:
- `+Strength` rather than a standalone Strength number;
- classifications;
- full ongoing/activated rules text;
- timing and once-per-Battle icons.

### Cost

Command cost can live toward the bottom because it matters primarily in hand, not while buried in a stack.


## Exact physical card anatomy

The V2 physical card is still **63 x 88 mm**, but its information hierarchy changes to match stacking.

The upper **10 mm** is the **exposed strip**. When Force + Bond + Name are stacked, the cards are offset so the Force strip and Bond strip remain visible above the Name.

The exposed strip contains only battlefield information:

- **Force:** large base Strength, classifications, and any continuing/recurring reminder that must survive burial.
- **Bond:** signed Strength modifier such as `+1`, classifications, and any compact continuing/recurring reminder.
- **Name:** signed Strength modifier such as `+1`, classifications, and timing icons. The Name remains the readable top card, so its full ability text stays visible.
- **Hero:** both Force base Strength and Name modifier are visible in the strip because either mode may matter while the card is in hand.

The **Command cost moves to the bottom-right corner**. Cost matters when choosing a card from hand; it should not consume exposed stack space after the card is committed.

Strength effects that remain relevant while stacked are shown in the strip. Do not make players reopen a stack merely to calculate Strength.

### Timing icons

Every ability uses one of the standard timing icons. The icon is printed next to the ability and, when the ability can matter while buried, repeated in the exposed strip.

| Icon concept | Timing | Meaning |
|---|---|---|
| Bolt | **PLAY** | Resolve when played. |
| Banner | **NAMED** | Resolve when Force + Bond + Name is completed. |
| Arrow | **ACTION** | Spend one Action to use the ability. |
| Spark | **TRIGGER** | Resolve when the printed event occurs. |
| Scales | **RESOLUTION** | Resolve while the Front is settled. |
| Infinity | **CONTINUOUS** | Active while its condition is true. |
| One-token | **1/BATTLE** | Mark the card after use; clear the marker next Battle. |
| Marker | **TEMPORARY** | Put the stated marker on the affected card or Front. |
| Card back | **HIDDEN** | The face-down Stratagem is the reminder. |

An icon does not replace necessary rules text. It makes timing/state scannable. The full rule remains printed where needed.

**Memory rule:** if a player could reasonably ask “was this already used?” or “is this effect still active?”, the table must answer without relying on memory.

## Complexity guardrails

- Classifications never carry rules.
- Ordinary cards should normally have one mechanical idea.
- A Name or Hero may have two abilities when its top-card visibility justifies it.
- No routine Retreat or driven-off mechanics.
- Permanent destruction should be rare.
- No “first card in this Front” sequencing mechanics.
- Avoid chained Maneuver triggers.
- Avoid hidden recurring effects on buried cards.
- Avoid more than one simple continuous Strength condition on a card.
- Class-wide Strength bonuses must be simple and sourced by a visible Narrative.
- Most Forces may be played in any row.
- Tactics provide immediate interaction so permanent pieces do not need to carry every tactical effect.
- Named Formations are allowed to be very strong because completing all three layers is a major investment.