# Physical playtest scenarios — rules reconciliation (October 2026)

**Scope:** print-only. These are reproducible tabletop checks, not a claim that the game has been physically playtested or balanced. Use the [rulebook](../rules/rulebook.md), the 131 printed cards with `print-overrides.json`, and the printed Reference/marker sheet. Leave native/Webgame behavior out of these tests.

The aim is to catch **unfun consequences** (unanswerable movement locks, unavoidable one-card wins, obvious infinite loops) as well as unclear instructions. For every scenario, record whether players knew the next legal Action **without consulting the design documents**.

## 1. Passing creates a deliberately short endgame

During Battle I, leave both players with several playable cards. At the **start of Player A's turn, before drawing**, A voluntarily Passes. A draws no card, spends no Actions. Player B draws 1 and takes up to 2 Actions; A then draws 1 and takes up to 2 Actions. Resolve the Battle immediately. Neither closing turn may Pass or extend the countdown. If the war continues, B starts Battle II.

**Check:** does Passing create meaningful urgency without allowing the passer to ambush by drawing immediately before deciding?

## 2. Front loss causes one future Battle of Exhaustion

After comparing Fronts, A loses Front 2 with three Forces in Frontline, Middle and Rear. The Middle Force is **Guarded**. If B has 8 total Strength and A has 5, deduct **3 Command** (the defeat margin), then check Collapse. A selects **Frontline** for defeat-caused Exhaustion. Clear all old conditions and Boons, then give **only that Force** one new Exhaustion token; Middle and Rear do not receive new tokens. Frontline has **−1 Strength** and cannot initiate ordinary Maneuvers next Battle, but may still Attack if not Depleted.

Repeat by selecting the **Guarded Middle Force** instead. Guarded prevents its Exhaustion and is consumed; do not select a replacement. Repeat with an empty lost Front: no Exhaustion occurs. At the following Battle end, clear any old Exhaustion; another loss permits choosing just one Force again.

**Watch for:** more than one new loss-based token per Front, clearing Guarded before prevention, or selecting another Force when Guarded prevents the chosen affliction.

## 3. Flanking influences Strength without adding a marker

During Battle I, A has a 3-Strength Frontline Force in Front 2, but none in Front 3. B has a Frontline Force in Front 3. A's Frontline Force in Front 2 is flanked and contributes 2 Strength. If Shaken, it contributes 0 (3−1−2, floored at 0). A then puts any legal friendly Frontline Force into Front 3, closing the flank: the first formation's Strength rises immediately by 1. No Exhaustion or Shaken is caused solely by being flanked, and two exposed sides would not multiply the −1.

**Watch for:** players remembering both the −1 and conditions without unnecessary tokens.

## 4. Names make new Attacks available

Play a Human Force without an Attack classification, attach a +1 Bond and attach **Elian** (Rider Name). The formation is Named and inherits Rider, so it may attempt a basic Rider Attack if an opposing flanked Frontline Force is present in an adjacent active Front. It may not both Rider Attack and use a different basic Attack that Battle. If Elian is removed, it immediately loses the Rider classification. Prepared Elian without a Force cannot Attack on its own.

**Watch for:** Names feeling transformative versus Attack-class combinations becoming too easy or too strong.

## 5. Completion sequences are intentionally powerful

Put a Force and **Mara** (Name) in one position, with no Bond. Play **Swore Again To** as the Bond. Because it completes a Named Formation, its PLAY effect gives that formation **+2 Strength this Battle**, then Mara's BECOMES NAMED effect lets you inspect the opponent's hand and optionally Move. Repeat by playing Swore Again To on a formation that remains Unnamed: instead, draw 1 card and discard 1 card. Return the first Bond through a legal card effect and play a different Bond to complete that formation again; Mara's BECOMES NAMED ability may resolve again. An unused PLAY effect on a Bond prepared earlier does not start when the Bond attaches by movement.

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

Give a Named **Grey Riders** formation Exhaustion by losing a Front. It may still initiate a Maneuver if its printed rule allows it, although its Exhaustion token remains until recovery or cleanup. Try the same with a non-exempt Force supported by **Covered the Withdrawal of** or **Trusted**: the exception follows the exposed Bond and disappears if that Bond leaves. Alternatively, play **The Relief Column** in Middle to remove all temporary negative markers from **another** Force in its Front and give it Guarded; it does not grant Maneuver permission. A card **Move** may still reposition an Exhausted formation without using a Maneuver.

**Watch for:** recovery cards mattering without Exhaustion becoming a hard permanent trap.

## 12. Hero mode cost and role selection

Put **Avaros**, **Tovan** and **Doros** on the table. Avaros costs 5 Command when played as a 5-Strength King Force, but 4 as a +1 Name. Tovan costs 3 as a 2-Strength Force, but 4 as a Name with ongoing discounts. Doros costs 5 as a 5-Strength Force, but only 1 as a +1 Name. Pay the chosen mode's price and apply only that mode's Strength and effects; there is no extra charge for being dual-mode. Repeat by preparing Tovan as a Name, paying **4 Command** on PLAY; later attachment does not replay his PLAY effects or require another Command payment. Verify that a discount referring to Names affects the Name price, not the Force price.

**Check:** both labelled prices legible on a printed Hero at actual size; single Hero Force and Hero Name allowances still respected; ability/Strength from the unchosen mode never applies.

## 13. Physical print integrity

Print one Force+Bond+Name stack and one Hero+Bond+Name stack at **actual size**, leaving the bottom card and middle card's **10.5 mm top strips** exposed. Confirm that every **ongoing** buried effect can be read without lifting the Name, including Grey Riders' single compact ongoing mobility-and-Attack rule. Confirm that PLAY-only text may be covered. Read the updated Reference next to the cards and flag any different rule.

## Pre-playtest usefulness and dominance checks

### Leadership disruption is not generic Name suppression

Give B a Named Captain in Front 2 and another Force in the same Front. A holds **All Banners Forward** and **They Let Them Through** (both cost 1 Command). Playing All Banners Forward gives the Captain's Force Shaken and applies −1 Strength to the other opposing formation this Battle. Playing They Let Them Through instead disables an opposing formation's ACTION abilities and removes its Name Strength if Named, **without applying Shaken**. Compare actual Front totals with the Captain's ACTION already spent: the choices must still differ. Repeat with an Unnamed Captain Force and with no King/Captain in play: All Banners Forward requires the leader but remains playable without a Name; without a leader it is not legal.

**Watch for:** an attractive leadership-specific payoff without creating universal 1C multi-target shutdown.

### The Ilyri's movement needs another occupied position

A has a friendly Frontline Force under threat; Middle is empty. Play **The Ilyri** into Middle and choose to swap with that Frontline Force. Move both formations into each other's places, keeping Bonds, Names and conditions attached to their Forces. Give the displaced Frontline Force Guarded. Contrast with placing The Ilyri in Frontline directly: ordinary deployment cannot both reposition the existing Force and Guard it. Repeat with a row-restricted friendly formation that cannot legally occupy the new row: no swap and no Guarded. Repeat without a second Force: The Ilyri remains a 2-Strength Skirmisher with its ordinary Attack option.

**Watch for:** the swap actually protecting something worth protecting; the 2-Strength fallback being enough to justify a 3C conditional tool.

### One-Action opportunity cost for logistics and scouting

During Battle II, compare playing **The Field Train** in Middle and spending Command for one additional Bond or Name from hand without another Action, versus spending two Actions to play those cards separately. Compare **The Signal Company's** immediate Move of an existing Force with a normal 1C Maneuver or a directional Move effect; count whether it changes a flank and draws a card. Compare **The Relief Column's** all-condition removal and Guarded with a 1C Guarded Bond or ordinary healing, counting the target's value. For scouting, record whether **The Watchtowers of Eren**, **The Lantern Scouts** and **Before Sunset, the Ford Would Be Ours** ever cause a different legal decision after inspecting a hidden Stratagem.

**Watch for:** spending Command and Actions to enable something that cannot pay back the tempo before this Battle ends. Count the legal setups that *could* have occurred, not just card draws.

### Lab-only cards do not disappear from the results

Before ordinary matched decks, run the targeted specialist cases for the 20 cards that appear in no standard deck (see `cards/preplaytest-readiness.md`). Record a playable/useful opportunity even when the ability never triggers; an unseen card is not evidence that its ability works.

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

Hold **The Field Train** and a Name in hand. Have a friendly Bonded
Force in an adjacent **active** Front with an empty Name slot. PLAY Field
Train in Middle (3 Command, one Action). As part of its PLAY, choose that
Force and play the Name from your hand, paying the Name's Command but **no
additional Action**. Resolve the Name's PLAY text if any, then its BECOMES
NAMED effects; Field Train gives the completed formation **Guarded**.
Rewind and instead spend one Action on Field Train and a second Action on
the same Name: Command is the same, but tempo and Guarded reward differ.
Field Train does **not** attach already-prepared layers.

Next, directly play **Swore Again To** as the missing Bond on another
Force with a Name: the Bond's own PLAY awards **+2 Strength this Battle**.
If Swore Again To is prepared first, its PLAY filters cards instead; it
does not award PLAY-based +2 when it attaches later.

**Check:** no free Command, no extra Action for the second hand play,
the adjacent Front is active, Name PLAY and completion trigger exactly
once, and Guarded is granted only on actual Named completion.

### Measure comeback viability, not merely legality

In separate matched trials, give A a lost Front with three surviving Forces and B an otherwise identical winning Front. The current rule imposes **at most one −1 Strength** from defeat in that Front next Battle. Test how A recovers with fresh Forces, healing, a Boon, an Attack or Named completion. Repeat with Guarded on A's *selected* Force, which prevents that loss Exhaustion. Compare against the historical all-Forces rule only as an explicitly labeled counterfactual. Record actual Front results and Command totals; these scenarios are not balance measurements.

## Phases 4–5: surprise interactions and combo consistency

These are **physical tabletop scripts**, not results of automated matches.

### Hidden protection: Tactic or Attack, never both

Player A sets **No Step Back** at Front 2. Player B declares a legal Archer
Attack that would Shake A's Rear Force there. A may reveal the plan
**before** applying Shaken. The Attack is still spent; the Shaken
affliction is prevented and the plan is discarded. Repeat with a Tactic targeting that
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
The River Raiders and Seven Black Ships for the same Strength-gated Raider
attachment removal at different timings. Compare The
Field Train's extra **card played from hand** with The House of Reed's
**transfer of already-prepared layers**, checking Command and Action
payments and the Named completion reward.

Inspect both Hero modes on physical cards; the print-only Hero text must
not change the native/Webgame data.

### Simple Forces against Named formation investment

Set two active Fronts with room. Player A has Thirty Spears (3S, 2C),
Fifty Men (5S, 4C) and Hundred Shields (6S, 5C). Player B has Fifty
Men with Followed and a +1 Name (8S after Named completion, 6C total).
Record *card-play Actions*, paid Command, occupied ranks and effective
Strength at Battle resolution. In a saturated late board, compare a
new Force with a Bond+Name improvement to an existing one. Test
whether high Command costs make Forces stranded in late Battles when
recovery falls to 3, then 1.

Repeat using [Raw Strength Control](mechanic-coverage-decks.md#raw-strength-control)
against each core deck with mirrored hand/deal order. The simple deck
does not automatically win: track conditions, attached-card disruption,
Guards, targeted Stratagems, and how often cards become unplayable.

### Current loss rule versus historical all-Force comparison

Under the **current physical rule**, after losing a Front with three unprotected friendly Forces, the loser chooses **one Force** for the new Exhaustion. It gives at most **−1 Strength** in the next Battle. A chosen Guarded Force prevents the affliction instead; no replacement is selected.

For a separately labelled **historical comparison only**, apply the old all-unprotected-Forces rule: the same Front would lose up to **−3 Strength** next Battle. Keep the same full Strength-margin Command loss, Collapse timing, draw and recovery schedule in both trials to isolate the Exhaustion change.

**Record:** repeated Front losses, comeback opportunities and the impact of recovery or Guarded. Do not mix historical-variant results into normal games.

## Tactical-combat prototype: immediate Incursions, not missions

These scenarios use the **printed paper pool**, not the native game engine.
Each Incursion is a basic Raider Attack: one Action, once per Force per Battle.
It is not movement into the opponent's positions and uses no marker.

### A locally weaker line can be penetrated

Put A's 4-Strength Raider in Frontline opposite B's 5-Strength Frontline
Force. Put a B Force in Rear. The Raider cannot Attack Rear: 4 is not greater
than 5. Apply Shaken to B's Frontline, reducing its current Strength to 3.
Now A's Raider can Attack B's Rear and give it Depleted, marking A's Attack
used. Resolve the same test with 4 versus 4: **tie blocks Incursion**.
If B has no Frontline Force, the Raider succeeds with any positive Strength,
provided an opposing Middle or Rear Force can be targeted.

**Check:** current formation Strength (including Bond, Name, penalties,
flanking), not just printed Force Strength. This Attack consumes the ordinary
Attack Action; it does not relocate the Raider or remove either Force.

### Archer pressure differs from post-defeat Exhaustion

Let A Archer target B Rear with no screening Guard. Its basic Attack
gives **Shaken (−2 Strength)**, not Exhaustion. Add B Guard in Middle:
the same basic Archer Attack is screened until Guard is Shaken or Depleted
(or a card grants a screening exception). At Battle resolution, choose
**one** B Force in each lost Front for next-Battle Exhaustion.
B may choose a Guarded Force to prevent it, with no replacement choice.

**Check:** no automatic multi-Force Exhaustion and no extra Command tax
from Archers or Incursions.

### A card may grant the combined Action; the rules never do

Place a Grey Rider where a legal Maneuver creates a new flanked enemy
Frontline target. Its printed ability grants its unused basic Rider Attack
without another Action after the Maneuver. If it has already Attacked,
it cannot Attack again. Now use an ordinary Named Rider without that printed
ability: it must spend **separate Actions** to Maneuver and Attack.

Place a Vardai in a legal position. Its once-per-Battle ACTION pays 1 Command
to Move and then make an unused Rider Attack if legal. An inactive Front,
an occupied destination, Depleted, or spent Attack still prevents the
corresponding part of the effect. The next turn cannot refresh Vardai's
once-per-Battle ACTION.

Finally play Damar while another Raider can Move forward into a legal
Frontline position. If this **newly creates** a legal basic Raid target, the
Raider may make its unused Attack as part of Damar's PLAY. An Attack target
that was legal before the Move does not satisfy Damar's bonus.

**Check:** one Action is saved only on the printed cards; no free
Maneuver, no infinite Attack chains and no unused-Attack refresh.

### Deploying Raider specialists is no longer empty-Frontline only

Try Seven Black Ships and River Raiders in Frontline opposite a weaker,
occupied opposing Frontline. Each may choose a basic Raider Attack target
for its attachment-return effect. The Ship does this immediately on PLAY;
the River Raider spends its separate ACTION and 1 Command. Neither effect
itself consumes the Force's Attack (the card did not say to Attack), but
their target still must pass the basic Raider's legal-target check.
When the opposing Frontline is stronger, neither may remove an attachment
through that ability.

**Watch for:** whether changing the local check creates a response window,
rather than allowing strong Raider Forces to overwhelm every other archetype.

## Post-Incursion economy correction: six printed effects and two prices

These tabletop counterfactuals require no new rules beyond the basic Attack
and Action menu.

1. **3C Thirty Spears**: play beside another friendly formation. That
   other formation gains +1 Strength **this Battle only**. Repeat with an
   otherwise empty friendly Front: no target, no bonus. Compare the same
   3C with Aradai in Frontline reducing the opposing Frontline by 1.
2. **4C Fifty Men**: play when another Human formation already occupies
   the same Front; the Fifty Men get +1 this Battle. Replay the same
   scene without another Human: the 5 Strength still counts, but no +1.
   Compare the same 4C with Red Shields' persistent Guard screening.
3. **4C Damar**: legally Move another formation toward Frontline. Permit
   a free basic Attack only if the Move makes that Attack **newly legal**.
   Re-run with a target already legal before Move, or an already-used
   Attack: no free Attack. Compare a 3C Vardai paying a separate 1C ACTION.
4. **2C Volley Before Dawn**: a friendly Archer anywhere in the Front
   lets the Tactic give an opposing **Frontline, Middle or Rear** Force
   Shaken. An ordinary Archer Attack still reaches only Rear and is
   subject to Guard screening. Compare Action and Command value.
5. **1C Shared the Spoils With** (0 Strength): after a Shaken enemy
   appears in the same Front, play the Bond and Move one friendly
   Raider/Skirmisher a legal adjacent position. Do not steal Command.
   When there is no Shaken enemy or legal Move, the Bond remains a
   zero-Strength investment.
6. **2C Brannoc**: complete a Named Formation while an opposing Shaken
   formation carries a Bond/Name; return one attachment. Then check
   Brannoc's **separately paid ACTION** remains available at its previous
   repeatability and 1C per activation. Exhaustion alone does not
   activate the Named-completion effect.

**Watch for:** losing-side affordability after Battle I; whether the
substantial Damar double action earns its +1 premium, and whether any
low-cost Bond/Tactic now strictly dominates an expensive Force Action.

## Role-led support cards: combat, movement and intrigue without new phases

The following are **ordinary card effects**. Resolve each in its
PLAY/ACTION/HIDDEN window; none modifies the universal Action menu.

1. **Elian** becomes Named on a Raider in Middle. After a legal
   1C ACTION Move to Frontline, the Raider may use its **unused** basic
   Attack if the Incursion Strength check succeeds. It is one Action,
   not two Attacks. Try the same with a used Attack: no second Attack.
2. **Neris** in Force mode may Move and make an unused basic Rider
   Attack on its 1/BATTLE ACTION. Check the opposite side's flanking
   at the new position. Compare the Hero's Command and Action value
   with a 3C Vardai and a plain Named Rider Maneuver.
3. **Rovan** enters Frontline facing a weaker Frontline defender.
   Shaken applies; optionally push the defender back **only if**
   its row restrictions and destination permit. Repeat with an
   equal-Strength defender: no breakthrough. Do not destroy cards.
4. **Kept Pace With / Carried Messages For**: a friendly Rider or
   Scout can Move on Bond PLAY; a Scout/Captain can peek at an
   opposing face-down Stratagem in its Front before making a local
   Move. Track whether information changes the positional choice.
5. **Iria / Lysa / Kael-as-Name**: complete a Named Formation.
   Iria can retarget an announced Opening Strike after reveal; Kael may peek and Move;
   Lysa inspects the opponent's hand and protects a Force with
   Guarded. No general information-triggered free Actions arise.
6. **Three distinct hidden resolution plans**: The Lines Held grants
   one late legal Move and +2; The Center Must Hold exchanges one
   formation across adjacent Fronts with a legal same-rank partner;
   The Flank Was Refused cancels a flanked outer Frontline Force's
   penalty and gives it +2. Each player can set **only one**
   Stratagem in total. Check eligibility after the Opening Orders,
   before simultaneous resolution reveals.
7. **They Returned With Names**: Shake an opposing Named Force
   and suppress that Name's text for this Battle; attachments
   remain in place and regain normal text at Battle cleanup.
   Compare this 2C Action with a cheaper single-purpose Tactic.
8. **The Raiders Came Home Loaded**: Move at most **two**
   Raider/Skirmisher formations on PLAY. No persistent Tactic
   discount or repeated Move triggers remain. Record whether
   either Move enables a later Attack before resolution.
9. **They Knew the Ground / Serai / Send a Runner**: a Seer
   protects a moved ally; Serai may spend 1C and one ACTION to
   reposition an Archer; Send a Runner Moves a Rear Scout and
   draws a card. None causes a free basic Attack by itself.

These tests must record the **actual change of Attack legality,
flanking, Front winner or informed defensive response**, not
only whether an effect's printed text could execute.

## Two secret Opening Orders and full Strength-margin losses

**Identical timing in every Battle, including Battle I:** Players
take normal turns and may deploy Forces. Someone eventually **Passes**.
The opponent takes one full closing turn, then the passer takes one full
closing turn. **Only then** both secretly write **two numbered Opening
Orders**. Reveal all four together; resolve the orders, then reveal
eligible Stratagems and score the Fronts. There is no special early
deployment turn or opening window before the Pass.

1. **Double Commit:** A has a Force with 5 Strength in Front 2.
   A secretly records **Commit Front 2 twice**. Reveal; pay 2 Command,
   gain **+4 Front Strength** while any friendly Force remains in that
   Front. This does **not** change the individual 5-Strength Force's
   Incursion eligibility. Move the only friendly Force away: the
   bonus no longer counts. Put another Force in the Front later:
   both Commit bonuses count again until Battle end.
2. **Maneuver + Strike:** A records opening Maneuver into Frontline
   (slot 1), and Strike with that same Raider against B's Middle
   Force (slot 2). B records Maneuver of its Frontline blocker
   (slot 1) and Hold (slot 2). Commit, if any, resolves first;
   simultaneously resolve slot-1 Maneuvers, then slot-2 Strike.
   Check the Raider's current Formation Strength against B's
   post-Maneuver Frontline. If greater or empty, Attack is legal;
   otherwise the Strike fails and **does not consume** the Attack.
3. **Strike + Strike:** A writes two Strikes with the same Archer.
   On reveal, both target an eligible Rear Force. The first
   Attack resolves and marks used. The second does nothing: one
   Force still gets at most **one basic Attack per Battle**.
   Repeat using two different legal Archers: both may Attack.
4. **Opposing simultaneous Strikes:** Both choose Strike in the
   same numbered slot against legal targets. Check both Attacks
   **before applying either**. If one inflicts Depleted on the
   other attacking Force, this does not retroactively cancel
   the simultaneous legal Attack. Normal Guarded prevention and
   reactive Stratagem timing still apply.
5. **Two Maneuvers:** A records the same legal formation moving
   one step twice. Execute the first Move, then recheck whether
   the second step remains legal. An initially invalid second
   step does nothing, never teleports or bypasses restricted
   rows. Simultaneous opposite-side movement may create or
   remove a flank before Strikes.
6. **No legal orders:** With no Forces available, a player may
   secretly choose Hold twice. Attempting to Commit to an empty
   Front is not legal; an Exhausted Force cannot initiate the
   opening Maneuver solely by being Unnamed-exempt.
7. **Command economy:** Resolve Fronts of 8 vs 5, 7 vs 6, and
   4 vs 4. The losing sides lose **3**, **1**, and **0**
   Command, respectively; losses add across Fronts before
   Collapse, even if they reduce Command below 0.
8. **A beneficial sacrifice:** At 5 against an 8-Strength enemy
   Front, a Commit costs 1 Command, increases the Front to 7,
   and reduces defeat loss from 3 to 1. The net Command saving
   is 1; both commanders committing to the same Front changes
   that calculation again. This is an economic example, not
   a demonstrated optimal strategy.

**Observe:** Does the four-order simultaneous reveal produce
new tactical commitments, or do double Commits routinely dominate
Maneuver and Strike? How rapidly does uncapped Strength-margin loss
cause Collapse on undefended Fronts? Keep the previous 12/9/6/3/1
recovery sequence for these initial tests; do not silently
compensate it without matched tabletop results.

## One Stratagem per Battle and ordinary Maneuvers by any formation

With an Unnamed and unexhausted Force, spend 1 Action and 1 Command to perform a legal ordinary Maneuver. Repeat with a Named Force: identical cost and reach. An Exhausted Force cannot initiate either without a printed exemption. Grey Riders retain this exemption and their unused Rider Attack combination. A Bonded Dust Riders formation instead saves the Command of its first Maneuver each Battle; the second costs 1.

Set The Center Must Hold via the usual Action. If Teren later completes a Named Formation, its BECOMES NAMED ability cannot set another Stratagem this Battle. Return the original Stratagem to hand via a legal card effect: the allowance remains spent. Re-setting **that same card** explicitly, as allowed by The Scouts Found the Gap, does not create an additional Stratagem identity.

After the first Pass and two closing turns, reveal two secret Opening Orders each. Had Been Ordered Forward may move its Bonded formation two legal steps with one Opening Maneuver; The Long March may Move **two different Riders** with one order; Iria may redirect a declared Strike aimed into her Front but may not invent a new Strike or violate Attack legality. Resolve one pre-set Stratagem per player at its eligible timing, including The Archers Were Ready or The Trap Closed reacting to an Opening Strike, then settle Fronts.
