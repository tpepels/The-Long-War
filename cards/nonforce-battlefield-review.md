# Non-Force battlefield-agency audit

**9 October 2026 — printed paper game only.** This is the missing
design-philosophy review following the Incursion and Force-price passes.
Its purpose is **not** to check only economic coherence: the question is
whether a card causes an actual **Attack, Maneuver, threat, interception,
deception, or counterdecision**. The separate native/AI runtime still does
not represent the current printed game.

## Scope and rule of restraint

Every **98 non-Force identities** was examined in
[`nonforce-battlefield-audit.json`](nonforce-battlefield-audit.json).
The decisions are **18 revised, 62 kept, 18 watch**. These are editorial
judgements, *not* observed playtest results. The count by type is:
24 Bonds, 20 Names, 11 Heroes, 14 Tactics, 11 Stratagems,
12 Narratives and 6 Orders.

**Card text can break the usual pattern, but it must explain the exception.**
We did **not** add a generic Move-and-Attack rule, a Raid mission phase,
a new keyword/classification, extra tokens, Force deaths, or more Command
loss. Most revised text is one short PLAY/HIDDEN/ACTION effect. The two
new free-Attack opportunities explicitly require an **unused Attack**,
not an extra Attack use. Previously persistent formations and the
Command economy are unchanged.

Not every card should cause combat. Plain Strength support, recovery,
layer attachments, simple cheap protection, and resource smoothing are
necessary alternatives to aggressive play. The target is meaningful
choices, **not maximum rules text on every card**.

## Revised card effects

| Family | Card | Battlefield difference |
| --- | --- | --- |
| Bond | **Kept Pace With** | Rider/Scout may Move as the Bond is played |
| Bond | **Rallied Behind** | Command-behind recovery can also reposition a friendly formation |
| Bond | **Carried Messages For** | Scout/Captain can scout a face-down enemy plan and reposition a formation |
| Bond | **Watched the Skies For** | View a nearby opposing hidden plan before hand filtering |
| Name | **Iria** | On Named completion, scout a nearby plan and reposition an ally |
| Name | **Lysa the Listener** | Hand knowledge plus immediate Guarded protection |
| Name | **Elian** | Paid Move with the formation's **unused** basic Attack, without another Action |
| Hero | **Kael — Name** | On Named completion, examine opposing plans and Move |
| Hero | **Rovan — Force** | A stronger Frontline Gatebreaker Shakes and may push the defender back, if legal |
| Hero | **Neris — Force** | Once-per-Battle Move and unused Rider Attack as a single ACTION |
| Hero | **Serai — Name** | Paid Archer repositioning instead of an ineffectual −1 Strength ACTION |
| Tactic | **They Returned With Names** | Shake a Named Force while suppressing its Name text this Battle |
| Stratagem | **The Lines Held** | Hidden resolution Move; the moved formation receives +2 Strength |
| Stratagem | **The Center Must Hold** | King's/Captain's hidden reallocation of a formation with +2 Strength |
| Stratagem | **The Flank Was Refused** | Outer-Front defender may reposition before scoring and gain +2 Strength |
| Narrative | **They Knew the Ground** | Immediate Move and conditional Seer Guarded, not a passive cross-Front aura |
| Narrative | **The Raiders Came Home Loaded** | Immediate Move of up to two Raiders/Skirmishers instead of repeated Tactic discounts and movement triggers |
| Order | **Send a Runner** | Move a Rear Scout and draw a card, rather than only filtering the hand |

For each change, compare not only the final outcome, but the **best
alternative use of the Action**. A +2 surprise at resolution matters when
it changes who wins a Front. Moving a formation is worthwhile when it
changes flanking, access to a basic Attack, the ability to defend a
threatened rank, or a different Front's outcome.

### Important timing examples

- **Elian/Neris** grant a free basic Attack *only as part of their
  printed movement ability*. Both still consume that Force's normal
  once-per-Battle Attack. They do not let an ordinary Maneuver grant
  an Attack to any Force.
- **Rovan** compares current complete formation Strength against the
  opposing Frontline **before** applying Shaken. A backwards Move obeys
  occupancy and printed row restrictions. A strong defender resists.
- **Hidden resolution Moves** are processed in the existing single
  Stratagem window, with normal simultaneous eligibility and
  conflicting-Move rules. They do not open extra response windows.
- **Scouting** is paired with an immediate action—Move, Guarded, or
  a card filter—so a peek is not useful only in a far-future turn.
- **Raider Narrative** permits one bounded deployment of two troops;
  it no longer creates a sequence of free Moves every time an eligible
  Tactic is played.

## Why 62 other cards were deliberately left alone

- **Bonds** still need permanent or temporary Strength, Guarded,
  attachment handling and some Maneuver eligibility. They are a major
  reason to invest in a Named Formation, not a second class of Tactics.
- **Names** need powerful completion moments, protection, discounted
  assembly and classification rewards. A few simple Named payoffs make
  the more tactical cards worth building toward.
- **Heroes** must retain meaningful Force/Name alternatives. Repricing
  Hero Strength or changing the once-per-Battle allowances is not
  justified by this editorial pass.
- **Tactics** already contain real hostile pressure: Shaken,
  Depleted, forced rearward Moves, Bond suppression/return and Tax.
  Adding arbitrary free Attacks would make them overly efficient.
- **Stratagems** need both proactive and defensive surprises; prevention,
  counterattacks, hidden information and a few plain Strength swings
  preserve uncertainty.
- **Narratives** can express a temporary battlefield doctrine.
  We retained bounded class buffs and recovery where they have a
  recognizable role, rather than converting every Narrative into
  yet another Move.
- **Orders** offer cheap, Action-consuming friendly responses;
  healing, withdrawal, useful card selection and Captain coordination
  are meaningful counterplay.

## The 18 remaining watches

These are **not** passed as balanced. The tracked risks are:

| Risk | Cards | What to measure |
| --- | --- | --- |
| Rare positional or prepared prerequisites | Covered the Withdrawal of; Kept the Gate For; Stayed Behind For; Supplied By; Nara | How often is the required position actually legal before another Action would be better? |
| Large/expensive buildup | Namar; Eira; Tovan; Yara | Does investment pay off without a runaway Command or card-advantage engine? |
| Swingy permanent or hidden effects | Seized the Standard of; Brannoc; The Ground Was Held | Can the opponent counteract a cheap attachment loss or late result flip? |
| Persistent passive amplification | The Long March; The Battle Had Chosen Them; Every Bow Was Strung | Do passive multipliers discourage actively attacking and Maneuvering? |
| Multi-action or avoidable plans | The Crows Came Down; The Line Had Begun to Move; Re-form the Line | Are the effects ever worth their Actions and permanent sacrifices? |

The [72 focused playtest questions](preplaytest-focus.json) include an
opportunity, a realistic alternative, and a failure signal for every
revised or watch-listed identity. Do not replace a watch card without
evidence that the interesting decision does not reliably occur.

## What this does **not** establish

This pass keeps exactly **131 card identities** and all existing
Command prices. It verifies printed wording, timings, family coverage,
website output and layout. It does **not** provide observed win rates,
real move activation frequencies or proof that the early loser can
recover. Measure how many Attacks and legal Moves are actually chosen
instead of a fresh Force and whether those decisions can reverse a
Front without destroying the losing army.
