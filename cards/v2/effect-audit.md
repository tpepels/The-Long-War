# V2 effect audit

This audit reviews **all 158 current card effects** for two problems:

1. **Superfluous bookkeeping** - especially limited-use effects whose only meaningful result is a small Strength change.
2. **Buried readability** - Force/Bond/Hero-as-Force text that would need the covered card face to be reread after a stack is completed.

## Result

- Pure `1/BATTLE -> +1 Strength` bookkeeping effects remaining: **0**.
- Buried ACTION/REACTION effects remaining: **3**.
- Those buried active effects are intentionally limited to strip-complete movement/repositioning:
  - The Vardai - `ACTION 1/B · MOVE 1 · FRONT +1`
  - Kael, the Roadless (force) - `ACTION 1/B · MOVE 2`
  - Neris, the Ferryman (force) - `ACTION 1/B · MOVE 1`
- Bonds with buried ACTION/REACTION abilities: **0**.
- Every non-PLAY live Force/Bond effect is required to carry an exposed reminder.
- Exact repeated effect text is listed but is not automatically treated as superfluous; repeated text across different card layers can be useful redundancy.

### Strength bookkeeping exceptions kept intentionally

- **The Vardai** - the once-per-Battle effect is fundamentally a Move; the +1 Strength is only the positional payoff for ending in Front.
- **Avaros, the Bronze King (Name mode)** - the once-per-Battle choice selects a classification and may affect several formations, so the decision is materially larger than a +1 button.

### Cleanup performed from this audit

- Arel's once-per-Battle adjacent `+1 Strength` button was replaced with a positional swap.
- Complex buried Force actions were converted to PLAY effects or concise positional states.
- Bonds no longer carry ACTION or REACTION abilities; one-shot choices resolve on PLAY, live Bond text is short state text.
- Duplicate Bond effects **Trusted** and **Kept the Gate For** were given distinct positional/Exhaustion identities.
- The River Raiders were differentiated from The Iron Boars with an Exhaustion payoff.

## Every effect

| Card | Layer | Timing | Visibility | Verdict | Effect / note |
|---|---|---|---|---|---|
| Seven Black Ships | force | bonded | Exposed strip | KEEP | While this formation is in the Rear, it has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The White Hands of Elara | force | play | Buried after PLAY | KEEP | If played in the Rear, remove one temporary negative marker from the friendly formation directly ahead. _(Resolves before this layer can be buried.)_ |
| The Red Shields | force | front | Exposed strip | KEEP | Opposing Tactics targeting this formation cost 1 additional Command. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Crow Archers | force | rear | Exposed strip | KEEP | SUPPORT +1. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The House of Reed | force | rear | Exposed strip | KEEP | SUPPLY. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Grey Riders | force | tireless | Exposed strip | KEEP | This formation may Maneuver while Exhausted. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Dust Riders | force | bonded | Exposed strip | KEEP | While this formation is in the Front or Middle row, it has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Red Duelists | force | play | Buried after PLAY | KEEP | Choose an opposing Named Formation in this Front. Its ACTION abilities cannot be used this turn. _(Resolves before this layer can be buried.)_ |
| The Thornbow Hunters | force | play | Buried after PLAY | KEEP | Look at one opposing face-down Stratagem in this Front or an adjacent Front. _(Resolves before this layer can be buried.)_ |
| The Iron Boars | force | play | Buried after PLAY | KEEP | Choose one opposing prepared Bond or prepared Name in this Front. Its owner pays 1 Command or returns it to hand. _(Resolves before this layer can be buried.)_ |
| The First Spear | force | front | Exposed strip | KEEP | If the position directly behind is occupied by a friendly formation, this formation has +2 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Old Guard | force | middle | Exposed strip | KEEP | RESERVE +2. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Late Banner | force | bonded | Exposed strip | KEEP | Names played onto this formation cost 1 less Command, to a minimum of 1. _(Short live state; complete meaning remains in the exposed strip. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| The Banner Singers | force | while_named | Exposed strip | KEEP | While this formation is in the Middle row, SUPPORT +1. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Vardai | force | action · 1/BATTLE | Exposed strip | KEEP | Move this formation one position. If it ends in the Front row, it gets +1 Strength this Battle. _(Strength is a payoff for the Move decision, not a standalone button. Buried active allowed only because the entire instruction is represented in the exposed strip.)_ |
| The Aradai | force | play | Buried after PLAY | KEEP | Place a Tax marker on this Front. The next Bond your opponent plays here before your next turn costs 1 additional Command. _(Resolves before this layer can be buried.)_ |
| The Ilyri | force | play | Buried after PLAY | KEEP | Choose an opposing Bonded Formation in this Front. Its Bond contributes no Strength this Battle. _(Resolves before this layer can be buried.)_ |
| The Damar | force | exhausted | Exposed strip | KEEP | This formation has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Serekh | force | front | Exposed strip | KEEP | Opposing Tactics targeting the friendly formation directly behind cost 1 additional Command. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Followed | bond | while_named | Exposed strip | KEEP | This Bond contributes +1 additional Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Guarded | bond | play | Buried after PLAY | KEEP | Remove one temporary negative marker from this formation. _(Resolves before this layer can be buried.)_ |
| Marched With | bond | play | Buried after PLAY | KEEP | Move this formation one position. _(Resolves before this layer can be buried.)_ |
| Kept Pace With | bond | play | Buried after PLAY | KEEP | If this formation contains a Rider or Scout, draw 1 card, then discard 1 card. _(Resolves before this layer can be buried.)_ |
| Covered the Withdrawal of | bond | bonded | Exposed strip | KEEP | The friendly formation directly ahead is TIRELESS. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Blocked the Road for | bond | play | Buried after PLAY | KEEP | Place a Tax marker on this Front. The next card your opponent plays here before your next turn costs 1 additional Command. _(Resolves before this layer can be buried.)_ |
| Held the Line for | bond | bonded | Exposed strip | KEEP | RESERVE +1. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Seized the Standard of | bond | play | Buried after PLAY | KEEP | If this formation contains a Raider or Skirmisher, look at two random cards from your opponent's hand. _(Resolves before this layer can be buried.)_ |
| Stayed Behind For | bond | play | Buried after PLAY | KEEP | Choose a prepared Name in this Front. Attach it to this formation if its Name slot is empty. _(Resolves before this layer can be buried.)_ |
| Swore Again To | bond | bonded | Exposed strip | KEEP | Names played onto this formation cost 1 less Command, to a minimum of 1. _(Short live state; complete meaning remains in the exposed strip. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Endured With | bond | play | Buried after PLAY | KEEP | Remove one -Strength marker from this formation. _(Resolves before this layer can be buried.)_ |
| Rallied Behind | bond | play | Buried after PLAY | KEEP | If you have less Command than your opponent, regain 1 Command. _(Resolves before this layer can be buried.)_ |
| Bought Time For | bond | play | Buried after PLAY | KEEP | You may pay 1 additional Command. If you do, draw 2 cards. _(Resolves before this layer can be buried.)_ |
| Trusted | bond | while_named | Exposed strip | KEEP | This formation is TIRELESS. _(Short live state; complete meaning remains in the exposed strip. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Marched Beneath the Banner of | bond | bonded | Exposed strip | KEEP | If this formation contains a Captain or King, this Bond contributes +1 additional Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Carried the Oath of | bond | while_named | Exposed strip | KEEP | This formation's Name text cannot be suppressed. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Had Been Ordered Forward | bond | bonded | Exposed strip | KEEP | If this formation contains a Guard or Spearman, this Bond contributes +1 additional Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Namar | name | becomes_named | Top-visible | KEEP | Regain 2 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Namar | name | action | Top-visible | KEEP | Pay 1 Command. Choose another friendly Human formation in this Front. The next card played onto it this turn costs 1 less Command, to a minimum of 1. _(Top-visible while live.)_ |
| Iria | name | becomes_named | Top-visible | KEEP | Look at the top 3 cards of your deck. Return them in any order. _(Top-visible while live.)_ |
| Iria | name | trigger · 1/BATTLE | Top-visible | KEEP | When your opponent sets a Stratagem in this Front, you may look at it. _(Top-visible while live.)_ |
| Oren | name | becomes_named | Top-visible | KEEP | Draw 2 cards, then discard 1 card. _(Top-visible while live.)_ |
| Oren | name | action · 1/BATTLE | Top-visible | KEEP | Play one Bond from your hand onto this formation or the friendly formation directly ahead, paying its Command cost. _(Top-visible while live.)_ |
| Elian | name | becomes_named | Top-visible | KEEP | Move this formation one position. _(Top-visible while live.)_ |
| Elian | name | action · 1/BATTLE | Top-visible | KEEP | Move this formation one position. _(Top-visible while live.)_ |
| Teren | name | becomes_named | Top-visible | KEEP | Set a Stratagem from your hand in this Front without spending another Action. Pay its Command cost. _(Top-visible while live.)_ |
| Teren | name | trigger | Top-visible | KEEP | When another friendly formation in this Front becomes Named, draw 1 card. _(Top-visible while live.)_ |
| Mara | name | becomes_named | Top-visible | KEEP | Look at your opponent's hand. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Mara | name | trigger · 1/BATTLE | Top-visible | KEEP | When your opponent plays a Tactic in this Front, you may look at one opposing face-down Stratagem in this or an adjacent Front. _(Top-visible while live.)_ |
| Asha, the Shield-Bearer | name | becomes_named | Top-visible | KEEP | Remove all temporary negative markers from this formation. _(Top-visible while live.)_ |
| Asha, the Shield-Bearer | name | trigger · 1/BATTLE | Top-visible | KEEP | When an opposing Tactic targets another friendly formation in this Front, you may make it target this formation instead, if legal. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Edrin | name | becomes_named | Top-visible | KEEP | Regain 1 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Edrin | name | trigger · 1/BATTLE | Top-visible | KEEP | When this formation would receive a temporary negative marker, you may ignore that marker. _(Top-visible while live.)_ |
| Sela | name | becomes_named | Top-visible | KEEP | Move this formation one row forward or backward. _(Top-visible while live.)_ |
| Sela | name | while_named | Top-visible | KEEP | This formation is TIRELESS. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Meren | name | becomes_named | Top-visible | KEEP | Return one Bond from your discard pile to your hand. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Meren | name | action · 1/BATTLE | Top-visible | KEEP | Choose one Unbonded friendly Formation in this Front. The next Bond you play onto it this turn costs 1 less Command, to a minimum of 0. _(Top-visible while live.)_ |
| Tala | name | becomes_named | Top-visible | KEEP | Choose an opposing formation in this Front. It gets -2 Strength this Battle. _(Top-visible while live.)_ |
| Tala | name | action · 1/BATTLE | Top-visible | KEEP | Choose an opposing Bonded Formation in this Front. Its Bond contributes no Strength this Battle. _(Top-visible while live.)_ |
| Sorin | name | becomes_named | Top-visible | KEEP | Draw 2 cards, then put 1 card from your hand on top of your deck. _(Top-visible while live.)_ |
| Sorin | name | action | Top-visible | KEEP | Pay 1 Command. Discard 1 card, then draw 2 cards. _(Top-visible while live.)_ |
| Iven | name | becomes_named | Top-visible | KEEP | Regain 1 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Iven | name | continuous | Top-visible | KEEP | Your Tactics cost 1 less Command, to a minimum of 1. _(Top-visible while live.)_ |
| Arel | name | becomes_named | Top-visible | KEEP | Choose one classification among your friendly formations in this Front. Those formations get +1 Strength this Battle. _(Top-visible while live.)_ |
| Arel | name | action · 1/BATTLE | Top-visible | KEEP | Swap this formation with the friendly formation directly ahead or directly behind. _(Top-visible while live.)_ |
| Torren | name | becomes_named | Top-visible | KEEP | Choose an Unbonded friendly Formation in this Front. You may immediately play a Bond from your hand onto it, paying its Command cost. _(Top-visible while live.)_ |
| Torren | name | trigger | Top-visible | KEEP | When another friendly formation in this Front becomes Named, regain 1 Command. _(Top-visible while live.)_ |
| Eira | name | becomes_named | Top-visible | KEEP | If you control another Named Human Formation, draw 2 cards. _(Top-visible while live.)_ |
| Eira | name | while_named | Top-visible | KEEP | While this formation is Named, Eira also has the King classification. _(Top-visible while live.)_ |
| Avaros, the Bronze King | Hero force | play | Buried after PLAY | KEEP | Choose up to two other friendly Human formations in this Front. Each gets +1 Strength this Battle. _(Resolves before this layer can be buried.)_ |
| Avaros, the Bronze King | Hero name | becomes_named | Top-visible | KEEP | Regain 2 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Avaros, the Bronze King | Hero name | action · 1/BATTLE | Top-visible | KEEP | Choose one classification among your friendly formations in this Front. Each friendly formation here containing it gets +1 Strength this Battle. _(Classification choice can affect several formations; not trivial bookkeeping. Top-visible while live.)_ |
| Kael, the Roadless | Hero force | action · 1/BATTLE | Exposed strip | KEEP | Move Kael up to two positions. _(Buried active allowed only because the entire instruction is represented in the exposed strip.)_ |
| Kael, the Roadless | Hero name | becomes_named | Top-visible | KEEP | Look at every opposing face-down Stratagem in this Front. _(Top-visible while live.)_ |
| Kael, the Roadless | Hero name | action · 1/BATTLE | Top-visible | KEEP | Look at one opposing face-down Stratagem in this or an adjacent Front. _(Top-visible while live.)_ |
| Rovan, the Gatebreaker | Hero force | play | Buried after PLAY | KEEP | Choose one opposing prepared Bond or Name in this Front. Its owner pays 1 Command or returns it to hand. _(Resolves before this layer can be buried.)_ |
| Rovan, the Gatebreaker | Hero name | becomes_named | Top-visible | KEEP | Choose an opposing Bond or Name in this Front. Its text is ignored this Battle. _(Top-visible while live.)_ |
| Rovan, the Gatebreaker | Hero name | action · 1/BATTLE | Top-visible | KEEP | Place a Tax marker on this Front. The next card your opponent plays here before your next turn costs 1 additional Command. _(Top-visible while live.)_ |
| Alda, Keeper of the Ford | Hero force | front | Exposed strip | KEEP | Opposing Tactics targeting Alda or the friendly formation directly behind cost 1 additional Command. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Alda, Keeper of the Ford | Hero name | becomes_named | Top-visible | KEEP | Remove all temporary negative markers from one friendly formation in this Front. _(Top-visible while live.)_ |
| Alda, Keeper of the Ford | Hero name | trigger · 1/BATTLE | Top-visible | KEEP | When an opposing Tactic targets another friendly formation in this Front, you may make it target this formation instead, if legal. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Tovan, the Quartermaster | Hero force | play | Buried after PLAY | KEEP | Draw 2 cards, then discard 1 card. _(Resolves before this layer can be buried.)_ |
| Tovan, the Quartermaster | Hero name | becomes_named | Top-visible | KEEP | Regain 2 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Tovan, the Quartermaster | Hero name | continuous | Top-visible | KEEP | Bonds and Names you play cost 1 less Command, to a minimum of 1. _(Top-visible while live.)_ |
| Nara, Builder of Walls | Hero force | play | Buried after PLAY | KEEP | Choose one prepared Bond or prepared Name in this Front. Attach it to a legal friendly Formation in this Front. _(Resolves before this layer can be buried.)_ |
| Nara, Builder of Walls | Hero name | becomes_named | Top-visible | KEEP | Return one Bond from your discard pile to your hand. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Nara, Builder of Walls | Hero name | action · 1/BATTLE | Top-visible | KEEP | Choose one prepared Bond or prepared Name in this Front. Attach it to a legal friendly Formation here. _(Top-visible while live.)_ |
| Neris, the Ferryman | Hero force | action · 1/BATTLE | Exposed strip | KEEP | Move Neris one position. _(Buried active allowed only because the entire instruction is represented in the exposed strip.)_ |
| Neris, the Ferryman | Hero name | becomes_named | Top-visible | KEEP | Move another friendly formation in this Front one position. _(Top-visible while live.)_ |
| Neris, the Ferryman | Hero name | action · 1/BATTLE | Top-visible | KEEP | Move this or another friendly formation in this Front one position. _(Top-visible while live.)_ |
| Veyra, Keeper of Oaths | Hero force | play | Buried after PLAY | KEEP | Remove one temporary negative marker from a friendly formation in this Front. _(Resolves before this layer can be buried.)_ |
| Veyra, Keeper of Oaths | Hero name | becomes_named | Top-visible | KEEP | This formation's Name text cannot be suppressed this Battle. _(Top-visible while live.)_ |
| Veyra, Keeper of Oaths | Hero name | continuous | Top-visible | KEEP | Opposing Tactics that target this formation cost 1 additional Command. _(Top-visible while live.)_ |
| Yara, the Chronicler | Hero force | play | Buried after PLAY | KEEP | Look at the top 3 cards of your deck. Put 1 into your hand and the rest on the bottom in any order. _(Resolves before this layer can be buried.)_ |
| Yara, the Chronicler | Hero name | becomes_named | Top-visible | KEEP | Return one Narrative from your discard pile to your hand. _(Top-visible while live.)_ |
| Yara, the Chronicler | Hero name | trigger | Top-visible | KEEP | When you play a Narrative, draw 1 card, then discard 1 card. _(Top-visible while live.)_ |
| The Baggage Was Abandoned | tactic | play | Immediate | KEEP | Choose an opposing formation. It gets -2 Strength this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| They Returned With Names | tactic | play | Immediate | KEEP | Choose an opposing Named Formation. Its Name text is ignored this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| They Were Gathering There | tactic | play | Immediate | KEEP | Choose one of your Scouts. Look at one opposing face-down Stratagem in its Front or an adjacent Front. _(One-shot immediate card; no persistent reread burden.)_ |
| The Muster Was False | tactic | play | Immediate | KEEP | Return one opposing prepared Bond or prepared Name to its owner's hand. _(One-shot immediate card; no persistent reread burden.)_ |
| They Had Gone Too Far | tactic | play | Immediate | KEEP | Choose an opposing formation. Move it one row toward its Rear, if that position is empty. _(One-shot immediate card; no persistent reread burden.)_ |
| All Banners Forward | tactic | play | Immediate | KEEP | Choose an opposing King or Captain. Its ACTION abilities cannot be used this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| The Line Wheeled | tactic | play | Immediate | KEEP | Choose an opposing Bonded Formation. Its Bond contributes no Strength and its 1/BATTLE ability cannot be used this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| They Let Them Through | tactic | play | Immediate | KEEP | Choose an opposing Formation. Its 1/BATTLE abilities cannot be used this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| All Reserves Forward | tactic | play | Immediate | KEEP | Choose an opposing Rear formation. It gets -2 Strength this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| The Line Had Begun to Move | tactic | play | Immediate | KEEP | Place a Tax marker on an active Front. The next card your opponent plays there costs 2 additional Command. _(One-shot immediate card; no persistent reread burden.)_ |
| The Ground Was Held | stratagem | hidden | Reveal source | KEEP | Reveal when a Front would tie. If you have a Named Formation there and your opponent does not, you win that Front instead. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Lines Held | stratagem | hidden | Reveal source | KEEP | Reveal after Front results are known. Up to two Fronts you lost do not reduce your Command this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| No Step Back | stratagem | hidden | Reveal source | KEEP | Reveal when an opposing Tactic targets one of your formations. Ignore that Tactic's effect on that formation. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Center Must Hold | stratagem | hidden | Reveal source | KEEP | Reveal before Strength is compared in a Front containing one of your Kings or Captains. Up to two other friendly formations there get +1 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Flank Was Refused | stratagem | hidden | Reveal source | KEEP | Reveal before Strength is compared in an outer Front. One friendly Archer, Guard, or Stronghold there gets +2 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Trap Closed | stratagem | hidden | Reveal source | KEEP | Reveal after one of your Raiders or Skirmishers places a temporary negative marker on an opposing formation. One other friendly Raider or Skirmisher in that Front gets +2 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Battle Turned East | stratagem | hidden | Reveal source | KEEP | Reveal after one of your Riders moves. That Rider gets +2 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| There Was No Road Back | stratagem | hidden | Reveal source | KEEP | Reveal when one of your formations becomes Named. Draw 2 cards, then discard 1 card. _(Hidden until reveal, then its source/effect is explicit.)_ |
| Every Banner Turned Toward Them | stratagem | hidden | Reveal source | KEEP | Reveal before Strength is compared in a Front containing one of your Kings, Captains, or Heirs. Every other friendly Human formation there gets +1 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Long March | narrative | continuous | Face-up | KEEP | Your Riders pay 0 Command to Maneuver this Battle. _(Face-up source remains visible.)_ |
| The Wall Did Not Break | narrative | continuous | Face-up | KEEP | Your Guards and Strongholds have +1 Strength this Battle. _(Face-up source remains visible.)_ |
| The Crows Came Down | narrative | continuous | Face-up | KEEP | Your Archers have +1 Strength this Battle. _(Face-up source remains visible.)_ |
| Before Sunset, the Ford Would Be Ours | narrative | action · 1/BATTLE | Face-up | KEEP | Choose one of your Scouts or Ships. Look at one opposing face-down Stratagem in its Front or an adjacent Front. _(Face-up source remains visible.)_ |
| They Lived to Tell It | narrative | action · 1/BATTLE | Face-up | KEEP | Choose one of your Veterans or Healers. Remove one temporary negative marker from its formation. _(Face-up source remains visible.)_ |
| No Road Was Too Long | narrative | continuous | Face-up | KEEP | Your Raiders and Skirmishers cost 1 less Command to play this Battle, to a minimum of 1. _(Face-up source remains visible.)_ |
| The Battle Had Chosen Them | narrative | continuous | Face-up | KEEP | Your Heroes and Named Formations have +1 Strength this Battle. _(Face-up source remains visible.)_ |
| No One Would Be First to Leave | narrative | continuous | Face-up | KEEP | Your Bonded Human Formations have +1 Strength this Battle. _(Face-up source remains visible.)_ |
| The King Had Given the Order | narrative | continuous | Face-up | KEEP | Bonds and Names you play into a Front containing one of your Kings or Captains cost 1 less Command, to a minimum of 1. _(Face-up source remains visible.)_ |
| The Ash Bowmen | force | bonded | Exposed strip | KEEP | This formation has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Lantern Scouts | force | play | Buried after PLAY | KEEP | Look at one opposing face-down Stratagem in this Front. _(Resolves before this layer can be buried.)_ |
| The River Raiders | force | play | Buried after PLAY | KEEP | Choose one opposing Exhausted formation in this Front. It gets -1 Strength this Battle. _(Resolves before this layer can be buried.)_ |
| The King's Spears | force | while_named | Exposed strip | KEEP | This formation has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Salt-Road Fleet | force | bonded | Exposed strip | KEEP | Tactics you play targeting this Front cost 1 less Command, to a minimum of 1. _(Short live state; complete meaning remains in the exposed strip.)_ |
| The Watchtowers of Eren | force | play | Buried after PLAY | KEEP | If played in the Rear, look at one opposing face-down Stratagem in this Front or an adjacent Front. _(Resolves before this layer can be buried.)_ |
| Watched the Skies For | bond | bonded | Exposed strip | KEEP | If this formation contains an Archer or Scout, this Bond contributes +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Kept the Gate For | bond | bonded | Exposed strip | KEEP | The friendly formation directly behind is TIRELESS. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Shared the Spoils With | bond | play | Buried after PLAY | KEEP | If this formation contains a Raider or Skirmisher, regain 1 Command. _(Resolves before this layer can be buried.)_ |
| Carried Messages For | bond | play | Buried after PLAY | KEEP | If this formation contains a Captain or Scout, draw 1 card, then discard 1 card. _(Resolves before this layer can be buried.)_ |
| Supported By | bond | bonded | Exposed strip | KEEP | SUPPORT +1. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Supplied By | bond | bonded | Exposed strip | KEEP | SUPPLY. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Corin of the High Wall | name | becomes_named | Top-visible | KEEP | Choose an opposing formation in this Front. It gets -1 Strength this Battle. _(Top-visible while live.)_ |
| Corin of the High Wall | name | continuous | Top-visible | KEEP | Other friendly Archers in this Front have +1 Strength. _(Top-visible while live.)_ |
| Lysa the Listener | name | becomes_named | Top-visible | KEEP | Look at your opponent's hand. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Lysa the Listener | name | action | Top-visible | KEEP | Pay 1 Command. Look at one opposing face-down Stratagem in any active Front. _(Top-visible while live.)_ |
| Brannoc | name | becomes_named | Top-visible | KEEP | Place a Tax marker on this Front. The next card your opponent plays here costs 1 additional Command. _(Top-visible while live.)_ |
| Brannoc | name | action | Top-visible | KEEP | Pay 1 Command. Choose one opposing prepared Bond or prepared Name in this Front. Its owner pays 1 Command or returns it to hand. _(Top-visible while live.)_ |
| Maelin | name | becomes_named | Top-visible | KEEP | Remove Exhaustion from one friendly formation in this Front. _(Top-visible while live.)_ |
| Maelin | name | continuous | Top-visible | KEEP | Opposing Tactics that target another friendly formation in this Front cost 1 additional Command. _(Top-visible while live.)_ |
| Serai, Queen of Crows | Hero force | bonded | Exposed strip | KEEP | If another friendly Archer is in this Front, Serai has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Serai, Queen of Crows | Hero name | becomes_named | Top-visible | KEEP | Your Archers in this Front get +1 Strength this Battle. _(Top-visible while live.)_ |
| Serai, Queen of Crows | Hero name | action | Top-visible | KEEP | Pay 1 Command. Choose an opposing formation in this Front with no -Strength marker. It gets -1 Strength this Battle. _(Top-visible while live.)_ |
| Doros, the Last Spear | Hero force | bonded | Exposed strip | KEEP | While Doros is in the Front row, he has +1 Strength. _(Short live state; complete meaning remains in the exposed strip.)_ |
| Doros, the Last Spear | Hero name | becomes_named | Top-visible | KEEP | Regain 1 Command. _(Top-visible while live. Exact effect text is repeated elsewhere; retained because the card layer/secondary identity differs.)_ |
| Doros, the Last Spear | Hero name | continuous | Top-visible | KEEP | Opposing Tactics cannot reduce this formation's Strength. _(Top-visible while live.)_ |
| A Volley Before Dawn | tactic | play | Immediate | KEEP | Choose an opposing formation in a Front containing one of your Archers. It gets -2 Strength this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| The Scouts Found the Gap | tactic | play | Immediate | KEEP | Choose one of your Scouts. Reveal one opposing face-down Stratagem in its Front or an adjacent Front. Its owner returns it to hand or pays 1 Command to set it face-down again. _(One-shot immediate card; no persistent reread burden.)_ |
| The Stores Were Taken | tactic | play | Immediate | KEEP | Choose one opposing prepared Bond or prepared Name in a Front containing one of your Raiders. Its owner pays 2 Command or returns it to hand. _(One-shot immediate card; no persistent reread burden.)_ |
| The Line Was Baited | tactic | play | Immediate | KEEP | Choose an opposing Guard or Spearman in a Front containing one of your Skirmishers. Its formation gets -2 Strength this Battle. _(One-shot immediate card; no persistent reread burden.)_ |
| The Archers Were Ready | stratagem | hidden | Reveal source | KEEP | Reveal when an opposing Tactic targets one of your formations in a Front containing one of your Archers. One friendly Archer there gets +2 Strength this Battle. _(Hidden until reveal, then its source/effect is explicit.)_ |
| The Scouts Had Warned Them | stratagem | hidden | Reveal source | KEEP | Reveal when your opponent sets a Stratagem in a Front containing one of your Scouts or Seers. Look at it. Draw 1 card, then discard 1 card. _(Hidden until reveal, then its source/effect is explicit.)_ |
| Every Bow Was Strung | narrative | continuous | Face-up | KEEP | Your Bonded Archer formations have +1 Strength this Battle. _(Face-up source remains visible.)_ |
| They Knew the Ground | narrative | action · 1/BATTLE | Face-up | KEEP | Choose one of your Scouts or Seers. Look at one opposing face-down Stratagem in any active Front. _(Face-up source remains visible.)_ |
| The Raiders Came Home Loaded | narrative | continuous | Face-up | KEEP | Tactics you play targeting a Front containing one of your Raiders or Skirmishers cost 1 less Command, to a minimum of 1. _(Face-up source remains visible.)_ |

## Repeated exact effect text

- **BONDED** - The Late Banner, Swore Again To: Names played onto this formation cost 1 less Command, to a minimum of 1.
- **WHILE_NAMED** - Trusted, Sela: This formation is TIRELESS.
- **BECOMES_NAMED** - Namar, Avaros, the Bronze King (name), Tovan, the Quartermaster (name): Regain 2 Command.
- **BECOMES_NAMED** - Mara, Lysa the Listener: Look at your opponent's hand.
- **TRIGGER** - Asha, the Shield-Bearer, Alda, Keeper of the Ford (name): When an opposing Tactic targets another friendly formation in this Front, you may make it target this formation instead, if legal.
- **BECOMES_NAMED** - Edrin, Iven, Doros, the Last Spear (name): Regain 1 Command.
- **BECOMES_NAMED** - Meren, Nara, Builder of Walls (name): Return one Bond from your discard pile to your hand.

The repetition list is a diversity check, not an automatic failure. The more important rule is that buried cards do not create hidden decisions or hidden bookkeeping.
