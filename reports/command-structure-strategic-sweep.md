# Command structure, Name density, and strategic-agent experiments

This report consolidates the experiments run after the first Command-economy prototype showed only about 2.2 Names and 1.4 completed formations per Battle under the original one-ply heuristic.

The design target for this round was explicit:

> **At least 3 Names played per Battle**, without solving the problem by inflating the hand, bloating the deck, or adding unnecessary core rules.

All work remains experimental. Nothing in this report is merged to `main`.

## Fixed Command rules

Unless a cell explicitly says otherwise, these experiments keep:

- 30-card deck;
- 10-card base hand unless hand size is the tested variable;
- 10 Subjects / 6 Names in the original Name-rich decks;
- 20 starting Command;
- +10 Command between Battles, maximum 20;
- one operation per turn;
- printed 1/2/3 Command card costs;
- Cycle = pay 1, discard 1, draw 1;
- Pass = 0;
- no generic Draw operation;
- the redesigned Name utility effects.

## Why the agent had to change

The original `HeuristicAgent` evaluates one action forward. Under Command, that is a serious limitation:

- completing a formation often requires several operations;
- Cycle may be bad immediately but good because it finds a missing component;
- conserving Command affects later Battles;
- with a persistent deck, spending or Cycling a card changes future availability;
- passing can intentionally trade the current Battle for future Command/cards.

A new `StrategicHeuristicAgent` was therefore added as a design-validation agent.

It:

- samples opponent hidden information from a belief state rather than reading the real hand;
- knows the controlled mirror-test deck hypothesis, but not hidden card locations/order;
- evaluates a small set of promising root actions;
- rolls through an opponent response and subsequent actions;
- retains the existing heuristic as its leaf evaluator.

Most strategic runs use **2 belief samples, 3 rollout plies, candidate width 5**. This is deliberately much cheaper than MCCFR and is intended for structural validation, not as a claim of optimal play.

## 1. Hand and deck size with the one-ply heuristic

Run: **Command Hand Deck Sweep — 35857054635**

The broad screen used 1,000 matches per structural cell.

### 30 cards, recycling between Battles

| Hand | Names/Battle | Complete/Battle | Choices |
| ---: | ---: | ---: | ---: |
| 10 | 2.25 | 1.41 | 32.0 |
| 11 | 2.31 | 1.51 | 35.8 |
| 12 | 2.46 | 1.66 | 39.0 |
| 13 | 2.55 | 1.79 | 42.7 |
| 14 | 2.60 | 1.81 | 46.3 |

This appeared to imply that hand size could not reach the 3-Name target efficiently.

### Larger decks did not solve it

At the same hand size, 36-card decks generally produced **fewer** Names/Battle because the useful formation components were diluted. Larger hands were then needed to compensate.

This makes 36/42 cards a poor mechanical fix for Name frequency. A larger deck can still be desirable for card-pool variety later, but the data does not justify it as a formation-frequency solution.

## 2. Fully persistent decks expose a real exhaustion problem

With no between-Battle recycling and no reshuffle-on-empty, Cycle consumes the remaining draw pile much faster than in the pre-Command experiments.

For 30 cards:

| Hand | Names/Battle | Complete/Battle | Player-game deck exhaustion | Refill shortfall |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 2.67 | 1.65 | 17.0% | 6.1% |
| 13 | 2.83 | 1.83 | 24.5% | 9.2% |
| 14 | 2.94 | 1.90 | 34.4% | 14.3% |

So a **fully persistent 30-card draw pile with no recycling mechanism is not a good rule**.

## 3. Increasing Name density helps, but was initially solving the wrong problem

### Seven Names, shallow heuristic

Run: **Seven Name Density Sweep — 35858072655**

With 7 Names in 30 cards and recycling:

- hand 10: 2.50 Names/Battle;
- hand 12: 2.69;
- hand 14: 2.84.

The target was still not reached.

### Eight Names, shallow heuristic

Run: **Eight Name Density Sweep — 35859036452**

A separate experimental eighth Name proxy was used only to isolate Name density.

| Hand | Names/Battle | Complete/Battle | Choices |
| ---: | ---: | ---: | ---: |
| 10 | 2.78 | 1.51 | 34.2 |
| 11 | 2.89 | 1.69 | 37.6 |
| 12 | 2.99 | 1.78 | 41.6 |
| 13 | **3.05** | 1.94 | 45.6 |
| 14 | 3.11 | 2.02 | 49.4 |

This proved that density could force the target, but only at the cost of a much larger hand/decision space under the shallow agent.

The later strategic results show that this was largely unnecessary.

## 4. Strategic play changes the result completely

### Six Names / 30 cards / recycle

Run: **Strategic Hand Curve — 35859790318**

200 matches per hand, four archetypes.

| Hand | Names/Battle | Complete/Battle | Cycles/Battle | Cards/Battle | Choices |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **10** | **3.37** | **1.85** | 3.11 | 15.44 | **28.1** |
| 11 | 3.20 | 1.81 | 2.95 | 15.60 | 31.0 |
| 12 | 3.26 | 1.89 | 2.42 | 15.95 | 34.7 |
| 13 | 3.28 | 2.03 | 2.05 | 16.34 | 37.9 |

This is the central finding of the whole round.

**The original six-Name, hand-10 structure already exceeds the 3-Name target when the agent plans beyond one ply.**

Increasing the hand is not required and mostly raises the decision space.

A second 100-match-per-cell sweep independently reproduced the direction:

- 6 Names / hand 10: 3.17 Names/Battle;
- 6 Names / hand 11: 3.21;
- 6 Names / hand 12: 3.27;
- 7 Names / hand 10: 3.75.

Run: **Strategic Name Hand Sweep — 35859950406**.

The earlier low Name rates were therefore primarily an **evaluation-agent artifact**, not evidence that the deck structurally lacked enough Names.

## 5. Persistent-until-empty is a viable simple deck rule

A third deck model was added:

> Do **not** reshuffle all non-hand cards between Battles. Played and discarded cards remain in the discard pile and the remaining draw pile persists. When the draw pile is empty and a card must be drawn, shuffle the discard pile to form a new draw pile.

This is the standard physical-card-game reshuffle rule, and it creates real match-level card persistence without permanent exhaustion.

### Shallow seven-Name test

Run: **Persistent Until Empty — 35859414844**

| Hand | Names/Battle | Complete/Battle | Hard exhaustion | Players reshuffling |
| ---: | ---: | ---: | ---: | ---: |
| 12 | 3.02 | 1.78 | 0% | 12.9% |
| 13 | 3.09 | 1.86 | 0% | 18.9% |
| 14 | 3.11 | 1.98 | 0% | 28.9% |

This already reached the target with the shallow heuristic.

### Strategic seven-Name test

Run: **Strategic Persistent Until Empty — 35860203031**

| Hand | Names/Battle | Complete/Battle | Choices | Players reshuffling |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 3.97 | 2.02 | 29.5 | 32.5% |
| 11 | 4.01 | 2.21 | 32.8 | 36.0% |
| 12 | 3.90 | 2.12 | 36.0 | 48.0% |

Again, hand 10 is enough.

## 6. Final isolated comparison: six Names, hand 10

Run: **Strategic Six Name Persistent Comparison — 35861132825**

This removes the remaining density/hand confounds.

| Mode | Hand | Names/Battle | Complete/Battle | Cycles/Battle | Cards/Battle | Choices | Players reshuffling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| recycle each Battle | 10 | 3.37* | 1.85* | 3.11* | 15.44* | 28.1* | n/a |
| persistent-until-empty | **10** | **3.54** | **1.88** | **3.10** | **15.56** | **28.3** | **24.8%** |
| persistent-until-empty | 11 | 3.56 | 2.00 | 2.80 | 15.81 | 31.6 | 34.8% |

*Recycle figures are from the 200-match Strategic Hand Curve above; persistent figures are also 200-match cells.

The persistent rule gives a modest improvement in Name/completion frequency with essentially the **same card volume, Cycle frequency, and decision load**.

It also creates the long-term planning property we wanted:

- cards played or Cycled in one Battle normally remain unavailable in the next;
- players can reason about what remains in their deck;
- only about one quarter of player-matches at hand 10 need a discard reshuffle;
- there is no hard deck exhaustion.

## 7. 36 cards remain unnecessary

Additional 36-card experiments, including 8 Names, did not outperform the 30-card alternatives efficiently.

A representative high-density cell:

- 36 cards / 8 Names / hand 14 / persistent: about 3.02 Names/Battle, 1.92 completions, 45.4 choices.

Compare:

- 30 cards / 6 Names / hand 10 / persistent-until-empty / strategic: **3.54 Names/Battle, 1.88 completions, 28.3 choices**.

The larger deck is therefore not justified as a Name-frequency fix.

## Current experimental recommendation

The strongest structural candidate is now:

- **30-card deck**
- **10-card hand**
- **10 Subjects**
- **6 Names**
- **Command economy**
- **no generic Draw**
- **Cycle: 1 Command, discard 1 / draw 1**
- **one operation per turn**
- **persistent draw pile across Battles**
- **no automatic between-Battle reshuffle**
- **when the draw pile empties, shuffle the discard pile into a new draw pile**
- existing redesigned Name utility effects
- use the strategic heuristic, not the one-ply heuristic, for serious structural evaluation.

### Why six Names, not seven or eight?

Six already clears the explicit target.

Seven Names remains a legitimate **card-design/content choice** if we want another named character or more Name variety. It is no longer required to repair the game mathematically.

Eight Names is not justified by the current evidence.

### Why hand 10, not 11–14?

Hand 10 already clears the target and has the lowest decision load among the successful strategic configurations.

The hand-11 persistent cell improves completions from 1.88 to 2.00, but raises choices from 28.3 to 31.6 and increases player-match reshuffling from 24.8% to 34.8%.

That is not enough benefit to justify enlarging the default hand yet.

## Important methodological conclusion

Future structural experiments involving Command, Cycle, passing, formation construction, or persistent deck state should **not use the one-ply heuristic as the final judge**.

It remains useful for cheap broad screens, but it materially undervalues multi-operation plans.

Recommended workflow:

1. use the ordinary heuristic for broad parameter screening;
2. confirm finalists with the belief-sampled strategic heuristic;
3. use human playtests for pacing, cognitive load, and whether strategic concessions/Cycling feel good;
4. reserve MCCFR for questions that truly require equilibrium analysis.

## Remaining human-play questions

The quantitative formation/Name-frequency problem is now substantially resolved. The important unresolved questions are qualitative:

- Does roughly **3 Cycles per Battle** feel useful or repetitive?
- Is remembering the persistent draw/discard state easy enough in physical play?
- Does preserving cards/Command across Battles create satisfying long-term planning?
- Do early concessions feel strategic rather than automatic?
- Are ~1.9 completed formations per Battle enough in real play, given that each completion now carries meaningful Name utility?
- Do the printed Command costs feel intuitive at the table?

These are now better targets for playtesting than further increasing hand size, deck size, or Name density.

## Robustness note

A more expensive 3-belief-sample / 4-ply structural check was launched after these results. It is intentionally **not a gate** for this report: the 3-ply experiments already provide the completed comparative evidence above, while the 4-ply version is too computationally expensive for routine simulation.
