# Fixed hand-size sweep

This experiment compares fixed **9, 10, and 11-card** Battle hand targets with the once-per-Battle **Draw** action disabled. It uses the flexible-formation / between-Battle recycle rules from PR #17 and preserves the existing Battle-I starter compensation (+1 opening card to the player acting first).

Each variant contains **8,000 heuristic mirror matches**: 2,000 Reference, 2,000 Avaros, 2,000 Mara, and 2,000 Sera. All variants use identical per-profile seeds.

## Summary

| Metric | 9 cards | 10 cards | 11 cards |
| --- | ---: | ---: | ---: |
| Matches | 8,000 | 8,000 | 8,000 |
| Battles/match | 2.61 | 2.61 | 2.60 |
| Cards/Battle | 13.04 | 14.03 | 14.98 |
| Cards/player/Battle | 6.52 | 7.01 | 7.49 |
| Complete Subject–Bond–Name formations/Battle | 0.81 | 0.98 | 1.14 |
| Names/Battle | 1.49 | 1.72 | 1.91 |
| Hand size at Pass | 2.74 | 3.28 | 3.82 |
| Dead-card share at Pass | 6.5% | 7.0% | 7.8% |
| Unplayable card-turn share | 1.8% | 2.0% | 2.2% |
| First passer wins Battle | 65.0% | 58.9% | 52.9% |
| Legal candidates/heuristic decision | 21.35 | 23.60 | 25.69 |

## Initial first-player match balance

| Profile | 9 cards | 10 cards | 11 cards |
| --- | ---: | ---: | ---: |
| Reference | 46.5% | 45.5% | 47.0% |
| Avaros | 45.8% | 47.1% | 44.4% |
| Mara | 47.6% | 48.1% | 44.2% |
| Sera | 48.5% | 48.3% | 45.5% |
| Equal-profile average | 47.1% | 47.2% | 45.3% |

## Interpretation

**9 cards** is not attractive. It reduces complete formations to 0.81 per Battle and makes passing first strongly advantageous under the current final tie-break.

**10 cards** preserves good initial-player balance and keeps the decision space lower, but first-passer Battle win rate is still 58.9%. Complete formation frequency remains essentially one per Battle across both players.

**11 cards** produces the cleanest Pass tension of the three: first-passer Battle win rate is 52.9%. It also raises Name play and complete formation frequency. The costs are more card plays, a larger action space, and a modest initial-first-player disadvantage in the Avaros and Mara mirrors.

The hand-size sweep therefore does **not** solve the low complete-formation frequency. Even 11 cards produces only 1.14 complete formations per Battle across both players. The limiting structure is deck composition: every current 30-card profile contains 12 Subjects but only 4 Names. A 10-card random hand contains only 1.33 Names on average; an 11-card hand only 1.47.

The next structural experiment should therefore change component ratios rather than continue increasing hand size. A useful first target is around **10 Subjects / 7 Bonds / 6 Names / 5 Stories / 2 Stratagems** in a 30-card playtest deck, followed by the same playability telemetry.

## Flank design direction

Left and Right should become tactically distinct **Flanks** rather than interchangeable scoring columns. A promising minimal rule is to make **complete formations** unlock facing:

- a complete formation on Left/Right may remain upright to **Hold** or rotate inward to **Flank Center**;
- a complete formation in Center may remain upright or rotate toward one side to **Guard** that flank;
- one guard does not protect both flanks;
- flank pressure should transfer strength rather than create free additional strength, to avoid a snowball where winning a Flank also automatically wins Center;
- prepared or incomplete formations cannot maneuver.

The physical rotation can be represented by rotating the **Name** card, which makes the Name the visible command layer of the completed Subject–Bond–Name formation.

No flank rule is implemented by this experiment; this section records the design direction for the next rules discussion.
