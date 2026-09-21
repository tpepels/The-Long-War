from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.health import analyze_simulation, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", type=Path, default=Path("artifacts/heuristic-selfplay.json"))
    parser.add_argument("--json-output", type=Path, default=Path("artifacts/balance-health.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("artifacts/balance-health.md"))
    args = parser.parse_args()

    simulation = json.loads(resolve(args.simulation).read_text(encoding="utf-8"))
    card_data = load_card_file(ROOT / "cards" / "cards.json")
    report = analyze_simulation(simulation, card_data)

    json_output = resolve(args.json_output)
    markdown_output = resolve(args.markdown_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(report), encoding="utf-8")

    summary = report["summary"]
    print(f"Health report: {summary['cards_analyzed']} cards, {summary['legends_observed']} observed Legends")
    print(f"Flags: high={summary['flags_high']} watch={summary['flags_watch']}")
    print(f"Wrote {json_output.relative_to(ROOT)}")
    print(f"Wrote {markdown_output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
