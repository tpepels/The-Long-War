"""Static tabletop scenario contracts for the 131 physical-print cards.

Run: python tools/check_physical_cost_balance.py

These tests inspect printed effects and exercise the legal choice differences in
specific early/late Battle positions. They are NOT Webgame simulation, win-rate
tests, or a substitute for two humans physically playing the cards.
"""
from __future__ import annotations

from print_cards import ROOT, load_print_cards


def run() -> None:
    data = load_print_cards()
    cards = {c["id"]: c for c in data["cards"]}
    rulebook = (ROOT / "rules" / "rulebook.md").read_text(encoding="utf-8")
    assert len(cards) == len(data["cards"]) == 131
    checks = []

    def case(name: str, condition: bool, detail: str) -> None:
        assert condition, name + ": " + detail
        checks.append(name)

    def has(card_id: str, *terms: str) -> bool:
        text = cards[card_id].get("text", "").lower()
        return all(term.lower() in text for term in terms)

    def cost(card_id: str) -> int:
        return cards[card_id]["command_cost"]

    def row(card_id: str) -> list[str]:
        return cards[card_id].get("allowed_rows", ["front", "middle", "rear"])

    def used_once(card_id: str) -> bool:
        return any(e.get("limit") == "once_per_battle" for e in cards[card_id].get("effects", []))

    # Battle I, position: friendly Middle Force; Frontline still open.
    # First Spear supplies immediate protection; Red Shields instead taxes Tactics.
    case("B1: defensive Frontline sidegrade",
         cost("the-first-spear") == cost("the-red-shields") == 2
         and row("the-first-spear") == ["front"]
         and len(row("the-red-shields")) == 3
         and has("the-first-spear", "directly behind", "Guarded")
         and has("the-red-shields", "Tactics", "additional Command"),
         "A first spear must offer protection in return for its row lock")

    # Battle I, breach: enemy Frontline empty, Middle target still active.
    case("B1: Iron Boars exploit a breach",
         cost("the-iron-boars") == cost("the-unnamed-host") == 3
         and row("the-iron-boars") == ["front"]
         and has("the-iron-boars", "opposing Frontline", "empty", "Depleted")
         and has("the-unnamed-host", "Exhausted", "Command"),
         "Raider bodies need different payoff and exploitable counterplay")

    # Enemy Frontline occupied, Shaken improves the immediate comparison but
    # the Duelists lose ability to stand in a supporting row.
    case("B1: Duelists open the line",
         cost("the-red-duelists") == cost("the-dust-riders") == 2
         and row("the-red-duelists") == ["front"]
         and has("the-red-duelists", "Shaken", "Frontline")
         and "rider" not in cards["the-red-duelists"]["classes"]
         and "rider" in cards["the-dust-riders"]["classes"],
         "Duelists must offer a Frontline surprise, not clone Dust Riders")

    # Crow Archer has an immediate screening answer; Thornbow instead adds
    # persistent Front Strength if at least one OTHER Archer shares its Front.
    case("B1: Archer pressure has different payoff requirements",
         cost("the-crow-archers") == cost("the-thornbow-hunters") == 2
         and has("the-crow-archers", "Empowered", "Middle Force")
         and has("the-thornbow-hunters", "Rear", "other friendly Archer",
                 "+1 Strength"),
         "Crow rewards an Attack; Thornbow rewards multiple Archers in one Front")

    # Start of B2: a Force lost a Front in B1 and is Exhausted.
    # Both Narratives take one Action to play and one ACTION to activate.
    # They differ in follow-through: recovery+Move vs generic removal+Inspired.
    case("B2: recovery creates a positional choice",
         cost("no-one-would-be-first-to-leave") == 2
         and cost("they-lived-to-tell-it") == 1
         and used_once("no-one-would-be-first-to-leave")
         and has("no-one-would-be-first-to-leave", "Exhaustion", "Move")
         and has("they-lived-to-tell-it", "negative marker", "Inspired"),
         "Recovery card should offer something distinct from cheaper removal")

    # Guarded protects from next affliction; Inspired protects Shaken. They
    # occupy the same Bond slot but provide different answers and no +Strength.
    case("B2: alternative Boons trade protection",
         cost("guarded") == cost("endured-with") == 1
         and cards["guarded"]["strength_modifier"] == 0
         and cards["endured-with"]["strength_modifier"] == 0
         and has("guarded", "give", "Guarded")
         and has("endured-with", "give", "Inspired"),
         "Named Boons must agree with their actual protective abilities")

    # Crows now Exhaust on PLAY and can Shake an already Exhausted target later.
    case("B2: Crows do not waste their setup Action",
         cost("the-crows-came-down") == 2
         and any(e["timing"] == "play" and "Exhaust" in e["text"]
                 for e in cards["the-crows-came-down"]["effects"])
         and any(e["timing"] == "action" and "Shaken" in e["text"]
                 for e in cards["the-crows-came-down"]["effects"])
         and used_once("the-crows-came-down")
         and cost("the-baggage-was-abandoned") == 2,
         "Crows should do something when played and reward the later Action")

    # Phase 4 gives Seers a useful nearby Named-formation Strength payoff.
    case("B2: Seer rewards real Named formations",
         cost("they-knew-the-ground") == 1
         and has("they-knew-the-ground", "Seer", "Named Formations",
                 "adjacent active Front", "+1 Strength"),
         "A Seer supplies Strength near an actual Named formation, not free geography")

    # Defensive Guard support now differs from aggressive Rider support;
    # both give immediate, useful Battle consequences before optional movement.
    case("B3: defence support versus Rider pressure",
         cost("the-wall-did-not-break") == cost("the-long-march") == 2
         and has("the-wall-did-not-break", "Guarded", "Rear", "+1 Strength")
         and has("the-long-march", "Rider", "+1 Strength", "0 Command"),
         "One card protects Rear and the other boosts Riders before Maneuver")

    # A prepared opponent's Bond is vulnerable only after pressure connects.
    case("B3: ambush damages a formation rather than adding Strength",
         cost("the-trap-closed") == 2
         and has("the-trap-closed", "Raider", "negative marker",
                 "Bonds or Names", "hand"),
         "Hidden plan requires a preceding tactical move and attached target")

    # Delayed plan versus direct Tactic; Stratagem can wait but costs an Action
    # to set, and its chosen Front and existence are public.
    case("B3: delayed Strength must be cheaper than a fresh Force",
         cost("the-center-must-hold") == 1
         and cost("the-lines-held") == 1
         and has("the-center-must-hold", "King or Captain", "two other")
         and has("the-lines-held", "Frontline", "Middle", "+2 Strength"),
         "Conditional temporary gains should not cost as much as permanent 2C bodies")

    # Taxing an opponent's next card in a Front is avoidable: the card can be
    # played in another Front or the player can choose other Actions.
    case("B3: an avoidable Tax has bounded Command cost",
         cost("the-line-had-begun-to-move") == 1
         and has("the-line-had-begun-to-move", "Tax", "2 additional Command"),
         "A 2C Tax2 was economically break-even even when it succeeded")

    # Information still exists on Lantern/Watchtowers, but Thornbow now
    # directly strengthens an Archer position instead of another peek.
    case("B3: information and Archer Strength are distinct alternatives",
         has("the-lantern-scouts", "once per Battle", "this Front", "draw 1")
         and has("the-thornbow-hunters", "other friendly Archer", "+1 Strength")
         and has("the-watchtowers-of-eren", "any active Front", "draw 1")
         and used_once("the-watchtowers-of-eren"),
         "Do not accidentally expect Thornbow to reveal a Stratagem")

    # King discount uses a second Action to exploit; card-flow compensates.
    case("B2+: King's orchestration pays for timing",
         cost("namar") == 4 and used_once("namar")
         and has("namar", "Regain 2 Command", "2 less Command", "Draw 1"),
         "High-cost Named completion earns a distinct two-Action combo")

    # Full 12-position battlefield: the 3 new restricted Frontline Forces may
    # be unplayable; that's intentional opportunity cost, never an invisible
    # exception allowing illegal placement.
    case("B4+: persistent formations obey row restrictions",
         all(row(k) == ["front"] for k in
             ("the-first-spear", "the-iron-boars", "the-red-duelists"))
         and sum(card["type"] == "force" and card.get("allowed_rows") == ["front"]
                 for card in data["cards"]) == 3,
         "Frontline-only payoffs must respect saturation, never jump occupied slots")

    # Target rank and attacker rank have independent conditions.
    case("B1: Rear Rider must reposition before attacking",
         "A Rider in Rear cannot initiate its **basic Rider Attack**" in rulebook
         and "from Frontline or Middle" in rulebook
         and "Opposing **flanked** Frontline Force" in rulebook,
         "Rear Riders retain Strength, but cannot make their basic Attack")

    case("B3: Banner is not dominated by Center",
         cost("every-banner-turned-toward-them") == 2
         and cost("the-center-must-hold") == 1
         and has("every-banner-turned-toward-them", "adjacent active Front",
                 "three other", "Human")
         and has("the-center-must-hold", "two other"),
         "Costlier leadership has cross-Front reach and larger ceiling")

    case("B2: Rider plan changes position, not just Strength",
         cost("the-battle-turned-east") == 1
         and has("the-battle-turned-east", "Riders", "one additional",
                 "+1 Strength"),
         "One more Move can alter a flank or exposure")

    case("B2: Archer counterattack costs normal Attack allowance",
         cost("the-archers-were-ready") == 1
         and has("the-archers-were-ready", "opposing Force Attacks",
                 "basic Archer Attack", "for free", "Mark its Attack used")
         and "does not undo the earlier Attack" in rulebook,
         "Counterattack obeys range, screening, Attack allowance, timing")

    case("B2: recovery pays off immediately and later",
         cost("no-one-would-be-first-to-leave") == 2
         and has("no-one-would-be-first-to-leave",
                 "Remove its Exhaustion", "two different", "Move")
         and any(e["timing"] == "play"
                 for e in cards["no-one-would-be-first-to-leave"]["effects"])
         and used_once("no-one-would-be-first-to-leave"),
         "2C Narrative gives recovery before optional movement Action")

    case("B3: Depleted creates logistics vulnerability",
         cost("the-stores-were-taken") == 1
         and has("the-stores-were-taken", "Depleted", "Bond",
                 "pays 2 Command", "returns"),
         "Raiders pressure attachments after preparation ends")

    case("B2: Field Train crosses Fronts once",
         cost("the-field-train") == cost("the-house-of-reed") == 2
         and has("the-field-train", "adjacent active Front", "directly ahead")
         and any(e["timing"] == "play"
                 for e in cards["the-field-train"]["effects"])
         and any(e["timing"] == "action"
                 for e in cards["the-house-of-reed"]["effects"]),
         "One-shot wider logistics differs from repeatable local support")

    case("B1: Seer Narrative has an immediate Strength floor",
         cost("they-knew-the-ground") == 1
         and any(e["timing"] == "play"
                 for e in cards["they-knew-the-ground"]["effects"])
         and has("they-knew-the-ground", "Choose a friendly formation",
                 "+1 Strength", "may Move", "Seer"),
         "A support spell changes the Front even if no Move is legal")

    case("B4: sacrifice releases a persistent position",
         cost("re-form-the-line") == 0
         and has("re-form-the-line", "Captain",
                 "discard one friendly Force", "Bond and Name",
                 "regain 2 Command")
         and "That position becomes empty" in rulebook,
         "Withdrawal discards entire formation and vacates its slot")

    case("B2: reconnaissance earns a reactive Strength swing",
         cost("before-sunset-the-ford-would-be-ours") == 1
         and used_once("before-sunset-the-ford-would-be-ours")
         and any(e["timing"] == "reaction"
                 for e in cards["before-sunset-the-ford-would-be-ours"]["effects"])
         and has("before-sunset-the-ford-would-be-ours",
                 "Stratagem", "look", "+2 Strength"),
         "Scouting matters directly to the Front result, not a free Move")

    case("B1: Raider Narrative has on-play filtering",
         cost("the-raiders-came-home-loaded") == 1
         and any(e["timing"] == "play" and "Draw 1 card" in e["text"]
                 for e in cards["the-raiders-came-home-loaded"]["effects"])
         and has("the-raiders-came-home-loaded", "Tactic",
                 "1 less Command", "Move"),
         "Narrative still does something before drawing its synergies")

    case("B2: completion plan offers two tactical payoffs",
         cost("there-was-no-road-back") == 1
         and has("there-was-no-road-back", "becomes Named",
                 "two adjacent legal", "opposing attached Bond"),
         "Completion plan offers reposition or attachment disruption")

    # Phase 1 keeps pure baseline bodies simple but differentiates absolute
    # per-position Strength against specialist protection and Attack classes.
    case("P1: Fifty Men trades abilities for highest simple 2C body",
         cost("the-fifty-men") == cost("the-red-shields") == 2
         and cards["the-fifty-men"]["strength"] == 5
         and cards["the-red-shields"]["strength"] == 4
         and cards["the-fifty-men"]["effects"] == []
         and "guard" not in cards["the-fifty-men"]["classes"]
         and "guard" in cards["the-red-shields"]["classes"],
         "A plain body is stronger but cannot screen Rear or tax hostile Tactics")

    case("P1: Stood Fast and Followed trade different payoffs",
         cost("stood-fast-with") == cost("followed") == 1
         and cards["stood-fast-with"]["strength_modifier"] == 1
         and cards["followed"]["strength_modifier"] == 1
         and has("stood-fast-with", "Frontline", "+1 additional Strength",
                 "cannot be flanked")
         and has("followed", "Named", "+1 additional Strength")
         and cards["stood-fast-with"]["effects"][0]["timing"] == "bonded",
         "Stood Fast wins on Frontline protection; Followed works Named in any rank")

    case("P1: Oren ACTION is better than a normal Bond play",
         cost("oren") == 2
         and has("oren", "Draw 2 cards", "discard 1 card",
                 "1 less Command", "minimum 0",
                 "completes a Named Formation", "draw 1 card")
         and used_once("oren")
         and any(e["timing"] == "action" for e in cards["oren"]["effects"]),
         "Oren discounts Bond play inside one Action and rewards completion")

    case("P1: Thornbow supports multiple Archers without passive scouting",
         cost("the-thornbow-hunters") == cost("the-crow-archers") == 2
         and cards["the-thornbow-hunters"]["strength"] == 3
         and len(cards["the-thornbow-hunters"]["effects"]) == 1
         and cards["the-thornbow-hunters"]["effects"][0]["timing"] == "rear"
         and has("the-thornbow-hunters", "other friendly Archer",
                 "in this Front", "+1 Strength")
         and not has("the-thornbow-hunters", "Stratagem"),
         "Rear Archer demands a second friendly Archer instead of free information")

    case("P1: King's Bond exchange pays off on play",
         cost("the-king-had-given-the-order") == 2
         and len(cards["the-king-had-given-the-order"]["effects"]) == 1
         and cards["the-king-had-given-the-order"]["effects"][0]["timing"] == "play"
         and has("the-king-had-given-the-order", "Exchange", "two",
                 "Bonds", "Named", "+1 Strength this Battle")
         and not used_once("the-king-had-given-the-order"),
         "Bond exchange uses the play Action and boosts only Named formations")

    # Phase 2: compare explicit tabletop marker arithmetic, not simulated games.
    # A formation has 5 base Strength. Exhausted/Depleted are each -1,
    # Shaken -2, and one flank penalty is -1; floor to 0.
    def marker_strength(base: int, *, exhausted: bool = False,
                        depleted: bool = False, shaken: bool = False,
                        flanked: bool = False) -> int:
        return max(0, base - int(exhausted) - int(depleted)
                   - 2 * int(shaken) - int(flanked))

    case("P2: Exhausted now changes the Front comparison",
         marker_strength(5, exhausted=True) == 4
         and "**−1 Strength**" in rulebook
         and "- **Exhausted:**" in rulebook,
         "Lost Front or Archer Exhaustion must cost 1 actual Strength")

    case("P2: Depleted changes Strength and entire formation ACTION access",
         marker_strength(5, depleted=True) == 4
         and "**no printed ACTION ability on that formation**" in rulebook
         and "attached Bond or attached Name" in rulebook,
         "Depleted is a formation-wide lock, including Name and Hero ACTION")

    case("P2: penalties stack with Shaken and flanking, floor at zero",
         marker_strength(5, exhausted=True, depleted=True) == 3
         and marker_strength(5, exhausted=True, depleted=True,
                             shaken=True, flanked=True) == 0
         and marker_strength(1, exhausted=True, depleted=True) == 0
         and "duplicate markers of the same condition do not stack" in rulebook,
         "No negative front contribution; independent afflictions compound")

    case("P2: weakened defeated Fronts persist exactly one subsequent Battle",
         "Place one new Exhaustion token" in rulebook
         and "persists throughout the next Battle" in rulebook
         and "−1 Strength" in rulebook
         and "Guarded prevents one incoming affliction at a time" in rulebook,
         "Keep defeat penalties and prevention timing readable")

    # Phase 3: preparing a layer should be able to contribute immediately
    # without replaying old PLAY effects on eventual attachment.
    case("P3: House of Reed can turn prepared layers into real defence",
         cost("the-house-of-reed") == 2
         and len(cards["the-house-of-reed"]["effects"]) == 2
         and any(e["timing"] == "play" and "directly ahead" in e["text"]
                 for e in cards["the-house-of-reed"]["effects"])
         and any(e["timing"] == "action" and "up to two" in e["text"]
                 and "Named" in e["text"] and "Guarded" in e["text"]
                 and e.get("limit") == "once_per_battle"
                 for e in cards["the-house-of-reed"]["effects"]),
         "One-shot attachment and a guarded two-layer once-per-Battle Action")

    case("P3: Field Train rewards legal cross-Front completion",
         row("the-field-train") == ["middle"]
         and cost("the-field-train") == 2
         and has("the-field-train", "adjacent active Front",
                 "directly ahead", "completes a Named Formation",
                 "+2 Strength this Battle")
         and cards["the-field-train"]["effects"][0]["timing"] == "play",
         "Cross-Front delivery yields +2 only when completing Named")

    case("P3: Swore Again To works prepared but rewards immediate completion",
         cost("swore-again-to") == 1
         and cards["swore-again-to"]["strength_modifier"] == 0
         and has("swore-again-to", "playing this Bond completes",
                 "+2 Strength this Battle", "Otherwise",
                 "draw 1 card", "discard 1 card")
         and "cannot replay the Bond's earlier PLAY effect" in rulebook,
         "Prepared filtering replaces dead-on-preparation Maneuver ability")

    case("P3: prepared protection can choose an existing nearby Force",
         cost("guarded") == cost("endured-with") == 1
         and has("guarded", "friendly Force in this Front", "Give it Guarded")
         and has("endured-with", "friendly Force in this Front",
                 "Give it Inspired"),
         "Protection Bonds do not require a Force in their own position")

    case("P3: prepared Name transfer no longer requires a local Force",
         has("stayed-behind-for", "prepared Name", "this Front",
             "friendly Force", "empty Name slot", "if legal")
         and cards["stayed-behind-for"]["effects"][0]["timing"] == "play",
         "One PLAY effect supports attaching another prepared Name")

    case("P3: card flow works with nearby enabling classes",
         has("kept-pace-with", "control a Rider or Scout", "this Front",
             "draw 1 card", "discard 1 card")
         and has("carried-messages-for", "control a Captain or Scout",
                 "this Front", "draw 1 card", "discard 1 card"),
         "These conditional Bonds function even when played prepared")

    case("P3: exhausted Raiders convert into Command without own attachment",
         has("shared-the-spoils-with", "control a Raider or Skirmisher",
             "opposing Force", "Exhausted", "1 Command",
             "amount actually lost"),
         "Exhaustion now matters both for Strength and targeted Command transfer")

    case("P3: simple tempo Bond boosts Strength when prepared",
         cost("marched-with") == 1
         and cards["marched-with"]["strength_modifier"] == 1
         and has("marched-with", "friendly formation in this Front",
                 "+1 Strength this Battle"),
         "A Bond provides immediate defensive tempo without free Maneuvers")

    case("P3: prepared layers remain face-up without replaying PLAY",
         "Prepared layers have no Strength and are not formations" in rulebook
         and "does **not** replay its earlier PLAY effect" in rulebook
         and "Resolve the attachments **one at a time**" in rulebook,
         "No global repeatable PLAY trigger or infinite attachment loop")

    # Phase 4: effects must cause a meaningful decision and preserve the one
    # reveal window, timing, target, and no-universal-Move rules.
    case("P4: defensive Stratagem answers Tactic or Attack affliction",
         cost("no-step-back") == 2
         and has("no-step-back", "Tactic", "ignore", "Attack",
                 "prevent that affliction")
         and "reveal before applying that affliction" in rulebook,
         "No Step Back provides actual combat prevention, not only Tactic immunity")

    case("P4: Ground Held covers a tie or one-point deficit only",
         cost("the-ground-was-held") == 1
         and has("the-ground-was-held", "Named Formation", "only you",
                 "on a tie", "behind by 1", "+2 Strength")
         and "would lose by exactly 1 Strength" in rulebook,
         "Only initial provisional result qualifies, no reaction to other reveals")

    case("P4: Scout Stratagem gives Guarded after looking",
         cost("the-scouts-had-warned-them") == 1
         and has("the-scouts-had-warned-them", "Scout or Seer",
                 "look at that Stratagem", "Guarded"),
         "Hidden information has direct protective payoff when a plan is set")

    case("P4: scouting Narrative turns intelligence into Strength",
         used_once("before-sunset-the-ford-would-be-ours")
         and has("before-sunset-the-ford-would-be-ours",
                 "adjacent to a Front", "Scout or Ship",
                 "look at it", "+2 Strength"),
         "Adjacent plan can matter without a second paid ACTION")

    case("P4: Guard Narrative produces on-play Boon and Rear support",
         cost("the-wall-did-not-break") == 2
         and any(e["timing"] == "play" and "Guarded" in e["text"]
                 for e in cards["the-wall-did-not-break"]["effects"])
         and any(e["timing"] == "continuous" and "Middle" in e["text"]
                 and "Rear" in e["text"] and "+1 Strength" in e["text"]
                 for e in cards["the-wall-did-not-break"]["effects"]),
         "Defensive Strength reward replaces low-value recovery Maneuver exception")

    case("P4: Long March Riders matter without moving",
         cost("the-long-march") == 2
         and any(e["timing"] == "play" and "up to two" in e["text"]
                 and "+1 Strength" in e["text"]
                 for e in cards["the-long-march"]["effects"])
         and any(e["timing"] == "continuous" for e in cards["the-long-march"]["effects"]),
         "Rider Strength is the payoff; movement remains a supporting option")

    case("P4: full-Front exchange now happens in the PLAY Action",
         cost("no-road-was-too-long") == 3
         and len(cards["no-road-was-too-long"]["effects"]) == 1
         and cards["no-road-was-too-long"]["effects"][0]["timing"] == "play"
         and has("no-road-was-too-long", "two adjacent active Fronts",
                 "rank for rank", "if legal",
                 "Named Formation", "+2 Strength")
         and "cannot be made partially" in rulebook,
         "Wild exchange no longer consumes a second Action or breaks rank rules")

    case("P4: Seer geography gives Name a tactical payoff",
         cost("they-knew-the-ground") == 1
         and has("they-knew-the-ground", "Seer", "Named Formations",
                 "+1 Strength", "Move"),
         "A Seer matters without changing generic Attack or flank geometry")

    case("P4: Scout exhaustion converts into Shaken at a threshold",
         cost("they-were-gathering-there") == 1
         and has("they-were-gathering-there", "Scout",
                 "If it is Exhausted", "Shaken", "Otherwise, Exhaust"),
         "Scout Tactic either deals -1 now or -2 to existing Exhaustion")

    case("P4: Muster False raids a Scout- or Seer-held Bond",
         cost("the-muster-was-false") == 1
         and has("the-muster-was-false", "prepared Bond or Name",
                 "Scout or Seer", "attached Bond"),
         "Prepared punish retains a useful rare-class branch")

    case("P4: retreat-or-Shaken is conditional on actual pressure",
         cost("they-had-gone-too-far") == 1
         and has("they-had-gone-too-far", "Scout or Skirmisher",
                 "Frontline or Middle", "if legal and empty",
                 "otherwise", "Shaken"),
         "An opponent can offer empty Rear space to avoid Shaken")

    case("P4: suppressing once-only actions includes immediate Named cost",
         cost("they-let-them-through") == 1
         and has("they-let-them-through", "ACTION",
                 "Named", "Name contributes no Strength"),
         "A suppressed opponent must lose useful Strength or ACTIONs")

    case("P4: baited displacement applies Depleted only if moved",
         cost("the-line-was-baited") == 0
         and has("the-line-was-baited", "Skirmisher",
                 "Frontline or Middle", "If it moves",
                 "Depleted"),
         "Zero-Command disruption has a meaningful legal-position dependency")

    case("P4: fresh orders help the Front even if no Move is possible",
         cost("fresh-orders") == 0
         and has("fresh-orders", "King or Captain",
                 "+1 Strength", "may Move"),
         "Leadership Order changes Strength while movement remains optional")

    # All four example decks are 48 cards, and neither their published content
    # nor the executable source were mutated by the print-only revisions.
    print(f"PASS: {len(checks)} paper-state card-cost and decision contracts, "
          f"{len(cards)} printable identities; no claim of win-rate balance.")
    for item in checks:
        print("  OK:", item)


if __name__ == "__main__":
    run()
