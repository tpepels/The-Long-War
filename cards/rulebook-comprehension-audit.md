# Physical card ↔ rulebook comprehension audit

**Date:** 8 October 2026. **Mode:** static print-first audit, **no edits to rules or card gameplay**. Compared the full 131-card physical pool generated from `cards/cards.json` plus 16 `cards/print-overrides.json` replacements and four print-only timing corrections, against `rules/rulebook.md`. Also inspected the separately printed `web/playmat.html` Reference, which a newcomer is directed to use.

**Short verdict:** the prose has a coherent premise, a mostly natural tutorial voice, helpful explanations for ordinary movement and combat, and fewer unnecessary keywords than earlier revisions. **But it is not yet a reliable, self-contained playable reference for the printed card pool.** The main obstacles are a handful of global contract gaps that affect many cards. Patching individual card wording before these are decided would be inefficient.

## Severity-ordered findings

| ID | Severity | Evidence | Why it matters | Recommended decision (not implemented) |
|---|---|---|---|---|
| R01 | **BLOCKER** | Rulebook §Narratives: only cards marked **Ongoing** persist; all **12** printed Narratives have `duration: this_battle` and `ACTION` or `CONTINUOUS`, but none has `ongoing` or an Ongoing label. | Under the literal rule, all 12 resolve then leave play, so their ACTION and continuous text cannot work. The two-Ongoing-card limit has no inspectable target. | Define a simple shared **Narrative stays face-up for this Battle** rule and precisely which limit applies, or mark and distinguish persistent Narrative cards on face. Do not invent new subtypes to solve this. |
| R02 | **BLOCKER** | Rulebook §Stratagems: play face-down in a separate area. **The Lines Held** says ‘this Front’; **The Scouts Had Warned Them** expects opponent to set a Stratagem ‘in a Front’. | The Front association and thus legal triggers/targets are undefined. Other global Stratagems do not need a Front, so a single blanket assumption may be wrong. | Specify whether choosing a Front is required for all Stratagems, optional or card-specific, when announced publicly, and what ‘this Front’ means from a separate area. Correct the two printed texts only if the shared rule cannot clarify them. |
| R03 | **BLOCKER** | Printed Reference `web/playmat.html` says lost Fronts Exhaust Forces and Exhaustion persists between Battles; rulebook §§Resolving a Battle and Recovery says lost Fronts do **not** afflict Forces, and all afflictions clear. | A first-time player given both documents receives mutually exclusive core rules about movement and recovery. | Update the Reference to match the resolved canonical rules; remove its stale assertions in both the Front-loss and Between-Battles sections. |
| R04 | **BLOCKER** | Rulebook §§Pass/Cycling: Pass only when no Action is legal; discard 2 → draw 1 is always legal with two hand cards; draw 1 every turn and reshuffle discards. | **Indefinite cycle:** start a turn with one unplayable card; draw another; cycle two into one; end the turn; repeat. With no legal way to progress and no permission to Pass, Battle resolution can stall forever. | Decide how Battles may end in this state without an always-available voluntary Pass. This is a game-rule resolution issue, not merely editing style. |
| R05 | **HIGH** | Rulebook §§Strength/Playing cards says Forces provide Strength; **24 Bonds** and **20 Names** print numeric modifiers, and Hero-as-Name has its own number. | Players are not taught how to calculate the Strength of a Formation (base Force + attached modifiers; what happens if no Force; zero and negative modifiers; whether all ranks sum). | Teach a worked stack and Front-total example before the first movement/combat section. State exactly how Bond, Name, Hero-as-Name, and temporary changes add. |
| R06 | **HIGH** | Cards carry classifications on both Forces and Names. `Elian`, `Sela`, `Corin of the High Wall`, `Tala` and others carry Attack-capable types as Names, while rulebook grants basic Attacks to ‘Forces with classifications’. | Does naming a non-Rider Force with a Rider Name grant the Rider basic Attack? Does a King's Name make the Formation count as a King? This affects targeting, discounts and support. | State which layer determines a Force's available intrinsic Attack, and how class-checking ‘formation containing a …’ and ‘your Kings/Captains/Archers’ works. Include a Name-on-differently-classed-Force example. |
| R07 | **HIGH** | §Your turn lists only play / Maneuver / Attack / cycle. **25 distinct cards** have printed `ACTION` abilities, but their activation as Actions is explained only in §Reference near the end. | A new player can reach Force and Name ACTION cards mid-game without a listed legal Action. | Add “Use an ACTION ability printed on a card in play” to the main turn list, with costs and once-per-Battle markers. |
| R08 | **HIGH** | `The Ground Was Held` reveals when a Front would tie; battle resolution says resolve effects before comparison then settle Fronts. | ‘Would tie’ becomes known only from the comparison; timing and tie-changing effects are not taught. | Add a general response window around Strength comparison and settling, with a small example that does not depend on remembering a particular card. |
| R09 | **MEDIUM** | Rulebook §Narratives lists seven Narrative forms and says forms appear on cards, but none of 12 physical Narrative definitions contains a form field; forms have no rules. | Seven unnecessary nouns cost attention and the reader cannot find their promised markers. | Either actually print meaningful form metadata or remove this catalogue of seven forms from the beginner rules. |
| R10 | **MEDIUM** | §Maneuver contains the separate subsections Afflictions, Boons, Flanking, before §Attacking. Special cards are not introduced until *after* Passing and Battle resolution. | Concepts are learned before the Actions that need them, while the player does not yet know how a Tactic, Order, Narrative or Stratagem is played. | Teach **play/build → Act → Maneuver → Attack → basic card families → Pass/resolve**, then put details of conditions and timing in an approachable reference. |
| R11 | **MEDIUM** | Printed text uses `ATTACK` on The Crow Archers and `MIDDLE`, `BONDED`, `HIDDEN`, `BECOMES NAMED`; §Reading card effects focuses on PLAY/ACTION and a few states. | The header taxonomy is not presented as a small, exhaustive grammar. ‘ATTACK’ looks like a separate Action allowance without explanation. | A compact timing table: PLAY (once), BECOMES NAMED (completion), ACTION (paid Action), ATTACK (modifies the existing basic Attack), state labels (continuous), HIDDEN (Stratagem trigger). |
| R12 | **MEDIUM** | `They Returned With Names`, `The Line Wheeled`, `All Banners Forward`, `Veyra` and `Carried the Oath of` use suppressed/ignored text. | Printed ‘text ignored’ and ‘ability locked’ leave uncertainty about past PLAY effects, persistent buffs, and previously resolved Named triggers. | Specify that suppression prevents future/ongoing application during its duration but does not rewind resolved events; decide whether completion triggers can occur again after attachment changes. |
| R13 | **MEDIUM** | `Swore Again To` allows a Maneuver immediately when playing the Bond completes a Name stack; Name BECOMES NAMED effects can also trigger at this instant. | Players cannot tell whether completion effect or free Maneuver happens first (affects destinations/targeting). | Give a shared ordering convention for PLAY vs BECOMES NAMED and triggered reactions, with this actual combo as example. |
| R14 | **MEDIUM** | `The Battle Had Chosen Them`: “Your Heroes and Named Formations have +1 Strength this Battle.” A Hero-as-Name may be in a Named Formation. | The union of categories can be misread as +1 or +2 on the same Formation. | Define once-per-formation versus per-matching-card treatment; otherwise use “each eligible formation gets +1 only once”. |
| R15 | **LOW** | Card `Guarded` is a Bond that removes a negative marker; the `Guarded` Boon is granted instead by `Endured With`. | Names do not have to reflect mechanics, but this exact rules-term collision invites a wrong assumption. | Consider distinguishing visually or renaming in a later card pass; no immediate change necessary. |
| R16 | **LOW** | §Boons and protection mentions **Druids** and **Carriers**, absent from the 14-current-classification vocabulary. §Timing defines ‘next Action affects a Front’ although **zero** current printed cards use it. | Stale vocabulary implies unsupported classes/mechanics and adds cognitive burden. | Remove unused examples and dormant timing rules from the beginner-facing book; maintain a separate design archive if desired. |
| R17 | **LOW** | Physical stack rules in `cards/visual-spec.md` specify Force below Bond below Name, 10.5 mm exposed strips, but the beginner §Playing cards does not explain how to read buried rules. | Core card operation is invisible behind the Name unless a player understands when to read the upper strip. | Add one physical stack diagram and a rule: PLAY resolves immediately; persistent Force/Bond effects must be readable in the exposed edges; the Name is on top. Rendered pixel proof still pending. |
| R18 | **LOW** | Current playtest deck descriptions still print retired `MOBILE` and `TIRELESS` shorthand, although card grammar uses ordinary phrases. | Reading deck descriptions reintroduces jargon not shown on the cards. | Use ordinary ‘may Maneuver without being Named’ and ‘may Maneuver while Exhausted’ phrasing. |

## Strengths to preserve

- The opening two paragraphs explain the persistent war and spending/losing Command in unusually concrete terms.
- The progressive Front activation schedule appears before setup and makes expanding geography intelligible.
- Normal turn, maneuver adjacency, no diagonal movement, hard row restrictions, and the four Attack targets have concise operative rules.
- Choice to voluntarily end a turn is distinguished from the exceptional Pass procedure, even though the forced Pass criterion itself has a cycle loophole.
- The core vocabulary is reasonably restrained: Force, Bond, Name, Formation, Front, Command, Action; no need to reintroduce SUPPORT/SUPPLY/OUTMATCHED.
- The Reference portion already provides many needed edge cases (prepared cards, attachment return, target legality); they are better as a lookup appendix than repeated on each card.

## Recommended teaching sequence (no rewrite performed)

1. **One-page worked battle overview**: four Fronts, three ranks, goal, Command, Frontline example.
2. **Play and build**: Force→Bond→Name physical stack; numeric modifiers, prepared cards, class scope, normal deployment.
3. **Take a turn**: draw and **five** Action categories, costs, target legality; simple two-Action example.
4. **Position and combat**: Maneuver versus Move versus Swap, row legality; four intrinsic Attacks and Guard screening; then Exhausted/Shaken/Depleted, Boons only when needed.
5. **Special card families**: Tactic, Order, face-up Narrative duration/limit, face-down Stratagem association/reveal, Hero Force/Name modes.
6. **When and how a Battle ends**: resolve Pass cycle problem first; draw/closing turns; Front settlement, collapse, recovery and expansion.
7. **One compact Reference**: timing grammar, suppression, public/hidden information, rare markers, simultaneous choices and explicit glossary. Remove obsolete examples and terms.

Place card-specific exceptional effects and exact targets **on the cards**. Put only shared rules that many cards need **in the rulebook**. Keep an optional reference sheet as a faithful condensation of the rulebook, not an independent source of rules.

## Full printable-card coverage register

This is an inventory of every printable identity, **not a claim that all 131 effects are independent or that all gameplay combinations were playtested**. Labels identify shared comprehension dependencies and extra individual ambiguities. Where a card is tagged “No additional card-specific rule ambiguity,” global blockers above still apply to the game.


### Forces (33)

| Printed card | Rulebook interpretation check |
|---|---|
| The Fifty Men | No additional card-specific rule ambiguity found; global rules still apply |
| Seven Black Ships | No additional card-specific rule ambiguity found; global rules still apply |
| The White Hands of Elara | Teaching: ACTION missing from turn menu |
| The Red Shields | No additional card-specific rule ambiguity found; global rules still apply |
| The Crow Archers | ATTACK label and expanded Archer targeting need reference grammar |
| The House of Reed | Teaching: ACTION missing from turn menu |
| The Grey Riders | No additional card-specific rule ambiguity found; global rules still apply |
| The Dust Riders | No additional card-specific rule ambiguity found; global rules still apply |
| The Black Pursuers | Teaching: ACTION missing from turn menu |
| The Red Duelists | No additional card-specific rule ambiguity found; global rules still apply |
| The Thornbow Hunters | No additional card-specific rule ambiguity found; global rules still apply |
| The Iron Boars | No additional card-specific rule ambiguity found; global rules still apply |
| The First Spear | No additional card-specific rule ambiguity found; global rules still apply |
| The Old Guard | Exception to Shaken Guard screening; text is explicit, but teach screening first |
| The Salt-Road Reavers | No additional card-specific rule ambiguity found; global rules still apply |
| The Late Banner | No additional card-specific rule ambiguity found; global rules still apply |
| The Banner Singers | No additional card-specific rule ambiguity found; global rules still apply |
| Thirty Spears | No additional card-specific rule ambiguity found; global rules still apply |
| A Hundred Shields | No additional card-specific rule ambiguity found; global rules still apply |
| The Vardai | Teaching: ACTION missing from turn menu |
| The Aradai | No additional card-specific rule ambiguity found; global rules still apply |
| The Ilyri | No additional card-specific rule ambiguity found; global rules still apply |
| The Damar | No additional card-specific rule ambiguity found; global rules still apply |
| The Serekh | No additional card-specific rule ambiguity found; global rules still apply |
| The Relief Column | No additional card-specific rule ambiguity found; global rules still apply |
| The Field Train | Teaching: ACTION missing from turn menu |
| The Signal Company | No additional card-specific rule ambiguity found; global rules still apply |
| The Wolf Skirmishers | No additional card-specific rule ambiguity found; global rules still apply |
| The Lantern Scouts | No additional card-specific rule ambiguity found; global rules still apply |
| The River Raiders | Teaching: ACTION missing from turn menu |
| The King's Spears | No additional card-specific rule ambiguity found; global rules still apply |
| The Salt-Road Fleet | No additional card-specific rule ambiguity found; global rules still apply |
| The Watchtowers of Eren | No additional card-specific rule ambiguity found; global rules still apply |

### Bonds (24)

| Printed card | Rulebook interpretation check |
|---|---|
| Followed | Shared: printed Strength modifiers not explained in Strength section |
| Guarded | Title 'Guarded' names a Bond whose effect removes a marker; it does not grant Guarded; Shared: printed Strength modifiers not explained in Strength section |
| Stood Fast With | Shared: printed Strength modifiers not explained in Strength section |
| Marched With | Shared: printed Strength modifiers not explained in Strength section |
| Kept Pace With | Shared: printed Strength modifiers not explained in Strength section |
| Covered the Withdrawal of | Shared: printed Strength modifiers not explained in Strength section |
| Blocked the Road for | Forced-movement immunity: ‘opposing card effects’ does not cover basic Maneuvers; Shared: printed Strength modifiers not explained in Strength section |
| Held the Line for | Shared: printed Strength modifiers not explained in Strength section |
| Seized the Standard of | Shared: printed Strength modifiers not explained in Strength section |
| Stayed Behind For | Shared: printed Strength modifiers not explained in Strength section |
| Swore Again To | Completion-powered free Maneuver needs ordering alongside BECOMES NAMED effects; Shared: printed Strength modifiers not explained in Strength section |
| Endured With | Guarded Boon on PLAY; do not confuse with Bond card named Guarded; Shared: printed Strength modifiers not explained in Strength section |
| Rallied Behind | Shared: printed Strength modifiers not explained in Strength section |
| Bought Time For | Shared: printed Strength modifiers not explained in Strength section |
| Trusted | Shared: printed Strength modifiers not explained in Strength section |
| Marched Beneath the Banner of | Shared: printed Strength modifiers not explained in Strength section |
| Carried the Oath of | Shared: printed Strength modifiers not explained in Strength section |
| Had Been Ordered Forward | Shared: printed Strength modifiers not explained in Strength section |
| Watched the Skies For | Shared: printed Strength modifiers not explained in Strength section |
| Kept the Gate For | Shared: printed Strength modifiers not explained in Strength section |
| Shared the Spoils With | Shared: printed Strength modifiers not explained in Strength section |
| Carried Messages For | Shared: printed Strength modifiers not explained in Strength section |
| Supported By | Shared: printed Strength modifiers not explained in Strength section |
| Supplied By | Shared: printed Strength modifiers not explained in Strength section |

### Names (20)

| Printed card | Rulebook interpretation check |
|---|---|
| Namar | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Iria | Shared: printed Strength modifiers not explained in Strength section |
| Oren | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Elian | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Teren | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Mara | Shared: printed Strength modifiers not explained in Strength section |
| Asha, the Shield-Bearer | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Edrin | Shared: printed Strength modifiers not explained in Strength section |
| Sela | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Meren | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Tala | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Sorin | Shared: printed Strength modifiers not explained in Strength section |
| Iven | Shared: printed Strength modifiers not explained in Strength section |
| Arel | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Torren | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Eira | Shared: printed Strength modifiers not explained in Strength section |
| Corin of the High Wall | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |
| Lysa the Listener | Shared: printed Strength modifiers not explained in Strength section |
| Brannoc | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack; Teaching: ACTION missing from turn menu |
| Maelin | Shared: printed Strength modifiers not explained in Strength section; Shared: Name's role/classification vs Force's basic Attack |

### Heros (11)

| Printed card | Rulebook interpretation check |
|---|---|
| Avaros, the Bronze King | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Kael, the Roadless | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Rovan, the Gatebreaker | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Alda, Keeper of the Ford | Shared: Hero-as-Name Strength + classification scope |
| Tovan, the Quartermaster | Shared: Hero-as-Name Strength + classification scope |
| Nara, Builder of Walls | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Neris, the Ferryman | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Veyra, Keeper of Oaths | Shared: Hero-as-Name Strength + classification scope |
| Yara, the Chronicler | Shared: Hero-as-Name Strength + classification scope |
| Serai, Queen of Crows | Shared: Hero-as-Name Strength + classification scope; Teaching: ACTION missing from turn menu |
| Doros, the Last Spear | Shared: Hero-as-Name Strength + classification scope |

### Tactics (14)

| Printed card | Rulebook interpretation check |
|---|---|
| The Baggage Was Abandoned | No additional card-specific rule ambiguity found; global rules still apply |
| They Returned With Names | No additional card-specific rule ambiguity found; global rules still apply |
| They Were Gathering There | No additional card-specific rule ambiguity found; global rules still apply |
| The Muster Was False | No additional card-specific rule ambiguity found; global rules still apply |
| They Had Gone Too Far | No additional card-specific rule ambiguity found; global rules still apply |
| All Banners Forward | No additional card-specific rule ambiguity found; global rules still apply |
| The Line Wheeled | No additional card-specific rule ambiguity found; global rules still apply |
| They Let Them Through | No additional card-specific rule ambiguity found; global rules still apply |
| All Reserves Forward | No additional card-specific rule ambiguity found; global rules still apply |
| The Line Had Begun to Move | No additional card-specific rule ambiguity found; global rules still apply |
| A Volley Before Dawn | No additional card-specific rule ambiguity found; global rules still apply |
| The Scouts Found the Gap | No additional card-specific rule ambiguity found; global rules still apply |
| The Stores Were Taken | No additional card-specific rule ambiguity found; global rules still apply |
| The Line Was Baited | No additional card-specific rule ambiguity found; global rules still apply |

### Orders (6)

| Printed card | Rulebook interpretation check |
|---|---|
| Fresh Orders | No additional card-specific rule ambiguity found; global rules still apply |
| Catch Your Breath | No additional card-specific rule ambiguity found; global rules still apply |
| Re-form the Line | No additional card-specific rule ambiguity found; global rules still apply |
| Bind the Wound | No additional card-specific rule ambiguity found; global rules still apply |
| Send a Runner | No additional card-specific rule ambiguity found; global rules still apply |
| Take Stock | No additional card-specific rule ambiguity found; global rules still apply |

### Narratives (12)

| Printed card | Rulebook interpretation check |
|---|---|
| The Long March | **BLOCKER** Narrative duration/ongoing classification not defined on face |
| The Wall Did Not Break | **BLOCKER** Narrative duration/ongoing classification not defined on face |
| The Crows Came Down | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| Before Sunset, the Ford Would Be Ours | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| They Lived to Tell It | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| No Road Was Too Long | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| The Battle Had Chosen Them | Hero + Named Formation may overlap; is the +1 counted once or twice?; **BLOCKER** Narrative duration/ongoing classification not defined on face |
| No One Would Be First to Leave | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| The King Had Given the Order | Bond exchange: whether completion effects retrigger and what may be exchanged; **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| Every Bow Was Strung | **BLOCKER** Narrative duration/ongoing classification not defined on face |
| They Knew the Ground | **BLOCKER** Narrative duration/ongoing classification not defined on face; Teaching: ACTION missing from turn menu |
| The Raiders Came Home Loaded | **BLOCKER** Narrative duration/ongoing classification not defined on face |

### Stratagems (11)

| Printed card | Rulebook interpretation check |
|---|---|
| The Ground Was Held | Front tie trigger needs explicit timing relative to Strength settlement; Shared: public Front association and reveal timing |
| The Lines Held | **BLOCKER:** ‘this Front’ on a Stratagem with no stated placement Front; Shared: public Front association and reveal timing |
| No Step Back | Shared: public Front association and reveal timing |
| The Center Must Hold | Shared: public Front association and reveal timing |
| The Flank Was Refused | Shared: public Front association and reveal timing |
| The Trap Closed | Shared: public Front association and reveal timing |
| The Battle Turned East | Shared: public Front association and reveal timing |
| There Was No Road Back | Shared: public Front association and reveal timing |
| Every Banner Turned Toward Them | Shared: public Front association and reveal timing |
| The Archers Were Ready | Shared: public Front association and reveal timing |
| The Scouts Had Warned Them | **BLOCKER:** reacts to setting a Stratagem ‘in a Front’, but rules use a separate area; Shared: public Front association and reveal timing |

## Scope verification

- 131 distinct `id` values across 33 Forces, 24 Bonds, 20 Names, 11 Heroes, 14 Tactics, 6 Orders, 12 Narratives, and 11 Stratagems.
- Used the **16 print-only card replacements** and four print-only ACTION timing fixes, rather than accidentally auditing only the canonical native cards.
- Checked the physical `web/playmat.html` Reference because the rulebook itself tells first-time players to use that sheet.
- Not a playtest, native executable rules test, art-legibility test, or full print-fit test; static correspondence and readability only.
- **No rules, card text, engine or visual component was changed by this audit.**
