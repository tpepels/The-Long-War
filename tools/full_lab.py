from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from longwar.fingerprint import (
    current_experiment_fingerprint,
    current_game_fingerprint,
)
from longwar.reference_decks import MCCFR_PROFILES
from longwar.parallelism import DEFAULT_WORKERS

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
STATE_ROOT = ARTIFACTS / "full-lab"
STAGE_ROOT = STATE_ROOT / "stages"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _policy_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _marker(name: str) -> Path:
    return STAGE_ROOT / f"{name}.json"


def _stage_current(
    name: str,
    config: dict[str, Any],
    outputs: list[Path],
    *,
    require_game_fingerprint: bool = True,
) -> bool:
    marker = _marker(name)
    if not marker.exists() or any(not path.exists() for path in outputs):
        return False
    try:
        payload = _json(marker)
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("game_fingerprint") != current_game_fingerprint():
        return False
    # Reuse is intentionally keyed to game semantics + stage config. A change
    # to an unrelated experiment helper must not retrain/replay expensive
    # current-game evidence. The experiment fingerprint remains in the marker
    # for provenance and --force is the explicit regeneration switch.
    if payload.get("config") != config:
        return False
    if require_game_fingerprint:
        for path in outputs:
            if path.suffix != ".json":
                continue
            try:
                output = _json(path)
            except (OSError, json.JSONDecodeError):
                return False
            if output.get("game_fingerprint") != current_game_fingerprint():
                return False
    return True


def _write_marker(name: str, config: dict[str, Any]) -> None:
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    _marker(name).write_text(
        json.dumps(
            {
                "game_fingerprint": current_game_fingerprint(),
                "experiment_fingerprint": current_experiment_fingerprint(),
                "config": config,
                "status": "complete",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _stage(
    name: str,
    config: dict[str, Any],
    outputs: list[Path],
    commands: list[list[str]],
    *,
    force: bool,
    require_game_fingerprint: bool = True,
) -> None:
    if not force and _stage_current(
        name,
        config,
        outputs,
        require_game_fingerprint=require_game_fingerprint,
    ):
        print(f"[reuse] {name}", flush=True)
        return
    print(f"[run] {name}", flush=True)
    for command in commands:
        _run(command)
    missing = [path for path in outputs if not path.exists()]
    if missing:
        raise SystemExit(
            f"Stage {name} completed without expected outputs: "
            + ", ".join(str(path.relative_to(ROOT)) for path in missing)
        )
    _write_marker(name, config)


def _python(*args: str) -> list[str]:
    return [sys.executable, *args]


def _check_final_lab() -> None:
    report = _json(ARTIFACTS / "lab-report.json")
    required = {
        "counterfactual": report.get("counterfactual"),
        "targeted_counterfactual": report.get("targeted_counterfactual"),
        "solver_strength": report.get("solver_strength"),
        "mccfr_suite": report.get("mccfr_suite"),
        "verification": report.get("verification"),
        "narrative_ablation": report.get("narrative_ablation"),
    }
    missing = [name for name, value in required.items() if value is None]
    profiles = report.get("progression_profiles") or {}
    if len(profiles) != len(MCCFR_PROFILES):
        missing.append(
            f"progression_profiles({len(profiles)}/{len(MCCFR_PROFILES)})"
        )
    suite_profiles = (report.get("mccfr_suite") or {}).get("profiles", [])
    if len(suite_profiles) != len(MCCFR_PROFILES):
        missing.append(
            f"mccfr_profiles({len(suite_profiles)}/{len(MCCFR_PROFILES)})"
        )
    if missing:
        raise SystemExit(
            "Full Lab finished with missing sections: " + ", ".join(missing)
        )
    stale = report.get("stale_evidence") or []
    if stale:
        raise SystemExit(
            "Full Lab still reports stale evidence: " + ", ".join(stale)
        )
    print(
        "Full Balance Lab complete: all required evidence is current.",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resumable one-command build of the complete Balance Lab."
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--jobs", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--balance-games", type=int, default=8)
    parser.add_argument("--ablation-games", type=int, default=24)
    parser.add_argument("--strength-games", type=int, default=24)
    parser.add_argument(
        "--strength-ismcts-iterations",
        type=int,
        # Explicit full-Lab budget. Keep this import-free so a fresh checkout
        # can reach the native-build validation stage before native search loads.
        default=100_000,
    )
    parser.add_argument("--strength-alpha-nodes", type=int, default=20_000)
    parser.add_argument("--strength-time-budget-seconds", type=float, default=5.0)
    parser.add_argument("--mccfr-iterations", type=int, default=5000)
    parser.add_argument("--mccfr-depth", type=int, default=3)
    parser.add_argument("--mccfr-workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--mccfr-eval-games", type=int, default=24)
    parser.add_argument("--mccfr-verification-iterations", type=int, default=50000)
    args = parser.parse_args()

    if min(
        args.jobs,
        args.ablation_games,
        args.strength_games,
        args.strength_ismcts_iterations,
        args.strength_alpha_nodes,
        args.mccfr_iterations,
        args.mccfr_depth,
        args.mccfr_workers,
        args.mccfr_eval_games,
        args.mccfr_verification_iterations,
    ) <= 0:
        raise SystemExit("Full-Lab counts and worker settings must be positive")
    if args.balance_games <= 0:
        raise SystemExit("--balance-games must be positive")
    if args.strength_time_budget_seconds <= 0:
        raise SystemExit("--strength-time-budget-seconds must be positive")

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    print(
        "Full Balance Lab\n"
        f"game fingerprint: {current_game_fingerprint()}\n"
        f"experiment fingerprint: {current_experiment_fingerprint()}",
        flush=True,
    )

    verification = ARTIFACTS / "mccfr-verification.json"
    validation_config = {
        "mccfr_verification_iterations": args.mccfr_verification_iterations,
    }
    _stage(
        "validation",
        validation_config,
        [verification],
        [
            ["make", "native-build"],
            ["make", "verify"],
            ["make", "verify-algorithms"],
            _python(
                "tools/verify_mccfr.py",
                "--iterations",
                str(args.mccfr_verification_iterations),
            ),
        ],
        force=args.force,
    )

    ablation_output = ARTIFACTS / "narrative-command-ablation.json"
    ablation_config = {
        "games": args.ablation_games,
        "seed": args.seed + 72,
        "jobs": args.jobs,
    }
    ablation_cmd = _python(
        "tools/run_experiments.py",
        "narrative-ablation",
        "--games",
        str(args.ablation_games),
        "--seed",
        str(args.seed + 72),
        "--jobs",
        str(args.jobs),
    )
    if args.force:
        ablation_cmd.append("--force")
    _stage(
        "narrative-ablation",
        ablation_config,
        [ablation_output],
        [ablation_cmd],
        force=args.force,
    )

    balance_outputs = [
        ARTIFACTS / name
        for name in (
            "balance-report.json",
            "balance-health.json",
            "balance-selfplay.json",
            "progression-selfplay.json",
            "progression-profiles.json",
            "playability-report.json",
            "balance-run-summary.json",
            "counterfactual-balance.json",
            "targeted-online-counterfactual.json",
        )
    ]
    balance_config = {
        "preset": "deep",
        "agent": "ismcts",
        "games": args.balance_games,
        "seed": args.seed,
        "jobs": args.jobs,
    }
    balance_cmd = _python(
        "tools/run_experiments.py",
        "balance",
        "--preset",
        "deep",
        "--agent",
        "ismcts",
        "--seed",
        str(args.seed),
        "--jobs",
        str(args.jobs),
        "--publish-lab",
    )
    balance_cmd.extend(["--games", str(args.balance_games)])
    _stage(
        "canonical-deep-balance",
        balance_config,
        balance_outputs,
        [balance_cmd],
        force=args.force,
    )

    solver_output = ARTIFACTS / "solver-strength.json"
    strength_config = {
        "games_per_orientation": args.strength_games,
        "jobs": args.jobs,
        "seed": args.seed + 26090000,
        "ismcts_iterations": args.strength_ismcts_iterations,
        "alpha_nodes": args.strength_alpha_nodes,
        "time_budget_seconds": args.strength_time_budget_seconds,
    }
    _stage(
        "solver-strength",
        strength_config,
        [solver_output],
        [
            _python(
                "tools/run_experiments.py",
                "strength-bench",
                "--games",
                str(args.strength_games),
                "--jobs",
                str(args.jobs),
                "--seed",
                str(args.seed + 26090000),
                "--iterations",
                str(args.strength_ismcts_iterations),
                "--alpha-nodes",
                str(args.strength_alpha_nodes),
                "--time-budget-seconds",
                str(args.strength_time_budget_seconds),
                "--publish-lab",
            )
        ],
        force=args.force,
    )

    for index, (profile_id, _label, deck_path) in enumerate(MCCFR_PROFILES):
        policy = ARTIFACTS / f"mccfr-policy-{profile_id}.json"
        train_seed = args.seed + 10_000 + index * 100
        train_config = {
            "profile": profile_id,
            "deck": deck_path,
            "iterations": args.mccfr_iterations,
            "depth": args.mccfr_depth,
            "workers": args.mccfr_workers,
            "seed": train_seed,
        }
        _stage(
            f"mccfr-train-{profile_id}",
            train_config,
            [policy],
            [
                _python(
                    "tools/train_mccfr.py",
                    "--iterations",
                    str(args.mccfr_iterations),
                    "--depth",
                    str(args.mccfr_depth),
                    "--workers",
                    str(args.mccfr_workers),
                    "--seed",
                    str(train_seed),
                    "--deck-a",
                    deck_path,
                    "--deck-b",
                    deck_path,
                    "--output",
                    str(policy.relative_to(ROOT)),
                )
            ],
            force=args.force,
        )

        policy_fingerprint = _policy_hash(policy)
        forward = ARTIFACTS / f"mccfr-{profile_id}-vs-heuristic.json"
        reverse = ARTIFACTS / f"heuristic-vs-mccfr-{profile_id}.json"
        eval_seed = args.seed + 20_000 + index * 100
        eval_config = {
            "profile": profile_id,
            "deck": deck_path,
            "games_per_orientation": args.mccfr_eval_games,
            "jobs": args.jobs,
            "seed": eval_seed,
            "policy_fingerprint": policy_fingerprint,
        }
        _stage(
            f"mccfr-eval-{profile_id}",
            eval_config,
            [forward, reverse],
            [
                _python(
                    "tools/simulate.py",
                    "--games",
                    str(args.mccfr_eval_games),
                    "--jobs",
                    str(args.jobs),
                    "--seed",
                    str(eval_seed),
                    "--deck-a",
                    deck_path,
                    "--deck-b",
                    deck_path,
                    "--agent-a",
                    "mccfr",
                    "--policy-a",
                    str(policy.relative_to(ROOT)),
                    "--agent-b",
                    "heuristic",
                    "--output",
                    str(forward.relative_to(ROOT)),
                ),
                _python(
                    "tools/simulate.py",
                    "--games",
                    str(args.mccfr_eval_games),
                    "--jobs",
                    str(args.jobs),
                    "--seed",
                    str(eval_seed),
                    "--deck-a",
                    deck_path,
                    "--deck-b",
                    deck_path,
                    "--agent-a",
                    "heuristic",
                    "--agent-b",
                    "mccfr",
                    "--policy-b",
                    str(policy.relative_to(ROOT)),
                    "--output",
                    str(reverse.relative_to(ROOT)),
                ),
            ],
            force=args.force,
        )

    suite_output = ARTIFACTS / "mccfr-suite.json"
    suite_config = {
        "profiles": [profile_id for profile_id, _label, _deck in MCCFR_PROFILES],
        "policy_fingerprints": {
            profile_id: _policy_hash(
                ARTIFACTS / f"mccfr-policy-{profile_id}.json"
            )
            for profile_id, _label, _deck in MCCFR_PROFILES
        },
    }
    _stage(
        "mccfr-suite",
        suite_config,
        [suite_output],
        [_python("tools/build_mccfr_suite.py")],
        force=args.force,
    )

    print("[run] final-lab-and-pages", flush=True)
    _run(_python("tools/build_lab_report.py"))
    _run(_python("tools/build_pages.py"))
    _check_final_lab()


if __name__ == "__main__":
    main()
