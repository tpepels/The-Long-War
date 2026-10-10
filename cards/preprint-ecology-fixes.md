# Pre-print ecology fixes: Rider exposure, scouting and defense

**Physical print pool only.** This pass changes the Banner & Blood playtest
list and two Hero Name-mode effect texts in `cards/print-overrides.json`.
No original `cards/cards.json` effects, rules, card count, or native AI
implementation are changed. The paper game remains authoritative.

## Changes and the decisions they create

### 1. A real Rider choice in a standard deck

Banner & Blood stays at 48 cards and 16 Forces. Changes by **copies**:

| Remove or reduce | Add |
| --- | --- |
| The Fifty Men: 3 -> 1 | The Vardai: 0 -> 2 |
| The Battle Had Chosen Them: 2 -> 1 | The Long March: 0 -> 2 |
| The King Had Given the Order: 2 -> 1 | |
| The Center Must Hold: 2 -> 1 | The Battle Turned East: 0 -> 2 |
| Every Banner Turned Toward Them: 2 -> 1 | |

Before: 2 Rider Forces, no Rider-specific Narrative or Rider-triggered Stratagem.
After: 4 Rider Forces, two Long Marches and two Battle Turned East plans, with
leadership and Named completion still available. Banner retains 48 cards,
31 titles, 18 singleton titles, six printed Names and three Heroes.

There are **three competing directions**, not one forced combo:

1. **Visible Rider mobility:** the Long March saves the 1 Command charged for
   *ordinary* Rider Maneuvers. It does not save their Action. Vardai's printed
   ACTION is a Move and cannot invoke a Maneuver-only payoff.
2. **Concealed position change:** Battle Turned East must be set as the single
   Stratagem this Battle and must actually see a Rider move into/out of its
   assigned Front. It can create another legal Move, including during Opening
   Orders, but does not automatically grant another Attack.
3. **Conventional formation defense:** Center Must Hold and Every Banner Turned
   remain competing alternatives to Battle Turned East. Stood Fast With protects
   *your* Frontline against flanking; it neither generates an enemy flank nor
   grants a Rider Attack.

**Counterplay:** occupy adjacent Frontlines to deny a flanked target; screen
Rear Archers with a live Guard (not a defense against a Rider Attack); use
afflictions, positioning and attachment disruption to contest the Rider's path.
A Rider's one Attack may already have been spent before its Maneuver.

The other five standard deck lists and all diagnostic deck lists are unchanged.
The dedicated Rider diagnostic deck remains valuable for testing the broader
pool, including Neris and The Flank Was Refused.

### 2. Opening Orders: tested first, no forced rule expansion

Keep **Maneuver, Commit, Strike and Hold** unchanged. A small, independently
implemented paper-board scenario check verifies:

- Commit spends 1 Command to convert a 3-3 tie to 5-3. Hold preserves the tie
  and spends nothing. Commit is a **Front-total** bonus, not a Raider's
  individual Strength for Incursion.
- A defender can use their second **Opening Maneuver** to vacate a Middle
  Guard's position. The attacker's first **Opening Strike** then reaches Rear,
  because **all Maneuvers resolve before any Strike**. Secret 1/2 numbering
  matters within the Maneuver and Strike phases, not across phases.
- Opening Moves do not gain a generic normal-turn Action or permit an exhausted
  non-exempt formation to initiate a Maneuver.
- The one-Stratagem rule makes concealment a *choice*: setting Battle Turned East
  prevents setting Center Must Hold or No Step Back that same Battle.

These are **legal/tactical model examples**, not observed player behavior and
not proof that Commit, Hold or the two-order timing is enjoyable. Before freezing
the printed rules, manually record at least 4-6 Battles, including one in which
both players could have chosen a useful alternative to Commit. Track frequency
of invalid orders and whether numbered orders change the decision. Do not add a
Commit/Hold card just to make every order explicitly named on printed cards.

### 3. Kael is a genuine tactical Scout in Name mode

Previous ACTION: inspect one opposing set Stratagem in the assigned or adjacent
Front; if none existed, spending the Action had no result.

New ACTION: inspect one opposing set Stratagem there **if any**, then optionally
Move **this formation** one legal adjacent position. This gives the Name a
strategic decision even against an opponent who sets no Stratagem.

Distinctions remain:
- Kael as Force can use an ACTION for up to two-step self movement.
- Kael as Name uses one-step self movement and can inspect a hidden plan.
- Watchtowers can inspect a plan **and filter cards**, but not reposition itself
  on that ACTION.
- Iria provides immediate inspection plus Move on PLAY; not a repeatable ACTION.
- Neris as Name may Move this or another friendly formation in its Front, but
  offers no inspection.

This can create *repeated* one-Action self Moves while Kael survives. That is
deliberate and should be observed in the opening two Battles; it is not free
movement, does not replay PLAY text, and cannot ignore row restrictions.

### 4. Protection includes a different decision, not another redirect

Asha's Name TRIGGER still **redirects** a hostile Tactic to herself *if legal*.
Alda Hero in Name mode instead may **once per Battle** grant Guarded to the
targeted ally's Force **before** an opposing Tactic resolves.

These are not interchangeable:

| Incoming effect | Asha (redirect) | Alda (Guarded) | No Step Back (hidden plan) |
| --- | --- | --- | --- |
| Shaken or Depleted affliction | Can take the effect instead if a legal target | Target's next affliction can be prevented | Prevents a qualifying Attack affliction or ignores targeted Tactic |
| Attached Bond returned to hand | May redirect only if targeting remains legal | Guarded does **not** stop layer return | Can ignore qualifying Tactic on that formation |
| No hostile Tactic is played | No trigger | No trigger | May remain concealed and be discarded |
| Opportunity cost | Name investment, valid replacement target | Unique Hero in Name mode; 1/Battle only | Consumes sole set Stratagem of that Battle |

Leave Red Shields, Serekh, Supported By and Maelin as distinct **positional**
Tactic taxes for now. They apply to different recipients and require different
rows or formation investments; mass conversion to Guarded would erase those
differences. Test their actual overlap before rewriting them.

### 5. False-friend combinations: specific verification

These are easy-to-miss constraints, not invalid cards:

- **Red Duelists + Iron Boars:** both require Frontline and cannot occupy the
  same Front's same row. The Duelists must be moved or redeployed into a
  different Front before the Boars can occupy that Frontline. Shaken conditions
  do not persist into the next Battle, so sequencing matters.
- **Grey Riders + Long March:** Long March saves ordinary Maneuver **Command**;
  Grey Riders' free Attack still needs an unused Attack, a legal flanked target,
  and Frontline/Middle origin. A printed Move is not a Maneuver.
- **Dust Riders + Long March:** both can remove the first Bonded normal Maneuver's
  Command cost; the savings **do not stack**, though the Long March helps later
  Rider Maneuvers in the same Battle.
- **The House of Reed + prepared Swore Again To:** preparing the Bond already
  resolves its PLAY branch. Attaching it later can complete a Named formation,
  but the Bond's PLAY +2 or filtering effect does **not** replay.
- **Opening Commit + Raider:** Commit increases only the entire Front's final
  Strength total. It does **not** help a Raider's strict Frontline Incursion.
- **Attack + one Stratagem:** a later attack reaction requires a Stratagem
  actually set in the Front earlier; setting an alternative plan was a competing
  decision, not an extra effect.
- **Guards in Middle:** basic Archer screening stops while Shaken/Depleted unless
  the Old Guard exception applies. Moving a Guard to Frontline exposes Rear.

## How to test the printed decks before committing to a print run

Run the following scenarios on paper. For every decision record whether a
different move/attachment/Stratagem was legal, what it cost, and whether the
opponent had a live response:

| Matchup | Board state to build | Observe |
| --- | --- | --- |
| Banner & Blood vs Crown of Crows | Battle II/III, one Rider can reach an adjacent Frontline; opponent has Middle Guard protecting Rear | Rider Attack legality, flanking, card movement versus Maneuver, Long March Command savings |
| Banner & Blood vs Crown of Crows | Assign Battle Turned East, hold Center Must Hold in hand, two Opening Maneuvers available | One-plan opportunity cost; movement trigger versus Opening phase sequencing |
| Broken Oaths vs Oathforge | Prepared Bond/Name next to a Force, opposing Raider and attachment removal | Prepared PLAY does not replay; completion timing; recovery/action trade-off |
| Blood & Spoils vs The Last Watch | Shaken target, Guarded defender, Bond attached, available Tactics | How affliction prevention differs from suppression and layer return |
| Crown of Crows vs Broken Oaths | Alda as Name and Asha on different formations; opponent plays a Tactic | Alda grants one Guarded versus Asha legal redirection |
| Broken Oaths vs any Stratagem deck | Kael as Name in an active Front, opponent chooses to set a plan or not | Does inspection plus 1-step self Move earn its Action versus a normal Maneuver? |

**Verification levels:** `tools/check_paper_ecology_scenarios.py` independently
checks selected position, Attack and Opening mechanics with simplified state;
`tools/check_physical_combo_decks.py` verifies list legality and card co-draw
availability; `tools/check_print_cards.py` verifies the print overlay.
**None** is a full rules engine or a substitute for observed physical matches.
The native/Webgame still uses the older independent executable definitions.
