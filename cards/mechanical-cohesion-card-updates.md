# Two printed-card updates: recovery and counterflanking

These changes apply only to the **physical game**, through
`cards/print-overrides.json` and the printable site. The executable
`cards/cards.json`, native AI, player rulebook, deck compositions and other
129 identities have not changed.

## They Lived to Tell It — make lost-Front Exhaustion spatially relevant

**Printed Narrative ACTION:**

> Remove one temporary negative marker from a friendly Force, if any. If it was Exhaustion, you may Move its formation one adjacent legal position; otherwise give it Inspired.

- **Exhaustion removed:** regain the Force's ability to initiate ordinary
  Maneuvers and *optionally* use the printed **Move** to shift the complete
  formation one adjacent legal space. No Inspired is granted along this branch,
  even if no legal Move exists.
- **Shaken, Depleted or other temporary negative marker removed:** remove that
  marker and grant Inspired. No extra Move is provided.
- **No removable marker:** grant Inspired, as the original print-only card did.
- **Printed use limits:** the physical Narrative's ACTION remains available by
  spending an Action while the Narrative is in play (unless another effect
  restricts its use); this change does *not* silently add a once-per-Battle limit
  or an extra Action. The Narrative still ends at the end of the Battle.

The printed Move is **not an ordinary Maneuver**. It respects active Fronts,
row restrictions and legal destination occupancy; it can relocate a formation
that was Exhausted, but cannot trigger Grey Riders' post-Maneuver Attack or
discounts from The Long March.

**Distinct from No One Would Be First to Leave:** that Narrative removes
Exhaustion on PLAY and has a separate card ACTION that may Move up to two
different formations. They Lived to Tell It now ties a *single recovery
choice* directly to repositioning, but takes the Action to do so and does not
give Inspired when recovering Exhaustion.

**Sample scenario:** After losing Front 2, start Battle II with an Exhausted
Force in Middle 2 and no friendly Force in Middle 3. Spend an Action using
They Lived to Tell It to clear its Exhaustion and optionally Move the complete
formation to Middle 3. Repeat with Middle 3 occupied or Front 1 still inactive;
recovery still occurs but no illegal Move happens. Repeat with Shaken instead
of Exhaustion: remove Shaken and grant Inspired without a Move.

## The Flank Was Refused — defend the original center, reward the outer edge

**Printed hidden Stratagem:**

> At resolution, a friendly flanked Frontline Force here ignores its flank penalty. In an outer Front, it also gets +2 Strength this Battle.

- **Any assigned active Front:** if a friendly Frontline Force is **actually
  flanked** at the single simultaneous resolution eligibility check, the
  Stratagem can reveal to ignore its ordinary −1 Strength flanking penalty.
- **Outer Front 1 or 4:** the same legal response also gives that Force the
  existing +2 Strength bonus. It does not open an inactive Front or let an
  unflanked Force receive the reward.
- **Important distinction:** the Force remains **flanked** for Rider Attack
  eligibility and other effects. The Stratagem ignores the **penalty**, not
  the positional condition. It does not prevent Attacks or Shaken.
- **Timing:** the Stratagem must have been set beforehand in the appropriate
  active Front. One Stratagem may be set per player per Battle; resolution
  eligibility is fixed before simultaneous reveals.

**Sample scenario:** In Battle I, A holds Frontline 2 and B holds Frontline 3,
with A's Frontline 3 empty. A's Force in Frontline 2 is flanked, so a prepared
The Flank Was Refused in Front 2 can ignore its −1 penalty even though Front 2
is not an outer Front. In Battle III, give A a flanked Force in Frontline 1
instead: the card cancels the penalty **and** gives +2 Strength. If a friendly
Frontline 3 prevents A's Frontline 2 from being flanked, the Stratagem has no
legal resolution response there.

## What to observe in physical play

1. **Recovery as a plan:** did repositioning the recovered Force genuinely
   affect the next contested Front, or was Inspired nearly always better?
2. **Narrative differentiation:** do players choose They Lived to Tell It
   versus No One Would Be First to Leave for different reasons?
3. **Early counterflank:** can a player facing a Rider/flank threat in Battle I
   use The Flank Was Refused without merely negating the opponent's ability to
   create future flanks?
4. **Outer payoff:** does saving the single Stratagem for an outer Front remain
   appealing once both outer Fronts become active?

## Verification

Run:

```bash
python tools/check_print_cards.py
python tools/check_nonforce_battlefield_roles.py
python tools/check_full_card_coherence.py
python tools/check_physical_combo_decks.py
python tools/check_recovery_flank_cohesion.py
python tools/check_card_layout.py --surface print --require-browser
```

The targeted scenarios test selected legality and triggered effects, **not**
actual human win rates or a complete executable physical-game simulation.
