# False-friend interactions: final pre-print disposition

These are physical paper-card rules and print overrides, not the older native game engine. **One printed ability is adjusted; thirteen pairings remain intentionally restricted.** Do not normalize Move to Maneuver, multiply zero-Command discounts, replay PLAY, or set multiple Stratagems per Battle.

The classification **Fixed** means a printed card was revised. **Keep** means the existing interaction is a deliberate timing, positioning, category or resource choice. The targeted checks in tools/check_print_false_friends.py examine simplified paper states and exact effect contracts; they are not balance or human playtest evidence.

## All fourteen decisions

| Pair | Decision | Reason |
| --- | --- | --- |
| The Red Duelists / The Iron Boars | **Keep** | Frontline-only Forces compete for the same position and both apply Shaken (which does not stack). Move Duelists away if sequential deployment is wanted; there is no automatic payoff for chaining them. |
| The Grey Riders / Kept Pace With | **Keep** | Kept Pace With grants Move, not Maneuver; Grey Riders' optional post-Maneuver Attack must not trigger. |
| The Grey Riders / No One Would Be First to Leave | **Keep** | The Narrative's ACTION moves formations; it does not grant Maneuvers. Grey Riders' post-Maneuver Attack does not trigger. |
| The Dust Riders / The Long March | **Keep** | Dust Riders' first Bonded normal Maneuver and The Long March both save its one Command; cost cannot go below zero. A printed ACTION Move is not a Maneuver. |
| Had Been Ordered Forward / The Long March | **Keep** | Opening Maneuvers are already free of Command. Long March does not further discount them; the Bond still adds one legal Move. |
| Swore Again To / The House of Reed | **Keep** | PLAY occurs when the Bond is prepared. House of Reed moving it into an existing Force can complete Named but never replays PLAY +2. |
| Every Bow Was Strung / The Crow Archers | **Keep** | Crow Archers extend ordinary Archer targeting to Middle only while opposing Frontline is empty. Every Bow Was Strung permits a Bonded Archer's Opening Strike to target Middle even when occupied. |
| The Line Was Baited / The Trap Closed | **Fixed** | The Line Was Baited is a Tactic, not the Skirmisher's own marker source. The Trap Closed now expressly includes a Tactic played while its controller has a Raider/Skirmisher in the assigned Front. |
| The King Had Given the Order / BECOMES NAMED (mechanic) | **Keep** | Swapping Bonds between already-Named formations preserves their Named state, so no completion trigger occurs. |
| They Let Them Through / Iven | **Keep** | The Tactic disables formation ACTION abilities and can remove Name Strength, not CONTINUOUS text. Iven's Tactic discount persists. |
| The Ground Was Held / The Battle Had Chosen Them | **Keep** | Continuous +1 Named Strength is included in provisional scoring before Stratagem eligibility. It can turn a tie into a lead and eliminate the tie branch. |
| No Step Back / The Wall Did Not Break | **Keep** | Guarded prevents one affliction; No Step Back can prevent an Attack affliction or ignore a qualifying Tactic. Its reveal is optional, and spending both against one marker is usually wasteful. |
| The Lines Held / The Center Must Hold | **Keep** | Only one Stratagem card may be set per player each Battle; the same player cannot combine these reveals. |
| The Crows Came Down / The Archers Were Ready | **Keep** | The Narrative ACTION gives Shaken to an Exhausted enemy without using the Archer's basic Attack. A counterattack via a pre-set Stratagem still needs a legal unused Archer Attack and an opponent's Attack trigger. |

## One justified printed change: The Trap Closed

**The Trap Closed (2 Command, hidden Stratagem)** now reads:

> After your Raider or Skirmisher, or a Tactic you play while one is here, gives an opposing Force here a negative marker, return its Bond or Name to its owner's hand.

The Line Was Baited is a **Tactic**, not an Attack by the Skirmisher that enables it. Previously that Tactic could not trigger The Trap Closed. Now a Tactic can trigger it if a friendly Raider or Skirmisher is present in the assigned Front when the negative marker is applied. The one-Stratagem limit, marker requirement, Front restriction and attachment availability still matter.

### Reproducible play sequence

1. Place a friendly Skirmisher and an opposing Middle Force with an attached Bond in one active Front. Leave the opposing Rear position empty.
2. Set The Trap Closed face-down assigned to that Front, using your single Stratagem allowance for the Battle.
3. Play The Line Was Baited against the opposing Middle Force. It moves one row into the legal empty Rear, and receives Depleted as an immediate Tactic effect.
4. Reveal The Trap Closed after that marker is applied. Return the affected enemy's Bond or Name to its owner's hand. Neither the Tactic nor the trap is a second Attack.
5. **Blocked variant:** occupy the opposing Rear beforehand. The Tactic cannot move the Middle Force; it gives no Depleted marker, so the trap does not trigger.
6. **No-class variant:** remove the friendly Skirmisher (and any Raider). The Tactic's class condition and therefore the trap's added route fail.

### Why thirteen other pairings stay unchanged

- **Frontline competition:** Red Duelists and Iron Boars are two different Frontline deployments that both cause Shaken, and Shaken never stacks. Requiring positional sequencing is meaningful; inventing a forced combo would erase that choice.
- **Movement vocabulary:** Kept Pace With and No One Would Be First to Leave grant Move, not Maneuver. Grey Riders' post-Maneuver Attack must not automatically activate from every card Move.
- **Zero-Command overlap:** Dust Riders and Long March both save the first Bonded ordinary Maneuver's 1 Command, but Long March still supports later Maneuvers and other Riders. Opening Maneuvers already cost zero; Had Been Ordered Forward instead adds an extra Move.
- **Preparation timing:** Swore Again To's PLAY text does not replay when House of Reed later attaches a prepared Bond. Direct formation completion and early preparation remain different decisions.
- **Archer targeting:** Every Bow Was Strung extends a Bonded Opening Strike to opposing Middle even with an occupied opposing Frontline. Crow Archers normally require an empty opposing Frontline for their own Middle extension.
- **Attachment vs completion:** Exchanging Bonds between two continuously Named Formations changes ongoing effects, but does not retrigger their BECOMES NAMED text.
- **Suppression specificity:** They Let Them Through locks ACTION abilities, not Iven's CONTINUOUS Tactic discount. Separate suppression cards can attack that category.
- **Reveal conditions:** The Ground Was Held uses provisional Strength including Narrative bonuses, so The Battle Had Chosen Them might remove tie eligibility. The Lines Held and The Center Must Hold are alternative Stratagems under the one-plan limit.
- **Protection distinction:** No Step Back may be unnecessary for a single affliction already stopped by Guarded; it can instead be saved for a later or broader Tactic response.
- **Attack tracking:** The Crows Came Down uses a Narrative ACTION, while The Archers Were Ready uses a previously set Stratagem and an unused legal Archer Attack. Those conditions must be checked separately.

## Verification and scope

- The fourteen pairings are recorded in cards/false-friend-decisions.json; tools/check_print_false_friends.py has a matching set of targeted scenario and text-contract checks.
- The revision affects physical print-overrides only. It does not change core rulebook semantics, card count, Hero costs, other card abilities, deck composition, or native/AI gameplay.
- Print and design checks are advisory so they cannot block iterative development. They are not evidence of real win rates or of how often the conditions arise.

**Recommended manual proof before bulk printing:** play Blood & Spoils against a deck with prepared or attached Bonds, set The Trap Closed before using The Line Was Baited, and check one successful and one blocked rearward displacement. Then check both a mistaken Move-as-Maneuver reaction and a planned one-Stratagem choice.
