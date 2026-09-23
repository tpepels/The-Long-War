# Deck size × hand size × between-Battle recycle sweep

This experiment extends the Name-rich / selective completion-draw configuration from `reports/name-completion-sweep.md`.

All variants use:

- flexible Subject/Bond/Name ordering;
- 6-Name 30-card baseline decks;
- selective completion draw on **Oren, Iria, and Teyra**;
- no generic once-per-Battle Draw action;
- Battle-I starter +1-card compensation.

The screen varied:

- deck size: **30, 36, 42**;
- hand/refill target: **9, 10, 11, 12**;
- between-Battle handling:
  - **recycle** — keep hand, reshuffle all non-hand cards, refill to target;
  - **persistent** — keep hand, leave played/discarded cards out, refill only from the remaining deck.

The screen used **24 cells × 1,000 mirror matches per cell = 24,000 matches** across Reference, Avaros, Mara, and Sera. A second confirmation used **4,000 matches per candidate** on the four leading configurations.

## 24-cell screen

| Deck | Hand | Mode | Complete/Battle | Names/Battle | Cards/Battle | Choices | First-pass WR | First-player WR | Refill shortfall |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 9 | persistent | 1.27 | 2.68 | 13.85 | 22.31 | 66.1% | 48.4% | 0.0% |
| 30 | 10 | persistent | 1.56 | 3.02 | 14.97 | 24.73 | 61.7% | 45.4% | 1.2% |
| 30 | 11 | persistent | 1.72 | 3.24 | 15.78 | 27.00 | 57.1% | 43.6% | 6.4% |
| 30 | 12 | persistent | 1.97 | 3.60 | 16.84 | 28.69 | 55.1% | 43.3% | 14.2% |
| 30 | 9 | recycle | 1.23 | 2.39 | 13.58 | 22.37 | 63.7% | 48.9% | 0.0% |
| 30 | 10 | recycle | **1.52** | **2.74** | **14.68** | **24.91** | **57.6%** | **45.9%** | **0.0%** |
| 30 | 11 | recycle | 1.77 | 3.06 | 15.66 | 27.36 | 52.2% | 44.8% | 0.0% |
| 30 | 12 | recycle | 2.08 | 3.44 | 16.94 | 29.43 | 48.1% | 47.2% | 0.0% |
| 36 | 9 | persistent | 1.11 | 2.47 | 13.55 | 22.04 | 68.4% | 49.0% | 0.0% |
| 36 | 10 | persistent | 1.29 | 2.76 | 14.69 | 24.23 | 63.5% | 47.5% | 0.0% |
| 36 | 11 | persistent | 1.57 | 3.03 | 15.68 | 26.61 | 59.1% | 46.5% | 0.0% |
| 36 | 12 | persistent | 1.85 | 3.41 | 16.93 | 28.64 | 54.5% | 49.4% | 0.7% |
| 36 | 9 | recycle | 1.11 | 2.27 | 13.40 | 22.14 | 64.2% | 50.4% | 0.0% |
| 36 | 10 | recycle | 1.35 | 2.55 | 14.59 | 24.31 | 61.4% | 46.0% | 0.0% |
| 36 | 11 | recycle | 1.57 | 2.83 | 15.58 | 26.51 | 57.2% | 46.2% | 0.0% |
| 36 | 12 | recycle | 1.85 | 3.21 | 16.67 | 28.69 | 51.1% | 47.1% | 0.0% |
| 42 | 9 | persistent | 1.09 | 2.23 | 13.78 | 22.24 | 68.0% | 49.3% | 0.0% |
| 42 | 10 | persistent | 1.22 | 2.46 | 14.72 | 24.78 | 63.4% | 48.6% | 0.0% |
| 42 | 11 | persistent | 1.47 | 2.72 | 15.66 | 27.17 | 55.9% | 45.4% | 0.0% |
| 42 | 12 | persistent | 1.71 | 2.99 | 16.72 | 29.41 | 51.3% | 47.6% | 0.0% |
| 42 | 9 | recycle | 1.07 | 2.09 | 13.62 | 22.30 | 67.5% | 49.9% | 0.0% |
| 42 | 10 | recycle | 1.20 | 2.33 | 14.64 | 24.63 | 63.0% | 48.1% | 0.0% |
| 42 | 11 | recycle | 1.40 | 2.56 | 15.33 | 27.27 | 54.3% | 44.9% | 0.0% |
| 42 | 12 | recycle | 1.70 | 2.92 | 16.50 | 29.60 | 49.0% | 46.3% | 0.0% |

## Higher-sample confirmation

| Candidate | Complete/Battle | Names/Battle | Cards/Battle | Choices | First-pass WR | First-player WR | Refill shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 / 10 / persistent | 1.51 | 3.00 | 14.89 | 24.76 | 61.4% | 47.5% | 1.0% |
| 30 / 10 / recycle | **1.50** | 2.74 | **14.72** | 24.82 | **58.5%** | 47.2% | **0.0%** |
| 36 / 11 / persistent | 1.60 | 3.10 | 15.84 | **26.52** | 59.7% | 47.4% | 0.0% |
| 36 / 11 / recycle | 1.58 | 2.91 | 15.58 | 26.62 | **56.1%** | 47.7% | 0.0% |

The confirmation contains **16,000 matches** total.

## Deck size result

Larger decks do not improve the formation problem efficiently.

At the same 10-card hand:

- 30/recycle: **1.52 completions/Battle**
- 36/recycle: **1.35**
- 42/recycle: **1.20**

The larger decks need larger hands to recover the lost completion frequency.

The clearest comparison is the confirmed pair:

- **30 cards / hand 10 / recycle:** 1.50 completions, 14.72 cards/Battle, 24.82 choices.
- **36 cards / hand 11 / recycle:** 1.58 completions, 15.58 cards/Battle, 26.62 choices.

The six extra deck cards plus one extra hand card therefore buy only about **+0.08 completed formations per Battle**, while costing roughly **+0.86 card plays per Battle** and **+1.80 legal choices per heuristic decision**.

The 42-card results are even less attractive at the current card-pool size.

### Important 42-card caveat

There are currently only **seven unique Name cards** in the canonical pool. Because Names are Unique, a 42-card deck cannot preserve the 30-card experiment's 20% Name ratio:

- 30-card Name-rich deck: 6 Names = **20.0%**
- 36-card experiment: 7 Names = **19.4%**
- 42-card experiment: 7 Names = **16.7%**

The 36-card comparison is therefore the fairer test of deck-size scaling. A future 42-card format with 8–9 distinct Names could be worth re-testing after the card pool grows.

## Hand-size result

Within the 30-card recycled format, increasing hand size has a predictable effect:

| Hand | Complete/Battle | Cards/Battle | Choices | First-pass WR |
| ---: | ---: | ---: | ---: | ---: |
| 9 | 1.23 | 13.58 | 22.37 | 63.7% |
| 10 | **1.52** | **14.68** | **24.91** | **57.6%** |
| 11 | 1.77 | 15.66 | 27.36 | 52.2% |
| 12 | 2.08 | 16.94 | 29.43 | 48.1% |

Every extra guaranteed card adds roughly one card play per Battle and about 2–2.5 legal options per decision.

Hand 11 is therefore a valid completion-heavy alternative, but hand 10 remains the more efficient baseline. Hand 12 pushes completion above two per Battle but also produces nearly 17 card plays and about 29 legal choices per heuristic decision.

## Recycle versus persistent deck

Removing between-Battle recycling does **not** materially increase completed formations.

Confirmed at deck 30 / hand 10:

- persistent: **1.51 completions/Battle**
- recycle: **1.50 completions/Battle**

Persistent play does expose more Names (3.00 vs 2.74 Names/Battle), but those extra Name plays do not convert into meaningfully more completed formations. It also:

- uses slightly more cards per Battle;
- raises first-passer Battle win rate from 58.5% to 61.4%;
- produces slightly more dead/unplayable pressure;
- causes a refill shortfall for about **1%** of players already at hand 10.

At hand 11 and 12, the 30-card persistent deck starts to deplete noticeably: the screen found refill shortfall rates of **6.4%** and **14.2%**, respectively.

The 36-card persistent format avoids depletion, but gives no meaningful formation advantage over recycling and needs the larger 11-card hand to reach the same completion range as the 30/10 game.

## Experimental conclusion

The most efficient current baseline remains:

- **30-card deck**
- **10-card hand/refill target**
- **between-Battle recycle**
- **10 Subjects / 6 Names in the 30-card experimental decks**
- no generic once-per-Battle Draw
- selected Names use completion-triggered utility such as **draw 1**

This configuration is not the absolute maximum for completed formations. Hand 11 reaches around 1.8/Battle in the larger Name experiment. It is the current best trade-off between:

- completion frequency;
- card volume;
- decision load;
- hand pressure;
- refill reliability;
- Pass behavior.

Larger decks should be revisited only if the design later wants a larger card pool for variety, or after enough new unique Names exist to preserve the intended Name ratio.
