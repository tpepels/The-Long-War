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


def test_mccfr_execution_is_not_part_of_routine_workflows() -> None:
    expensive_markers = (
        "tools/verify_mccfr.py",
        "tools/train_mccfr.py",
        "--agent-a mccfr",
        "--agent-b mccfr",
        "--agent-a online_mccfr",
        "--agent-b online_mccfr",
        "make test-algorithm",
    )
    for workflow in ("ci.yml", "pages.yml", "balance.yml"):
        content = text(workflow)
        for marker in expensive_markers:
            assert marker not in content, f"{marker} leaked into {workflow}"


def test_counterfactual_workflow_is_manual_and_online_mccfr_is_opt_in() -> None:
    content = text("counterfactual.yml")
    assert "workflow_dispatch:" in content
    assert "schedule:" not in content
    assert "tools/counterfactual_balance.py" in content
    assert "tools/targeted_online_counterfactual.py" in content
    assert "run_online_mccfr" in content
    assert 'if: ${{ inputs.run_online_mccfr }}' in content
    assert "counterfactual-reports" in content


def test_mccfr_validation_is_manual_only() -> None:
    content = text("mccfr.yml")
    assert "workflow_dispatch:" in content
    assert "schedule:" not in content
    assert "push:" not in content
    assert "pull_request:" not in content
    assert "tools/verify_mccfr.py" in content
    assert "tools/train_mccfr.py" in content
    assert "mccfr-reports" in content


def test_routine_workflows_use_per_run_seeds() -> None:
    for workflow in ("ci.yml", "pages.yml", "balance.yml"):
        content = text(workflow)
        assert "RUN_SEED" in content
        assert "GITHUB_RUN_ID" in content
        assert "--seed 1701" not in content
        assert "--seed 6401" not in content
        assert "--seed 7401" not in content


def test_expanded_playtest_gate_confirms_counterfactual_reds_before_failing() -> None:
    content = text("expanded-playtest-gate.yml")
    assert "Build human-playability statistics" in content
    assert "gate-playability.json" in content
    assert "Confirm red counterfactual outliers" in content
    assert '--cards "$card_id"' in content
    assert "26092341 + index" in content
    assert "confirmed_red" in content
    assert "independently confirmed red card outliers" in content
