# Physical playtest scenarios — rules reconciliation (October 2026)

**Scope:** print-only. These are reproducible tabletop checks, not a claim that the game has been physically playtested or balanced. Use the [rulebook](../rules/rulebook.md), the 131 printed cards with `print-overrides.json`, and the printed Reference/marker sheet. Leave native/Webgame behavior out of these tests.

The aim is to catch **unfun consequences** (unanswerable movement locks, unavoidable one-card wins, obvious infinite loops) as well as unclear instructions. For every scenario, record whether players knew the next legal Action **without consulting the design documents**.

## 1. Passing creates a deliberately short endgame

During Battle I, leave both players with several playable cards. At the **start of Player A's turn, before drawing**, A voluntarily Passes. A draws no card, spends no Actions. Player B draws 1 and takes up to 2 Actions; A then draws 1 and takes up to 2 Actions. Resolve the Battle immediately. Neither closing turn may Pass or extend the countdown. If the war continues, B starts Battle II.

**Check:** does Passing create meaningful urgency without allowing the passer to ambush by drawing immediately before deciding?

## 2. Front loss causes one future Battle of Exhaustion

After comparing Fronts, A loses Front 2 with three Forces in Frontline, Middle and Rear. The Middle Force is **Guarded**. Deduct 1 Command and check Collapse. A selects **Frontline** for defeat-caused Exhaustion. Clear all old conditions and Boons, then give **only that Force** one new Exhaustion token; Middle and Rear do not receive new tokens. Frontline has **−1 Strength** and cannot initiate ordinary Maneuvers next Battle, but may still Attack if not Depleted.

Repeat by selecting the **Guarded Middle Force** instead. Guarded prevents its Exhaustion and is consumed; do not select a replacement. Repeat with an empty lost Front: no Exhaustion occurs. At the following Battle end, clear any old Exhaustion; another loss permits choosing just one Force again.

**Watch for:** more than one new loss-based token per Front, clearing Guarded before prevention, or selecting another Force when Guarded prevents the chosen affliction.

## 3. Flanking influences Strength without adding a marker

During Battle I, A has a 3-Strength Frontline Force in Front 2, but none in Front 3. B has a Frontline Force in Front 3. A's Frontline Force in Front 2 is flanked and contributes 2 Strength. If Shaken, it contributes 0 (3−1−2, floored at 0). A then puts any legal friendly Frontline Force into Front 3, closing the flank: the first formation's Strength rises immediately by 1. No Exhaustion or Shaken is caused solely by being flanked, and two exposed sides would not multiply the −1.

**Watch for:** players remembering both the −1 and conditions without unnecessary tokens.

## 4. Names make new Attacks available

Play a Human Force without an Attack classification, attach a +1 Bond and attach **Elian** (Rider Name). The formation is Named and inherits Rider, so it may attempt a basic Rider Attack if an opposing flanked Frontline Force is present in an adjacent active Front. It may not both Rider Attack and use a different basic Attack that Battle. If Elian is removed, it immediately loses the Rider classification. Prepared Elian without a Force cannot Attack on its own.

**Watch for:** Names feeling transformative versus Attack-class combinations becoming too easy or too strong.

## 5. Completion sequences are intentionally powerful

Put a Force and **Mara** (Name) in one position, with no Bond. Play **Swore Again To** as the Bond. Its PLAY effect grants an immediate no-Action/no-Command Maneuver, subject to other Maneuver restrictions; resolve that movement first. Then Mara's BECOMES NAMED effect lets you inspect the opponent's hand and optionally Move. Return the Bond through a legal card effect; the Force with Name is no longer Named. Playing a different Bond later can trigger Mara again. An unused PLAY effect on a Bond prepared earlier does not start when that Bond attaches by movement.

**Watch for:** legal spatial combinations and degenerate resource loops; do not automatically suppress BECOMES NAMED just because it can be repeated.

## 6. Prepared cards are legal movement destinations

Prepare a Bond and Name together in a position with no Force. Move a bare Force into that adjacent active position using a legal card Move: both prepared layers attach and the formation becomes Named. The prepared cards' old PLAY effects do not replay; BECOMES NAMED text triggers. Repeat with an incoming Force already holding a Bond: the move is **illegal** because two Bonds would collide. No card is silently discarded.

**Watch for:** clear card placement without ever lifting a stack to inspect buried active abilities.

## 7. Suppression is not removal

Attach a King Name to a Force and resolve a completed-Named Command gain. An opponent plays **They Returned With Names** and suppresses the Name text for this Battle. Do not take back Command already gained. The Name's printed +Strength and King classification still count, but its ACTION and ongoing text are unavailable until suppression expires. **The Line Wheeled** is a stronger printed exception because it explicitly removes a Bond's Strength contribution too.

**Watch for:** confusion between suppressing text, reducing Strength and removing an attachment.

## 8. The single simultaneous Stratagem window

Both players set one face-down Stratagem publicly at the same active Front. Before comparison, provisional Strength would tie at 5–5. One player has **The Ground Was Held** and is the only player with a Named Formation there; the other has **The Lines Held**, with an eligible Middle formation to move and an empty Frontline. Both privately choose to reveal, and both choices are shown at once. The Lines Held moves its formation and gives +2; the Front no longer ties, so The Ground Was Held does **not** override that final result. No later tie-break window opens.

Repeat from a provisional 5–4 non-tie in which the *Ground Was Held* owner is leading by 1: it is **not** eligible merely because another reveal later creates a 5–5 tie. Now reverse the scores so its owner **loses 4–5** with a Named Formation and the opponent has none. It may reveal, giving +2 Strength to that Named Formation and winning 6–5. Eligibility is evaluated before any reveal, and the two branches are not interchangeable.

**Watch for:** meaningful hidden information versus a single lucky reveal determining the result with no counterplay.

## 9. Front-assigned scouting and reactions

Set **The Scouts Had Warned Them** face-down at a Front containing one of your Scouts or Seers. When your opponent sets a Stratagem **in that same Front**, you may reveal yours, inspect theirs, and give one friendly Force there Guarded. If your opponent sets a Stratagem elsewhere, this trigger does not fire. Try **The Scouts Found the Gap** to reveal an opposing face-down Stratagem involuntarily; its opponent may pay to set it down again as the Tactic specifies.

**Watch for:** Front assignment being genuinely meaningful without revealing hidden identity prematurely.

## 10. Four simultaneous Narratives

Play four Narratives across turns; their CONTINUOUS text applies only when eligible, and printed ACTION text still requires its own Action. A fifth Narrative cannot be played while four are face-up. At Battle end, discard all four. Test at least one pairing of movement discount + front-rearrangement or faction support. Check that an effect such as **The Battle Had Chosen Them** applies +1 only once per formation that is both a Hero and Named, while independent Narratives still stack.

**Watch for:** satisfying combinations versus excessive persistent bonuses and board-memory burden.

## 11. Exhaustion / Maneuver exceptions create recovery choices

Give a named **Grey Riders** formation Exhaustion by losing a Front. It may still initiate a Maneuver if its printed rule allows it, although its Exhaustion token remains until recovery or cleanup. Try the same with a non-exempt Force supported by **The Relief Column** or **Covered the Withdrawal of**: the exception should follow the exposed support effect and disappear if that support leaves. A card **Move** may still reposition an Exhausted formation without using a Maneuver.

**Watch for:** recovery cards mattering without Exhaustion becoming a hard permanent trap.

## 12. Physical print integrity

Print one Force+Bond+Name stack and one Hero+Bond+Name stack at **actual size**, leaving the bottom card and middle card's **10.5 mm top strips** exposed. Confirm that every **ongoing** buried effect can be read without lifting the Name, including Grey Riders' two movement permissions. Confirm that PLAY-only text may be covered. Read the updated Reference next to the cards and flag any different rule.

## Evaluation record

For each scenario record: **Rules lookup needed?**, **unanticipated outcome?**, **meaningful decision?**, **opponent counterplay?**, **too much marking?**. Do not conclude the system is balanced from a static audit; revise problematic *effects* rather than simply adding more cards. Keep the 131 identities fixed until actual physical games justify a change.

## Phases 2–3: condition and preparation regression scenarios

These are **manual test instructions**, not logged playtest results.

### Exhaustion now changes a real Front outcome

At the start of Battle II, A has a 3-Strength Force, +1 Bond and +1 Name in
Front 2. It lost this Front in Battle I and carries Exhaustion. It now has
**4 Strength instead of 5** and may still Attack. If B contributes exactly 5
Strength here, B wins unless A removes Exhaustion or plays another Strength
source. If the Force also receives Depleted, its strength becomes **3** and
it cannot Attack or use Oren's ACTION if Oren is its attached Name. Remove
Depleted and the same Oren ACTION becomes available again, provided it has
not been used already that Battle.

**Check:** the two independent −1 penalties and source-layer ACTION lock are
tracked, and previously used ACTION allowances do not reset.

### Conditions stack but cannot make another formation weaker

Use a 5-Strength Force at a flanked Frontline position. Apply Exhausted
(−1), Depleted (−1), and Shaken (−2). The flank contributes another −1:
the formation has **0 Strength**, not −1. A friendly 4-Strength Force in that
Front still contributes all 4 Strength. Reapplying Exhausted leaves the
first Force at 0 rather than subtracting another point. Give it Guarded
before applying a card that Exhausts and then Shakes: Guarded prevents the
first Exhaustion and is spent, so Shaken can still apply.

**Watch for:** extra token stacking, subtracting below 0 or Guarded blocking
the entire two-step Tactic rather than one affliction.

### Preparing a defensive Bond should be useful immediately

A has a Force in the Frontline and an empty Rear position in the same Front.
A plays **Guarded** into the Rear, without a Force there, and chooses the
Frontline Force for Guarded. The prepared Bond still contributes no Strength.
When a Force later enters that Rear position, the Bond attaches but its
PLAY ability does **not** fire again. Repeat with **Endured With** and Inspired.

**Check:** the existing Force is protected immediately, the prepared Bond
remains visible, and attachment does not duplicate the Boon.

### House of Reed can finish two prepared layers in one ACTION

A controls **The House of Reed** in Middle. A already has three prepared
layers in its Front, and friendly Forces with available Bond or Name slots,
including one in Frontline directly ahead. When House of Reed is played, its PLAY may attach one prepared
layer directly ahead. On a subsequent turn, its **once-per-Battle ACTION**
may attach up to two remaining prepared layers, one at a time, to legal
friendly formations in that Front. If a particular attachment genuinely
completes Named, resolve its BECOMES NAMED triggers and then give that
Force Guarded. The second layer is not automatically another Named event.
Returning the House of Reed and playing the same physical card again does
not refresh its already spent once-per-Battle ACTION.

**Check:** each individual attachment is legal, no second Command is
charged for prepared components, no old PLAY effects replay and no
unearned Guarded is granted.

### Field Train and Swore Again To are different completion rewards

With **The Field Train** in Middle, arrange a friendly Force directly ahead
that has a Bond but no Name. Prepare a Name in an adjacent active Front.
Playing Field Train attaches that Name across the Front boundary. The
resulting Named Formation gets **+2 Strength this Battle**, after its
BECOMES NAMED effect. Next, directly play **Swore Again To** as the missing
Bond on a Force that already has a Name: it gets another temporary +2
Strength from the Bond's own PLAY effect. But if Swore Again To is prepared
first, it only draws 1/discards 1 immediately and does not award that
PLAY-based +2 when it eventually joins a formation.

**Check:** the adjacent Front is active, all placements are legal and no
PLAY effect runs twice.

### Measure comeback viability, not merely legality

In separate matched trials, give A a lost Front with three surviving Forces and B an otherwise identical winning Front. The current rule imposes **at most one −1 Strength** from defeat in that Front next Battle. Test how A recovers with fresh Forces, healing, a Boon, an Attack or Named completion. Repeat with Guarded on A's *selected* Force, which prevents that loss Exhaustion. Compare against the historical all-Forces rule only as an explicitly labeled counterfactual. Record actual Front results and Command totals; these scenarios are not balance measurements.

## Phases 4–5: surprise interactions and combo consistency

These are **physical tabletop scripts**, not results of automated matches.

### Hidden protection: Tactic or Attack, never both

Player A sets **No Step Back** at Front 2. Player B declares a legal Archer
Attack that would Exhaust A's Rear Force there. A may reveal the plan
**before** applying Exhausted. The Attack is still spent; the Exhaustion
is prevented and the plan is discarded. Repeat with a Tactic targeting that
formation: the plan can instead ignore that Tactic's effect on the formation.
It cannot be revealed twice or cancel unrelated effects on another Front.

**Record:** was either branch consequential to a Strength result, and was
the timing evident without looking up the rules?

### The Ground Was Held: down by exactly one

Set the Ground Was Held for a Front in which A has a Named Formation, B has
no Named Formation, and provisional Front totals are A=5, B=6. A may reveal
and give one Named Formation +2 to make A=7. Repeat from A=5, B=7:
**not eligible**. From A=6, B=6, the tie-break wins only if the Front
remains tied after the other simultaneous reveal effects. Do not open a new
reveal window.

**Record:** did the hidden one-point comeback create meaningful counterplay?

### Scout and Seer react with actual protection

A's Scout occupies Front 2 and sets **The Scouts Had Warned Them** there.
When B sets a new hidden Stratagem at Front 2, A can reveal, look, and give
one friendly Force there Guarded. With **Before Sunset, the Ford Would Be
Ours** face up, a newly set Stratagem in Front 3 (adjacent to that Scout)
may instead produce +2 temporary Strength on one friendly formation in
Front 3. If no formation is present in Front 3, looking still occurs but
that +2 is unavailable.

**Record:** was the revealed information worth paying an Action/Command,
and was its protective effect used?

### Whole-Front exchange must be all-or-nothing

In Battle II (three active Fronts), place differently sized and marked
formations in Fronts 1 and 2, with a prepared Bond in one empty rank.
Play **No Road Was Too Long** for 3 Command. Exchange each matching rank
between the adjacent active Fronts, taking entire stacks and attached
markers and preserving prepared layers without replaying PLAY effects.
Choose one moved Named Formation to gain +2 temporary Strength. The full
exchange must be legal before starting. Neither player's opponent-side
cards move. Re-test with a Frontline-only Force and with incompatible
prepared/attachment arrangements.

**Record:** did the exchange change a Front winner enough to justify its
3 Command and Action without making it an automatic winner?

### Suppression and forced retreat

With a Scout or Skirmisher in Front 2, play **They Had Gone Too Far**
against B's opposing Frontline Force. If its matching Middle position is
empty and the Force can legally occupy it, Move it there. Otherwise
apply Shaken (−2 Strength). With a Skirmisher use **The Line Was Baited**:
only a *successful* move into the Rearward adjacent legal position gives
Depleted; if blocked it inflicts nothing. With **They Let Them Through**,
target an opposing Named Formation and suppress its printed ACTION
abilities plus the attached Name's Strength modifier for the Battle.

**Record:** effect success, legal counterplay, any unexpectedly
unconditional −2 Strength or condition suppression.

### Main-deck combo availability versus actual usefulness

Use all four Phase 5 decks. For each one, track three printed combo
packages: first legal opportunity to combine an enabler and payoff, whether
the two cards were jointly useful that Battle, real changes to Front winners,
and Command/Actions spent. The [deck guide](playtest-decks.md) includes
hypergeometric baseline probabilities for *seeing* both categories in
10/20 cards; those numbers are **not** the expected activation rate.
Run mirrored opening hands and starting players, paying particular attention
to Rear congestion in Crown of Crows and prepared-layer congestion in
Oathforge.

### Three isolated coverage lists

Use [Rider & Flank, Seer & Hidden Plans, and Front Exchange &
Preparation](mechanic-coverage-decks.md) as separate diagnostic lists.
Do not force their rare classifications into the main decks. Run the
same layouts with Battle I, II, III and a saturated late board. Record
Stratagems discarded unrevealed, number of legal Riders' flanked targets,
Seer-supported Named formations, and successful Front exchanges.

## Card-language, raw Strength and snowball review

This section documents **future tabletop comparisons**. It does not change
the canonical physical rules or claim that any match was played.

### Similar printed effects must read alike

Put The Red Shields, The Serekh, Supported By, Alda and The Banner Singers
side by side. Each Tactic surcharge should clearly identify *whose* Tactic
is affected and *which* friendly target is protected; do not apply a
self-protection ability to adjacent formations automatically. Compare
The River Raiders and Seven Black Ships for the same open-Frontline
attachment return instruction at different timings. Compare The
Field Train and The House of Reed for legal prepared-card transfer and
the Named completion reward.

Inspect both Hero modes on physical cards; the print-only Hero text must
not change the native/Webgame data.

### Simple Forces against Named formation investment

Set two active Fronts with room. Player A has Thirty Spears (3S, 1C),
Fifty Men (5S, 2C) and Hundred Shields (6S, 3C). Player B has Fifty
Men with Followed and a Name (8S after Named completion, 4C total).
Record number of *card-play Actions*, total Command, occupied ranks and
Strength at the moment of each Battle resolution. In a late saturated
board, compare replacing one plain Force with a Bond+Name improvement
to an existing Force.

Repeat using [Raw Strength Control](mechanic-coverage-decks.md#raw-strength-control)
against each core deck with mirrored hand/deal order. The simple deck
does not automatically win: track conditions, attached-card disruption,
Guards, targeted Stratagems, and how often cards become unplayable.

### Current loss rule versus historical all-Force comparison

Under the **current physical rule**, after losing a Front with three unprotected friendly Forces, the loser chooses **one Force** for the new Exhaustion. It gives at most **−1 Strength** in the next Battle. A chosen Guarded Force prevents the affliction instead; no replacement is selected.

For a separately labelled **historical comparison only**, apply the old all-unprotected-Forces rule: the same Front would lose up to **−3 Strength** next Battle. Keep the identical −1 Command penalty, Collapse timing, draw and recovery schedule to isolate the change.

**Record:** repeated Front losses, comeback opportunities and the impact of recovery or Guarded. Do not mix historical-variant results into normal games.
