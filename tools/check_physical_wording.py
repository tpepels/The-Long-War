"""Lightweight language consistency audit for the physical (not Webgame) cards.

Checks only clear, durable terminology conventions. Reports long effects as
advisory rather than freezing design text or imposing arbitrary line lengths.
Run: python tools/check_physical_wording.py
"""
from __future__ import annotations

import re
from print_cards import load_print_cards

PATTERNS = {
    "legacy row term": re.compile(r"\b(?:Front|Middle|Rear) row\b", re.I),
    "ASCII negative Strength": re.compile(r"(?<![\w−])-\d+ Strength\b"),
    "inconsistent Formation capitalization": re.compile(
        r"\b(?:legal friendly Formation|Named Human Formation)\b"),
}


def run() -> None:
    cards = load_print_cards()["cards"]
    assert len(cards) == 131
    problems: list[str] = []
    long: list[str] = []
    effect_count = 0
    for card in cards:
        if card["type"] == "hero":
            entries = [(mode, effect) for mode in ("force", "name")
                       for effect in card["modes"][mode]["effects"]]
        else:
            entries = [(card["type"], effect) for effect in card.get("effects", [])]
        for mode, effect in entries:
            effect_count += 1
            value = effect.get("text", "")
            if not value.strip():
                problems.append(f"{card['id']} {mode}: empty effect")
            for label, pattern in PATTERNS.items():
                if pattern.search(value):
                    problems.append(f"{card['id']} {mode}: {label}")
            if len(value) > 190:
                long.append(f"{card['id']} {mode}: {len(value)} characters")
    assert not problems, "Inconsistent physical card wording:\n" + "\n".join(problems)
    print(f"PASS: checked {len(cards)} printed identities, {effect_count} effect texts, "
          "including both Hero modes, for agreed terminology.")
    if long:
        print("ADVISORY: longest effect texts (inspect fit, do not automatically shorten):")
        for line in long:
            print("  ", line)


if __name__ == "__main__":
    run()
