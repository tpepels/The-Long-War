# Physical D6 cards — print and dice coordination

This is **not** an extra rules document. The [short paper rulebook](../rules/rulebook.md) and four [drawable Orders](paper-d6-orders.json) define the current game. Every Force's wording is in [paper-d6.json](paper-d6.json). The old `Nothing` slot has become playable support on all 44 Forces; the six dice assignments remain unchanged.

## Printed card hierarchy

Each Force has its name in the top band, with Force and permitted ranks; artwork takes the next large section. Four D6-result passages follow in the lower portion, with one die cue, short bold action verbs, lighter conditional clauses and generous spacing instead of four table rows. Command cost and classification are visible without the old layering/exposure zones. The physical template and headless 44-card layout check, not an old fixed artwork measurement, determine fit.

## Tactical cohesion

Players roll one shared D6 per occupied Front. A card's six-face mapping determines how its four printed effects cooperate with other Forces on that roll. These mappings and every individual result probability have been preserved in the **44-Force identity pass**.

Read the [complete 44-card interaction matrix](paper-d6-identity-matrix.md) for the individual identities, six verified shared-roll formations and proposed counterplay. All interactions are on the cards, with no new universal rules, markers or combo keywords.

Print and content regression checks:

```sh
python tools/check_paper_d6.py
python tools/check_paper_d6_synergy.py
python tools/check_paper_d6_identity.py
python tools/check_paper_d6_layout.py
```

The 44 distinctive Specials are design hypotheses. Simultaneous combat and Command outcomes need further physical playtesting; passing structural tests does not establish balance.
