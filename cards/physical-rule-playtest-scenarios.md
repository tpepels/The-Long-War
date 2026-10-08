# Physical playtest scenarios — rules reconciliation (October 2026)

**Scope:** print-only. These are reproducible tabletop checks, not a claim that the game has been physically playtested or balanced. Use the [rulebook](../rules/rulebook.md), the 131 printed cards with `print-overrides.json`, and the printed Reference/marker sheet. Leave native/Webgame behavior out of these tests.

The aim is to catch **unfun consequences** (unanswerable movement locks, unavoidable one-card wins, obvious infinite loops) as well as unclear instructions. For every scenario, record whether players knew the next legal Action **without consulting the design documents**.

## 1. Passing creates a deliberately short endgame

During Battle I, leave both players with several playable cards. At the **start of Player A's turn, before drawing**, A voluntarily Passes. A draws no card, spends no Actions. Player B draws 1 and takes up to 2 Actions; A then draws 1 and takes up to 2 Actions. Resolve the Battle immediately. Neither closing turn may Pass or extend the countdown. If the war continues, B starts Battle II.

**Check:** does Passing create meaningful urgency without allowing the passer to ambush by drawing immediately before deciding?

## 2. Front loss causes one future Battle of Exhaustion

After comparing Fronts, Player A loses Front 2 with three Forces across its Frontline, Middle and Rear. The Middle Force has **Guarded**; the others do not. Deduct 1 Command for the lost Front and check Collapse. Guarded protects the Middle Force from the new loss-based Exhaustion; consume Guarded. Clear all old conditions and then give the Frontline and Rear Forces one Exhaustion token each. These start the next Battle Exhausted and cannot initiate ordinary Maneuvers. They still have Strength and may Attack. A recovery card can remove their tokens.

At the following Battle end, those old tokens clear. If A loses Front 2 again, the defeated, unprotected Forces receive fresh Exhaustion tokens for the Battle after that.

**Watch for:** two Battles of Exhaustion from one loss (wrong); Guarded clearing before it protects (wrong); immobilized armies without enough recovery options (balance risk).

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

Repeat from a provisional 5–4 non-tie that becomes 5–5 because of a reveal: The Ground Was Held was not eligible beforehand and cannot reveal in response.

**Watch for:** meaningful hidden information versus a single lucky reveal determining the result with no counterplay.

## 9. Front-assigned scouting and reactions

Set **The Scouts Had Warned Them** face-down at a Front containing one of your Scouts or Seers. When your opponent sets a Stratagem **in that same Front**, you may reveal yours and inspect theirs, draw 1 and discard 1. If your opponent sets a Stratagem elsewhere, this trigger does not fire. Try **The Scouts Found the Gap** to reveal an opposing face-down Stratagem involuntarily; its opponent may pay to set it down again as the Tactic specifies.

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
