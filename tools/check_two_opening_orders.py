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
        opening = source.split("## Opening Orders {#opening-orders}", 1)[1].split("## Resolving a Battle {#scoring}", 1)[0]
        assert "**two" in opening.lower() or "**2" in opening
        for choice in ("Maneuver", "Commit", "Strike", "Hold"):
            assert choice in opening
        assert "simultaneous" in opening.lower()
        assert "Battle I" in opening
        assert "closing turns" in opening
        assert "Pass" in opening
        assert "before" in opening.lower() and "Stratagem" in opening
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
    assert "Check Attack legality for **both** sides at the start of their paired Strike step" in DETAILED
    assert "If both Strikes use the same Force, the second cannot Attack again" in DETAILED
    assert "does **not** help a Raider" in DETAILED
    assert "identical in every Battle, including Battle I" in SHORT
    assert "The same sequence applies to every Battle, including Battle I" in DETAILED
    assert "No initial deployment turn, skipped order phase, or Battle I exception" in DETAILED
    assert "after both closing turns" in DETAILED
    assert "two closing turns following the first **Pass**" in SHORT
    assert "after the first Pass and the **two closing turns**" in DETAILED
    assert "before the single Stratagem reveal window" in DETAILED
    assert SHORT.index("## Passing and ending a Battle") < SHORT.index("## Opening Orders") < SHORT.index("## Resolving a Battle")
    assert DETAILED.index("## Passing and ending a Battle") < DETAILED.index("## Opening Orders") < DETAILED.index("## Resolving a Battle")
    assert "Both players reveal their **Opening Orders**, then **resolve the Battle**" in SHORT
    assert "**Opening Orders** are revealed and resolved; then resolve the Battle's Stratagems" in DETAILED

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
    assert "chooses one of their Forces in each lost Front" in DETAILED
    assert "before recovery" in SHORT

    # Recheck that opening Strikes do not grant unlimited normal attacks,
    # and the price remains a Command expenditure, not an extra Action.
    assert "one Attack per Battle" in DETAILED
    assert "No Action or Command cost" in SHORT
    assert "all valid Commit costs" in DETAILED
    assert "two Commits" in SHORT or "Two Commits" in SHORT
    assert "followed by Strikes" in SHORT
    print("PASS: two secret Opening Orders/player, repeated types and simultaneous steps")
    print("PASS: identical post-Pass/post-closing-turn timing for every Battle; Commit and Attack limits")
    print("PASS: independent full-margin Command loss, tie=0, Collapse-before-recovery")
    print("LIMIT: tabletop balance and native AI are not verified by this static contract")


if __name__ == "__main__":
    run()
