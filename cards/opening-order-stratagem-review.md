# Opening Orders, one Stratagem and 131-card coherence

**Physical paper game | 9 October 2026 | current design audit**

## The simplified shared rules

- **Every formation may Maneuver**, whether it is Named or not: one Action and one Command for one legal step or legal friendly swap. An Exhausted Force still cannot initiate unless a printed effect says otherwise.
- After the first **Pass**, the opponent takes one full closing turn, then the passer takes one full closing turn. **Every Battle, including Battle I**, now has two secret Opening Orders per player after these turns and before the final Stratagem reveal and Front comparison.
- Both players simultaneously reveal their two orders. Any card expressly modifying those revealed orders resolves first, then paid Commits, the numbered simultaneous Maneuvers, and the numbered simultaneous Strikes. Orders cannot create a second basic Attack use.
- **Only one Stratagem card per player may be set during each Battle**, whether played normally or set by Teren/another effect. Returning or revealing it does not reopen the slot. A card effect expressly *re-setting the same card* is allowed; it does not introduce another Stratagem.
- Up to **four Narratives** may still be face-up per player. This was not changed. A lost Front costs the full final **Strength difference** in Command; the existing single exhausted Force and Command recovery schedule remain.

## Three existing cards become Opening Order cards

| Card | Printed Command | New job | Why it earns its cost |
| --- | ---: | --- | --- |
| **Had Been Ordered Forward** (Bond) | 1C | The bonded formation may travel two legal steps with one Opening Maneuver | Zero Strength; buys a positional surprise, not access to an ordinary Maneuver |
| **The Long March** (Narrative) | 2C | On PLAY, two Riders may get +1 Strength; during Opening Orders, one Maneuver may shift **two different Riders** | Pays for Rider concentration and a simultaneous multi-unit feint; no repeated free normal Maneuvers |
| **Iria** (Name) | 1C | A Named formation with Iria lets its player retarget one already declared Strike aimed into her Front after the orders are revealed | +1 printed Name Strength and an information advantage; no additional Attack or hidden Stratagem |

They retain their original art and card identities. All three are now together in the 48-card **Broken Oaths** test deck; Long March and Iria also remain in their specialist Rider and Seer labs.

## Revaluing previously redundant Maneuver exceptions

| Card | Price | Result |
| --- | ---: | --- |
| **The Dust Riders** | 3C | Bonded first normal Maneuver each Battle costs **0 Command**, rather than giving permission every Force now has |
| **The Grey Riders** | 4C | May still Maneuver **while Exhausted**, followed by an **unused** basic Rider Attack. The redundant Unnamed exception was removed; the 1C Force ability premium remains |
| **Teren** | 1C | Its completion effect saves an Action when setting **the player's one Stratagem**, rather than permitting multiple cards |

Other cards allowing movement **while Exhausted**—including Trusted, Sela, Covered the Withdrawal Of and Kept the Gate For—remain meaningful exceptions and retain their prices. Cards with ordinary printed **Move** effects remain useful because they save Maneuver Command, overcome Exhaustion where allowed, change a legal target, or bundle a move with a different payoff.

We retained printed Command costs for these cards on this pass. These are **relative valuations and design hypotheses**, not proven win-rate or play-frequency results.

## Stratagems versus Opening Orders: all 11 reviewed

Only one of these can be selected/set by a given player in any Battle. A set Stratagem is assigned to a publicly known Front before the closing sequence; Opening Orders are written **only after** the two post-Pass turns. The opponent sees the Stratagem's location but not its identity. This gives distinct information and timing.

| Stratagem | Timing and specific value | Overlap review |
| --- | --- | --- |
| **The Ground Was Held** | At final scoring, contingent tie/one-point Named recovery | Not an Opening Order |
| **The Lines Held** | Final legal Move with +2 Strength **after** all Opening Orders | Late rescue, not a revealed opening destination |
| **No Step Back** | Prevent a Tactic or an Attack affliction, potentially from an Opening Strike | Reaction, not a competing Strike |
| **The Center Must Hold** | King/Captain permits a **same-rank swap across adjacent active Fronts** at resolution | Replaced redundant Move-and-+2; now a late two-unit exchange |
| **The Flank Was Refused** | Outer flanked Frontline Force ignores its flank penalty and gains +2 | Replaced redundant Move-and-+2; a specific counterflank |
| **The Trap Closed** | Raider/Skirmisher affliction strips an attachment | Can react to an Opening Strike; no added order |
| **The Battle Turned East** | An existing Rider Move, including an Opening Maneuver, gains one further Move and +1 | A conditional single-Front Rider trap, not generic free Maneuver |
| **There Was No Road Back** | Named completion causes displacement or attachment return | Builds during card play, before Opening Orders |
| **Every Banner Turned Toward Them** | Broad Captain/King Human Strength support across two Fronts | Wider than one paid Commit but needs leadership and the Stratagem slot |
| **The Archers Were Ready** | Counterattack from an Archer with an unused legal basic Attack | Can react to an Opening Strike; normal Attack limit remains |
| **The Scouts Had Warned Them** | On the opponent *setting* their one Stratagem, reveal and give a local Force Guarded | Reconnaissance during turns, not an Opening Order reveal |

The central overlap removed is the earlier trio of **Lines Held, Center Must Hold and Flank Was Refused** all offering nearly identical resolution-window Move and Strength. Those now have three distinguishable battlefield decisions.

## Whole-pool audit and unresolved questions

[The complete 131-card ledger](whole-pool-opening-audit.json) checks **33 Forces, 24 Bonds, 20 Names, 11 Heroes, 14 Tactics, 11 Stratagems, 12 Narratives and 6 Orders**, with identity, printed Command, role, effect length and relation to Opening Orders. Exactly **eight** existing identities received a new or clarified effect; no cards were added.

Watch these in actual mirrored playtests:

- **Full-margin Command loss:** does one undefended Front end the war too quickly, even with two secret defensive opportunities?
- **Two-Maneuver orders:** does having one per player available twice at zero Command already supply enough repositioning without the new Bonds/Narratives?
- **One Stratagem cap:** are reactive Stratagems often unplayable because they require an opponent's one planned card or a specific Attack?
- **Battle Turned East and Grey Riders:** do card-granted Rider bonus moves or Move-plus-Attack chains overtake ordinary Force deployment?
- **Teren and Iria:** are Name investments meaningful after the stricter one-Stratagem allowance and at the late Opening Orders window?

### Evidence status

The repository checks validate **printed identity coverage, rule wording, timing distinctions, pricing ledger consistency and 48-card deck construction**. They cannot establish match win rates, decision frequencies or that the new economy avoids Command snowballing. The native/Webgame and AI still require an independent update to match this paper design.
