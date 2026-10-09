# Physical card cost and choice audit — 8–9 October 2026

> **Scope:** all **131** identities in `cards/cards.json` assembled with the **physical print** overlay `cards/print-overrides.json`. No changes to the native/Webgame engine. The old-cost column compares with the immediately preceding **print-only** pool, not the old unmodified executable card text. **These are tabletop design judgments, not measured win rates.**


## 9 October decision pass (supersedes earlier effect descriptions below)

**Scope:** 12 physical-card effect revisions, a physical-only Rider Attack rank
restriction, and a single controlled way to free a persistent position.
The pool remains **131 identities**. This pass **did not change printed Command
costs** or native/Webgame rules. The old four decks were subsequently replaced
by four combo-driven decks; their **new aggregate costs appear below**. The 8 October rationale is
retained as historical context where effects have since changed.

| Card | Revised decision and balancing guard |
| --- | --- |
| Every Banner Turned Toward Them | 2C now projects up to three +1 Human bonuses across its Front and one adjacent active Front; no longer a strictly worse 1C Center Must Hold |
| The Battle Turned East | 1C reveals after Rider movement, permits one further adjacent Move and grants +1 temporary Strength; positional cost if it moves Rear |
| The Archers Were Ready | 1C triggers a legal free basic Archer counterattack after an opposing Attack; consumes that Archer's once-per-Battle Attack allowance |
| The Crows Came Down | 2C Exhausts one opposing Force immediately on PLAY; later 1/BATTLE ACTION can Shake an opposing Exhausted Force in an Archer-held Front |
| No One Would Be First to Leave | 2C removes one Force's Exhaustion on PLAY; later 1/BATTLE ACTION moves up to two different friendly formations by one legal step |
| The Stores Were Taken | 1C now pressures an opposing prepared layer or an attached Bond on a Depleted Force in a Raider-held Front |
| The Field Train | 2C one-shot transport of prepared Bond/Name from own or adjacent active Front to directly-ahead formation; House of Reed retains repeatable local ACTION |
| They Knew the Ground | 1C immediately Moves one formation; Seer still bends outermost active Front adjacency without changing flanks or Attacks |
| Re-form the Line | 0C Order now chooses an adjacent friendly swap or discards a friendly Force with its layers in a Captain-held Front to regain 2C and release the slot |
| Before Sunset, the Ford Would Be Ours | 1C Narrative now reacts once/Battle to a newly set nearby Stratagem: look, then optionally Move a formation in its assigned Front |
| The Raiders Came Home Loaded | 1C immediate draw-then-discard on PLAY; retains qualifying Tactic discounts and subsequent Raider/Skirmisher movement |
| There Was No Road Back | 1C hidden Named-completion reward now chooses a two-step legal Move or returns an opposing attached Bond in the assigned Front |

The physical rulebook now requires basic **Rider** Attacks to originate from
Frontline or Middle, not Rear. This applies to a Rider-classified formation
regardless of whether Rider originates on the Force or Name; it does not narrow
other card effects. Explicit **Force discard** from Re-form the Line removes
attached Bond/Name and their markers, opening a persistent position. It does
not create generic Retreat.

**Verification:** `tools/check_physical_cost_balance.py` now contains **27
paper-state contracts** covering the earlier 15 cases plus the 12 new
decisions. They remain syntax/rules assertions rather than observed gameplay.
`tools/physical_playtest_metrics.py` accepts event logs and reports per-card
playability, utility, triggers, actions, occupancy and deck outcomes. Use the
[playtest evidence guide](physical-playtest-evidence.md); no true win-rate claims
are made without logged games or a rules-compatible simulation.

## Cost model: Command alone is not the price

There are three relevant expenses:

1. **Command payment** — visible printed Command, constrained by diminishing between-Battle recovery (12, 9, 6, 3, then 1 while surviving).
2. **Action payment** — almost every played card uses **one of two Actions per turn**. A Narrative played and then activated generally needs **two Actions**, so a 2-Command Narrative is not equivalent to a 2-Command immediate Tactic.
3. **Activation and exposure** — row, class, named/attached gate, target, a limited reveal, an occupied destination, and whether the card lasts one Battle or persists across the war. Force Strength persists but slots saturate; Battle-only bonuses do not.

Assess *early Battle with empty space*, *mid-Battle with completed formations*, *late Battle with tight Command and occupied Fronts*. A low-Command card is not automatically a good card if it consumes an Action for negligible benefit.

## Current cost distribution

| Type | Cards | Mean printed Command | Typical role |
| --- | ---: | ---: | --- |
| Force | 33 | 2.12 | Persistent Strength, Attack and position |
| Bond | 24 | 1.00 | Cost-efficient formation modifier or interaction |
| Name | 20 | 1.60 | Named completion, classes and repeating abilities |
| Hero | 11 | 3.00 | Flexible unique Force/Name mode |
| Tactic | 14 | 1.21 | Immediate hostile reaction to a board state |
| Stratagem | 11 | 1.27 | One assigned-Front secret plan; one setting Action |
| Narrative | 12 | 1.67 | Battle-only ongoing engine; activation often takes another Action |
| Order | 6 | 0.17 | Cheap, conditional friendly response |

## Ten Command-cost corrections

Costs are deliberately **not** uniformly lowered. Most revised effects keep their prior Command cost and trade a narrower condition for a stronger, distinct decision.

| Card | Previous print cost | New print cost | Why |
| --- | ---: | ---: | --- |
| The Black Pursuers | 4 | **3** | Attachment raid still requires an Exhausted target and an extra 1C ACTION |
| Iven | 4 | **3** | High-cost Name needs repeated Tactics to earn back its persistent discount |
| They Were Gathering There | 2 | **1** | Single conditional Exhaustion does not affect Strength directly |
| All Banners Forward | 2 | **1** | Only disables printed ACTION abilities on King/Captain |
| The Line Had Begun to Move | 2 | **1** | One avoidable +2 Tax should cost less than the opponent's possible payment |
| The Lines Held | 2 | **1** | Single Front transfer and +2 at Battle resolution needs an empty Frontline |
| The Center Must Hold | 2 | **1** | Temporary +1 to at most two other formations needs a King/Captain |
| The Trap Closed | 3 | **2** | Delayed two-Action raid now removes an attachment rather than +2 Strength |
| No Road Was Too Long | 4 | **3** | Big one-time geography exchange still costs three Command and activation Action |
| The King Had Given the Order | 3 | **2** | Once/Battle Bond exchange has a large two-Action setup |

## Effect replacements with a concrete purpose

| Cards | Decision gained | Limitation or opponent's response |
| --- | --- | --- |
| The First Spear | Frontline Guard protects the Force behind it | Frontline-only; requires occupied friendly Middle |
| The Iron Boars | Deplete support when a Raider enters an open breach | Frontline-only; opposing Frontline must be empty |
| The Red Duelists | Shake enemy Frontline on arrival | Frontline-only; no enemy Frontline means no surprise |
| The Crow Archers | Empowered bypasses Guard screening on next Attack | Still only one Attack per Battle; next Attack consumes Boon |
| Guarded / Endured With | Choose Guarded vs Inspired protection | Both Bonds now +0 Strength; prepared Bond PLAY cannot wait for a Force |
| No One Would Be First to Leave | Immediately remove Exhaustion; later move up to two formations | 2C; second Action only if its optional mobility is used |
| They Lived to Tell It | Remove a temporary negative marker and give Inspired | Requires an Action each time after the 1C Narrative is played |
| The Crows Came Down | Exhaust one on PLAY, then optionally Shake one exhausted enemy | 2C; Archer requirement; second Action and once-per-Battle limit |
| They Knew the Ground | Immediate Move, plus Seer bends outermost-Front adjacency | Seer required for geography effect; flanking and Attack targets unchanged |
| The Raiders Came Home Loaded | Discount qualifying Tactics, then shift a Raider/Skirmisher | 1C+Action to set up, class and target-Front gate |
| The Long March | Riders Maneuver unnamed and pay 0C | 2C Narrative plus one Action; other movement constraints still apply |
| The Wall Did Not Break | Exhausted Guards/Strongholds can Maneuver at 0C | 2C Narrative; the Named requirement remains |
| The Trap Closed | Return an attached component after a successful affliction | 2C to set, an affliction trigger, an attached target, and counterplay via Guarded |
| Watchtowers / Thornbow / Lantern | Paid global reconnaissance versus limited local reactions | No permanent free visibility of hidden Stratagems |
| Namar | One orchestration Action gives a 2C attachment discount + card | 4C Name, must become Named, once/Battle |

**Core safeguards:** The 131 identities, Hero modes, existing formation/attachment combinations, one-Front assigned hidden Stratagems, voluntary Pass, and the physical-only/native split all remain. The three new Frontline-only restrictions make good Force placement a deliberate opportunity cost.

## Current combo-deck composition and cost checks (9 October)

The four previous mechanic-themed decks were replaced with combos that
compete primarily through permanent Strength, formation completion and
protection, or attack-linked Strength/Command pressure.

| Deck | 48 cards | Force count | Printed Force Strength | Sum of all printed Command costs |
| --- | ---: | ---: | ---: | ---: |
| Banner & Blood | 48 | 16 | 58 | 78 |
| Crown of Crows | 48 | 16 | 55 | 78 |
| Oathforge | 48 | 16 | 51 | 79 |
| Blood & Spoils | 48 | 17 | 65 | 91 |

**Interpretation:** the values above are sums over all cards in a deck, not
expenditure or expected winning Strength in a game. Blood & Spoils deliberately
uses expensive high-Strength Raiders and must earn that extra Command through
affliction, attachment raids and resource transfers. Oathforge gives up some
unattached Force Strength to build larger Named stacks. Their relative win
rates are **unmeasured**. See [actual lists and signature combinations](playtest-decks.md).

## Paper-state usefulness tests

The complementary executable check `python tools/check_physical_cost_balance.py` verifies **27 defined decision situations**: first-Battle Frontline placement, gaps, screened Archers, next-Battle exhaustion, competing Boons, dual-target Archer pressure, geography changing after Front expansion, exhausted defensive Maneuvers, attachment ambushes, single-window secret plans, Command Tax, distinct reconnaissance, the King's two-Action combo, and persistent-formation row legality. These tests validate printed-cost/trigger contracts; they do **not** assert sampled games were played.

Suggested hands-on measurements for actual sessions:

- **Card activation rate:** percent of hands where each card could legally change a decision within the next two turns.
- **Conditional payoff:** actual number of Forces affected, Command gained/spent, and formations moved or recovered.
- **Deadline sensitivity:** does passing one turn earlier/later flip the value of a Narrative or hidden Stratagem?
- **Counterplay:** can the opponent close a breach, occupy a support slot, prevent a marker, or stop an attachment raid?
- **Opportunity cost:** compare playing the revised card to playing a normal Force or completing an existing formation for the same Action/Command.
- **Saturation:** by Battle III/IV count stranded Forces and whether defensive decks can still initiate useful Actions.

If any new effect proves too strong, first **raise its Command by 1 or narrow its trigger**. If a Narrative never earns back the Action to set it, replace the effect rather than repeatedly lowering its printed cost.

## Remaining deliberate risks

1. **Board saturation:** no generic Retreat; narrow Frontline placement is strategically meaningful but can increase dead Force draws once all positions are occupied.
2. **Conditional Battles:** The Seer adjacency Narrative is most unusual after Battle I, but now has an immediate Move on PLAY so its first-Battle usefulness is not entirely Seer-dependent.
3. **Unmeasured balance:** static costs and seeded opening hands cannot demonstrate win rates, underpriced combos or repeated strategic dominance. The actual win-rate test requires a runtime aligned with the physical rules or controlled tabletop games.
4. **No new keyword inflation:** Inspired and Empowered already existed in the rules; this pass finally puts them on cards.
5. **Print geometry:** the existing headless layout test reports missing frame decorations and footer placements across the whole catalogue, including unchanged cards; this is a fixture/renderer compatibility issue and is **not** a reliable pass/fail for this rebalance. Full-size text fitting remains to be visually checked after the fixture is repaired.

## Complete 131-card printed cost ledger

This ledger is the audit's full accounting scope. **Prior** means the last physical-print version. The *Status* column distinguishes changed effects from Command-only changes, while ordinary cards remain visible for follow-up evaluation.

### Forces

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| The Fifty Men | 2 | 2 | Retained |
| Seven Black Ships | 3 | 3 | Retained |
| The White Hands of Elara | 1 | 1 | Retained |
| The Red Shields | 2 | 2 | Retained |
| The Crow Archers | 2 | 2 | Effect rebalanced |
| The House of Reed | 2 | 2 | Retained |
| The Grey Riders | 3 | 3 | Retained |
| The Dust Riders | 2 | 2 | Retained |
| The Black Pursuers | 4 | 3 | Cost adjusted |
| The Red Duelists | 2 | 2 | Effect rebalanced |
| The Thornbow Hunters | 2 | 2 | Effect rebalanced |
| The Iron Boars | 3 | 3 | Effect rebalanced |
| The First Spear | 2 | 2 | Effect rebalanced |
| The Old Guard | 2 | 2 | Retained |
| The Salt-Road Reavers | 3 | 3 | Retained |
| The Late Banner | 2 | 2 | Retained |
| The Banner Singers | 1 | 1 | Retained |
| Thirty Spears | 1 | 1 | Retained |
| A Hundred Shields | 3 | 3 | Retained |
| The Vardai | 2 | 2 | Retained |
| The Aradai | 2 | 2 | Retained |
| The Ilyri | 2 | 2 | Retained |
| The Damar | 2 | 2 | Retained |
| The Serekh | 2 | 2 | Retained |
| The Relief Column | 2 | 2 | Retained |
| The Field Train | 2 | 2 | Effect rebalanced |
| The Signal Company | 2 | 2 | Retained |
| The Wolf Skirmishers | 3 | 3 | Retained |
| The Lantern Scouts | 1 | 1 | Effect rebalanced |
| The River Raiders | 3 | 3 | Retained |
| The King's Spears | 2 | 2 | Retained |
| The Salt-Road Fleet | 2 | 2 | Retained |
| The Watchtowers of Eren | 2 | 2 | Effect rebalanced |

### Bonds

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| Followed | 1 | 1 | Retained |
| Guarded | 1 | 1 | Effect rebalanced |
| Stood Fast With | 1 | 1 | Retained |
| Marched With | 1 | 1 | Retained |
| Kept Pace With | 1 | 1 | Retained |
| Covered the Withdrawal of | 1 | 1 | Retained |
| Blocked the Road for | 1 | 1 | Retained |
| Held the Line for | 1 | 1 | Retained |
| Seized the Standard of | 1 | 1 | Retained |
| Stayed Behind For | 1 | 1 | Retained |
| Swore Again To | 1 | 1 | Retained |
| Endured With | 1 | 1 | Effect rebalanced |
| Rallied Behind | 1 | 1 | Retained |
| Bought Time For | 1 | 1 | Retained |
| Trusted | 1 | 1 | Retained |
| Marched Beneath the Banner of | 1 | 1 | Retained |
| Carried the Oath of | 1 | 1 | Retained |
| Had Been Ordered Forward | 1 | 1 | Retained |
| Watched the Skies For | 1 | 1 | Retained |
| Kept the Gate For | 1 | 1 | Retained |
| Shared the Spoils With | 1 | 1 | Retained |
| Carried Messages For | 1 | 1 | Retained |
| Supported By | 1 | 1 | Retained |
| Supplied By | 1 | 1 | Retained |

### Names

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| Namar | 4 | 4 | Effect rebalanced |
| Iria | 1 | 1 | Retained |
| Oren | 2 | 2 | Retained |
| Elian | 1 | 1 | Retained |
| Teren | 1 | 1 | Retained |
| Mara | 1 | 1 | Retained |
| Asha, the Shield-Bearer | 1 | 1 | Retained |
| Edrin | 1 | 1 | Retained |
| Sela | 1 | 1 | Retained |
| Meren | 1 | 1 | Retained |
| Tala | 2 | 2 | Retained |
| Sorin | 1 | 1 | Retained |
| Iven | 4 | 3 | Cost adjusted |
| Arel | 2 | 2 | Retained |
| Torren | 1 | 1 | Retained |
| Eira | 2 | 2 | Retained |
| Corin of the High Wall | 2 | 2 | Retained |
| Lysa the Listener | 1 | 1 | Retained |
| Brannoc | 2 | 2 | Retained |
| Maelin | 2 | 2 | Retained |

### Heros

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| Avaros, the Bronze King | 3 | 3 | Retained |
| Kael, the Roadless | 3 | 3 | Retained |
| Rovan, the Gatebreaker | 4 | 4 | Retained |
| Alda, Keeper of the Ford | 2 | 2 | Retained |
| Tovan, the Quartermaster | 3 | 3 | Retained |
| Nara, Builder of Walls | 3 | 3 | Retained |
| Neris, the Ferryman | 3 | 3 | Retained |
| Veyra, Keeper of Oaths | 3 | 3 | Retained |
| Yara, the Chronicler | 3 | 3 | Retained |
| Serai, Queen of Crows | 3 | 3 | Retained |
| Doros, the Last Spear | 3 | 3 | Retained |

### Tactics

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| The Baggage Was Abandoned | 2 | 2 | Effect rebalanced |
| They Returned With Names | 2 | 2 | Retained |
| They Were Gathering There | 2 | 1 | Cost adjusted |
| The Muster Was False | 1 | 1 | Retained |
| They Had Gone Too Far | 1 | 1 | Retained |
| All Banners Forward | 2 | 1 | Cost adjusted |
| The Line Wheeled | 1 | 1 | Retained |
| They Let Them Through | 1 | 1 | Retained |
| All Reserves Forward | 2 | 2 | Retained |
| The Line Had Begun to Move | 2 | 1 | Cost adjusted |
| A Volley Before Dawn | 2 | 2 | Retained |
| The Scouts Found the Gap | 1 | 1 | Retained |
| The Stores Were Taken | 1 | 1 | Effect rebalanced |
| The Line Was Baited | 0 | 0 | Retained |

### Stratagems

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| The Ground Was Held | 1 | 1 | Retained |
| The Lines Held | 2 | 1 | Effect rebalanced |
| No Step Back | 2 | 2 | Retained |
| The Center Must Hold | 2 | 1 | Effect rebalanced |
| The Flank Was Refused | 1 | 1 | Retained |
| The Trap Closed | 3 | 2 | Effect rebalanced |
| The Battle Turned East | 1 | 1 | Effect rebalanced |
| There Was No Road Back | 1 | 1 | Effect rebalanced |
| Every Banner Turned Toward Them | 2 | 2 | Effect rebalanced |
| The Archers Were Ready | 1 | 1 | Effect rebalanced |
| The Scouts Had Warned Them | 1 | 1 | Retained |

### Narratives

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| The Long March | 2 | 2 | Effect rebalanced |
| The Wall Did Not Break | 2 | 2 | Effect rebalanced |
| The Crows Came Down | 2 | 2 | Effect rebalanced |
| Before Sunset, the Ford Would Be Ours | 1 | 1 | Effect rebalanced |
| They Lived to Tell It | 1 | 1 | Effect rebalanced |
| No Road Was Too Long | 4 | 3 | Cost adjusted |
| The Battle Had Chosen Them | 2 | 2 | Retained |
| No One Would Be First to Leave | 2 | 2 | Effect rebalanced |
| The King Had Given the Order | 3 | 2 | Cost adjusted |
| Every Bow Was Strung | 1 | 1 | Retained |
| They Knew the Ground | 1 | 1 | Effect rebalanced |
| The Raiders Came Home Loaded | 1 | 1 | Effect rebalanced |

### Orders

| Card | Prior C | Current C | Status |
| --- | ---: | ---: | --- |
| Fresh Orders | 0 | 0 | Retained |
| Catch Your Breath | 0 | 0 | Retained |
| Re-form the Line | 0 | 0 | Effect rebalanced |
| Bind the Wound | 0 | 0 | Retained |
| Send a Runner | 0 | 0 | Retained |
| Take Stock | 1 | 1 | Retained |

