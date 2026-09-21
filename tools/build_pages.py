from __future__ import annotations

import json
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = ROOT / "dist"
RULEBOOK = ROOT / "rules" / "rulebook.md"
CARDS = ROOT / "cards" / "cards.json"
BALANCE_HEALTH = ROOT / "artifacts" / "balance-health.json"


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(WEB, DIST)

    data_dir = DIST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CARDS, data_dir / "cards.json")
    if BALANCE_HEALTH.exists():
        shutil.copy2(BALANCE_HEALTH, data_dir / "balance-health.json")

    artifacts_dir = ROOT / "artifacts"
    if artifacts_dir.exists():
        for artifact in artifacts_dir.glob("*.json"):
            shutil.copy2(artifact, data_dir / artifact.name)

    rulebook_md = RULEBOOK.read_text(encoding="utf-8")
    rulebook_html = markdown.markdown(
        rulebook_md,
        extensions=["extra", "sane_lists"],
    )

    template = (WEB / "rulebook.template.html").read_text(encoding="utf-8")
    rendered = template.replace("{{RULEBOOK}}", rulebook_html)
    (DIST / "rulebook.html").write_text(rendered, encoding="utf-8")
    (DIST / "rulebook.template.html").unlink(missing_ok=True)

    card_data = json.loads(CARDS.read_text(encoding="utf-8"))
    balance = "with balance data" if BALANCE_HEALTH.exists() else "without balance data"
    print(f"Built Pages site with {len(card_data['cards'])} cards ({balance}) at {DIST}")


if __name__ == "__main__":
    main()
