from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_github_workflows_are_manual_only() -> None:
    for path in WORKFLOWS.glob("*.yml"):
        content = path.read_text(encoding="utf-8")
        assert "workflow_dispatch:" in content, path
        for automatic_trigger in (
            "push:",
            "pull_request:",
            "schedule:",
            "workflow_run:",
        ):
            assert automatic_trigger not in content, (
                f"{path.name} reintroduced automatic trigger "
                f"{automatic_trigger}"
            )


def test_broken_ci_and_mccfr_workflows_stay_removed() -> None:
    assert not (WORKFLOWS / "ci.yml").exists()
    assert not (WORKFLOWS / "mccfr.yml").exists()


def test_counterfactual_analysis_is_explicit_only() -> None:
    content = text("counterfactual.yml")
    assert "workflow_dispatch:" in content
    assert "tools/counterfactual_balance.py" in content
    assert "tools/targeted_online_counterfactual.py" in content
    assert "run_online_mccfr" in content
    assert "inputs.run_online_mccfr" in content


def test_pages_and_balance_do_not_run_expensive_research() -> None:
    expensive_markers = (
        "tools/counterfactual_balance.py",
        "tools/targeted_online_counterfactual.py",
        "tools/verify_mccfr.py",
        "tools/train_mccfr.py",
        "--agent-a mccfr",
        "--agent-b mccfr",
        "--agent-a online_mccfr",
        "--agent-b online_mccfr",
    )
    for workflow in ("pages.yml", "balance.yml"):
        content = text(workflow)
        for marker in expensive_markers:
            assert marker not in content, f"{marker} leaked into {workflow}"


def test_remaining_routine_analysis_workflows_use_per_run_seeds() -> None:
    for workflow in ("pages.yml", "balance.yml"):
        content = text(workflow)
        assert "RUN_SEED" in content
        assert "GITHUB_RUN_ID" in content


def test_expanded_playtest_gate_confirms_counterfactual_reds_before_failing() -> None:
    content = text("expanded-playtest-gate.yml")
    assert "Build human-playability statistics" in content
    assert "gate-playability.json" in content
    assert "Confirm red counterfactual outliers" in content
    assert '--cards "$card_id"' in content
    assert "26092341 + index" in content
    assert "confirmed_red" in content
    assert "independently confirmed red card outliers" in content
