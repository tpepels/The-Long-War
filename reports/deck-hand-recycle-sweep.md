# Deck size × hand size × recycle experiment

This experiment extends the Name-rich / selective-completion-draw configuration from `reports/name-completion-sweep.md`.

## Scope

Screening run **35848575711** tested:

- deck sizes **30, 36, 42**;
- hand targets **9, 10, 11, 12**;
- **recycle**: keep hand, shuffle all other cards back between Battles, draw to target;
- **persistent**: keep hand, leave played/discarded cards out, draw to target only from the remaining deck;
- generic once-per-Battle Draw disabled;
- Oren / Iria / Teyra draw 1 when their formation becomes complete;
- four mirror profiles: Reference, Avaros, Mara, Sera.

The screening matrix contains **24,000 matches**: 1,000 per cell.

The 36-card and 42-card experimental decks use all seven existing unique Names. No new Name cards were invented for this experiment.

A second run, **35849136696**, confirmed four leading cells with **4,000 matches each / 16,000 matches total**.

## Full screening matrix

| Deck | Hand | Mode | Complete/Battle | Names/Battle | Cards/Battle | Choices | First-pass WR | First-player WR | Refill shortfall |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 9 | persistent | 1.27 | 2.68 | 13.85 | 22.31 | 66.1% | 48.4% | 0.0% |
| 30 | 10 | persistent | 1.56 | 3.02 | 14.97 | 24.73 | 61.7% | 45.4% | 1.2% |
| 30 | 11 | persistent | 1.72 | 3.24 | 15.78 | 27.00 | 57.1% | 43.6% | 6.4% |
| 30 | 12 | persistent | 1.97 | 3.60 | 16.84 | 28.69 | 55.1% | 43.3% | 14.2% |
| 30 | 9 | recycle | 1.23 | 2.39 | 13.58 | 22.37 | 63.7% | 48.9% | 0.0% |
| 30 | 10 | recycle | 1.52 | 2.74 | 14.68 | 24.91 | 57.6% | 45.9% | 0.0% |
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

The first-player figures in this table are only 1,000-match screening measurements and should not be used alone for balance conclusions.

## Higher-sample confirmation

| Candidate | Complete/Battle | Names/Battle | Cards/Battle | Choices | First-pass WR | First-player WR | Refill shortfall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 / hand 10 / persistent | **1.51** | **3.00** | **14.89** | **24.76** | 61.4% | 47.5% | **1.0%** |
| 30 / hand 10 / recycle | 1.50 | 2.74 | 14.72 | 24.82 | 58.5% | 47.2% | 0.0% |
| 36 / hand 11 / persistent | 1.60 | 3.10 | 15.84 | 26.52 | 59.7% | 47.4% | 0.0% |
| 36 / hand 11 / recycle | 1.58 | 2.91 | 15.58 | 26.62 | 56.1% | 47.7% | 0.0% |

All four confirmation cells used 4,000 matches.

## Findings

### 1. Larger decks require larger hands to recover the same formation rate

At hand 10, completion frequency falls as the deck grows:

- 30 recycle: about **1.50 complete formations/Battle**;
- 36 recycle: screening **1.35**;
- 42 recycle: screening **1.20**.

A 36-card deck needs roughly hand 11 to return to the 1.5–1.6 range. A 42-card deck needs roughly hand 12 to reach 1.7.

The larger deck therefore does not give free additional design space: the hand has to grow with it.

### 2. The extra hand size costs more than the larger deck gains

Confirmed persistent comparison:

- 30 / hand 10: **1.51 completions**, 14.89 cards/Battle, 24.76 choices;
- 36 / hand 11: **1.60 completions**, 15.84 cards/Battle, 26.52 choices.

The larger configuration gains only **0.09 complete formations per Battle**, while adding about **0.95 card plays per Battle** and **1.76 legal choices per decision**.

This is not an efficient exchange if the purpose of the larger deck is to solve the Name/completion problem.

### 3. Recycling is not required at 30 cards / hand 10

The strongest practical result is the direct 30/10 comparison:

- recycle: **1.50 completions**, 2.74 Names/Battle, 14.72 cards/Battle;
- persistent: **1.51 completions**, 3.00 Names/Battle, 14.89 cards/Battle.

Only **1.0%** of next-Battle player refills in the persistent version fall below the 10-card target. Mean next-Battle hand size is 9.98.

So the deck can remain persistent across Battles without materially breaking refill at the current 30/10 scale.

This restores a real match-level resource consequence: cards committed in one Battle are not immediately available again in the next.

### 4. Larger decks mainly solve an exhaustion problem that 30/10 barely has

At 36/11 persistent, refill shortfall is effectively zero. That is clean, but 30/10 persistent already misses the refill target only about one time in a hundred.

The additional six cards therefore mostly buy insurance against a problem that is already rare, while increasing hand size and decision load.

### 5. Hand size remains the dominant pacing lever

Across every deck size, increasing the hand raises:

- complete formations;
- Names played;
- cards committed per Battle;
- legal choices;
- and generally moves first-pass outcomes closer to parity.

The cost is consistent: larger hands make Battles longer and more cognitively dense.

## Experimental conclusion

The most efficient baseline remains:

- **30-card deck**
- **10-card hand**
- **10 Subjects / 6 Names** in the current Name-rich test decks
- **no generic Draw action**
- selective Name completion utility (Oren / Iria / Teyra draw 1 in this prototype)

The new evidence suggests that **between-Battle recycling can be removed**:

> Keep your hand. Played and discarded cards stay out of the deck. Draw from the remaining deck until you have 10 cards, or until the deck is empty.

That version produces essentially the same formation rate as recycling, retains acceptable pacing and decision load, and creates meaningful multi-Battle resource progression.

The 36-card / hand-11 version is viable if a larger deck is desired for card-pool variety, but the current data does not justify it as a mechanical improvement. The 42-card variants are less efficient with the existing seven-Name pool.

No experimental deck-size, hand-size, or recycle-mode change in this branch has been merged to `main`.
