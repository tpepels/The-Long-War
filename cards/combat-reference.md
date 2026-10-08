# Combat and condition quick reference

> **Design reference only:** the Attack, affliction and Boon system is specified in the rulebook, but not fully implemented by the current native runtime. The canonical card catalogue still displays executable card text from `cards.json`.

## Actions and Attack

On a normal turn, draw one card and take up to two Actions: play a card, Maneuver a Named Formation (1 Command), Attack with an eligible Force, or discard two cards to draw one. A Force may Attack once per Battle, without Command payment by default, unless Depleted. A multi-class Force chooses one basic Attack.

| Force | Target | Attack |
|---|---|---|
| Archer | Opposing Rear Force in the same Front | Exhaust |
| Skirmisher | Opposing Middle Force in the same Front | Shake |
| Raider | Opposing Middle/Rear Force in the same Front if its opposing Frontline is empty | Deplete |
| Rider | Flanked opposing Frontline Force in adjacent active Front | Shake |

## Conditions

| Code | Condition | Meaning |
|---|---|---|
| E | Exhausted | Cannot initiate Maneuver |
| S | Shaken | -2 formation Strength at Front resolution; minimum zero |
| D | Depleted | Cannot Attack or activate printed formation ACTION abilities |
| G | Guarded | Prevent next affliction on that Force, then remove Guarded |
| I | Inspired | Remove/prevent Shaken while active |
| P | Empowered | Next Attack ignores screening, then remove Empowered |

All conditions are binary, move with the affected formation and clear at Battle end. A condition marker never covers buried Force/Bond reminders or the top Name's rules. A single six-position check strip beside the formation can record all six with generic cubes or pencil marks; used-Attack is tracked separately. Flanking itself needs no marker.

## Position and screening

Adjacent active Frontlines can flank each other **in either direction**. A Frontline Force is flanked if the opponent occupies the neighboring Frontline and it does not. An inactive Front and the outside battlefield edge never create a flank. Being flanked has no automatic penalty. A Middle Guard screens the Rear Force directly behind from basic Archer Attacks, unless Shaken or Depleted. A card that explicitly bypasses screening can still target it.

## Recovery and Battle end

No general recovery Action. Printed Healer, Steward, Druid, Order and other card effects can remove or prevent conditions. After resolving Fronts, applying Command losses and checking Collapse, clear all conditions and Attack-used markers. Force, Bond, Name and battlefield positioning persist between Battles.
