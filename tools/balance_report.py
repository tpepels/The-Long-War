from __future__ import annotations

import json
from pathlib import Path

from longwar.balance import build_report
from longwar.cards import load_card_file
from longwar.fingerprint import current_game_fingerprint

ROOT = Path(__file__).resolve().parents[1]
CARD_FILE = ROOT / "cards" / "cards.json"
OUTPUT = ROOT / "artifacts" / "balance-report.json"


def main() -> None:
    data = load_card_file(CARD_FILE)
    report = build_report(data)
    report["game_fingerprint"] = current_game_fingerprint()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    stats = report["static_strength"]
    print(f"Validated {len(data['cards'])} cards")
    print(f"Evaluated {report['legend_count']} Subject–Bond–Name combinations")
    print(
        "Static Subject–Bond–Name Strength: "
        f"mean={stats['mean']:.2f}, sd={stats['population_sd']:.2f}, "
        f"range={stats['min']}–{stats['max']}"
    )
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
