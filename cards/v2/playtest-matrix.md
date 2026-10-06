# V2 playtest and archetype matrix

The pool is evaluated on classification depth, mechanical coverage, and the card-value heuristic. The four exploratory decks collectively cover every current V2 card.

## Mechanical coverage

| Mechanical family | Designs |
|---|---:|
| Strength | 40 |
| Command | 37 |
| Marker State | 37 |
| Classification Synergy | 36 |
| Named Payoff | 34 |
| Formation Building | 27 |
| Persistent State | 26 |
| Positional Support | 22 |
| Action Engine | 19 |
| Card Flow | 17 |
| Hostile Interaction | 17 |
| Command Recovery | 15 |
| Information | 15 |
| Protection | 14 |
| Army Support | 12 |
| Movement | 12 |
| Tax | 12 |
| Exhaustion | 11 |
| Hidden Plan | 11 |
| Suppression | 10 |
| Play Effect | 8 |
| Prepared Cards | 6 |
| Zero Command | 5 |
| Healing | 4 |
| Baseline | 3 |
| Disruption | 3 |
| Raider Pressure | 3 |
| Outmatched | 2 |
| Reserve | 2 |
| Supply | 2 |
| Prepared Pressure | 1 |
| Reaction | 1 |

## Timing coverage

| Timing | Effects |
|---|---:|
| Play | 38 |
| Becomes_named | 31 |
| Action | 22 |
| Continuous | 22 |
| Bonded | 16 |
| Hidden | 11 |
| Trigger | 8 |
| While_named | 7 |
| Front | 5 |
| Rear | 4 |
| Exhausted | 2 |
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
| **Captain** | Rank | 8 | 8 |
| **Raider** | Role | 8 | 6 |
| **Rider** | Role | 6 | 3 |
| **Scout** | Role | 6 | 9 |
| **Skirmisher** | Role | 6 | 6 |
| **Veteran** | Rank | 6 | 1 |
| **Archer** | Role | 5 | 6 |
| **King** | Rank | 4 | 6 |
| **Spearman** | Role | 4 | 2 |
| **Seer** | Role | 3 | 2 |
| **Steward** | Role | 3 | 2 |
| **Builder** | Role | 2 | 0 |
| **Healer** | Role | 2 | 3 |
| **Ship** | Kind | 2 | 1 |
| **Stronghold** | Kind | 2 | 4 |
| **Heir** | Rank | 1 | 1 |

## Playtest focus after the value/breadth pass

- Replace provisional applicability multipliers in `value-model.md` with observed condition-active rates.
- Compare Fresh Orders with the narrower but stronger Send a Runner.
- Check whether Catch Your Breath and Bind the Wound are useful enough despite requiring both a support class and an existing adverse state.
- Check whether Re-form the Line creates meaningful positional turns without replacing normal Maneuver.
- Compare 1-Command Take Stock against other card-selection engines.
- Watch MOBILE + TIRELESS Grey Riders, PRESS snowballing against already Exhausted Fronts, Supply raids, persistent taxes, and zero-cost Bond chains.

Per card, record drawn, played, dead in hand, Command spent, Action spent, condition-active rate, whether it changed a decision or Front result, counterplay, forgotten state, rules questions, and voluntary re-inclusion.
