# The Long War — physical rules and card reconciliation plan

**Status: design proposal only.** No rules, cards, reference sheets or engine code are changed by this plan. Based on the 131-card print audit (`cards/rulebook-comprehension-audit.md`), the approved 16 print-only sidegrades (`cards/print-overrides.json`), and the October 6–8 history of lost-Front Exhaustion.

## Guiding tests

1. Preserve positional pressure, persistence, distinctive combinations and meaningful counterplay.
2. Teach shared rules once. Do not embed universal mechanics in individual cards or reinstate retired shorthand.
3. Avoid new statuses/markers unless required. Prefer one visible state over hidden bookkeeping.
4. Print version first; engine/Webgame remains untouched and may lag.
5. Preserve 131 card identities, existing basic Attack types, Guard screening, 4 Front × 3 row battlefield, 2-Action turns, Command economy and physical Force→Bond→Name stack.

## Phase 0 — settle canonical decisions before rewriting prose

### Lost Front → Exhaustion (high priority)

**History**: on 6 Oct, a lost Front Exhausted all its Forces (maximum one token each), denied their initiating Maneuver and persisted across Battles. Commit `dda7b7d` implemented this. On 8 Oct commit `f9bc217` deliberately removed lost-Front Exhaustion from rulebook while adding Shaken, Depleted and an all-temporary-afflictions design. `web/playmat.html` still says lost Fronts Exhaust and the marker persists. The deletion was a design simplification, not a technical necessity.

**Preferred print-playtest compromise** (must be explicitly approved as a rule, not silently applied):
- Finish Battle *N*, compare Fronts and record losses. Resolve any before/after-score effects, assess lost-Front Command and Collapse.
- Clear **old** temporary afflictions and Boons, including Exhaustion already present during the Battle.
- **Then give each Force in every lost Front one Exhaustion token**, maximum one; it starts Battle *N+1* Exhausted and normally clears at the end of that Battle. It may be removed sooner by a recovery card. If it loses its Front again in Battle *N+1*, a new token is placed after that Battle's cleanup.
- Exhausted blocks only initiating Maneuvers; Forces still contribute Strength and can Attack/use abilities. Explicit Move effects may reposition them. Preserve printed exceptions such as The Grey Riders, Trusted, Cover the Withdrawal, The Relief Column.
- No Retreat/discard of the defeated Force, no automatic flanking Exhaustion.

**Tradeoff**: loss has a real next-Battle consequence, but armies do not accumulate permanent mobility lockouts. The alternative is the exact Oct 6 indefinite-until-recovered Exhaustion; compare both in physical playtests before committing. Whichever variant wins must be described identically in rulebook, playmat and condition tracker.

### Other decisions to fix before copy editing

- **Narratives:** all 12 printed Narratives have `duration: this_battle`, with CONTINUOUS or ACTION effects; none is marked Ongoing. Proposed baseline: all remain face-up until this Battle ends, then discard. The current rulebook says max 2 *Ongoing Narratives* while earlier physical design recorded max 4 Narratives. Choose a single cap deliberately; 4 preserves more multi-Narrative setups, 2 improves simplicity. Test both; never leave an invisible subtype.
- **Classifications:** propose *formation union*: a Force with an attached Name gains the classifications on that Name for targeting/support and intrinsic basic Attack eligibility (but each Force gets only **one Attack per Battle**, even if several classes qualify). An unattached prepared Name never Attacks. If this is too powerful, limit actual intrinsic Attacks to Force classes explicitly—still define it once.
- **Pass deadlock:** cycling 2→1 with a drawn card each turn can remain legal forever with no playable cards, so the required Pass never occurs. Preferred small fix to test: **cycle once per Battle per player**, visible spent marker, so eventually the player runs out of legal Actions and must Pass; retain no voluntary Pass. Check whether ordinary play still allows unreasonably prolonged voluntary zero-Action turns.
- **Strength:** a formation's Strength is Force Strength + attached Bond and Name modifiers (including Hero-as-Name), plus active changes, minimum 0 per formation; prepared layers contribute zero. Sum formation Strength across all three ranks of the same Front, then compare. A named Hero counts once as a formation for any overlap between classifications/categories.
- **Stratagem association:** a face-down Stratagem sits in the public separate area. Choose/declare Front only if its printed text requires one; the chosen Front is public, identity hidden. Clarify the “this Front” on The Lines Held and how The Scouts Had Warned Them interacts with Front-chosen versus Front-agnostic Stratagems.

## Phase 1 — fix the core rules and printed reference together

- Write the outcome/condition sequence explicitly, including at what moment old markers clear and lost-Front Exhaustion is applied.
- Correct `web/playmat.html` Front-loss paragraph and Between-Battles box. Remove obsolete assertion that Exhaustion persists indefinitely if the one-Battle compromise is chosen.
- Make the marker sheet and `web/playtest-kit.js` mechanics sheet agree. No extra token type unless physical testing demonstrates a need.
- Correct all force/attachment-removal and preparation rules to account for shifts without implying Retreat.
- Centralize numeric constants and printed cap information in one authoritative rulebook plus reference, not a patchwork of contrary documents.

**Gate:** simulate by hand a Front lost with Force in Front/Middle/Rear, repeated loss, tie, recovered exhausted Force, Shaken/Depleted/Guarded, and card-enabled Move of an Exhausted Force.

## Phase 2 — establish common card grammar

Give beginners one small table:
- **PLAY:** resolves once when played, including a component played prepared; conditions checked at the time specified.
- **BECOMES NAMED:** when Force+Bond+Name completes; never again merely from a Battle reset.
- **ACTION:** a legal turn Action, in addition to playing, Maneuvering, Attacking or cycling; any printed Command cost paid.
- **ATTACK:** modifies a Force's existing once-per-Battle Attack, not a second free Attack.
- **FRONT/MIDDLE/REAR/BONDED/WHILE NAMED/CONTINUOUS:** effects remain active only while conditions hold and their card is in play.
- **HIDDEN/REVEAL:** Stratagem trigger; explain the pre-Strength and tie-result windows without allowing post-outcome surprises after the result is final.
- **REACTION/TRIGGER:** resolve when stated; no reaction stack; used markers for limited effects.

Also define **target legality, moving versus Maneuvering versus swapping, suppression, front ownership, timing of simultaneous PLAY and BECOMES NAMED effects**, and whether prior PLAY effects can ever be undone (recommended: no retroactive undo). Use Swore Again To as a completion-and-free-Maneuver example and They Returned With Names as a suppression example.

**Gate:** all printed effects can be mapped to one timing rule, and “this Front” has a unique answer wherever printed.

## Phase 3 — rewrite the rulebook in a learner-friendly order

1. Opening story + victory objective, growing Fronts, Command risk (retain current appealing introduction).
2. Battlefield and **worked Force → Bond → Name stack**, visible 10.5-mm strips, prepared cards, +Strength calculation and occupied slots.
3. Setup, then **all five Action types** on a normal turn: play, use ACTION ability, Maneuver, Attack, cycle; short two-Action example.
4. Movement and placement; the distinction between Move, Maneuver and Swap; row restrictions.
5. Attacks and screening; **only then** introduce Exhausted, Shaken, Depleted and Guarded/Inspired/Empowered.
6. Special cards: one-shot Tactic/Order; face-up Battle Narrative; face-down Stratagem; two-mode Hero.
7. End of Battle: Pass, two closing turns, Strength settlement, Battle-end effects, Command loss/Collapse, status cleanup, newly lost-Front Exhaustion, refill/Front expansion.
8. Reference appendix: timing table, uncommon suppression/targeting, simultaneous effects, glossary and deck construction.

Use flowing explanatory prose with short examples. Retain numbered lists/tables only for genuine procedures, not as the primary voice of the manual. Introduce a concept just before its first necessary use.

**Gate:** a new player can finish an example Battle without paging into the appendix for basic Actions, Strength, card attachment, combat, Narratives or Stratagems.

## Phase 4 — harmonize card faces; avoid a wholesale 131-card rewrite

- **The Lines Held:** explicitly associate the face-down card with a chosen Front if required.
- **The Scouts Had Warned Them:** define whether it triggers only against Stratagems assigned to a Front; avoid a technically unusable window.
- **The Ground Was Held:** describe the tie-intervention timing with a clear comparison-window rule.
- **Swore Again To:** resolve completion timing and free Maneuver order alongside Name PLAY / BECOMES NAMED abilities.
- **The Battle Had Chosen Them:** specify no double +1 if the same Formation satisfies Hero and Named.
- **The Crow Archers:** explicit rule that ATTACK modifies normal basic Attack and once-per-Battle limit.
- **Guarded (Bond) versus Guarded (Boon):** preserve artwork but distinguish mechanically in rules/visualization, consider renaming the Bond only if genuine table confusion is observed.
- Remove irrelevant printed Narrative forms if they are not on card faces; do not invent seven new types solely because the old rulebook mentions them.
- Keep new PLAY effects on buried Bonds/Forces; verify every ongoing Force/Bond rule is fully actionable from its exposed strip.

**Gate:** all 131 cards can be read without ad hoc rulings. Every exception is explicit; shared semantics appear only in rulebook.

## Phase 5 — update every supporting surface

- Print-only sources first: `rules/rulebook.md`, `web/playmat.html`, `web/tokens.html`, physical `web/playtest-kit.js` reference; `cards/print-overrides.json` for genuinely needed textual exceptions.
- Update `cards/mechanics.md`, `cards/combat-reference.md`, physical glossary and deck descriptions (`MOBILE`, `TIRELESS` obsolete).
- `cards/catalogue.md` currently describes **native** cards, not physical-print overrides; ensure physical player does not mistake it for the printed catalogue. Include a straightforward current-print card index.
- Update diagrams and one worked two-player Battle example; no new illustration required.
- **No engine, AI, native schema or Webgame mechanics edits** in this pass.

## Phase 6 — structured table playtests (protect fun)

Try at least two decks representing maneuver, breach/attack, formation-building, and counterplay. Log setup/use/counter frequency rather than merely recording winner:
- Lost Front → Exhausted reserves next Battle; can Move effects/Healers rescue them? Does being Exhausted matter without entirely trapping the army? Compare **until removed** vs **next-Battle only** over 3–5 Battles.
- Named completion burst (Swore Again To + relevant Names): can one move too many? Does the opponent get any meaningful response?
- Raider opening + Wolf Skirmishers / The Line Was Baited; Archer targeting and Guard screening.
- Guarded, Inspired, Empowered, Shaken/Depleted interactions; does a defense prevent too much?
- Hidden Strats: chosen Front remains public; can scouts counter hidden cards; is information meaningful?
- Two versus four Narratives: do extra slots unlock enjoyable combos or create an unreadable passive modifier board?
- Empty-hand/no-legal-cards Pass and cycling. Check the Battle always reaches resolution.
- Physical stack scan: can you play without lifting or memorizing buried ongoing effects?

**Gate:** no recurring deadlocks, no unresolved rule questions in tracked scenarios, no recurrent involuntary skipping of interesting Actions, no extra status memory required.

## Phase 7 — approve canonical print baseline

- Lock the selected mechanics in the rulebook; reconcile every physically printed card and Reference sheet.
- Verify 131 IDs unchanged, legal 48-card sample decks, printed timing consistency and 10.5 mm exposed edge.
- Run nonblocking static print checks and a Chromium/PDF physical layout check when available; inspect stacked samples manually.
- Merge docs/card/print revisions only after choices are approved. Keep engine/Webgame explicitly out of scope, with a later *separate* parity task.
- Preserve a change log explaining why the lost-Front rule was selected and how it differs from the Oct 6 and Oct 8 revisions.

## Scope lock

This proposal does not itself change a card, rule or engine file. The design choices with true rule/balance impact (lost-Front duration, Narrative cap, classification-based Attacks, cycling limit, Stratagem Front binding) must be reviewed as a connected set before merely polishing wording.
