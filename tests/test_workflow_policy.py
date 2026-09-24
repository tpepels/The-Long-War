from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_github_actions_are_pages_deployment_only() -> None:
    workflows = sorted(path.name for path in WORKFLOWS.glob("*.yml"))
    assert workflows == ["pages.yml"]

    content = (WORKFLOWS / "pages.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in content
    for automatic_trigger in (
        "push:",
        "pull_request:",
        "schedule:",
        "workflow_run:",
    ):
        assert automatic_trigger not in content

    assert "tools/build_pages.py" in content
    assert "actions/deploy-pages" in content


def test_pages_workflow_contains_no_analysis_or_solver_jobs() -> None:
    content = (WORKFLOWS / "pages.yml").read_text(encoding="utf-8")
    forbidden = (
        "tools/simulate.py",
        "tools/analyze_telemetry.py",
        "tools/balance_report.py",
        "tools/playability_report.py",
        "tools/counterfactual_balance.py",
        "tools/targeted_online_counterfactual.py",
        "tools/verify_mccfr.py",
        "tools/train_mccfr.py",
        "mccfr-policy",
        "counterfactual-reports",
    )
    for marker in forbidden:
        assert marker not in content
