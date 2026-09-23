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

## Deferred execution

`.github/workflows/force-availability-draw-comparison.yml` is **manual-only** (`workflow_dispatch`). It is intentionally not push-triggered, so this implementation commit does not request an Actions run. When credits are available, run that workflow to compare A and B independently across Reference, Avaros, Mara and Sera.
