# First 80 - reference decks

These four 40-card decks are initial balance/playtest reference decks built from the approved first-80 pool. They are deliberately strategic builds, not coverage decks: cards were selected for the deck plan rather than to ensure every title appeared somewhere.

| File | Deck | Forces | Bonds | Names | Narratives | Stratagems | Heroes | Unique cards |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `decks/mobility-open-bonds.json` | Mobility / Open Bonds | 15 | 9 | 7 | 4 | 5 | 3 | 12 |
| `decks/persistent-elite-heroes.json` | Persistent Elite / Heroes | 16 | 9 | 7 | 3 | 5 | 5 | 13 |
| `decks/narrative-command.json` | Narrative / Command | 14 | 9 | 7 | 7 | 3 | 2 | 11 |
| `decks/battlefield-control-stratagems.json` | Battlefield Control / Stratagems | 15 | 8 | 6 | 4 | 7 | 2 | 8 |

All four decks:

- contain exactly 40 cards;
- meet the minimum Force and printed-Name requirements;
- obey Unique and non-Unique copy limits;
- contain only IDs from `cards/cards.json`.

## Strategic identities

### Mobility / Open Bonds

Built around sideways movement, incomplete/open-Bond formations, prepared cards, and chaining position changes.

Core package includes:

- The Grey Riders
- The Dust Riders
- The Unnamed Host
- The Late Banner
- Kael, the Roadless
- Veyra, Keeper of Oaths
- Marched With
- Kept Pace With
- Carried the Oath of
- Marched Beneath the Banner of
- Eira
- No Road Was Too Long
- The Line Wheeled
- The Battle Turned East

### Persistent Elite / Heroes

Built around forming a smaller number of valuable Named Formations and keeping them alive across Battles.

It deliberately carries five Heroes, the highest Hero density of the four decks.

Core package includes:

- Avaros, the Bronze King
- Rovan, the Gatebreaker
- Alda, Keeper of the Ford
- Tovan, the Quartermaster
- Nara, Builder of Walls
- The House of Reed
- The Old Guard
- Stayed Behind For
- Swore Again To
- Edrin
- The Wall Did Not Break
- No Step Back

### Narrative / Command

Built around generating, preserving, and converting Command through Narratives.

It has seven Narratives and only three Stratagems, the most Narrative-heavy composition.

Core package includes:

- The Banner Singers
- Yara, the Chronicler
- Rallied Behind
- Bought Time For
- Trusted
- Endured With
- The Baggage Was Abandoned
- The Wall Did Not Break
- They Returned With Names
- They Lived to Tell It
- Before Sunset, the Ford Would Be Ours
- No Road Was Too Long

### Battlefield Control / Stratagems

Built around Front geometry, Strength denial, Front-specific combat rules, and Battle-wide plans.

It has seven Stratagems and only six printed Names.

Core package includes:

- The Red Duelists
- The Thornbow Hunters
- The Iron Boars
- The First Spear
- Held the Line for
- Seized the Standard of
- Blocked the Road for
- The Center Must Hold
- The Flank Was Refused
- The Line Wheeled
- The Trap Closed
- They Let Them Through
- All Reserves Forward
- The Battle Turned East

## Cross-deck inclusion signal

Across the four independently constructed decks:

- 1 card appears in all four decks;
- 2 cards appear in three decks;
- 33 cards appear in two decks;
- 43 cards appear in one deck;
- 1 card appears in none.

### The Fifty Men - 4/4 decks

This is the clearest generic-staple warning.

At 2 Command it is a printed Strength 4 Force that is normally Strength 5 in the Frontline, with no setup requirement beyond position. It fit every strategy despite none of the decks being built around it.

This does not prove it is overpowered, but it is the first card to watch for automatic inclusion.

### Followed - 3/4 decks

The Bond appears in Mobility, Persistent Elite, and Narrative/Command.

Its +3 Strength when the formation is Named is useful to almost every deck trying to build persistent formations. The Battlefield Control deck is the only one whose more specialized Bond package displaced it.

This is a second candidate for being too generically efficient.

### The Wall Did Not Break - 3/4 decks

The Legend appears in Persistent Elite, Narrative/Command, and Battlefield Control.

Its success condition is relatively forgiving because a tie counts as "did not lose"; on success it refunds 1 Command, and a win can also recover a Bond.

Its broad usefulness outside a dedicated Narrative deck makes it worth watching.

## Omitted-card signal

### Covered the Withdrawal of - 0/4 decks

> After an adjacent formation you control Retreats, you may Maneuver this formation for 0 Command.

This was not selected even though both the Mobility deck and Battlefield Control deck contain relevant movement/Retreat themes.

The effect requires:

1. an adjacent formation to lose and Retreat;
2. this formation to still be positioned appropriately;
3. a useful Maneuver to exist afterwards.

That is a lot of situational setup for a Bond that gives no benefit until the player has already lost an adjacent Front.

This is the clearest initial underpowered/too-narrow candidate from deck construction alone.

## Interpretation

These are deck-building signals, not balance verdicts.

The first cards to watch in actual play are therefore:

Potentially too generically attractive:
- The Fifty Men
- Followed
- The Wall Did Not Break

Potentially too narrow:
- Covered the Withdrawal of

Do not change these solely from this audit. Use games/simulations to establish whether their inclusion or exclusion is actually associated with performance.
