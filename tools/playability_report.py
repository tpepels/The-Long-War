from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.playability import build_playability_report, render_markdown

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate AI simulation telemetry into human-playability statistics."
    )
    parser.add_argument("simulations", nargs="+", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/playability-report.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("artifacts/playability-report.md"),
    )
    args = parser.parse_args()

    simulations = []
    for path in args.simulations:
        source = resolve(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["_label"] = source.stem
        simulations.append(payload)

    report = build_playability_report(simulations)
    markdown = render_markdown(report)

    json_output = resolve(args.json_output)
    markdown_output = resolve(args.markdown_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_output.write_text(markdown, encoding="utf-8")

    print(markdown)
    print(f"Wrote {json_output.relative_to(ROOT)}")
    print(f"Wrote {markdown_output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
