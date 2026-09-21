from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_counterfactual_analysis_is_not_part_of_routine_workflows() -> None:
    expensive_markers = (
        "tools/counterfactual_balance.py",
        "tools/targeted_online_counterfactual.py",
    )
    for workflow in ("ci.yml", "pages.yml", "balance.yml"):
        content = text(workflow)
        for marker in expensive_markers:
            assert marker not in content, f"{marker} leaked into {workflow}"


def test_counterfactual_workflow_is_manual_and_contains_both_stages() -> None:
    content = text("counterfactual.yml")
    assert "workflow_dispatch:" in content
    assert "schedule:" not in content
    assert "tools/counterfactual_balance.py" in content
    assert "tools/targeted_online_counterfactual.py" in content
    assert "counterfactual-reports" in content


def test_routine_workflows_use_per_run_seeds() -> None:
    for workflow in ("ci.yml", "pages.yml", "balance.yml"):
        content = text(workflow)
        assert "RUN_SEED" in content
        assert "GITHUB_RUN_ID" in content
        assert "--seed 1701" not in content
        assert "--seed 6401" not in content
        assert "--seed 7401" not in content
