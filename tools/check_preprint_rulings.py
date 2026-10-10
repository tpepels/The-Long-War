"""Advisory static checks for the seven adopted physical preprint rulings.

Checks contract examples and printed-card relationships, not executable-engine
parity or human-playtest balance. Run: python tools/check_preprint_rulings.py
"""
from __future__ import annotations

from pathlib import Path
from print_cards import ROOT, load_print_cards


def run() -> None:
    rules = (ROOT / "rules" / "rulebook.md").read_text(encoding="utf-8")
    short = (ROOT / "rules" / "player-rulebook.md").read_text(encoding="utf-8")
    printed = load_print_cards()["cards"]
    assert len(printed) == 131
    cards = {c["id"]: c for c in printed}

    def says(cid: str, *parts: str) -> bool:
        c = cards[cid]
        effects = (
            [*c["modes"]["force"]["effects"], *c["modes"]["name"]["effects"]]
            if c["type"] == "hero" else c["effects"]
        )
        text = " ".join(e["text"] for e in effects)
        return all(piece in text for piece in parts)

    # D01: a Tactic choosing the Force counts against formation-level protection.
    assert "selects an opposing Force also targets its formation" in rules
    assert "Targeting a Force also targets its formation" in short
    assert says("the-red-shields", "Tactics", "formation", "additional Command")
    assert says("a-volley-before-dawn", "opposing Force", "Shaken")
    assert says("asha-the-shield-bearer", "opposing Tactic", "redirect")

    # D02/D03: unspent Front Tax ends with the Battle; a selected target
    # creates a Front association even for cards that are immediately discarded.
    assert "unspent Tax markers" in rules and "unspent Tax markers" in short
    assert "Declare the relevant Front and targets before paying" in rules
    assert "global Narrative" in rules and "no selected Front" in rules
    assert says("the-line-had-begun-to-move", "Tax marker", "next card")
    assert says("rovan-the-gatebreaker", "Tax marker", "before your next turn")

    # D04: removing Shaken is possible; removing generic temporary effect text
    # alone is not. Do not alter ordinary suppression or Tax rules to achieve it.
    assert "Only such markers can be removed" in rules
    assert "Temporary −Strength" in rules and "are **not individually removable**" in rules
    assert "Tax markers belong to Fronts" in rules
    assert says("they-lived-to-tell-it", "negative marker", "Exhaustion", "Inspired")
    assert says("they-returned-with-names", "ignore its Name text")

    # D05: 'here' scoped to containing Front, not only position.
    assert "**here** always means **its Front**" in rules
    assert "**here** means **in this Front**" in short
    assert says("the-red-duelists", "Frontline Force", "this Front")

    # D06: a marker actually applied after a Raider/Skirmisher or Tactic
    # can trigger The Trap Closed, but reveal and return happen only once.
    assert "For *The Trap Closed*, check its assigned Front" in rules
    assert "A prevented marker is not applied" in rules
    assert "resolves once" in rules
    assert says("the-trap-closed", "a Tactic you play while one is here",
                "negative marker", "that Force's Bond or Name")
    assert says("the-baggage-was-abandoned", "Exhaust", "Shaken")

    # D10: prepared names retain their PLAY behavior without becoming an
    # always-on Name until there is a Force in the position.
    assert "A prepared Name (including a Hero used as a Name) cannot use" in rules
    assert "even if the formation is not yet Named" in rules
    assert "other abilities wait until attached to a Force" in short
    assert says("asha-the-shield-bearer", "Remove all temporary negative markers",
                "When an opposing Tactic")

    # Editorial confirmations: free Attack restrictions; simultaneous
    # The Ground Was Held eligibility; shared classification.
    assert "The same is true when *The Vardai*, *Elian*" in rules
    assert "The Ground Was Held" in rules and "**before the reveals**" in rules
    assert "If a card such as *Arel* or *Avaros*" in rules
    assert "If it needs a Force or other legal target" in rules

    print("PASS: seven physical rulebook rulings and four editorial confirmations")
    print("PASS: 131 printed identities and affected card interactions remain present")
    print("LIMIT: this does not run full games or verify native/Webgame rules parity")


if __name__ == "__main__":
    run()
