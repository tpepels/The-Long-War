# Mechanic coverage decks — physical playtest lab

These **three diagnostic 48-card lists** exist to test underrepresented mechanics. They are separate from the four main Strength-first combo decks, which should **not** be diluted to include every rare classification or unusual card.

The labs are reproducible scripted situations, **not proven competitive decks**. Use the current [physical rulebook](../rules/rulebook.md), cards with [print overrides](print-overrides.json), and the [mechanical scenario checklist](physical-rule-playtest-scenarios.md). No native/Webgame results establish balance here.

## Rider & Flank Lab

**Focus:** Rider Attacks, exposed Frontline, and whether +1 Strength and forced placement reward worthwhile positioning.

**Set up:** Deliberately form a flank in Battle II/III, test Rider Attack from Middle versus Rear, and compare Long March's +1 Strength payoff to repeated Maneuvers.

**Check after games:**

- Rider Attack can only start in Frontline/Middle and needs an opposing flanked Frontline target
- New Rider Stratagem changes an actual Front result versus one more Force
- 0-Command Maneuver does not eclipse the raw Strength plan

| Copies | Card | Role |
|---:|---|---|
| 3 | The Grey Riders | force |
| 3 | The Dust Riders | force |
| 3 | The Vardai | force |
| 2 | The Red Duelists | force |
| 2 | The First Spear | force |
| 2 | The Fifty Men | force |
| 1 | The Old Guard | force |
| 3 | Kept Pace With | bond |
| 2 | Stood Fast With | bond |
| 2 | Marched With | bond |
| 2 | Followed | bond |
| 1 | Elian | name |
| 1 | Sela | name |
| 1 | Mara | name |
| 1 | Lysa the Listener | name |
| 1 | Arel | name |
| 1 | Teren | name |
| 1 | Neris, the Ferryman | hero |
| 1 | Kael, the Roadless | hero |
| 1 | Avaros, the Bronze King | hero |
| 2 | They Had Gone Too Far | tactic |
| 2 | The Line Was Baited | tactic |
| 2 | The Battle Turned East | stratagem |
| 2 | The Flank Was Refused | stratagem |
| 2 | The Long March | narrative |
| 2 | They Knew the Ground | narrative |
| 2 | Fresh Orders | order |

## Seer & Hidden Plans Lab

**Focus:** Seer and Scout classification support, hidden-plan responses, and meaningful counterplay after viewing a plan.

**Set up:** Use Scouts or Seers to trigger a hostile Stratagem, compare Guarded versus +2 temporary Strength responses, and test Ground Was Held from both tied and down-by-one provisional totals.

**Check after games:**

- At least one Scout and one Seer can be deployed and completed
- Scouts Had Warned Them prevents an actual targeted affliction
- Before Sunset has a same/adjacent Front trigger and changes Strength
- Ground Was Held reveals only from an eligible pre-reveal total

| Copies | Card | Role |
|---:|---|---|
| 3 | The Lantern Scouts | force |
| 3 | The Watchtowers of Eren | force |
| 3 | The Thornbow Hunters | force |
| 2 | The Signal Company | force |
| 2 | The Red Shields | force |
| 3 | The Fifty Men | force |
| 3 | Carried Messages For | bond |
| 2 | Kept Pace With | bond |
| 2 | Watched the Skies For | bond |
| 2 | Guarded | bond |
| 1 | Iria | name |
| 1 | Lysa the Listener | name |
| 1 | Mara | name |
| 1 | Teren | name |
| 1 | Oren | name |
| 1 | Corin of the High Wall | name |
| 1 | Yara, the Chronicler | hero |
| 1 | Kael, the Roadless | hero |
| 1 | Alda, Keeper of the Ford | hero |
| 2 | The Scouts Found the Gap | tactic |
| 1 | The Muster Was False | tactic |
| 1 | They Let Them Through | tactic |
| 2 | The Scouts Had Warned Them | stratagem |
| 2 | The Ground Was Held | stratagem |
| 2 | Before Sunset, the Ford Would Be Ours | narrative |
| 2 | They Knew the Ground | narrative |
| 2 | Send a Runner | order |

## Front Exchange & Preparation Lab

**Focus:** Prepared layers, Bond/Name exchanges, sudden Front shifts and one-time PLAY effects.

**Set up:** Build a Named stack in adjacent Fronts with support Forces. Play No Road Was Too Long to exchange columns legally, then verify Named Strength and all token transfer details.

**Check after games:**

- Two prepared layers can attach without replaying PLAY or exceeding slot capacity
- A swapped Front retains each card's matching row and marker ownership
- No Road Was Too Long costs 3 Command and only one Action
- Line Held reveal requires an empty friendly Frontline

| Copies | Card | Role |
|---:|---|---|
| 3 | The House of Reed | force |
| 3 | The Field Train | force |
| 2 | The Late Banner | force |
| 2 | The Fifty Men | force |
| 2 | The Red Shields | force |
| 2 | The Watchtowers of Eren | force |
| 2 | The King's Spears | force |
| 3 | Swore Again To | bond |
| 2 | Stayed Behind For | bond |
| 2 | Supplied By | bond |
| 2 | Followed | bond |
| 1 | Oren | name |
| 1 | Torren | name |
| 1 | Namar | name |
| 1 | Eira | name |
| 1 | Meren | name |
| 1 | Asha, the Shield-Bearer | name |
| 1 | Nara, Builder of Walls | hero |
| 1 | Yara, the Chronicler | hero |
| 1 | Tovan, the Quartermaster | hero |
| 2 | The Muster Was False | tactic |
| 2 | All Reserves Forward | tactic |
| 2 | There Was No Road Back | stratagem |
| 2 | The Lines Held | stratagem |
| 2 | No Road Was Too Long | narrative |
| 2 | The King Had Given the Order | narrative |
| 2 | Take Stock | order |

## Structured observations

In each lab record the trigger count, how often the effect was still legal, the Command/Action investment, total Strength changed, and whether the Front was won **because of** that effect. Record unused hidden Stratagems and Narrow Frontline/Middle/Rear placement restrictions.

Test unusual effects against **multiple active Front configurations**: Battle I two central Fronts, Battle II three, Battle III four, and later-Battle saturated boards. Have both players exchange seats for the same card layout. Do not infer fun or balance from a legal scenario alone.

These lists live in [mechanic-coverage-decks.json](mechanic-coverage-decks.json) for automated composition checks. They are not added to the standard four-deck printable selector.
