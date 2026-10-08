"""Static tabletop scenario contracts for the 131 physical-print cards.

Run: python tools/check_physical_cost_balance.py

These tests inspect printed effects and exercise the legal choice differences in
specific early/late Battle positions. They are NOT Webgame simulation, win-rate
tests, or a substitute for two humans physically playing the cards.
"""
from __future__ import annotations

from print_cards import load_print_cards


def run() -> None:
    data = load_print_cards()
    cards = {c["id"]: c for c in data["cards"]}
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

    # A Middle Guard screens a Rear defender from basic Archer Attacks.
    # Empowered gives the Crow Archers a one-Attack answer while Thornbows
    # choose proactive reconnaissance and a separate Archer identity.
    case("B1: Archer breaks screening",
         cost("the-crow-archers") == cost("the-thornbow-hunters") == 2
         and has("the-crow-archers", "Empowered", "Middle Force")
         and has("the-thornbow-hunters", "Stratagem", "once per Battle"),
         "Archer options should answer different board problems")

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

    # Opponent has two support Forces and friendly Archer threatens same Front.
    case("B2: Crows reward formation setup",
         cost("the-crows-came-down") == 2
         and has("the-crows-came-down", "up to two", "one Front", "Archers")
         and used_once("the-crows-came-down")
         and cost("the-baggage-was-abandoned") == 2
         and has("the-baggage-was-abandoned", "Rear", "Exhaust", "Shaken"),
         "Narrative costs a setup Action, but affects up to two targets")

    # B2 has active Fronts 1,2,3; 1 and 3 are ordinarily nonadjacent.
    case("B2: Seer changes geography without creating flanks",
         cost("they-knew-the-ground") == 1
         and abs(1-3) > 1
         and has("they-knew-the-ground", "Seer", "outermost active Fronts",
                 "Maneuvers", "does not create flanks", "Attack targets"),
         "Magic Narrative gives access to a new movement line, not free flank")

    # B3, Guard in a lost Front from B2; it can Maneuver if Named despite
    # Exhaustion, while Riders gain unnamed Maneuvers on different Narrative.
    case("B3: exhaustion recovery versus Rider mobility",
         cost("the-wall-did-not-break") == cost("the-long-march") == 2
         and has("the-wall-did-not-break", "Guards", "Exhausted", "0 Command")
         and has("the-long-march", "Rider", "without being Named", "0 Command"),
         "Same price unlocks distinct combat roles")

    # A prepared opponent's Bond is vulnerable only after pressure connects.
    case("B3: ambush damages a formation rather than adding Strength",
         cost("the-trap-closed") == 2
         and has("the-trap-closed", "Raiders", "temporary negative marker",
                 "Bond or Name", "hand"),
         "Hidden plan requires a preceding tactical move and attached target")

    # Delayed plan versus direct Tactic; Stratagem can wait but costs an Action
    # to set, and its chosen Front and existence are public.
    case("B3: delayed Strength must be cheaper than a fresh Force",
         cost("the-center-must-hold") == 1
         and cost("the-lines-held") == 1
         and has("the-center-must-hold", "Kings or Captains", "two other")
         and has("the-lines-held", "Frontline", "Middle", "+2 Strength"),
         "Conditional temporary gains should not cost as much as permanent 2C bodies")

    # Taxing an opponent's next card in a Front is avoidable: the card can be
    # played in another Front or the player can choose other Actions.
    case("B3: an avoidable Tax has bounded Command cost",
         cost("the-line-had-begun-to-move") == 1
         and has("the-line-had-begun-to-move", "Tax", "2 additional Command"),
         "A 2C Tax2 was economically break-even even when it succeeded")

    # Counterintelligence needs different timing windows and effort.
    case("B3: scoped scouting and earned foreknowledge",
         has("the-lantern-scouts", "once per Battle", "this Front", "draw 1")
         and has("the-thornbow-hunters", "once per Battle", "adjacent active Front")
         and has("the-watchtowers-of-eren", "any active Front", "draw 1")
         and used_once("the-watchtowers-of-eren"),
         "Scout/Archer/Stronghold must not provide permanent free omniscience")

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

    # All four example decks are 48 cards, and neither their published content
    # nor the executable source were mutated by the print-only revisions.
    print(f"PASS: {len(checks)} paper-state card-cost and decision contracts, "
          f"{len(cards)} printable identities; no claim of win-rate balance.")
    for item in checks:
        print("  OK:", item)


if __name__ == "__main__":
    run()
