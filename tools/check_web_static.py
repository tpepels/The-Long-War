"""Static integrity checks for the browser site.

This is deliberately not a second web build system. It catches the cheap class
of failures that should never reach a browser: JavaScript syntax errors and
references to local modules/data assets that the Pages build did not publish.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = ROOT / "dist"

HTML_REF_RE = re.compile(r'\b(?:src|href)=["\']([^"\']+)["\']')
MODULE_FROM_RE = re.compile(r'\bfrom\s+["\']([^"\']+)["\']')
DYNAMIC_IMPORT_RE = re.compile(r'\bimport\(\s*["\']([^"\']+)["\']\s*\)')
DATA_REF_RE = re.compile(r'["\'](data/[^"\']+?\.json)(?:\?[^"\']*)?["\']')
META_RUNTIME_RE = re.compile(
    r'new URL\(\s*["\']([^"\']+)["\']\s*,\s*runtimeURL\s*\)'
)
IMPORT_META_RE = re.compile(
    r'new URL\(\s*["\']([^"\']+)["\']\s*,\s*import\.meta\.url\s*\)'
)
PNG_ICON_DECL_RE = re.compile(r"PNG_ICONS\s*=\s*new Set\(\s*\[([\s\S]*?)\]\s*\)")
PNG_ICON_NAME_RE = re.compile(r'"([a-z0-9_]+)"')

DOM_HELPER_ID_RE = re.compile(r'\$\(\s*["\']([^"\']+)["\']\s*\)')
GET_ELEMENT_ID_RE = re.compile(
    r'getElementById\(\s*["\']([^"\']+)["\']\s*\)'
)
DECLARED_ID_RE = re.compile(r'\bid=["\']([^"\']+)["\']')
CHECKED_HTML_SUFFIXES = {
    ".css", ".js", ".mjs", ".json", ".svg", ".png", ".jpg", ".jpeg", ".webp",
}


def _clean_ref(value: str) -> str:
    return urlsplit(value).path


def _is_external(value: str) -> bool:
    return (
        not value
        or value.startswith(("#", "data:", "mailto:", "tel:"))
        or "://" in value
    )


def _display_path(path: Path, root: Path) -> Path:
    """Return a stable human-readable path for repository or temporary roots."""
    for base in (ROOT, root.parent):
        try:
            return path.relative_to(base)
        except ValueError:
            continue
    return path


def _node_syntax_errors(root: Path) -> list[str]:
    node = shutil.which("node")
    if node is None:
        return ["node is required for browser syntax checks"]

    errors: list[str] = []
    for path in sorted(
        item
        for item in root.iterdir()
        if item.is_file() and item.suffix in {".js", ".mjs"}
    ):
        result = subprocess.run(
            [node, "--check", "--input-type=module"],
            input=path.read_text(encoding="utf-8"),
            text=True,
            capture_output=True,
        )
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            errors.append(f"{_display_path(path, root)}: JavaScript syntax error\n{detail}")
    return errors


def _play_dom_errors(root: Path) -> list[str]:
    page = root / "play.html"
    script = root / "play.js"
    if not page.exists() or not script.exists():
        return []

    js = script.read_text(encoding="utf-8")
    declared = set(
        DECLARED_ID_RE.findall(page.read_text(encoding="utf-8"))
    )
    # Controls such as reveal-hand and confirm-mulligan are authored as HTML
    # strings inside play.js, so include literal ids created there too.
    declared.update(DECLARED_ID_RE.findall(js))

    referenced = set(DOM_HELPER_ID_RE.findall(js))
    referenced.update(GET_ELEMENT_ID_RE.findall(js))
    missing = sorted(referenced - declared)
    return [
        f"{_display_path(script, root)} references missing DOM id #{value}"
        for value in missing
    ]


def _png_icon_errors(root: Path) -> list[str]:
    """Verify every opted-in PNG exists in both authored and built site assets."""
    script = root / "card-symbols.js"
    if not script.exists():
        return []
    source = script.read_text(encoding="utf-8")
    match = PNG_ICON_DECL_RE.search(source)
    if not match:
        return []
    names = PNG_ICON_NAME_RE.findall(match.group(1))
    if len(names) != len(set(names)):
        return ["card-symbols.js declares duplicate PNG icon names"]
    return [
        f"{_display_path(script, root)}: missing PNG icon asset for {name}"
        for name in names
        if not (root / "art" / "icons" / "sizes" / "128" / (name + ".png")).is_file()
    ]


def _source_reference_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for page in sorted(root.glob("*.html")):
        source = page.read_text(encoding="utf-8")
        for value in HTML_REF_RE.findall(source):
            if _is_external(value):
                continue
            clean = _clean_ref(value)
            suffix = Path(clean).suffix.lower()
            if suffix not in CHECKED_HTML_SUFFIXES:
                continue
            target = (page.parent / clean).resolve()
            if not target.exists():
                errors.append(
                    f"{_display_path(page, root)} references missing local asset {value}"
                )

    for script in sorted([*root.glob("*.js"), *root.glob("*.mjs")]):
        source = script.read_text(encoding="utf-8")
        refs = [
            *MODULE_FROM_RE.findall(source),
            *DYNAMIC_IMPORT_RE.findall(source),
        ]
        for value in refs:
            if _is_external(value) or not value.startswith("."):
                continue
            clean = _clean_ref(value)
            target = (script.parent / clean).resolve()
            if not target.exists():
                errors.append(
                    f"{_display_path(script, root)} imports missing module {value}"
                )
    errors.extend(_play_dom_errors(root))
    return errors


def _dist_reference_errors(root: Path) -> list[str]:
    errors = _source_reference_errors(root)

    for script in sorted([*root.glob("*.js"), *root.glob("*.mjs")]):
        source = script.read_text(encoding="utf-8")

        for value in DATA_REF_RE.findall(source):
            target = root / _clean_ref(value)
            if not target.exists():
                errors.append(
                    f"{_display_path(script, root)} requests missing built data asset {value}"
                )

        for value in IMPORT_META_RE.findall(source):
            clean = _clean_ref(value)
            target = (script.parent / clean).resolve()
            if not target.exists():
                errors.append(
                    f"{_display_path(script, root)} references missing import.meta asset {value}"
                )

        for value in META_RUNTIME_RE.findall(source):
            clean = _clean_ref(value)
            target = root / "runtime" / clean
            if not target.exists():
                errors.append(
                    f"{_display_path(script, root)} references missing runtime asset {value}"
                )

    manifest = root / "runtime" / "longwar-runtime.json"
    if manifest.exists():
        import json

        payload = json.loads(manifest.read_text(encoding="utf-8"))
        wheel = payload.get("wheel")
        if not wheel or not (manifest.parent / wheel).is_file():
            errors.append("runtime/longwar-runtime.json points to a missing wheel")

    return errors


def check(source: Path = WEB, dist: Path | None = None) -> list[str]:
    errors = _node_syntax_errors(source)
    errors.extend(_source_reference_errors(source))
    errors.extend(_png_icon_errors(source))
    if dist is not None:
        errors.extend(_node_syntax_errors(dist))
        errors.extend(_dist_reference_errors(dist))
        errors.extend(_png_icon_errors(dist))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check authored browser syntax and built static references."
    )
    parser.add_argument(
        "--dist",
        type=Path,
        help="Also validate a completed Pages build (normally dist/).",
    )
    args = parser.parse_args()

    dist = args.dist.resolve() if args.dist else None
    errors = check(WEB, dist)
    if errors:
        raise SystemExit(
            "Browser static integrity failed:\n- " + "\n- ".join(errors)
        )
    suffix = f" and {dist.relative_to(ROOT)}" if dist else ""
    print(f"Browser static integrity OK: web{suffix}")


if __name__ == "__main__":
    main()
