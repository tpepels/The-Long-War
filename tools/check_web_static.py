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
            errors.append(f"{path.relative_to(ROOT)}: JavaScript syntax error\n{detail}")
    return errors


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
                    f"{page.relative_to(ROOT)} references missing local asset {value}"
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
                    f"{script.relative_to(ROOT)} imports missing module {value}"
                )
    return errors


def _dist_reference_errors(root: Path) -> list[str]:
    errors = _source_reference_errors(root)

    for script in sorted([*root.glob("*.js"), *root.glob("*.mjs")]):
        source = script.read_text(encoding="utf-8")

        for value in DATA_REF_RE.findall(source):
            target = root / _clean_ref(value)
            if not target.exists():
                errors.append(
                    f"{script.relative_to(ROOT)} requests missing built data asset {value}"
                )

        for value in IMPORT_META_RE.findall(source):
            clean = _clean_ref(value)
            target = (script.parent / clean).resolve()
            if not target.exists():
                errors.append(
                    f"{script.relative_to(ROOT)} references missing import.meta asset {value}"
                )

        for value in META_RUNTIME_RE.findall(source):
            clean = _clean_ref(value)
            target = root / "runtime" / clean
            if not target.exists():
                errors.append(
                    f"{script.relative_to(ROOT)} references missing runtime asset {value}"
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
    if dist is not None:
        errors.extend(_node_syntax_errors(dist))
        errors.extend(_dist_reference_errors(dist))
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
