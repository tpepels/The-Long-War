# Pass-rule experiment log

This file preserves the Pass/Battle-ending evidence so rule iterations do not erase the baseline.

## Historical consecutive-Pass evidence

Source: the 2026-10-01 balance snapshot produced before direct Front-loss Command attrition and simultaneous 0-0 draws became canonical. These figures are diagnostic history, **not an apples-to-apples comparison with the current rules**.

- 48 same-deck ISMCTS games
- 1,055 resolved Battles recorded
- 2,778 Pass operations
- 1,723 first-Pass events
- 668 first Passes were later cleared by an opponent operation before the Battle finally ended
- those 668 repeated first-Pass events were 24.0% of all Pass operations
- 0.63 cleared/re-established first Passes per Battle
- 90.6% of Passes occurred while at least one playable card action remained
- mean hand at Pass: 9.96 cards
- mean Command at Pass: 1.63
- mean playable cards remaining at Pass: 4.36
- mean legal alternatives at Pass: about 23
- 37/48 games decisive, 11/48 censored (22.9%)
- mean match length: about 278 actions, with a 500-action censor horizon
- first-player wins among decisive games: 51.4%

Interpretation retained from that run: consecutive Pass created substantial administrative re-Passing, while low-Command non-termination was also present. Later engine review showed that run used the wrong Front-loss implementation and 0-0 continuation, so matchup/card-balance conclusions from it are historical only.

## Current controlled candidates

All new variants use the current Command rules: each unprotected lost Front removes 1 Command before Collapse; 0-0 is a draw.

| Variant | Signal costs turn? | Automatic closing window |
| --- | ---: | --- |
| permanent | yes | none |
| closing-2 | yes | 2 full rounds = 4 turns after first Pass |
| closing-3 | yes | 3 full rounds = 6 turns after first Pass |
| battle-flag | no | none |

For closing variants, the Battle still ends immediately if the other player Passes before the window expires.

Run the paired screen with:

```bash
python tools/run_experiments.py pass-variants
```

The default is deliberately small: 6 games per canonical deck per variant, four workers, ISMCTS at 5,000 iterations and 2 belief samples. Every variant uses the same deck/game seeds. Results are written under `artifacts/pass-variants/<fingerprint>/summary.json`.

Do not use this screen for card balance. Its question is Battle-ending behavior: match length, Battles per game, Pass/flag frequency, draw/censor rate, first-player rate, and Command at the first signal.


## First current-rules paired screen - 2026-10-01

Command:

```bash
python tools/run_experiments.py pass-variants
```

Configuration: 6 games per canonical same-deck profile, 6 profiles, 36 games per variant; paired seeds; ISMCTS 5,000 iterations, 2 belief samples; 4 workers. Current Command rules include direct -1 Command per unprotected lost Front before Collapse and simultaneous 0-0 as a draw.

| Variant | Games | Decisive | Draws | Draw rate | Censored | Mean actions | Mean Battles | Approx actions/Battle |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| permanent | 36 | 28 | 8 | 22.2% | 0 | 69.5 | 3.25 | 21.4 |
| closing-2 | 36 | 31 | 5 | 13.9% | 0 | 86.4 | 6.42 | 13.5 |
| closing-3 | 36 | 33 | 3 | 8.3% | 0 | 96.4 | 4.97 | 19.4 |
| battle-flag | 36 | 21 | 15 | 41.7% | 0 | 48.4 | 1.42 | 34.1 |

### Immediate reading

- All 144 games completed below the 500-action censor horizon.
- Permanent Pass produced substantially shorter wars than either fixed closing window.
- Closing-2 produced the shortest Battles but the most Battles per war.
- Closing-3 produced the lowest observed draw rate in this small sample, but also the longest wars by action count.
- The free Battle Flag produced the shortest wars and fewest Battles, but the highest observed draw rate by a wide margin.
- These are screening samples (n=36 per variant, 6 per deck), not final balance evidence. Inspect the saved per-deck reports before choosing a rule.

Artifact from this run: `artifacts/pass-variants/052e9c28939d/summary.json` (local/generated artifact; not versioned by default).
