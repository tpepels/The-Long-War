#!/usr/bin/env python3
"""Build the canonical printable rulebook with Typst.

The web rulebook remains HTML for convenient reading. The printable PDF is
compiled independently so browser pagination cannot change the physical layout.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

from build_pages import print_build_version, render_rule_tokens
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]
RULEBOOK = ROOT / "rules" / "rulebook.md"
DIST = ROOT / "dist"
TYPST_SOURCE = DIST / "rulebook.typ"
OUTPUT = DIST / "rulebook.pdf"

MIN_PAGE_TEXT = 80
MAX_PAGES = 8


TEACHING_PLATE_IMAGES = {
    "rulebook-passing.png",
    "rulebook-battle-resolution.png",
    "rulebook-command-collapse.png",
}


def _string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )


def _inline(value: str) -> str:
    """Render the small inline-Markdown subset used by the rulebook."""
    value = re.sub(r"\s+\{#[A-Za-z0-9_-]+\}\s*$", "", value)
    parts: list[str] = []
    cursor = 0
    pattern = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")
    for match in pattern.finditer(value):
        if match.start() > cursor:
            parts.append(f'#text("{_string(value[cursor:match.start()])}")')
        token = match.group(0)
        if token.startswith("**"):
            parts.append(f'#text(weight: "bold", "{_string(token[2:-2])}")')
        else:
            parts.append(f'#text(style: "italic", "{_string(token[1:-1])}")')
        cursor = match.end()
    if cursor < len(value):
        parts.append(f'#text("{_string(value[cursor:])}")')
    return "".join(parts) or '#text("")'


def _flush_paragraph(lines: list[str], out: list[str]) -> None:
    if not lines:
        return
    text = " ".join(line.strip() for line in lines).strip()
    if text:
        out.append(_inline(text))
        out.append("")
    lines.clear()


def _pdf_safe_image_path(path: str) -> str:
    """Decode JPEG rulebook art to PNG before Typst embeds it.

    The generated card illustrations are deliberately kept as raster artwork.
    Some JPEG decoders tolerate their source streams more readily than PDF
    viewers do, so the print path normalizes them through FFmpeg first.
    """
    source = DIST / path
    if source.suffix.lower() not in {".jpg", ".jpeg"}:
        return path
    if not source.exists():
        raise FileNotFoundError(f"Rulebook image not found: {source}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "FFmpeg is required to normalize rulebook card art for print."
        )

    target = source.with_name(source.stem + "-print.png")
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-err_detect",
            "ignore_err",
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(target),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not target.exists() or target.stat().st_size < 2_000:
        detail = result.stderr.strip() or "no decoder output"
        raise RuntimeError(
            f"Could not normalize rulebook card art {source.name}: {detail}"
        )
    return target.relative_to(DIST).as_posix()


def markdown_to_typst(source: str, version: str) -> str:
    """Convert the intentionally simple player-facing Markdown to Typst."""
    lines = source.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_quote = False
    quote_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []
    columns_started = False

    preamble = f"""#set page(
  paper: "a4",
  margin: (top: 12mm, bottom: 14mm, x: 13mm),
  fill: rgb("#f8f3e9"),
  footer: context [
    #align(right)[
      #text(size: 7pt, fill: rgb("#666666"))[
        TLW print v{version} · #counter(page).display("1")
      ]
    ]
  ],
)
#set text(size: 9.2pt, fill: rgb("#222222"))
#set par(justify: true, leading: 0.5em)
#set list(indent: 12pt, body-indent: 6pt, spacing: 2pt)
#set enum(indent: 12pt, body-indent: 6pt, spacing: 2pt)
#set heading(numbering: none)

#show heading.where(level: 2): it => block(
  sticky: true,
  above: 8pt,
  below: 4pt,
  breakable: false,
  fill: rgb("#efe6d4"),
  stroke: 0.55pt + rgb("#b6a487"),
  inset: (x: 7pt, y: 5pt),
  radius: 2pt,
)[#text(size: 15pt, weight: "semibold", fill: rgb("#2d261f"))[#it.body]]

#show heading.where(level: 3): it => block(
  sticky: true,
  above: 6pt,
  below: 2.5pt,
  breakable: false,
  fill: rgb("#f2ecdf"),
  inset: (x: 5pt, y: 3pt),
  radius: 1.5pt,
)[#text(size: 9pt, weight: "bold", fill: rgb("#3a3229"))[#it.body]]

#align(left)[
  #text(size: 31pt, weight: "semibold")[The Long War]
]
#line(length: 100%, stroke: 1.1pt + rgb("#222222"))
#v(4pt)
#text(size: 12pt, style: "italic", fill: rgb("#666666"))[Fight now. Live with it later.]
#v(8pt)
"""
    out.append(preamble)

    def finish_quote() -> None:
        nonlocal quote_lines, in_quote
        if not quote_lines:
            in_quote = False
            return
        text = " ".join(quote_lines).strip()
        out.append(
            '#block(fill: rgb("#f2eee4"), stroke: (left: 2pt + rgb("#555555")), '
            'inset: 8pt, width: 100%)[' + _inline(text) + "]"
        )
        out.append("")
        quote_lines = []
        in_quote = False

    def finish_table() -> None:
        nonlocal table_rows, in_table
        if not table_rows:
            in_table = False
            return
        rows = table_rows
        if len(rows) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in rows[1]):
            rows = [rows[0], *rows[2:]]
        cells: list[str] = []
        for row_index, row in enumerate(rows):
            for cell in row:
                rendered = _inline(cell.strip())
                if row_index == 0:
                    rendered = f'#text(weight: "bold")[{rendered}]'
                cells.append(f"[{rendered}]")
        out.append(
            '#table(columns: (0.95fr, 1.65fr), inset: 4pt, '
            'stroke: 0.35pt + rgb("#aaaaaa"), ' + ", ".join(cells) + ")"
        )
        out.append("")
        table_rows = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()

        if in_code:
            if line.strip() == "```":
                in_code = False
                if any("BATTLE LINE" in item for item in code_lines):
                    out.append('#align(center)[#image("assets/rulebook-battlefield.svg", width: 96%)]')
                else:
                    block = "\n".join(code_lines)
                    out.append(f'#raw(block: true, "{_string(block)}")')
                out.append("")
                code_lines = []
            else:
                code_lines.append(line)
            continue

        image_match = re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)", line.strip())
        if image_match:
            _flush_paragraph(paragraph, out)
            finish_quote()
            finish_table()
            alt, path = image_match.groups()
            path = _pdf_safe_image_path(path)
            name = Path(path).name.replace("-print.png", ".jpg")
            teaching_plate = name in TEACHING_PLATE_IMAGES
            label = "BATTLE PLATE" if teaching_plate else "FIELD EXAMPLE"
            image_width = "100%" if teaching_plate else "94%"
            out.append(
                '#block('
                'breakable: false, above: 4pt, below: 5pt, '
                'fill: rgb("#f7f2e8"), '
                'stroke: 0.45pt + rgb("#9b8e77"), '
                'inset: 4pt, radius: 2pt'
                ')['
                f'#align(center)[#image("{_string(path)}", width: {image_width})]'
                '#v(2.5pt)'
                f'#text(size: 6.5pt, weight: "bold", fill: rgb("#5e5446"), "{label}")'
                '#h(3pt)'
                f'#text(size: 6.5pt, fill: rgb("#6f6558"), "{_string(alt)}")'
                ']'
            )
            continue

        if line.strip().startswith("```"):
            _flush_paragraph(paragraph, out)
            finish_quote()
            finish_table()
            in_code = True
            continue

        if line.startswith(">"):
            _flush_paragraph(paragraph, out)
            finish_table()
            in_quote = True
            quote_lines.append(line[1:].strip())
            continue
        if in_quote and line.strip():
            quote_lines.append(line.strip())
            continue
        if in_quote:
            finish_quote()
            continue

        if line.startswith("|") and line.endswith("|"):
            _flush_paragraph(paragraph, out)
            finish_quote()
            in_table = True
            table_rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        if in_table:
            finish_table()

        if not line.strip():
            _flush_paragraph(paragraph, out)
            continue

        if line.startswith("# "):
            # Title is typeset by the fixed Typst preamble.
            continue

        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            # The Markdown subtitle is also typeset by the fixed preamble.
            continue

        if line.startswith("## "):
            _flush_paragraph(paragraph, out)
            if not columns_started:
                out.append("#columns(2, gutter: 9mm)[")
                columns_started = True
            title = re.sub(r"\s+\{#[A-Za-z0-9_-]+\}\s*$", "", line[3:].strip())
            out.append(f"== {title}")
            continue

        if line.startswith("### "):
            _flush_paragraph(paragraph, out)
            title = re.sub(r"\s+\{#[A-Za-z0-9_-]+\}\s*$", "", line[4:].strip())
            out.append(f"=== {title}")
            continue

        if line.strip() == "---":
            _flush_paragraph(paragraph, out)
            out.append('#v(3pt)')
            out.append('#line(length: 100%, stroke: 0.45pt + rgb("#999999"))')
            out.append('#v(3pt)')
            continue

        bullet = re.match(r"^\s*-\s+(.+)$", line)
        if bullet:
            _flush_paragraph(paragraph, out)
            out.append("- " + _inline(bullet.group(1)))
            continue

        numbered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if numbered:
            _flush_paragraph(paragraph, out)
            out.append("+ " + _inline(numbered.group(1)))
            continue

        paragraph.append(line)

    _flush_paragraph(paragraph, out)
    finish_quote()
    finish_table()
    if columns_started:
        out.append("]")

    return "\n".join(out).rstrip() + "\n"


def verify_pdf(path: Path, version: str) -> None:
    reader = PdfReader(str(path))
    if not 2 <= len(reader.pages) <= MAX_PAGES:
        raise RuntimeError(
            f"Unexpected rulebook length: {len(reader.pages)} pages "
            f"(expected 2-{MAX_PAGES})"
        )

    stamp = f"TLW print v{version}"
    for page_number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if len(text) < MIN_PAGE_TEXT:
            raise RuntimeError(
                f"Rulebook page {page_number} is blank or nearly blank "
                f"({len(text)} extracted characters)"
            )
        if stamp not in text:
            raise RuntimeError(
                f"Rulebook page {page_number} is missing print version {stamp}"
            )


def build_rulebook_pdf() -> None:
    typst = shutil.which("typst")
    if typst is None:
        raise RuntimeError(
            "Typst is required to build the printable rulebook. "
            "Install Typst 0.15.1 or run the Pages workflow."
        )

    version = print_build_version()
    source = render_rule_tokens(RULEBOOK.read_text(encoding="utf-8"), GameRules.standard())
    typst_source = markdown_to_typst(source, version)

    DIST.mkdir(parents=True, exist_ok=True)
    TYPST_SOURCE.write_text(typst_source, encoding="utf-8")

    subprocess.run(
        [
            typst,
            "compile",
            "--root",
            str(ROOT),
            str(TYPST_SOURCE),
            str(OUTPUT),
        ],
        cwd=ROOT,
        check=True,
    )
    verify_pdf(OUTPUT, version)

    if OUTPUT.stat().st_size < 10_000:
        raise RuntimeError(f"Rulebook PDF output looks incomplete: {OUTPUT}")


def main() -> None:
    build_rulebook_pdf()
    print(f"Built {OUTPUT} with Typst")


if __name__ == "__main__":
    main()
