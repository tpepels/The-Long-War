# Hero role-based Command pricing

Heroes are **one physical card with two mutually exclusive modes**. A Hero used as a Force contributes its Force Strength, classification and Force ability, while a Hero used as a Name contributes its +1 Name Strength modifier, classification and Name abilities. You select one mode on PLAY and **pay only that mode's Command price**. A prepared Hero Name uses its Name price. A Hero never receives both modes' effects just because both prices appear on the card.

This pricing is **physical-print only**. The native/Webgame engine and the canonical `cards/cards.json` Hero source remain unchanged.

## Valuation approach

- **Force mode:** the same `1 + ceil(printed Force Strength / 2) + 0–1 ability premium` as ordinary physical Forces. A useful class-native Attack or Guard screen can contribute to that premium.
- **Name mode:** compare the +1 Name modifier and printed effects with ordinary Names, typically costing 1–4 Command. Strong continuous savings, recursion or reliable battle swings cost more than limited information or one-off movement.
- **Flexible choice:** there is no additional flat surcharge for offering both modes. A Hero is already Unique, cannot act in both modes when played, and uses the per-Battle allowance for its chosen mode.
- **No Strength adjustments:** increasing Force Strength to match an expensive Name ability would reward the wrong mode; making all Heroes share one higher cost would make their weaker Name modes unattractive.

| Hero | Force Strength | Previous single cost | Force cost | Name cost | Pricing focus |
| --- | ---: | ---: | ---: | ---: | --- |
| Avaros, the Bronze King | 5 | 3 | **5** | **4** | King Name immediately regains 2 Command and offers a once-per-Battle classification-wide Strength bonus |
| Kael, the Roadless | 3 | 3 | **3** | **1** | Name brings information from a hidden plan and a paid once-per-Battle second peek |
| Rovan, the Gatebreaker | 5 | 4 | **5** | **3** | Name suppresses an attached effect on completion and can impose a one-use local Tax |
| Alda, Keeper of the Ford | 3 | 2 | **4** | **2** | Name removes harmful markers when completed and redirects one hostile Tactic when eligible |
| Tovan, the Quartermaster | 2 | 3 | **3** | **4** | Name regains 2 Command and provides persistent global Bond/Name price reductions |
| Nara, Builder of Walls | 3 | 3 | **4** | **3** | Name recovers a discarded Bond and attaches prepared layers once per Battle |
| Neris, the Ferryman | 4 | 3 | **4** | **2** | Name repositions an ally on completion and has a once-per-Battle Move Action |
| Veyra, Keeper of Oaths | 4 | 3 | **4** | **2** | Name protects itself from suppression and makes opposing targeted Tactics cost more |
| Yara, the Chronicler | 3 | 3 | **4** | **2** | Name recovers a Narrative on completion and filters cards when you play Narratives |
| Serai, Queen of Crows | 4 | 3 | **4** | **2** | Name temporarily buffs friendly Archers and weakens opponents with a paid ACTION |
| Doros, the Last Spear | 5 | 3 | **5** | **1** | Name regains 1 Command and passively prevents hostile Tactic Strength reduction |

## Mode-specific comparison

**Avaros:** playing as a 5-Strength King with an immediate team buff costs **5 Command**. As a Name, his completion recovery and repeatable classification support cost **4 Command**. We do not turn his 5 Force Strength into Name Strength.

**Tovan:** as a 2-Strength Force with a useful draw/filter effect he costs **3 Command**; as a Name providing continuous Bond and Name discounts he costs **4**. This is an important counterexample to pricing a Hero solely from its Force Strength.

**Doros:** 5 Strength with a Bonded Frontline bonus costs **5** as a Force, but the protective Name with +1 Name modifier is **1**. A flat 5 Command price would strongly discourage using his Name mode.

## Validation and outstanding balance questions

The printed card shows both mode prices **only in its diagonal Command seal**, with the Force shield and Name banner beside their respective amounts. The Force and Name rules headings identify the modes without repeating Command costs. The Force and Name versions each contribute only their chosen Strength and abilities.

The final 9 October support-and-Hero comparison review adjusted five Name mode prices; see [final balance audit](final-balance-audit-2026-10-09.md). Test the prices with six combo decks and four mechanic-coverage decks, mirroring first player and comparable hands. Track whether **both modes are sometimes chosen**, when a Hero is stranded in hand, the actions to reach a Named Formation, Command at each Battle boundary, and actual effects on Front winners. Prices are design appraisals, **not proven win rates**. Name costs may need further adjustment once how often their abilities trigger is observed.

See [force-pricing.json](force-pricing.json) for the ordinary Force tariff and [print-overrides.json](print-overrides.json) for the exact Hero role-specific values.
