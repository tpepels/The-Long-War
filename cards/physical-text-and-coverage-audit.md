# Physical card text and deck coverage audit — 9 October 2026

**Source:** 131 printed card identities assembled from `cards/cards.json`
and `cards/print-overrides.json`. The print-only Hero wording layer is
included. The native/Webgame's executable card texts are not changed.

## Writing grammar

Use these conventions when creating and reviewing effects, including both
Hero modes:

1. **Rows:** Frontline, Middle, Rear. Use *Front* only for one of the
   four battlefield columns. Do not say "Front row" or "Rear row".
2. **Effects and targets:** A visible formation's local effects say
   "in this Front"; for a Stratagem already assigned to a Front, "here"
   refers to that assigned Front. For a cross-Front effect, name which
   Front can supply the source and which must contain the target.
3. **Conditions:** "Exhaust it", "Give it Shaken", "Give it Depleted" and
   "Give it Guarded". The rulebook defines their consequences; don't
   repeat numerical penalties or marker rules on every card.
4. **Strength:** "gets +2 Strength this Battle" for temporary effects;
   "has +1 Strength" or "contributes +1 additional Strength" for an
   ongoing bonus. A **negative Strength value uses the − sign**.
5. **Attachments:** Say "Attach a prepared Bond or Name ... if legal"
   and "Return its attached Bond to its owner's hand." This does not
   replay PLAY text; the rulebook explains the timing.
6. **Movement:** Capitalize **Move**, **Maneuver**, **Attack** and printed
   timing labels consistently. Distinguish a forced Move from a
   Maneuver; "one row toward Rear" means one rank only.
7. **Conditional traps:** Describe the eligible trigger first, then
   exactly one alternative or consequence. Don't restate the
   simultaneous reveal procedure on every Stratagem.
8. **Readable sentences:** Prefer one short target/condition sentence
   and one effect sentence over several nested clauses. Avoid
   abbreviations or icon-only mechanical meanings.

The audit standardized 31 earlier printed effects, shortened additional
dense multi-step text, and corrected another six Hero Force/Name effect
wordings with a new **print-only** override mechanism. The 131 identities
and their intended Command/Strength/effect behavior are preserved.
`tools/check_physical_wording.py` inspects all printed effect texts,
including Heroes. It flags leftover row/negative-Strength vocabulary and
advises on unusually long effects, but does **not** freeze card designs
with brittle exact-text assertions.

## Similar abilities are intentionally different

| Cluster | Shared language | Intentional difference |
| --- | --- | --- |
| Return a Bond/Name | Return a specified attached component to its owner's hand | Some require an open opposing Frontline, some an Exhausted or Depleted target |
| Temporary Strength | Give an eligible formation ±N Strength this Battle | A positive bonus, a negative penalty, and persistent Strength are not interchangeable |
| Reveal hidden plans | When an opposing Stratagem is set here, look at it | Scouts Had Warned grants Guarded; Before Sunset gives +2 in the Stratagem's Front; Lantern Scouts filter the hand |
| Prepared attachment | Attach a prepared Bond or Name to a legal formation | Field Train can source an adjacent Front; House of Reed can attach two via ACTION |
| Forced retreat | Move an opposing Force one row toward Rear, if legal and empty | They Had Gone Too Far gives Shaken if blocked; Line Was Baited gives Depleted only if moved |
| Protective taxation | Opposing Tactics targeting [specified formation] cost +1 Command | Red Shields protect themselves; Serekh and Supported By protect the formation directly behind |
| Name/Action suppression | Ignore specified text or disable ACTION abilities this Battle | They Returned With Names suppresses Name text; They Let Them Through also removes printed Name Strength |

**Readability limits:** static language checking does not establish actual
text fit on a printed card or whether human playtesters understand the
effect on first reading. Check dense effects at actual-size print and
collect rules lookup count per card; simplify any that repeatedly require
explaining. Where shorter text would erase a critical exception, keep the
exception rather than relying on designer intent.

## 100% card coverage

Previously **25 of 131** card identities were absent from all seven decks.
Two additional **48-card supplementary combo/coverage decks** now represent
all those identities:

- **The Last Watch:** losing-Front recovery, Heal/Steward support,
  protective Bonds, Guard screens, and emergency defensive plans.
- **Broken Oaths:** Scouts, Skirmishers, Raiders, forced retreats,
  prepared-layer sabotage and economic pressure.

These supplement the original four core combo decks. The Last Watch has
more one-copy entries because many previously untested defensive Bonds and
recovery cards are distinct single cases. Treat it as an exploratory list,
not evidence of competitive consistency.

The four diagnostic lists test Rider/flank, Seer/Stratagem,
Front-exchange/preparation, and **Raw Strength Control**. They are still
distinct from the main combo decks. The validator now requires all 131
printed identities to appear in **at least one** of the ten lists; it
checks legal card counts, copy limits and package membership.

## Design judgment

The core four decks are **based on repeatable combinations**, not purely
archetype names: leadership + Bond Strength, Archer + screening/reactions,
prepared Named completion, and Exhaustion + Command/attachment disruption.
Not every claimed combo is equally meaningful: a high-Strength Force plus
a generic +1 effect is often merely a good curve. Judge packages by whether
their interaction changes the optimal legal play, not just by whether
their components are simultaneously drawn.
