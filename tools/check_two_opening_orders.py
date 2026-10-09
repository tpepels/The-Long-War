"""Static paper-game contract for two secret Opening Orders and margin loss.

Run: python tools/check_two_opening_orders.py

This verifies reference and test-case agreement; no claim that native gameplay
already implements the revised physical rules or that balance is established.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHORT = (ROOT / "rules/player-rulebook.md").read_text(encoding="utf-8")
DETAILED = (ROOT / "rules/rulebook.md").read_text(encoding="utf-8")
COMBAT = (ROOT / "cards/combat-reference.md").read_text(encoding="utf-8")
KIT = (ROOT / "web/playtest-kit.js").read_text(encoding="utf-8")


def command_loss(my_strength: int, opposing_strength: int) -> int:
    """Each Front settles independently; losing margin is paid in full."""
    assert my_strength >= 0 and opposing_strength >= 0
    return max(opposing_strength - my_strength, 0)


def front_strength(formation_strength: int, committed: int, has_force: bool) -> int:
    """A Front bonus never changes the individual Force's Incursion test."""
    assert committed in (0, 1, 2)
    assert formation_strength >= 0
    return formation_strength + (2 * committed if has_force else 0)


def run() -> None:
    # The paper manual should tell the whole rule with no card expansion
    # or added turn Actions.
    for source in (SHORT, DETAILED):
        assert "## Opening Orders {#opening-orders}" in source
        opening = source.split("## Opening Orders {#opening-orders}", 1)[1].split("## Your turn {#turn}", 1)[0]
        assert "**two" in opening.lower() or "**2" in opening
        for choice in ("Maneuver", "Commit", "Strike", "Hold"):
            assert choice in opening
        assert "simultaneous" in opening.lower()
        assert "Battle I" in opening and "first turn" in opening
        assert "Battle II" in opening
        assert "Pass" in opening
        assert "Unnamed" in opening or "without a Name" in opening
        assert "Exhausted" in opening
        assert "once-per-Battle" in opening or "one Attack per Battle" in opening
        assert "two Commits" in opening or "Two Commits" in opening
        assert "+2" in opening and "1 Command" in opening
        assert "Front" in opening
        assert "no" in opening.lower() and "Action" in opening
    assert "You may choose the same order twice" in SHORT
    assert "repeating a type is allowed" in DETAILED
    assert "both players" in DETAILED.lower()
    assert "Simultaneous Strikes check legal attackers and targets before either Strike" in DETAILED
    assert "If both Strikes use the same Force, the second cannot Attack again" in DETAILED
    assert "does **not** help a Raider" in DETAILED
    assert "If someone has already Passed, skip Opening Orders" in SHORT
    assert "As setup currently places no Force on the battlefield" in DETAILED

    # Loss is a per-Front margin, not a winning score, 1/Front, per-row,
    # count of weaker cards or special threshold. Command collapse still
    # happens before recovery, and the loser's scar remains ONE Force.
    assert [command_loss(a, b) for a, b in
            ((5, 8), (8, 5), (8, 8), (0, 10), (4, 5))] == [3, 0, 0, 10, 1]
    assert command_loss(5, 8) + command_loss(6, 7) == 4
    assert front_strength(5, 1, True) == 7
    assert front_strength(5, 2, True) == 9
    assert front_strength(5, 2, False) == 5
    assert command_loss(front_strength(5, 1, True), 8) == 1
    assert 1 + command_loss(front_strength(5, 1, True), 8) == 2
    assert command_loss(5, 8) == 3
    for source in (SHORT, DETAILED, COMBAT, KIT):
        assert "1 Command per lost Front" not in source
        assert "lose 1 Command per lost Front" not in source
        assert "Strength difference" in source or "Strength deficit" in source
        assert "Commit" in source
    assert "winning margin does not matter" not in DETAILED.lower()
    assert "one Force in each lost Front" in DETAILED
    assert "before recovery" in SHORT

    # Recheck that opening Strikes do not grant unlimited normal attacks,
    # and the price remains a Command expenditure, not an extra Action.
    assert "one Attack per Battle" in DETAILED
    assert "No Action or Command cost" in SHORT
    assert "all valid Commit costs" in DETAILED
    assert "two Commits" in SHORT or "Two Commits" in SHORT
    assert "then Strikes" in SHORT
    print("PASS: two secret Opening Orders/player, repeated types and simultaneous steps")
    print("PASS: Battle I first-turn placement; Commit fronts and normal Attack-use legality")
    print("PASS: independent full-margin Command loss, tie=0, Collapse-before-recovery")
    print("LIMIT: tabletop balance and native AI are not verified by this static contract")


if __name__ == "__main__":
    run()
