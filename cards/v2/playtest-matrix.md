# V2 playtest and archetype matrix

The pool is evaluated on classification depth, mechanical coverage, and the card-value heuristic.

## Mechanical coverage

| Mechanical family | Designs |
|---|---:|
| Strength | 38 |
| Command | 36 |
| Marker State | 36 |
| Named Payoff | 34 |
| Classification Synergy | 30 |
| Formation Building | 27 |
| Persistent State | 24 |
| Positional Support | 20 |
| Action Engine | 19 |
| Command Recovery | 15 |
| Card Flow | 14 |
| Hostile Interaction | 14 |
| Information | 14 |
| Protection | 14 |
| Army Support | 12 |
| Tax | 12 |
| Hidden Plan | 11 |
| Movement | 11 |
| Suppression | 10 |
| Exhaustion | 8 |
| Play Effect | 7 |
| Baseline | 6 |
| Prepared Cards | 6 |
| Disruption | 3 |
| Healing | 2 |
| Outmatched | 2 |
| Reserve | 2 |
| Prepared Pressure | 1 |
| Raider Pressure | 1 |
| Reaction | 1 |

## Timing coverage

| Timing | Effects |
|---|---:|
| Becomes_named | 31 |
| Play | 31 |
| Action | 22 |
| Continuous | 21 |
| Bonded | 16 |
| Hidden | 11 |
| Trigger | 8 |
| While_named | 7 |
| Front | 5 |
| Rear | 4 |
| Exhausted | 1 |
| Middle | 1 |
| Mobile | 1 |
| Tireless | 1 |

There are **0 RESOLUTION effects**, **0 bare 1/BATTLE timings**, **0 regular Force once-per-Battle effects**, and **0 Bond ACTION/REACTION effects** by design.

## Physical-state pressure

| Representation | Effects |
|---|---:|
| Used_marker | 20 |
| Effect_marker | 16 |
| Face_up_source | 16 |
| Face_down_source | 11 |
| Front_marker | 8 |
| Suppression_marker | 6 |

## Classification support

| Classification | Layer | Carriers | Explicit support |
|---|---|---:|---:|
| **Human** | Kind | 57 | 2 |
| **Guard** | Role | 9 | 5 |
| **Scout** | Role | 6 | 8 |
| **Captain** | Rank | 8 | 6 |
| **Raider** | Role | 7 | 6 |
| **Archer** | Role | 5 | 6 |
| **Skirmisher** | Role | 4 | 6 |
| **Rider** | Role | 6 | 3 |
| **King** | Rank | 4 | 5 |
| **Spearman** | Role | 5 | 2 |
| **Veteran** | Rank | 6 | 1 |
| **Stronghold** | Kind | 2 | 3 |
| **Seer** | Role | 3 | 2 |
| **Ship** | Kind | 2 | 1 |
| **Healer** | Role | 2 | 1 |
| **Steward** | Role | 3 | 0 |
| **Builder** | Role | 2 | 0 |
| **Heir** | Rank | 1 | 1 |


## Playtest focus after the value/breadth pass

- Replace provisional applicability multipliers in `value-model.md` with observed condition-active rates.
- Watch MOBILE + TIRELESS Grey Riders, especially with The Long March.
- Check whether repeatable Force Actions (Vardai and White Hands) justify half a turn without becoming automatic.
- Watch persistent taxes on Aradai, Iron Boars and Red Duelists for oppressive stacking.
- Check whether positional information Forces reveal too much hidden Stratagem information.
- Compare 2-Command Baggage with 1-Command conditional -2 Tactics and the 2-Command Rear-only -3 Tactic.
- Track whether 0-Command cards are useful Action-for-selection trades rather than automatic inclusions.
- Continue watching SUPPORT / SUPPLY / RESERVE arithmetic and zero-cost Bond chains.

Per card, record drawn, played, dead in hand, Command spent, Action spent, condition-active rate, whether it changed a decision or Front result, counterplay, forgotten state, rules questions, and voluntary re-inclusion.
