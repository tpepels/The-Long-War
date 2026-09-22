# First-playtest AI pacing statistics

This snapshot aggregates the exact-rules heuristic self-play evidence from **Expanded Pool Playtest Gate run 35763345667**, artifact **10711860903**, on PR #15 head `46b71f67479a1ac1b677c7c6ab2446ceda4c1b5b`. That revision was merged as `261e6eb803d0913479bc62c2491d0d42960fb609`. All ten simulation reports carry game fingerprint `3893976b92901b46`.

The dataset contains **20,000 matches and 50,921 Battles**: Reference mirror, Avaros mirror, Mara mirror, Sera mirror, and both seat orders for every archetype matchup.

## Match and Battle pacing

| Metric | Result |
| --- | ---: |
| Battles per match | 2.55 |
| 2-Battle matches | 9,079 (45.4%) |
| 3-Battle matches | 10,921 (54.6%) |
| Action events per match | 34.82 |
| Cards played per match | 25.88 |
| Action events per Battle | 13.07 |
| Normal turn actions per Battle | 12.48 |
| Normal turn actions per player per Battle | 6.24 |
| Cards played per Battle | 10.16 |
| Cards played per player per Battle | 5.08 |
| Complete Subject–Bond–Name combinations created per Battle | 0.85 |

`Action events` includes card plays, Draw, Pass, and the free Stratagem-setting action. The between-Battle `ChooseFirst` decision is excluded from the Battle figure. `Cards played` includes Subjects, Bonds, Names, Stories, Veiled Stories, and Stratagems.

## Card mix per Battle

| Card type | Mean per Battle | Share of card plays |
| --- | ---: | ---: |
| Subjects | 5.34 | 52.6% |
| Bonds | 1.75 | 17.3% |
| Names | 0.85 | 8.4% |
| Stories | 0.46 | 4.5% |
| Veiled Stories | 1.17 | 11.5% |
| Stratagems | 0.59 | 5.8% |

Subjects account for just over half of all cards played. Across both players, fewer than one complete Subject–Bond–Name chain is created per Battle on average.

## Draw, passing, and hand pressure

| Metric | Result |
| --- | ---: |
| Draw actions per Battle | 0.90 |
| Draw opportunity used | 45.2% |
| Stratagem opportunity used | 29.4% |
| Hand size when passing | 3.87 |
| Dead cards when passing | 1.01 |
| Dead-card share of cards held at pass | 26.2% |
| Card-in-hand turns that were unplayable | 22.1% |
| Drawn cards eventually played | 79.4% |
| First passer wins the Battle | 35.4% |
| Mean legal candidates per heuristic decision | 11.58 |

The Draw figure uses two player-opportunities per Battle as its denominator. On this policy it is used less than half the time, so it is not behaving as an automatic action. Passing first is costly in the heuristic policy: the first passer wins only about 35% of Battles. At pass time, roughly one quarter of the cards still held are mechanically dead.

## Simulation breakdown

| Simulation | Games | Battles/match | 3-Battle matches | Cards/Battle | Cards/match | Draw use |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Reference mirror | 5,000 | 2.52 | 52.0% | 10.37 | 26.12 | 46.0% |
| Avaros mirror | 2,000 | 2.58 | 58.4% | 10.10 | 26.10 | 45.0% |
| Mara mirror | 2,000 | 2.54 | 53.7% | 10.22 | 25.93 | 45.9% |
| Sera mirror | 2,000 | 2.54 | 54.1% | 10.09 | 25.64 | 44.0% |
| Avaros–Mara, seat order A | 1,500 | 2.58 | 58.1% | 10.17 | 26.26 | 46.6% |
| Avaros–Mara, seat order B | 1,500 | 2.55 | 54.9% | 10.27 | 26.19 | 46.3% |
| Avaros–Sera, seat order A | 1,500 | 2.55 | 55.5% | 10.07 | 25.74 | 45.5% |
| Avaros–Sera, seat order B | 1,500 | 2.56 | 55.7% | 10.03 | 25.64 | 45.2% |
| Mara–Sera, seat order A | 1,500 | 2.54 | 54.3% | 9.92 | 25.23 | 43.3% |
| Mara–Sera, seat order B | 1,500 | 2.55 | 54.8% | 9.94 | 25.32 | 42.5% |

## What this can and cannot tell us

The structural pacing is fairly consistent across decks: roughly 10 cards are played per Battle and 25–26 per match, while just over half of matches reach Battle III. Draw usage is genuinely situational in the heuristic policy rather than compulsory.

The two statistics worth watching most closely in the human test are the **35.4% first-passer Battle win rate** and the **22–26% dead/unplayable-card load**. The former may create pressure to keep spending cards instead of conserving them; the latter may make hands feel constrained. The low frequency of complete Subject–Bond–Name chains also means the Name layer may be less central in actual play than the rules structure suggests.

AI self-play cannot establish human match duration, reading burden, rules comprehension, memory load, whether 11–12 apparent choices feel manageable, or whether the decisions are enjoyable. Those require the human playtest; these numbers provide the baseline against which the human observations can be compared.
