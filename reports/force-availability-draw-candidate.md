# Force availability / draw redesign candidate

Status: **implemented, not simulated**. Actions credits were unavailable when this candidate was committed.

## Composition decision

The previous 30-card name-rich experiment decks contain 10 Subjects/Forces, not 12. Preserving their existing Bond/Story/Stratagem package while reaching the requested 14 Forces therefore produces a clean **34-card** candidate:

- 14 Forces
- 6 Names
- the existing tactical/support package from each corresponding 30-card deck
- opening hand 10
- exactly one Hero

The four added Forces lean toward unrestricted placement so the experiment directly addresses hands with too few battlefield pieces or only awkward Frontline/Rear pieces.

Internal engine identifiers remain `subject` / `PlaySubject` for compatibility. The experimental card text uses **Force**.

## Shared rules

- Command starts at 20, carries between Battles, +10 between Battles, cap 20.
- One operation per turn.
- Cycle disabled.
- Draw pile and discard pile persist between Battles.
- No automatic between-Battle reshuffle.
- When a draw is required with an empty draw pile, shuffle the discard pile into a new draw pile.
- First Pass is unavailable until both players have performed at least one operation, unless there is literally no other legal operation.
- First Pass gives the opponent exactly one final operation, then the Battle scores.
- The first passer starts the next Battle.
- First completion of Force + Bond + Name regains 1 Command.
- Name completion utility then resolves normally.
- Oren draws 1 card on completion instead of granting a free Cycle.
- Veiled Stories use FACE-DOWN / WHEN wording and remain local hidden traps.
- Stratagems are played face-up as ordinary paid operations and apply their Battle-wide rule immediately.
- The Bronze Teeth is a public Frontline penalty in this candidate.
- The False Muster is a public Battle rule preventing immediate Stories while active.

## Draw A — automatic

At the start of every turn: draw 1 card, then perform one operation.

The old Battle-I first-player bonus card is disabled in this variant; the first player's first-turn draw replaces it.

## Draw B — paid

No automatic draw.

**Draw** costs 1 Command, uses the operation, draws 1 card, and does not discard.

## Diagnostics implemented

The simulator now records a `human_flow` block containing:

- opening 0-Force rate;
- opening 0/1-Force rate;
- full opening Force-count distribution;
- opening Force roles and Frontline/Rear/unrestricted composition;
- mean Forces in hand;
- no-playable-Force decision rate;
- longest consecutive no-playable-Force streak;
- operation number of the first Force play;
- cards drawn per player-Battle;
- fraction of the deck accessible/seen per player-Battle;
- mean hand size through the Battle and at Pass;
- completion events per player-Battle;
- Command spent per player-Battle;
- Command actually refunded by the universal completion reward;
- early first-Pass frequency;
- final-operation margin/control swing and final-actor Battle win rate;
- reshuffles, cards recycled per reshuffle, and hand size when reshuffling.

Existing telemetry still supplies Names/Battle, Bonds/Battle, action counts, pass records, decision-space size, and per-card diagnostics.

## Strategic agent

The strategic agent now uses belief-sampled **iterative-deepening alpha-beta search** rather than greedy rollout.

For each real decision it:

1. ranks plausible root actions with the public heuristic;
2. samples several hidden opponent states through `BeliefSampler`;
3. searches both sides adversarially inside each sampled state;
4. uses alpha-beta pruning and a bounded candidate beam;
5. deepens one ply at a time until the configured depth or node budget is reached;
6. keeps the last fully completed depth if the node budget interrupts a deeper iteration;
7. averages root-action values over belief samples.

The search records mean completed depth and mean searched nodes in telemetry. The true opponent hand is never used; hidden cards come from belief samples.

## Run locally

Install/update the development environment once:

```bash
python -m pip install -e '.[dev]'
```

Optional focused rule/AI tests:

```bash
pytest -q tests/test_force_draw_candidate.py tests/test_strategic_heuristic.py
```

Fast smoke experiment:

```bash
python tools/run_force_draw_experiment.py --preset quick
```

Normal experiment — this is the default recommended comparison:

```bash
python tools/run_force_draw_experiment.py --preset deep --jobs 4
```

Strongest preset:

```bash
python tools/run_force_draw_experiment.py --preset max --jobs 4
```

Override the number of games without changing the AI preset:

```bash
python tools/run_force_draw_experiment.py --preset deep --games 50 --jobs 4
```

Run one specific cell of the matrix:

```bash
python tools/run_force_draw_experiment.py --preset deep --mode automatic --deck reference
```

Inspect the exact underlying `tools/simulate.py` commands without running them:

```bash
python tools/run_force_draw_experiment.py --preset deep --dry-run
```

Results are written under `artifacts/local-force-draw/<preset>/`:

- one raw JSON per draw-mode/deck combination;
- `summary.json` with the full comparison;
- `summary.md` with the main human-flow and AI-search metrics.

The presets are:

| Preset | Games/run | Belief samples | Max depth | Beam | Nodes/decision |
| --- | ---: | ---: | ---: | ---: | ---: |
| quick | 8 | 2 | 4 | 4 | 4,000 |
| deep | 20 | 4 | 6 | 5 | 20,000 |
| max | 20 | 6 | 8 | 6 | 60,000 |

All experiment workflows on this branch are now intended as manual fallbacks. The local runner is the primary path.


## Cython alpha-beta backend

The strategic search now has two interchangeable recursion backends:

- `cython`: compiled alpha-beta recursion with one reusable GameState scratch object per search depth;
- `python`: reference implementation with the same search semantics and the same scratch-state reuse;
- `auto`: prefer Cython when the extension compiled, otherwise fall back to Python.

The Cython path deliberately continues to call the authoritative Python GameEngine for legal actions and rule application. This keeps the experimental rules identical while removing Python recursive-call overhead and most search-state allocation. The older packed `_fast_search` engine is not used for this experiment yet because it predates Command, paid/automatic draw, final-operation Pass, completion refunds, and persistent-deck reshuffling.

Rebuild the editable install after pulling:

```bash
python -m pip install -e '.[dev]'
```

Verify that the extension imports:

```bash
python -c "import longwar._alphabeta_accel; print('Cython alpha-beta: OK')"
```

Run the parity test:

```bash
pytest -q tests/test_strategic_heuristic.py -k cython
```

Normal local experiment, preferring Cython:

```bash
python tools/run_force_draw_experiment.py --preset deep --games 50 --jobs 4 --backend cython
```

For an exact backend timing comparison, use one matrix cell and the same seed/settings:

```bash
time python tools/run_force_draw_experiment.py --preset deep --games 10 --jobs 1 --mode automatic --deck reference --backend python --output-dir artifacts/bench-python
time python tools/run_force_draw_experiment.py --preset deep --games 10 --jobs 1 --mode automatic --deck reference --backend cython --output-dir artifacts/bench-cython
```
