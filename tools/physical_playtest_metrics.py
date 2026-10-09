"""Summarize logged physical-card playtests; never simulates the Webgame.

Usage:
  python tools/physical_playtest_metrics.py playtests.jsonl
  python tools/physical_playtest_metrics.py playtests.jsonl --format json
  python tools/physical_playtest_metrics.py --self-test
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from print_cards import load_print_cards


def load_events(path: Path) -> list[dict]:
    events = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        events.append(event)
    return events


def summarize(events: list[dict]) -> dict:
    known = {c["id"] for c in load_print_cards()["cards"]}
    opportunities: dict[str, dict[str, int]] = defaultdict(
        lambda: {"seen": 0, "playable": 0, "useful": 0}
    )
    plays: dict[str, dict[str, int]] = defaultdict(
        lambda: {"played": 0, "triggered": 0, "command": 0,
                 "actions": 0, "moves": 0, "markers": 0, "fronts_flipped": 0}
    )
    decks: dict[str, dict[str, int]] = defaultdict(
        lambda: {"games": 0, "wins": 0, "draws": 0}
    )
    pairs: dict[str, int] = defaultdict(int)
    seen_opportunities: set[tuple] = set()
    seen_games: set[str] = set()
    late_turns = 0
    stranded_turns = 0
    full_turns = 0

    for index, e in enumerate(events, 1):
        kind = e.get("kind")
        if kind not in {"opportunity", "play", "turn", "result"}:
            raise ValueError(f"event {index}: unknown kind {kind!r}")
        if kind in {"opportunity", "play"}:
            card = e.get("card_id")
            if card not in known:
                raise ValueError(f"event {index}: unknown physical card {card!r}")
        if kind == "opportunity":
            key = tuple(e.get(k) for k in ("game_id", "player", "battle", "turn", "card_id"))
            if None in key or key in seen_opportunities:
                raise ValueError(f"event {index}: duplicate/incomplete opportunity key")
            seen_opportunities.add(key)
            playable = e.get("playable")
            useful = e.get("useful")
            if type(playable) is not bool or type(useful) is not bool or (useful and not playable):
                raise ValueError(f"event {index}: playable/useful must be consistent booleans")
            d = opportunities[e["card_id"]]
            d["seen"] += 1
            d["playable"] += int(playable)
            d["useful"] += int(useful)
        elif kind == "play":
            if type(e.get("effect_triggered")) is not bool:
                raise ValueError(f"event {index}: effect_triggered must be boolean")
            d = plays[e["card_id"]]
            d["played"] += 1
            d["triggered"] += int(e["effect_triggered"])
            for field, out in (("command_spent", "command"), ("actions_spent", "actions"),
                               ("formations_moved", "moves"), ("markers_changed", "markers"),
                               ("fronts_flipped", "fronts_flipped")):
                value = e.get(field, 0)
                if type(value) is not int or value < 0:
                    raise ValueError(f"event {index}: {field} must be nonnegative integer")
                d[out] += value
        elif kind == "turn":
            battle = e.get("battle")
            occupied = e.get("occupied_positions")
            available = e.get("active_positions")
            stranded = e.get("stranded_forces")
            if any(type(x) is not int for x in (battle, occupied, available, stranded)):
                raise ValueError(f"event {index}: turn counts must be integers")
            if battle < 1 or available not in (6, 9, 12) or not (0 <= occupied <= available) or stranded < 0:
                raise ValueError(f"event {index}: invalid turn occupancy")
            if battle >= 4:
                late_turns += 1
                stranded_turns += int(stranded > 0)
                full_turns += int(occupied == available)
        else:
            game_id = e.get("game_id")
            a, b, winner = e.get("deck_a"), e.get("deck_b"), e.get("winner")
            if not isinstance(game_id, str) or not game_id or game_id in seen_games:
                raise ValueError(f"event {index}: duplicate/incomplete game result")
            if not isinstance(a, str) or not a or not isinstance(b, str) or not b or winner not in ("A", "B", "draw"):
                raise ValueError(f"event {index}: invalid decks/winner")
            seen_games.add(game_id)
            pairs[" vs ".join(sorted([a, b]))] += 1
            for role, deck in (("A", a), ("B", b)):
                d = decks[deck]
                d["games"] += 1
                d["wins"] += int(winner == role)
                d["draws"] += int(winner == "draw")

    def ratio(n: int, d: int) -> float | None:
        return round(n / d, 4) if d else None

    card_rows = []
    for card_id in sorted(set(opportunities) | set(plays)):
        a, b = opportunities[card_id], plays[card_id]
        card_rows.append({
            "card_id": card_id,
            "observed_opportunities": a["seen"],
            "playable_rate": ratio(a["playable"], a["seen"]),
            "useful_rate": ratio(a["useful"], a["seen"]),
            "plays": b["played"],
            "effect_trigger_rate": ratio(b["triggered"], b["played"]),
            "mean_command_spent": ratio(b["command"], b["played"]),
            "mean_actions_spent": ratio(b["actions"], b["played"]),
            "mean_moves": ratio(b["moves"], b["played"]),
            "mean_markers_changed": ratio(b["markers"], b["played"]),
            "mean_fronts_flipped": ratio(b["fronts_flipped"], b["played"]),
        })
    deck_rows = [{
        "deck": name, **d,
        "score_rate": ratio(d["wins"] + d["draws"] / 2, d["games"]),
    } for name, d in sorted(decks.items())]
    alerts = []
    for c in card_rows:
        if c["observed_opportunities"] >= 10 and c["useful_rate"] < 0.25:
            alerts.append(f"{c['card_id']}: useful in fewer than 25% of logged opportunities")
        if c["plays"] >= 10 and c["effect_trigger_rate"] < 0.25:
            alerts.append(f"{c['card_id']}: effect triggered on fewer than 25% of plays")
    if late_turns >= 10 and stranded_turns / late_turns > 0.1:
        alerts.append("Late-battle turns with stranded Forces exceed 10%")
    if any(d["games"] >= 30 and (d["score_rate"] < 0.45 or d["score_rate"] > 0.55) for d in deck_rows):
        alerts.append("A deck has an observed score rate outside 45-55%; check matchup and sample size")
    return {
        "events": len(events),
        "unique_game_results": len(seen_games),
        "cards": card_rows,
        "decks": deck_rows,
        "matchups": dict(sorted(pairs.items())),
        "late_battle": {
            "observed_turns": late_turns,
            "stranded_force_turn_rate": ratio(stranded_turns, late_turns),
            "full_occupancy_turn_rate": ratio(full_turns, late_turns),
        },
        "investigation_flags": alerts,
        "limitations": ("Observational logs only; usefulness and fronts_flipped are "
                        "entered by players. No counterfactual win-rate inference, "
                        "no physical game simulation. Small samples are inconclusive."),
    }


def self_test() -> None:
    cards = load_print_cards()["cards"]
    assert len(cards) == len({c["id"] for c in cards}) == 131
    sample = [
        {"kind": "opportunity", "game_id": "test", "player": "A",
         "battle": 4, "turn": 1, "card_id": "re-form-the-line",
         "playable": True, "useful": True},
        {"kind": "play", "card_id": "re-form-the-line", "effect_triggered": True,
         "actions_spent": 1, "command_spent": 0, "formations_moved": 0},
        {"kind": "turn", "battle": 4, "occupied_positions": 11,
         "active_positions": 12, "stranded_forces": 1},
        {"kind": "result", "game_id": "test", "deck_a": "mobility",
         "deck_b": "defense", "winner": "A"},
    ]
    r = summarize(sample)
    assert r["cards"][0]["useful_rate"] == 1.0
    assert r["cards"][0]["mean_actions_spent"] == 1.0
    assert r["late_battle"]["stranded_force_turn_rate"] == 1.0
    assert {d["deck"] for d in r["decks"]} == {"mobility", "defense"}
    assert r["unique_game_results"] == 1
    print("PASS: physical playtest analyzer self-test (synthetic fixture; no actual games)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.log is None:
        parser.error("provide a JSONL playtest log or --self-test")
    report = summarize(load_events(args.log))
    if args.format == "json":
        print(json.dumps(report, indent=2))
        return
    print("Physical playtests:", report["unique_game_results"], "completed games;",
          report["events"], "logged events")
    for d in report["decks"]:
        score = f"{d['score_rate']:.1%}" if d["score_rate"] is not None else "n/a"
        print("  Deck:", d["deck"], d["wins"], "wins,", d["games"], "games; score rate", score)
    print("  Late battle:", report["late_battle"])
    for c in report["cards"]:
        print("  Card:", c["card_id"],
              "opportunities", c["observed_opportunities"],
              "useful-rate", c["useful_rate"],
              "plays", c["plays"], "trigger-rate", c["effect_trigger_rate"])
    for flag in report["investigation_flags"]:
        print("  Investigate:", flag)
    print(report["limitations"])


if __name__ == "__main__":
    main()
