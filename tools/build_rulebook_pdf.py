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

if __package__:
    from .build_pages import print_build_version, render_rule_tokens
else:
    from build_pages import print_build_version, render_rule_tokens
from longwar.rules import GameRules


ROOT = Path(__file__).resolve().parents[1]
RULEBOOK = ROOT / "rules" / "rulebook.md"
DIST = ROOT / "dist"
TYPST_SOURCE = DIST / "rulebook.typ"
OUTPUT = DIST / "rulebook.pdf"

MIN_PAGE_TEXT = 80
MAX_PAGES_WARNING = 8



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
        if re.match(r"^\\*\\*(?:Tactics|Orders|Narrative|Stratagem|Heroes)\\*\\*", text):
            out.append(
                '#block(fill: rgb("#ecebe4"), '
                'stroke: (left: 2pt + rgb("#ad8a50")), '
                'inset: (x: 10pt, y: 8pt), width: 100%)['
                + _inline(text) + ']'
            )
        else:
            out.append(_inline(text))
        out.append("")
    lines.clear()



def markdown_to_typst(source: str, version: str) -> str:
    """Typeset the canonical Markdown as a two-column handbook with full-width aids."""
    lines = source.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    in_quote = False
    quote_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []
    current_section = ""
    pending_list: list[str] = []
    pending_kind = ""
    resolution_open = False
    resolution_index = 0
    columns_open = False

    preamble = f"""#set page(
  paper: "a4",
  margin: (top: 17mm, bottom: 18mm, x: 17mm),
  fill: rgb("#faf7ef"),
  header: [
    #text(size: 7pt, weight: "bold", fill: rgb("#53636a"))[THE LONG WAR   /   FIELD MANUAL]
    #v(3pt)
    #line(length: 100%, stroke: .55pt + rgb("#c5b9a4"))
  ],
  footer: context [
    #line(length: 100%, stroke: .45pt + rgb("#c5b9a4"))
    #v(3pt)
    #grid(
      columns: (1fr, 1fr),
      [#text(size: 7pt, fill: rgb("#666056"))[TLW print v{version}]],
      align(right)[#text(size: 7pt, fill: rgb("#666056"))[PAGE #counter(page).display("1")]],
    )
  ],
)
#set text(size: 9.5pt, fill: rgb("#242620"))
#set par(justify: false, leading: .63em, spacing: .78em)
#set list(indent: 12pt, body-indent: 6pt, spacing: 4pt)
#set enum(indent: 12pt, body-indent: 6pt, spacing: 4pt)
#set heading(numbering: none)

#show heading.where(level: 2): it => block(
  sticky: true,
  above: 15pt,
  below: 7pt,
  breakable: false,
  fill: rgb("#e7ebea"),
  stroke: (left: 3pt + rgb("#293c47"), bottom: .55pt + rgb("#bbc6c4")),
  inset: (x: 11pt, y: 9pt),
  radius: 1pt,
)[#text(size: 17pt, weight: "semibold", fill: rgb("#283b45"))[#it.body]]

#show heading.where(level: 3): it => block(
  sticky: true,
  above: 11pt,
  below: 4pt,
  breakable: false,
  fill: rgb("#f0e8dc"),
  stroke: (left: 1.6pt + rgb("#986448")),
  inset: (x: 8pt, y: 5pt),
  radius: 1pt,
)[#text(size: 10.5pt, weight: "bold", fill: rgb("#39342d"))[#it.body]]

#block(
  fill: rgb("#293c47"),
  width: 100%,
  inset: (x: 14pt, y: 16pt),
)[
  #text(size: 7.5pt, weight: "bold", fill: rgb("#eacb92"))[A GAME OF COMMITMENT AND CONSEQUENCE]
  #v(7pt)
  #text(size: 32pt, weight: "semibold", fill: white)[The Long War]
  #v(5pt)
  #text(size: 12pt, style: "italic", fill: rgb("#f6edda"))[Fight now. Live with it later.]
]
#v(10pt)
#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  gutter: 5pt,
  [#block(fill: rgb("#ece5d7"), inset: 9pt, width: 100%, stroke: (bottom: 2pt + rgb("#ad8a50")))[
    #text(size: 23pt, weight: "bold", fill: rgb("#293c47"))[20]
    #v(3pt)
    #text(size: 7pt, weight: "bold")[STARTING COMMAND]
  ]],
  [#block(fill: rgb("#ece5d7"), inset: 9pt, width: 100%, stroke: (bottom: 2pt + rgb("#ad8a50")))[
    #text(size: 23pt, weight: "bold", fill: rgb("#293c47"))[2]
    #v(3pt)
    #text(size: 7pt, weight: "bold")[ACTIONS PER TURN]
  ]],
  [#block(fill: rgb("#ece5d7"), inset: 9pt, width: 100%, stroke: (bottom: 2pt + rgb("#ad8a50")))[
    #text(size: 23pt, weight: "bold", fill: rgb("#293c47"))[4]
    #v(3pt)
    #text(size: 7pt, weight: "bold")[FRONTS BY BATTLE III]
  ]],
  [#block(fill: rgb("#ece5d7"), inset: 9pt, width: 100%, stroke: (bottom: 2pt + rgb("#ad8a50")))[
    #text(size: 23pt, weight: "bold", fill: rgb("#293c47"))[3]
    #v(3pt)
    #text(size: 7pt, weight: "bold")[FORMATION LAYERS]
  ]],
)
#v(9pt)
"""
    out.append(preamble)

    def open_columns() -> None:
        nonlocal columns_open
        if not columns_open:
            out.append("#columns(2, gutter: 8mm)[")
            columns_open = True

    def close_columns() -> None:
        nonlocal columns_open
        if columns_open:
            out.append("]")
            columns_open = False

    def finish_list() -> None:
        """Render actual Markdown lists as legible decision aids where helpful."""
        nonlocal pending_list, pending_kind
        if not pending_list:
            return

        cards = {
            ("The shape of the war", "bullet"): (2, "BATTLE", "#e8e8e1", "#293c47"),
            ("What you need", "bullet"): (2, "PREPARE", "#f0e8d9", "#ad8a50"),
            ("Setup", "numbered"): (2, "STEP", "#f0e8d9", "#986448"),
            ("Your turn", "bullet"): (2, "ACTION", "#e8eeed", "#293c47"),
            ("Conditions and protection", "bullet"): (2, "CONDITION", "#f3e8df", "#986448"),
            ("Passing and ending a Battle", "numbered"): (3, "CLOSING TURN", "#e8eeed", "#293c47"),
        }
        # One continuous two-column flow: no forced page endings at each panel.
        style = cards.get((current_section, pending_kind))
        if style is None:
            for index, item in enumerate(pending_list):
                out.append(("- " if pending_kind == "bullet" else "+ ") + _inline(item))
        else:
            _, label, bg, accent = style
            for index, item in enumerate(pending_list, 1):
                item_bg, item_accent = bg, accent
                if current_section == "Conditions and protection" and item.startswith(
                    ("**Guarded:**", "**Inspired:**", "**Empowered:**")
                ):
                    item_bg, item_accent = "#e7eee7", "#5f7966"
                # One independent, short card per item. This can wrap to the
                # next column without pushing an entire grid to another page.
                out.append(
                    '#block(fill: rgb("' + item_bg
                    + '"), stroke: (left: 2pt + rgb("' + item_accent
                    + '")), inset: (x: 8pt, y: 6pt), width: 100%,'
                    ' breakable: false)['
                    + '#text(size: 7pt, weight: "bold", fill: rgb("' + item_accent
                    + '"))[' + label + ' ' + f"{index:02d}" + ']'
                    + '#v(3pt)'
                    + _inline(item) + ']'
                )
                out.append("#v(3pt)")
        out.append("")
        pending_list = []
        pending_kind = ""

    def close_resolution() -> None:
        nonlocal resolution_open
        if resolution_open:
            out.append("]")
            out.append("")
            resolution_open = False

    def finish_quote() -> None:
        nonlocal quote_lines, in_quote
        if not quote_lines:
            in_quote = False
            return
        text = " ".join(quote_lines).strip()
        out.append(
            '#block(fill: rgb("#efe8db"), stroke: (left: 2pt + rgb("#ab8950")), '
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
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("Rulebook Markdown table has inconsistent column counts")
        # Convert wide tables to a compact sequence of labelled reference
        # entries in the text column. All original cell content is preserved,
        # and each entry can independently move to the next column.
        headings = rows[0]
        for row_index, row in enumerate(rows[1:], 1):
            # Balance the final Reference page manually. Typst cannot balance
            # the last two columns automatically, and without this break the
            # final reference cards occupy only the left-hand column.
            if headings[0].strip().lower() == "event" and row_index == 3:
                out.append("#colbreak()")
            colour = "#f1eadd" if row_index % 2 else "#e9eeec"
            out.append(
                '#block(fill: rgb("' + colour
                + '"), inset: (x: 8pt, y: 7pt), width: 100%,'
                ' stroke: (left: 2pt + rgb("#af9167")), breakable: false)['
            )
            out.append(_inline(row[0]))
            for cell_name, cell_text in zip(headings[1:], row[1:]):
                out.append(
                    '#v(2pt)'
                    '#text(size: 7.2pt, weight: "bold", fill: rgb("#53636a"))['
                    + _string(cell_name.strip().upper()) + ':] '
                    + _inline(cell_text)
                )
            out.append("]")
            out.append("#v(4pt)")
        out.append("")
        table_rows = []
        in_table = False

    for raw in lines:
        line = raw.rstrip()

        if in_code:
            if line.strip() == "```":
                in_code = False
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
            finish_list()
            finish_quote()
            finish_table()
            alt, path = image_match.groups()
            out.append(f'#align(center)[#image("{_string(path)}", width: 100%)]')
            out.append(f'#text(size: 6.5pt, "{_string(alt)}")')
            continue

        if line.strip().startswith("```"):
            _flush_paragraph(paragraph, out)
            finish_list()
            finish_quote()
            finish_table()
            in_code = True
            continue

        if line.startswith(">"):
            _flush_paragraph(paragraph, out)
            finish_list()
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
            finish_list()
            finish_quote()
            in_table = True
            table_rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        if in_table:
            finish_table()

        if not line.strip():
            _flush_paragraph(paragraph, out)
            finish_list()
            continue

        if line.startswith("# "):
            # Title is typeset by the fixed Typst preamble.
            continue

        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            # The Markdown subtitle is also typeset by the fixed preamble.
            continue

        if line.startswith("## "):
            _flush_paragraph(paragraph, out)
            finish_list()
            close_resolution()
            current_section = re.sub(
                r"\s+\{#[A-Za-z0-9_-]+\}\s*$", "", line[3:].strip()
            )
            open_columns()
            if current_section == "The battlefield":
                out.append(f"== {current_section}")
                # A small illustrated key stays with the explanation.
                out.append(
                    '#block(fill: rgb("#f0e8dc"), width: 100%,'
                    ' inset: 8pt, stroke: (left: 2pt + rgb("#ad8a50")))['
                    '#text(weight: "bold")[FORMATION LAYERS]'
                    '#v(3pt)'
                    '#text(size: 8pt)[Name (top) · Bond (middle) · Force (base)]'
                    ']'
                )
            else:
                out.append(f"== {current_section}")
            continue

        if line.startswith("### "):
            _flush_paragraph(paragraph, out)
            finish_list()
            close_resolution()
            title = re.sub(r"\s+\{#[A-Za-z0-9_-]+\}\s*$", "", line[4:].strip())
            if current_section == "Resolving a Battle" and re.match(r"^\d+\.", title):
                resolution_index += 1
                accent = "#986448" if resolution_index % 2 == 0 else "#293c47"
                fill = "#f5ece4" if resolution_index % 2 == 0 else "#e9eeec"
                out.append(
                    '#block(width: 100%, breakable: true, inset: (x: 11pt, y: 10pt),'
                    ' fill: rgb("' + fill + '"),'
                    ' stroke: (left: 3pt + rgb("' + accent + '")))['
                )
                out.append(
                    '#text(size: 12pt, weight: "bold", fill: rgb("' + accent
                    + '"))[' + _string(title) + ']'
                )
                out.append("#v(5pt)")
                resolution_open = True
            else:
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
            if pending_list and pending_kind != "bullet":
                finish_list()
            pending_kind = "bullet"
            pending_list.append(bullet.group(1))
            continue

        numbered = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if numbered:
            _flush_paragraph(paragraph, out)
            if pending_list and pending_kind != "numbered":
                finish_list()
            pending_kind = "numbered"
            pending_list.append(numbered.group(1))
            continue

        finish_list()
        paragraph.append(line)

    _flush_paragraph(paragraph, out)
    finish_list()
    finish_quote()
    finish_table()
    close_resolution()
    close_columns()

    return "\n".join(out).rstrip() + "\n"


def verify_pdf(path: Path, version: str) -> None:
    reader = PdfReader(str(path))
    if len(reader.pages) < 2:
        raise RuntimeError(
            f"Rulebook PDF output looks incomplete: {len(reader.pages)} page(s)"
        )
    if len(reader.pages) > MAX_PAGES_WARNING:
        print(
            f"Warning: rulebook is {len(reader.pages)} pages "
            f"(design target is at most {MAX_PAGES_WARNING}); continuing build."
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
