# Symbol vocabulary

Symbols are a scanning language for the physical table. They do not create intrinsic rules for classifications.

## Repeated game concepts

| Concept | Visual |
|---|---|
| Force | shield |
| Bond | chain link |
| Name | military standard |
| Strength | crossed weapons |
| Command | d20 / faceted die |
| Action | diamond action mark |
| Reaction | returning arrow |
| Once per Battle | empty use socket beside Action/Reaction |
| Front / Middle / Rear | three horizontal bars with the relevant row filled |

## Classification enclosure

- circle = Kind;
- diamond = Role;
- pennant = Rank.

Kind: Human, Ship, Stronghold.

Role: Archer, Guard, Scout, Rider, Skirmisher, Raider, Healer, Steward, Seer.

Rank: King, Captain.

The full face always spells these names out under the title. Only the exposed battlefield row relies on compact pictograms.

## Exposed upper-right check cues

The right side of an exposed Force/Bond/Hero edge is a **reminder to consult
the full printed rule**, not an abbreviated rulebook. Use brief textual cues:

- `CHECK · ACTION` — a player-activated effect may be available.
- `CHECK · FRONTLINE` / `CHECK · MIDDLE` / `CHECK · REAR` —
  an effect may matter when the Force occupies this row.
- `CHECK · BONDED` / `CHECK · NAMED` — a layer-dependent effect
  may be active.
- `CHECK · ATTACK` / `CHECK · PLAN SET` — review the card at that event.

For layered requirements, a minimal context such as
`CHECK · BONDED/FRONT` is enough. **Never** put Strength bonuses,
Command taxes, movement permissions, recovery details or other outcomes
in the strip. A player must look at the card body for the actual effect.
The full rule is also available to assistive technology through the cue's
accessible label. Once-per-Battle use sockets are preserved.

The short trigger text is assigned through `edge_cues` in
`cards/print-overrides.json`, not the canonical engine card effects.
Each exposed effect must have an explicit cue of at most 16 characters,
and identical contexts on one card can share a single cue. Do not add
inline symbols to these prompts. `tools/check_edge_cue_layout.py`
verifies that the printed text fits the exposed area in Chromium.

## Symbols inside the rules text

The rules must read like **ordinary sentences**, with very few inline icons.

- **Use inline icons only for explicit references to another card family or classification**, such as “an opposing Force,” “play a Bond,” “your Human formations,” or “an enemy Archer.” Those icons help locate and recognize the referenced cards. Use the existing Force/Bond/Name/etc. and class symbols.
- **No icons** for Strength, Command, outcomes (Shaken, Guarded, Exhausted, etc.), movement, ranks, Fronts, durations, deck/hand references or generic gameplay words. “This Force” is a self-reference and remains plain.
- **At most two inline icons per effect**, and at most one per referenced family/class, even if mentioned again. Later occurrences stay plain words. Icons never replace text.
- **Timing headings** (PLAY, ACTION, BECOMES NAMED, etc.) and **Hero mode headings** (FORCE / NAME) are text only, without duplicate pictograms. Once-per-Battle retains its functional use socket.
- **Keep structural icons outside the rules**: the exposed card edge, classification footer, placement strip and diagonal Hero Command seal. Those have different scanning purposes.

Example: “Choose an opposing Force. Give it Shaken and −2 Strength.” Only **Force** receives an inline shield. “Your Human Archers get +1 Strength” may display Human and Archer symbols once each. “Regain 2 Command” has no inline icon.

This policy applies to Heroes, ordinary formation layers, Tactics, Stratagems, Narratives and Orders alike. Printed effect meanings and phrasing remain authoritative.

## Live buried reminders

The exposed strip uses symbols for **structure**, not for whole sentences.

Keep:
- the timing/state pictogram;
- the once-per-Battle use socket where applicable;
- classification and row pictograms;
- a short text reminder for the actual effect.

Examples:

- Action + use socket + `ENEMY -1`.
- Reaction + use socket + `IGNORE TACTIC`.
- Bonded + `ARCHER/SCOUT +1`.
- Action + use socket + `TAX NEXT BOND`.

The complete prose remains on the full card face. This avoids replacing readable rules with strings of tiny rebus symbols.
