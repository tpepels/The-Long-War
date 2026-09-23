# Name availability and completion-reward sweep

This experiment follows the flexible-formation / between-Battle recycle rules merged in PR #17. It asks whether the low Subject–Bond–Name completion rate is primarily caused by Name availability, and whether selected Name completions should grant a non-Strength utility reward.

Workflow run: **35839793171**  
Experiment head: `1f89f0220a2d91ea7c73980baeeb8b001f272b52`

The sweep contains **36,000 heuristic mirror matches**: 4,000 per cell across Reference, Avaros, Mara, and Sera.

All cells:

- disable the generic once-per-Battle Draw action;
- preserve the Battle-I starter +1-card compensation;
- preserve flexible Subject/Bond/Name ordering;
- preserve between-Battle recycling and refill to the tested hand target.

## Variants

**Current** uses the existing 30-card playtest decks: 12 Subjects and 4 Names.

**Name-rich** replaces two Subjects with two existing unique Names in each deck, producing 10 Subjects and 6 Names while leaving each deck's other card counts unchanged.

**Name-rich + selective draw** uses the same 10-Subject / 6-Name decks. If a formation containing **Oren, Iria, or Teyra** becomes complete, its controller draws 1 card. The reward triggers regardless of whether Subject, Bond, or Name was the last component. It adds no Strength.

## Main results

| Hand | Deck / reward | Complete formations / Battle | Names / Battle | Cards / Battle | Legal choices / decision | First passer Battle WR | Dead-card share at Pass | First-player match WR |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | Current | 0.81 | 1.50 | 13.04 | 21.36 | 65.3% | 6.6% | 48.4% |
| 9 | 6 Names | 1.13 | 2.37 | 13.41 | 22.23 | 70.8% | 6.3% | 49.6% |
| 9 | 6 Names + selective draw | 1.27 | 2.44 | 13.62 | 22.39 | 63.1% | 6.2% | 48.7% |
| 10 | Current | 0.98 | 1.71 | 14.06 | 23.50 | 58.7% | 7.2% | 46.6% |
| 10 | 6 Names | 1.37 | 2.71 | 14.54 | 24.58 | 66.6% | 6.8% | 47.3% |
| 10 | 6 Names + selective draw | **1.55** | **2.78** | **14.78** | **24.80** | **57.6%** | **6.7%** | **48.3%** |
| 11 | Current | 1.14 | 1.91 | 14.98 | 25.64 | 52.8% | 7.9% | 47.0% |
| 11 | 6 Names | 1.59 | 3.01 | 15.60 | 26.96 | 61.2% | 6.9% | 46.8% |
| 11 | 6 Names + selective draw | 1.80 | 3.10 | 15.85 | 27.17 | 53.3% | 6.8% | 46.9% |

Unplayable card-turn share remains around **1.8–2.3%** in every cell, so none of these variants reintroduces the old dead-hand problem.

## Availability is the larger lever

Moving from 4 to 6 Names produces a large completion increase at every hand size:

| Hand | Current completion rate | 6-Name completion rate | Increase |
| ---: | ---: | ---: | ---: |
| 9 | 0.81 | 1.13 | +40% |
| 10 | 0.98 | 1.37 | +40% |
| 11 | 1.14 | 1.59 | +39% |

This is much more efficient than increasing hand size. Most notably:

- **9 cards + 6 Names:** 1.13 completed formations/Battle, 13.41 cards/Battle, 22.23 legal choices.
- **11 cards + 4 Names:** 1.14 completed formations/Battle, 14.98 cards/Battle, 25.64 legal choices.

Those two variants produce essentially the same completion frequency, but the Name-rich 9-card game uses about **1.6 fewer card plays per Battle** and presents about **3.4 fewer legal choices per decision**.

The remaining formation bottleneck is therefore primarily deck composition rather than hand size.

## Selective completion draw is useful

The three reward Names account for roughly half of all completed formations in the Name-rich decks:

| Hand | Reward-eligible completions / Battle | Share of all completions |
| ---: | ---: | ---: |
| 9 | 0.68 | 53.7% |
| 10 | 0.83 | 53.4% |
| 11 | 0.94 | 52.1% |

Adding the reward consistently increases completion rate:

| Hand | 6 Names | 6 Names + draw | Completion gain | Extra cards / Battle | Extra legal choices |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 1.13 | 1.27 | +0.13 | +0.21 | +0.16 |
| 10 | 1.37 | 1.55 | +0.18 | +0.23 | +0.22 |
| 11 | 1.59 | 1.80 | +0.21 | +0.25 | +0.20 |

The completion reward therefore creates additional formation play without a large complexity penalty. It also pulls the heuristic's first-passer win rate downward by roughly 8–9 percentage points at each hand size.

This supports making Names stronger as a **utility class** rather than simply adding more Strength. Draw is one viable completion ability; other Names can use movement, information, recovery, protection, or positional effects instead.

## Best experimental baseline

The strongest compromise in this sweep is:

- **10-card hand target**
- **10 Subjects / 6 Names**
- generic once-per-Battle Draw removed
- selected Name completions grant utility rewards
- Oren/Iria/Teyra → draw 1 is the tested prototype

It produces:

- **1.55 completed formations per Battle**
- **2.78 Names played per Battle**
- **14.78 cards played per Battle**
- **24.80 legal choices per heuristic decision**
- **57.6% first-passer Battle win rate**
- **6.7% dead-card share at Pass**
- **2.0% unplayable card-turn share**
- **48.3% equal-profile average first-player match win rate**

The 11-card reward variant reaches 1.80 completions/Battle but costs another full card play per Battle and pushes the decision space above 27 legal options. The 9-card reward variant is lighter but produces only 1.27 completions/Battle and retains a stronger first-pass advantage.

## Interpretation

This experiment does not establish that every Name should draw, or that Oren/Iria/Teyra are the final three cards that should do so. It establishes two structural points:

1. **Six Names is a much better fit for the formation system than four.**
2. **Completion-triggered utility is an efficient way to make Names worth finishing without relying on raw Strength.**

The next rules design should distribute distinct completion abilities across the Name class rather than giving every Name the same reward. The 10-card / 6-Name / selective-utility configuration is the best baseline for the next experiments on between-Battle reshuffling and larger deck sizes.
