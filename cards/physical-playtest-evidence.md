# Physical playtest evidence (131-card print pool)

The printable card set is **not** the current native/Webgame card set. Do not
derive physical card win rates from existing Webgame matches. Collect gameplay
from the physical rules or first implement that ruleset in a dedicated runtime.

## Record JSONL events

Write one JSON object per line in a local `playtests.jsonl` file. Do not commit
real player-identifiable data. The following are **schema examples, not match results**:

```jsonl
{"kind":"opportunity","game_id":"sample-01","player":"A","battle":2,"turn":3,"card_id":"the-crows-came-down","playable":true,"useful":false}
{"kind":"play","card_id":"the-crows-came-down","effect_triggered":true,"command_spent":2,"actions_spent":1,"formations_moved":0,"markers_changed":1,"fronts_flipped":0}
{"kind":"turn","battle":4,"active_positions":12,"occupied_positions":12,"stranded_forces":1}
{"kind":"result","game_id":"sample-01","deck_a":"Banner & Blood","deck_b":"Crown of Crows","winner":"A"}
```

- **opportunity:** one record per card title, player and normal turn when the
  card was observed in hand. `playable` means at least one legal play existed
  within that turn. `useful` means at least one play was judged meaningfully
  better than passing the Action or cycling; log the judgment consistently.
  Do not report an unobserved opportunity.
- **play:** record each play, including cards with no effect. `effect_triggered`
  indicates whether at least one conditional effect actually did something,
  rather than only whether the card entered play. `actions_spent` includes
  the play Action; count later ACTION uses in separate `play` observations
  only if using that convention consistently, or sum them with the original
  event. This is a *manual observation* metric, not rules adjudication.
  `fronts_flipped` records Front outcomes known to have changed because of
  the card; leave 0 when uncertain. Numeric effect fields default to 0.
- **turn:** each player's normal turn; `active_positions` on one player's
  side is 6, 9, or 12. Count occupied Force slots and friendly Forces in hand
  unable to enter due to occupancy. Record both players' turns separately.
- **result:** once per completed game, label the two decks and winner `A`,
  `B` or `draw`. Use distinct `game_id` per match. Mirrored pairings
  should swap decks and starting positions; capture match IDs consistently.

## Generate the report

```bash
python tools/physical_playtest_metrics.py --self-test
python tools/physical_playtest_metrics.py playtests.jsonl
python tools/physical_playtest_metrics.py playtests.jsonl --format json > playtests-summary.json
```

The report shows per-card playable/useful opportunity rates, conditional effect
trigger rates, average Command/Action costs and effect counts; by-deck game
scores; matchup counts; and late-battle full-occupancy/stranded-Force rates.

Diagnostic flags require a minimum sample (10 card opportunities or plays,
10 late turns, 30 games per deck). They are **investigation prompts, not
balance proofs**. In particular, manual `useful` judgments and inferred
`fronts_flipped` are subjective; scored game outcomes depend on deck
selection, player experience and opening-hand luck.

## Recommended controlled sequence

1. Compare **Every Banner Turned Toward Them** with **The Center Must Hold**
   in identical board states; record whether the extra Front matters.
2. Run Battle II and IV test hands for **The Field Train**, **The Stores Were
   Taken**, and **Re-form the Line**. Count Field Train's saved attachment
   Action and full Command paid, plus stranded Forces and actual
   sacrifices (Strength lost and future deployment enabled).
3. Test Riders in Rear versus Middle/Frontline, especially with **The Long
   March**, and counterattacks with **The Archers Were Ready**. Record each
   legal target and Attack marker.
4. Compare the four published 48-card decks with mirrored deals, both starting
   players, and more than one opponent archetype. Record full game results,
   not just opening-hand Command affordability.

Do not tune numerical card costs based on the analyzer's synthetic self-test.
No automated game-balance evidence exists until real matches or a physical
rules-compatible simulation are supplied.

## Conditions and preparation: Phase 2/3 playtest measurements

Record the following alongside ordinary card plays and game results:

- The **before/after Front Strength** for each Exhausted or Depleted effect.
  An Exhausted Force contributes −1 Strength and a Depleted Force another −1;
  when combined with Shaken (−2), the penalty can be −4 before flanking.
- Whether a **Guarded** prevention or condition removal actually changed the
  Front winner, rather than merely avoiding a marker.
- **Lost-Front follow-up:** for each lost Front in Battle N, record the **one Force selected by its losing player**, whether Guarded prevented its Exhaustion, and whether the unprevented −1 Strength or Maneuver restriction changed a result in Battle N+1. Note repeat losses and the case where no friendly Force survives.
- **Baggage/Crows overpressure:** both may impose Exhausted and Shaken for a
  potential combined −3 Strength. Record how often this is achieved and
  whether that single threat forces too much Command or protection.
- **Prepared layer effectiveness:** count Bonds/Names played without a Force,
  how often their immediate PLAY effect mattered, how many were later
  attached, and how often House of Reed produced a Named completion reward.
  Track Field Train separately: no-extra-Action Bond/Name **plays from hand**,
  Command still paid, and actual Guarded protection of a completed formation.
  Record instances where preparation cost more Actions than direct attachment.
- **Named-completion diversity:** count completed formations and whether a
  +2 temporary Strength or Guarded reward actually altered a Front.
  Distinguish stable formation Strength from Battle-only spikes.

Use the manual scenarios in
[physical-rule-playtest-scenarios.md](physical-rule-playtest-scenarios.md) to
catch timing errors. The existing JSONL analyzer does **not** automatically
infer which card caused a Front to change hands: this requires observed logs
or a future physical rules-compatible simulator.

## Phase 4–5 experiments: hidden plans and combo reliability

- **Stratagem activation:** for each set plan log whether its printed
  trigger occurred, whether its controller could legally reveal it, whether
  it was actually revealed, and whether it changed an eventual Front winner.
  An unrevealed plan is **not automatically useless** if its credible threat
  influenced an opponent, but record that separately as qualitative evidence.
- **Single-window result flips:** distinguish initial ties, initial one-point
  deficits, and ties created *only after another reveal*. The latter must
  not activate Ground Was Held retroactively.
- **Narrative efficiency:** record the immediate PLAY effect, any separately
  paid ACTION, total Command/Actions spent, and effective Strength or
  protective advantage. Include No Road Was Too Long's full-column
  exchange as one PLAY Action.
- **Combo assembly:** use the enabler/payoff sets in
  [playtest-decks.json](playtest-decks.json) for consistent category naming.
  Measure *cards seen*, *both categories actually useful*, *legal combo
  actions*, and *Front results changed*. Do not compare observed activation
  rates directly to the hypergeometric draw baselines as if they measured
  the same event.
- **Diagnostic coverage:** three 48-card lists in
  [mechanic-coverage-decks.json](mechanic-coverage-decks.json)
  test Rider/flank, Scout/Seer/secret plans, and prepared/full-Front
  exchange separately from the four main decks.
- **32–36 to 10–14 singleton reduction:** verify whether having more
  repeated enablers actually increases the number of meaningful decisions.
  More consistency does not by itself imply greater fun or healthy balance.

Test the unusual effects against active-Front schedules and rank restrictions,
with mirrored turns. The static contracts and probability checker do **not**
provide victory probabilities or demonstrated playtest win rates.

## Tactical-breakthrough observation sheet

For each legal Raider incursion opportunity, record the Raider's **current**
Strength, opposing Frontline formation's current Strength (or empty), and
the target's rank. Count threatened targets at 4 vs 5 before Shaken, 4 vs
3 afterward, and 4 vs 4 ties. Track whether a Raid consumes an ordinary
Attack, changes a Front's winner, or merely spends an Action for no swing.

For Archer Attacks, log successful **Shaken** Rear targets and whether a
Guard screened them. Track combined Move/Maneuver+Attack Actions granted by
**Grey Riders**, **The Vardai**, or **The Damar** separately; none are
universal movement rules. If one free Attack creates several effects,
check its once-per-Battle use and whether the response was comprehensible
without consulting the reference.

For both players, compare Battle I losses and subsequent Battle II/III
front reversals. An incursion should create immediate tactical pressure,
**not** compound Command loss or destroy a persistent Force.
