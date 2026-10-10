# The Long War — physical-card wording and terminology guide

**Scope:** adopted editorial guidance for the physical-print card faces and both rulebooks, based on the full 131-card audit of `50971d2a`. The October 2026 copy pass applied 94 card passages and 31 rulebook passages; a subsequent preprint ruling pass resolved seven previously open physical-game interactions. This document is a writing convention, **not a new game rule or keyword**; check current printed text for actual mechanics.

## 1. Prioritize the player's reading order

A player should read, in order: the card's **type**, **timing label**, **one- or two-sentence effect**, and finally any conditional exception. Place a restriction next to the operation it qualifies. Avoid an effect that must be re-read backward to determine whether the condition applied.

Write **“Give a friendly Force Guarded”** rather than **“Choose one of your friendly Forces, if any, and give that chosen Force Guarded”**, unless the card's selection itself matters. Don't omit an essential location, legal target, optional word (“may”), sequence (“then”) or use limit to save a line.

## 2. Existing timing labels (do not add new ones)

| Printed text | Write the effect as | Editorial cautions |
|---|---|---|
| PLAY | Immediate effect in imperative form | A prepared Bond/Name resolves PLAY when played, not when it later attaches. |
| BECOMES NAMED | State what happens at an actual formation-completion event | No retrigger merely from moving or exchanging Bonds between already-Named formations. |
| ACTION | Verb first; any additional Command payment second | Costs **one Action** already; no extra Action unless explicitly required. Do not silently add a once-per-Battle limit. |
| TRIGGER / REACTION | Begin with **When [specific event], …** | Keep trigger, eligibility and any one-per-Battle limit explicit. |
| HIDDEN | Begin with **At resolution, …** or **When/After [specified trigger], …** | The one-set-Stratagem limit and assigned Front are shared; don't repeat them unless a card specifically changes them. |
| FRONT / MIDDLE / REAR | **While in Frontline/Middle/Rear, …** | Labels are reminders, but the current visual specification requires a self-contained body sentence. |
| BONDED / WHILE NAMED / CONTINUOUS | **While Bonded/Named, …** where the condition matters | Leave the card readable even when its label is covered or read aloud separately. |
| ATTACK | State which existing basic Attack gains what target/condition | Never imply an extra Attack; the normal used-Attack limit still applies. |

Do not equate **TRIGGER** with **REVEAL**, or a printed **Move** with a paid **Maneuver**.

## 3. Nouns and locations

Use the actual game nouns consistently: **Force** (the card/attacker), **formation** (Force and attached layers in one position), **Bond**, **Name**, **Bonded Formation**, **Named Formation**, **Front**, **Frontline**, **Middle**, **Rear**. Avoid “troop,” “unit,” “square,” and “tile” inside rules text unless used only in a narrative example. “Frontline” is one rank, not a synonym for the whole Front.

Use **“in this Front”** or **“in the same Front”** when the location is important. **“Directly ahead/behind”** means the neighboring rank of the same Front; **“adjacent Front”** means left/right. The physical rulebook now establishes **“here” = the card's Front** for all stationed Force/Bond/Name/Hero cards, and the assigned Front for a Stratagem. Prefer “this formation” when the single attached stack is intended. Avoid changing one into the other during copy-editing.

Classifications such as **Rider**, **Guard**, **Scout**, **Seer**, **King**, and **Captain** come from a Force and its attached Name. If a card applies to several categories, one formation matching more than one receives that card's effect once. Only symbols for explicit card-family/classification *references* belong inline with prose, at most two per effect; never substitute rebus icons for ordinary words.

## 4. Verbs with fixed meanings

| Verb/term | Use | Do not write as |
|---|---|---|
| **Move** | Printed effect: relocate the complete formation via the card's range and legal occupancy; a normal one-step Move is adjacent | “Maneuver” unless the ability truly uses Maneuver rules |
| **Maneuver** | Normal paid action, or a card explicitly permitting/discounting a Maneuver | A generic Move or swap |
| **swap** | Exchange the full contents of two specified legal positions | Two sequential Moves that may allow intermediate triggers |
| **Attack** | Make the Force's legal basic Attack; mark that Attack used | A card's affliction that merely happens to resemble an Attack |
| **Exhaust / give Shaken / give Depleted** | Apply the named marker, subject to prevention and repetition limits | “Damage,” “hit,” “wound” as additional game effects |
| **give Guarded / give Inspired / give Empowered** | Grant the defined Boon | A vague “protect” that obscures which marker stops what |
| **return to its owner's hand** | Return the named attached or prepared layer | “Discard,” because Bond discard has different consequences |
| **ignore [text]** | Suppress card text when the rules allow | “Remove [card]” or suppress printed Strength automatically |
| **draw N cards, then discard M** | Sequence matters; discard chooses from the new hand | “Replace cards” without the hand-selection timing |
| **look at / reveal** | Private inspection versus compelled public reveal | Interchangeable verbs; the effects on Stratagems differ |

## 5. Restriction language

Prefer **“if”** for eligibility, **“when”** for triggers, and **“after/then”** for resolved sequence. Retain **“may”** for an actual option. Avoid adding “may” to a mandatory instruction: this changes mechanics (for example Teren's free Stratagem set). Do not omit **“if it moves”** from cards where affliction depends on a successful displacement.

Spell out a special target such as **“an opposing Middle Force”**, **“an attached Bond”**, or **“one legal adjacent empty position”** only if narrower than the shared default. The word **“legal”** can be omitted if it merely repeats universal placement rules, but **“empty”**, **“same rank”**, **“while Exhausted”**, or **“Frontline-only”** may be essential and must be retained.

Costs: **“Pay 1 Command”** is an additional ability cost, not the printed seal price. Use **“cost 1 less Command (minimum 0)”** or **“(minimum 1)”** consistently. Never repeat a Hero mode's seal cost in its rules text. Numbers (Strength, Command, draws) should use digits. Preserve explicit **“this Battle”** where it scopes an effect; do not drop a meaningful duration for brevity.

## 6. Card-text boundaries

What the rulebook should teach once: active Fronts; one Force/Bond/Name per position; prepared attachment and PLAY-versus-BECOMES NAMED order; one normal Action per play/Attack; ordinary Maneuver versus card Move; legal targets and screening; once-per-Battle Attack limits; one Stratagem set per Battle; simultaneous Opening Orders; the single resolution window; persistence, cleanup and Collapse.

What each card should still say: **which specific target** it can affect; **whether it overrides** a restriction; **which event** makes an effect trigger; **how many targets, positions, steps, cards or markers** it changes; **whether resolution is optional**; **which unusual timing/row/class restriction** is unique to that card.

## 7. Print access and visual checks

The current design specification uses **68 × 96 mm** cards and a **10.5 mm** formation overlap. Full body prose must remain self-contained; exposed-strip cues are reminders, not extra rules. Preserve the established rule: icons only for explicit card-family/classification references, at most two distinct such references per effect. Timing labels, row bars and existing one-use sockets must not be replaced with extra decorative icons.

After adopting any editorial copy, validate the exact printed text in the card lab, including Hero dual-mode faces, buried Force/Bond reminders, and legal-row icon alignment. Use the repository's Chromium print-overflow check and a printed 100%-scale proof. A shorter sentence is not necessarily easier to read if punctuation, line breaks or tiny type worsen the printed result.

## 8. Copy-edit release checklist

- [ ] Exact current **before** text matches the selected print override/source mode.
- [ ] No altered target, optionality, row restriction, number, payment, duration or trigger.
- [ ] Move/Maneuver, suppression/return/discard, and Attack/card-inflicted affliction remain distinct.
- [ ] No new timing symbols, keywords or exceptions introduced.
- [ ] Reference and short player rulebook teach the same mechanics.
- [ ] Full body text is independently readable even when a cue is hidden.
- [ ] Browser clipping and 100%-size paper print are legible.