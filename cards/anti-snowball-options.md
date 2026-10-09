# Lost-Front Exhaustion and snowball prevention — design options

**Status: proposals for the next physical playtest. None of these is a rules change yet.** The canonical print-only rulebook continues to apply until a candidate is adopted explicitly.

## Why the current rule snowballs

The current rulebook gives **−1 Command per lost Front**, checked for Collapse before recovery. Then **every unprotected Force** in the lost Front receives Exhaustion for the **next Battle**. Since Phase 2, that Exhaustion also imposes **−1 Strength per Force**, as well as restricting Maneuver. The cards and their positions persist.

Therefore a player who loses a Front with three surviving unprotected Forces can start the next Battle **3 Strength behind** the exact same board position that just lost, in addition to the Command loss. If they lose again, they may receive fresh Exhaustion again after the previous tokens clear. A player already ahead can therefore become more likely to win the same contested Front again — the feedback loop is not hypothetical in its *direction*, although its match-level magnitude is not measured.

The high early Command recovery (12 then 9, subject to cap 20) often restores spent Command. That may soften early economic collapse but does not remove the Strength penalty; therefore simply increasing recovery is not a reliable answer.

## Recommended candidate: one Exhausted defender per lost Front

Change **only defeat-caused Exhaustion**:

> **At Battle end, for each Front you lost, choose one of your Forces in that Front. It becomes Exhausted for the next Battle. Guarded may prevent this as usual. If you have no Force in that Front, no Exhaustion is applied.**

Keep all other rules unchanged:
- Losing the Front still costs 1 Command; Collapse still happens before recovery.
- Exhaustion inflicted by an Archer, Tactic or other effect during Battle still applies immediately and gives −1 Strength until removed or cleaned up.
- Old Exhaustion clears before the new loss-based token is placed.
- A Force cannot carry more than one Exhaustion.
- The loser selects the Force. Guarded can prevent that selected Exhaustion and is consumed under the existing protection rules. Do **not** force the player to pick an unprotected Force instead: choosing a protected defender is legitimate defensive preparation.
- Only one Force per lost Front is selected, not one per rank. There is no new marker or keyword.

This preserves a visible scar, meaningful Healer and Guarded counterplay, and the narrative of a lost Front — but caps loss-based next-Battle Strength damage at **−1 per lost Front** rather than up to **−3** from the three surviving Force positions.

## Controlled alternatives

| Variant | After losing one Front with 3 unprotected Forces | Design consequence |
| --- | --- | --- |
| **A. Current** | All three Exhausted, **−3 next-Battle Strength** | Strongest attrition / greatest repeat-loss snowball |
| **B. Recommended** | Loser chooses one Exhausted, **−1 next-Battle Strength** | Persistent wound; smaller comeback penalty, more agency |
| **C. Command-only defeat** | No defeat Exhaustion; only −1 Command | Least snowball from lost-Front Strength; reduces Guarded/Healer relevance |
| **D. First defeat only, recover afterward** | All three Exhausted for next Battle but cannot recur on same Front consecutively | Larger memory burden; timing and repeat-loss exceptions |

Variant B is the simplest targeted change. Variant C is the strongest anti-snowball fallback if even a one-Force penalty proves too punishing. Variant D requires tracking which Front was previously lost, adding complexity for uncertain value. Changing the *global* −1 Exhausted penalty is less desirable because Archer Attacks and recovery would revert to being weak.

## One concrete trial

Prepare matching Fronts before Battle II:

- Both players have three Forces totaling 11 printed Strength across the ranks and no other bonuses or conditions.
- Player A lost that Front in Battle I; B did not.
- Under A, A's surviving Force line contributes **8** instead of 11.
- Under B, A contributes **10** instead of 11.
- Under C, A contributes **11** instead of 11.
- Now replay with Guarded on one of A's Forces; test A/B/C with the same hands and card order.

Track the number of lost Fronts repeated in the next Battle, comeback rate after losing Battle I, Command trajectories, use of healing and Guarded, and average **effective** Strength penalty (many already-0 Strength Forces may suffer less than a nominal −1).

## Decision criterion

Adopt the lightest defeat penalty that still leaves losing a Front consequential without creating an effectively foregone next Battle. In particular, if the same side wins a Front again almost automatically without committing more cards or Command, **Variant A has failed** the tactical-agency test. Do not declare Variant B balanced from static examples: it needs mirrored physical games or a physical-rules-compatible engine.
