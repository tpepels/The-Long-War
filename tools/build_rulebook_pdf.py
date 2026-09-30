#!/usr/bin/env python3
"""Build the canonical four-page printable rulebook PDF."""

from __future__ import annotations

import argparse
from pathlib import Path

from weasyprint import HTML


EXPECTED_PAGES = 4


def build_rulebook_pdf(source: Path, output: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    if not source.exists():
        raise FileNotFoundError(source)

    document = HTML(
        filename=str(source),
        base_url=str(source.parent),
    ).render()

    if len(document.pages) != EXPECTED_PAGES:
        raise RuntimeError(
            f"Rulebook PDF must contain exactly {EXPECTED_PAGES} pages; "
            f"renderer produced {len(document.pages)}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    document.write_pdf(str(output))

    if output.stat().st_size < 10_000:
        raise RuntimeError(f"Rulebook PDF output looks incomplete: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path("dist/rulebook.html"),
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("dist/rulebook.pdf"),
    )
    args = parser.parse_args()
    build_rulebook_pdf(args.source, args.output)
    print(f"Built {args.output} ({EXPECTED_PAGES} pages)")


if __name__ == "__main__":
    main()
