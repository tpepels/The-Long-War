# Preprint editorial rulings — physical game

**Resolved 10 October 2026.** These are the adopted physical-game decisions from the editorial audit. The authoritative wording lives in `rules/rulebook.md`; the shorter `rules/player-rulebook.md` teaches the same behavior. No card costs, Strength values, deck composition, new keywords or extra timing windows were introduced. The old open-question status is superseded by this record.

| ID | Ruling | Where implemented |
| --- | --- | --- |
| **D01 — Force targeting** | A Tactic that selects a Force also targets its whole formation for Tactic protections, taxes and legal redirection. Guarded still prevents only an affliction, not an entire Tactic. | Rulebook, Special cards; player rulebook |
| **D02 — Tax lifetime** | An unconsumed Tax marker expires during Battle-end cleanup. A shorter printed deadline, such as Rovan's `before your next turn`, still applies. | Rulebook, Cleanup and Tax markers; player rulebook |
| **D03 — Cards played in a Front** | Playing a Tactic or Order counts in each Front containing an explicitly selected target or specified Front. Declare affected Fronts/targets before paying Command so applicable Taxes can be calculated. A global Narrative or other card with no selected Front does not count as played in one. Multiple applicable Taxes combine. | Rulebook, Special cards and Tax markers; player rulebook |
| **D04 — Negative markers** | Marker-removal effects remove **actual harmful markers on a Force**, such as Exhausted, Shaken and Depleted, or another marker explicitly placed there by a card. A temporary Strength penalty, ignored text, suppression or ACTION lock is not individually removable merely because it is harmful. Front Tax markers are not negative Force markers. | Rulebook, Suppression and other effects; player rulebook |
| **D05 — Here** | For a Force, Bond, Name or Hero in play, `here` means **in its Front**, never only its physical position. A Stratagem's `here` is its publicly assigned Front. `This formation`, `directly ahead` and `directly behind` are narrower terms. | Rulebook, Formations and Positions; player rulebook |
| **D06 — The Trap Closed** | Check each **actually applied** negative marker event in the assigned Front; a prevented marker does not qualify. At the marker event, the source must be your Raider/Skirmisher there or your Tactic played while one is there. The Stratagem can optionally reveal on one eligible event **once**, and is discarded after resolving; a sequence of markers does not give multiple triggers. | Rulebook, Hidden responses; clarified pronoun in printed card |
| **D10 — Prepared Names** | A prepared Name (including a Hero used as a Name) resolves PLAY when played, but cannot use ACTION, TRIGGER, REACTION or CONTINUOUS while prepared. Once attached to a Force, those effects operate under their own conditions even without a Bond; WHILE NAMED and BECOMES NAMED retain their explicit all-three-layer requirements. | Rulebook, Formations and Reference; player rulebook |

## Other editorial confirmations

- **D07 — Free basic Attacks:** An Attack permitted after a Move still requires an eligible attacker, an unused Attack and a legal target. It does not gain a second Attack or avoid screening unless card text says so. See the Reference example of The Vardai and Elian.
- **D08 — The Ground Was Held:** Eligibility and tie/one-point-deficit branch are checked against the provisional Front **before** simultaneous reveals. Its tie-win applies only if still tied afterward; a newly produced tie does not open another window.
- **D09 — Classifications:** Arel/Avaros-style choices name one classification once, then grant the bonus once to each qualifying formation. Classifications can come from the Force or its attached Name.
- **D11 — No eligible PLAY target:** The existing rule stands: play a legal card as normal, and any PLAY instruction with no eligible target simply has no effect. The former D11 audit entry contained only a heading; this confirmation does not create a new restriction.
- **Printed brevity:** Shared rules are written here and in the rulebooks rather than repeated as icons or exceptions on every card. The Trap Closed received only a referent clarification, not an extra timing label.

## Table examples for checking these rulings

1. **Protecting a Force from a Tactic:** A Volley Before Dawn chooses the Force in a Frontline Red Shields formation; the Tactic also targets the formation. Calculate the applicable Tactic tax before paying. Guarded may prevent its Shaken affliction, but is not blanket Tactic immunity.
2. **Tax and card location:** The Line Had Begun to Move puts a Tax on Front 2. A Tactic selecting an opposing Force in Front 2 is taxed even though the Tactic is discarded. A global Narrative with no selected Front is not taxed. If the Tax was not consumed, remove it at Battle end.
3. **Recovery:** They Lived to Tell It may remove Exhaustion, Shaken or Depleted on a friendly Force, but not a bare `ignore Name text this Battle` restriction or an unmarked −Strength effect. Removing Exhaustion offers its printed optional Move; other cases grant Inspired.
4. **Prepared Name:** A prepared Asha is face-up and cannot redirect a Tactic. After it attaches to a Force it may use its TRIGGER when eligible; it gains BECOMES NAMED only if a Bond also completes the formation.
5. **Hidden trigger:** One Tactic gives the same opposing Force both Exhausted and Shaken in order. If the first affliction is prevented, the hidden Trap cannot reveal from that first marker; it can reveal on the second actual marker only if the assigned-Front Raider/Skirmisher requirement is met. It cannot resolve again afterward.

## Scope and next checks

The rulings are for the **physical printed game**. `cards/cards.json` still defines the older executable runtime and was **not rewritten** in this rulebook clarification. The physical web catalogue uses `cards/print-overrides.json`. Engine behavior needs separate parity work; these rulebook assertions do not constitute evidence that the engine already implements them.
