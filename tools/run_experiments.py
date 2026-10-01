from __future__ import annotations

import argparse
import copy
import hashlib
import json
import select
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from collections import Counter
from dataclasses import asdict
from itertools import combinations
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - interactive skip is POSIX-only
    termios = None
    tty = None

from longwar.reference_decks import (
    CANONICAL_DECK_PATHS,
    DECK_CATALOG,
    DEFAULT_DECK_PATH,
)

from longwar.agents.ismcts_agent import (
    DEFAULT_ISMCTS_BELIEF_SAMPLES,
    DEFAULT_ISMCTS_EXPLORATION,
    DEFAULT_ISMCTS_ITERATIONS,
    DEFAULT_ISMCTS_MAX_TREE_NODES,
    DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    DEFAULT_ISMCTS_REUSE_TREE,
    DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    DEFAULT_ISMCTS_ROLLOUT_POLICY,
    ISMCTSAgent,
)
from longwar.balance import validate_command_costs
from longwar.belief import DeckHypothesis, HypothesisDeckPrior
from longwar.cards import load_card_file
from longwar.decks import (
    MINIMUM_DECK_SIZE,
    validate_deck_definition,
)
from longwar.game import GameEngine
from longwar.game.actions import Pass
from longwar.game.model import Phase
from longwar.fingerprint import artifact_directory, experiment_identity
from longwar.health import wilson_interval
from longwar.heuristics import DEFAULT_HEURISTIC_WEIGHTS
from longwar.parallelism import DEFAULT_WORKERS
from longwar.rules import GameRules
from longwar.protocol import PolicySource

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_experiments.py"
VALIDATION_ROOT = ROOT / "artifacts" / "search-validation"
BENCH_ROOT = ROOT / "artifacts" / "search-benchmark"
# Deliberately small, human-readable arithmetic recovery grid. The rule
# structure is fixed; only start/decrement are tuned.
COMMAND_RECOVERY_CANDIDATES = (
    (10, 2),
    (12, 2),
    (12, 3),
    (15, 3),
)


class ExperimentSkipped(RuntimeError):
    """Raised when the user skips a comparison, carrying its live score."""

    def __init__(
        self,
        message: str,
        *,
        partial: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.partial = partial or {}


def validate_data() -> None:
    """Validate canonical cards/decks against the current standard rules."""
    data = load_card_file(ROOT / "cards" / "cards.json")
    validate_command_costs(data)
    deck_paths = [
        ROOT / path
        for path in CANONICAL_DECK_PATHS.values()
    ]
    engine = GameEngine(data, rules=GameRules.standard())
    for path in deck_paths:
        deck = json.loads(path.read_text(encoding="utf-8"))["cards"]
        validate_deck_definition(deck, engine.cards)
        engine.validate_deck(deck)
        engine.legal_actions(engine.new_game(deck, deck, seed=1701))
    print(
        f"Validated canonical data: {len(data['cards'])} cards, "
        f"{len(deck_paths)} canonical reference decks "
        f"(minimum {MINIMUM_DECK_SIZE} cards), standard rules"
    )




def artifact_matches_game_fingerprint(path: Path, expected: str) -> bool:
    """Return whether a JSON artifact belongs to the current game build."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("game_fingerprint") == expected

def balance_run(args: argparse.Namespace) -> Path:
    """Canonical balance pipeline; experimental rules stay in `run`.

    quick:
        cheap structural smoke test using canonical same-deck cells only.
    deep:
        broad heuristic evidence across all canonical matchups, full-pool
        paired card screening, then targeted online-MCCFR confirmation.
    exhaustive:
        the same evidence hierarchy as deep with the old 2,000-games-per-cell
        structural sample size.
    """
    from longwar.balance import build_report
    from longwar.counterfactual import (
        run_counterfactual_card_sweep,
        validate_counterfactual_baselines,
    )
    from longwar.health import (
        aggregate_simulations_for_health,
        analyze_simulation,
    )
    from longwar.playability import build_playability_report
    from longwar.simulate import SimulationBatchCell, simulate_games_batch
    from longwar.targeted_counterfactual import run_targeted_online_validation

    # balance_run is also called directly by tests and research helpers.
    # Supply the same defaults as parse_args instead of requiring every caller
    # to construct a parser-complete Namespace.
    balance_defaults = {
        "ismcts_belief_samples": DEFAULT_ISMCTS_BELIEF_SAMPLES,
        "ismcts_iterations": DEFAULT_ISMCTS_ITERATIONS,
        "ismcts_time_budget_seconds": None,
        "ismcts_rollout_depth": DEFAULT_ISMCTS_ROLLOUT_DEPTH,
        "ismcts_tree_depth_limit": 96,
        "ismcts_exploration": DEFAULT_ISMCTS_EXPLORATION,
        "ismcts_progressive_widening": DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
        "ismcts_no_tree_reuse": False,
        "ismcts_max_tree_nodes": DEFAULT_ISMCTS_MAX_TREE_NODES,
        "ismcts_rollout_epsilon": DEFAULT_ISMCTS_ROLLOUT_EPSILON,
        "ismcts_rollout_policy": DEFAULT_ISMCTS_ROLLOUT_POLICY,
        "strategic_belief_samples": 3,
        "strategic_rollout_plies": 5,
        "strategic_candidate_width": 6,
        "strategic_node_budget": 20000,
        "strategic_time_budget_seconds": None,
        "online_agent_iterations": 16,
        "online_agent_depth": 2,
        "recovery_start": GameRules.standard().command_recovery_start,
        "recovery_decrement": GameRules.standard().command_recovery_decrement,
        "jobs": 8,
    }
    for option, default in balance_defaults.items():
        if not hasattr(args, option):
            setattr(args, option, default)

    deep_pipeline = args.preset in {"deep", "exhaustive"}
    publish_lab = deep_pipeline or bool(getattr(args, "publish_lab", False))
    agent_name = str(getattr(args, "agent", "heuristic"))
    recovery_start = int(getattr(
        args,
        "recovery_start",
        GameRules.standard().command_recovery_start,
    ))
    recovery_decrement = int(getattr(
        args,
        "recovery_decrement",
        GameRules.standard().command_recovery_decrement,
    ))
    skip_card_screen = bool(getattr(args, "skip_card_screen", False))
    run_card_screen = deep_pipeline and not skip_card_screen

    if recovery_start < 0 or recovery_decrement < 0:
        raise SystemExit("Recovery start and decrement must be non-negative")
    rules = GameRules.standard().with_overrides(
        command_recovery_start=recovery_start,
        command_recovery_decrement=recovery_decrement,
    )

    default_games_by_agent = {
        "heuristic": {"quick": 8, "deep": 250, "exhaustive": 2000},
        "random": {"quick": 8, "deep": 250, "exhaustive": 2000},
        "strategic_heuristic": {"quick": 2, "deep": 8, "exhaustive": 24},
        "ismcts": {"quick": 1, "deep": 8, "exhaustive": 24},
        "mccfr": {"quick": 2, "deep": 8, "exhaustive": 24},
        "online_mccfr": {"quick": 1, "deep": 4, "exhaustive": 12},
    }
    default_games = default_games_by_agent[agent_name][args.preset]
    games = args.games if args.games is not None else default_games

    online_iterations = int(getattr(args, "online_iterations", 16))
    online_depth = int(getattr(args, "online_depth", 2))
    target_max_cards = int(getattr(args, "target_max_cards", 8))
    target_min_effect = float(getattr(args, "target_min_effect", 0.05))
    target_contexts_arg = getattr(args, "target_contexts", None)
    target_games_arg = getattr(args, "target_games_per_context", None)
    skip_online_validation = bool(
        getattr(args, "skip_online_validation", False)
    )
    target_contexts = (
        args.contexts
        if target_contexts_arg is None
        else min(args.contexts, int(target_contexts_arg))
    )
    target_games_per_context = (
        args.games_per_context
        if target_games_arg is None
        else min(args.games_per_context, int(target_games_arg))
    )

    if (
        games <= 0
        or (run_card_screen and args.contexts <= 0)
        or (run_card_screen and args.games_per_context <= 0)
        or (run_card_screen and target_contexts <= 0)
        or (run_card_screen and target_games_per_context <= 0)
        or args.jobs <= 0
        or online_iterations <= 0
        or online_depth <= 0
        or target_max_cards < 0
        or target_min_effect < 0
    ):
        raise SystemExit("Game/context/search counts must be positive")

    validate_data()
    config = {
        "preset": args.preset,
        "games_per_cell": games,
        "seed": args.seed,
        "agents": [agent_name, agent_name],
        "agent_profile": {
            "name": agent_name,
            "heuristic_weights": DEFAULT_HEURISTIC_WEIGHTS.as_dict(),
            "ismcts": {
                "belief_samples": args.ismcts_belief_samples,
                "iterations": args.ismcts_iterations,
                "time_budget_seconds": args.ismcts_time_budget_seconds,
                "rollout_depth": args.ismcts_rollout_depth,
                "tree_depth_limit": args.ismcts_tree_depth_limit,
                "exploration": args.ismcts_exploration,
                "progressive_widening": args.ismcts_progressive_widening,
                "tree_reuse": not args.ismcts_no_tree_reuse,
                "max_tree_nodes": args.ismcts_max_tree_nodes,
                "rollout_epsilon": args.ismcts_rollout_epsilon,
                "rollout_policy": args.ismcts_rollout_policy,
            },
            "strategic_heuristic": {
                "belief_samples": args.strategic_belief_samples,
                "rollout_plies": args.strategic_rollout_plies,
                "candidate_width": args.strategic_candidate_width,
                "node_budget": args.strategic_node_budget,
                "time_budget_seconds": args.strategic_time_budget_seconds,
            },
            "online_mccfr": {
                "iterations": args.online_agent_iterations,
                "depth": args.online_agent_depth,
            },
        },
        "recovery_start": recovery_start,
        "recovery_decrement": recovery_decrement,
        "jobs": args.jobs,
        "skip_failed_games": bool(getattr(args, "skip_failed_games", False)),
        "rules": rules.as_dict(),
        "contexts": args.contexts,
        "games_per_context": args.games_per_context,
        "targeted_online_mccfr": {
            "enabled": run_card_screen and not skip_online_validation,
            "iterations": online_iterations,
            "depth": online_depth,
            "contexts": target_contexts,
            "games_per_context": target_games_per_context,
            "max_cards": target_max_cards,
            "minimum_abs_effect": target_min_effect,
        },
    }
    identity = experiment_identity(config)
    output = artifact_directory(
        ROOT / "artifacts" / "balance" / args.preset,
        identity,
    )

    def save(name: str, data: dict[str, Any]) -> None:
        (output / f"{name}.json").write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )

    data = load_card_file(ROOT / "cards" / "cards.json")
    if run_card_screen:
        validate_counterfactual_baselines(data)
        print(
            f"Validated {len(data['cards'])} counterfactual baselines",
            flush=True,
        )
    engine = GameEngine(data, rules=rules)
    decks = {
        Path(entry["file"]).stem: json.loads(
            (ROOT / "decks" / entry["file"]).read_text(encoding="utf-8")
        )["cards"]
        for entry in DECK_CATALOG
    }
    profile_ids = {
        Path(entry["file"]).stem: entry["id"]
        for entry in DECK_CATALOG
    }

    def policy_for(deck_name: str) -> dict[str, Any] | None:
        if agent_name != "mccfr":
            return None
        if rules != GameRules.standard():
            raise SystemExit(
                "Offline MCCFR policies are only valid for the current Command "
                "recovery candidate. Retrain policies before using MCCFR with "
                "an experimental start/decrement pair."
            )
        profile = profile_ids.get(deck_name)
        if profile is None:
            raise SystemExit(f"No MCCFR profile mapping for {deck_name}")
        path = ROOT / "artifacts" / f"mccfr-policy-{profile}.json"
        if not path.exists():
            raise SystemExit(
                f"Missing {path.relative_to(ROOT)}; train current policies first."
            )
        raw_policy = path.read_bytes()
        policy = json.loads(raw_policy)
        if policy.get("game_fingerprint") != identity["game_fingerprint"]:
            raise SystemExit(
                f"Stale MCCFR policy for {deck_name}; retrain for current rules."
            )
        policy["_policy_fingerprint"] = hashlib.sha256(
            raw_policy
        ).hexdigest()[:16]
        return policy

    cells = [(name, name) for name in decks]
    if deep_pipeline:
        for left, right in combinations(decks, 2):
            cells.extend([(left, right), (right, left)])

    print(
        f"[1/4] Structural {agent_name} play "
        f"(recovery {recovery_start}-{recovery_decrement}x(Battle-1), floor 1): "
        f"{len(cells)} matchup cells x "
        f"{games} games = {len(cells) * games:,} attempted games",
        flush=True,
    )
    static_payload = {**build_report(data), **identity}
    save("static", static_payload)
    simulations = []
    selfplay_simulations: dict[str, dict[str, Any]] = {}
    total_draws = 0
    total_censored = 0
    total_failed = 0

    cell_metadata: dict[
        str,
        tuple[str, str, int, tuple[dict[str, Any] | None, dict[str, Any] | None]],
    ] = {}
    batch_cells: list[SimulationBatchCell] = []
    for index, (left, right) in enumerate(cells):
        seed = args.seed + index * games
        policies = (policy_for(left), policy_for(right))
        name = f"{left}--{right}"
        cell_metadata[name] = (left, right, seed, policies)
        batch_cells.append(
            SimulationBatchCell(
                key=name,
                deck_a=decks[left],
                deck_b=decks[right],
                games=games,
                seed=seed,
                options={"agent_policies": policies},
            )
        )

    common_simulation_options = {
        "agent_names": (agent_name, agent_name),
        "online_iterations": args.online_agent_iterations,
        "online_depth": args.online_agent_depth,
        "strategic_belief_samples": args.strategic_belief_samples,
        "strategic_rollout_plies": args.strategic_rollout_plies,
        "strategic_candidate_width": args.strategic_candidate_width,
        "strategic_node_budget": args.strategic_node_budget,
        "strategic_time_budget_seconds": args.strategic_time_budget_seconds,
        "ismcts_belief_samples": args.ismcts_belief_samples,
        "ismcts_iterations": args.ismcts_iterations,
        "ismcts_time_budget_seconds": args.ismcts_time_budget_seconds,
        "ismcts_rollout_depth": args.ismcts_rollout_depth,
        "ismcts_tree_depth_limit": args.ismcts_tree_depth_limit,
        "ismcts_exploration": args.ismcts_exploration,
        "ismcts_progressive_widening": args.ismcts_progressive_widening,
        "ismcts_reuse_tree": not args.ismcts_no_tree_reuse,
        "ismcts_max_tree_nodes": args.ismcts_max_tree_nodes,
        "ismcts_rollout_epsilon": args.ismcts_rollout_epsilon,
        "ismcts_rollout_policy": args.ismcts_rollout_policy,
        "skip_failed_games": bool(getattr(args, "skip_failed_games", False)),
    }

    def structural_progress(key: str, completed: int, total: int) -> None:
        if completed == total:
            print(f"  completed {key}: {completed}/{total} games", flush=True)

    def consume_structural_payload(
        left: str,
        right: str,
        payload: dict[str, Any],
        *,
        reused: bool = False,
    ) -> None:
        nonlocal total_draws, total_censored, total_failed
        total_draws += int(payload.get("draws", 0))
        total_censored += int(payload["censored_games"])
        total_failed += int(payload["failed_games"])
        simulations.append(payload)
        if left == right:
            selfplay_simulations[left] = payload
        prefix = "reused " if reused else ""
        print(
            f"{prefix}{left}--{right}: {payload['games']} games, "
            f"{payload['decisive_games']} decisive, "
            f"{payload.get('draws', 0)} draws, "
            f"{payload['censored_games']} censored, "
            f"{payload['failed_games']} failed, first-player wins "
            f"{payload['first_player_wins']}; 95% interval "
            f"{payload['first_player_wilson_95']}"
        )

    structural_config = {
        key: config[key]
        for key in (
            "games_per_cell",
            "seed",
            "agents",
            "agent_profile",
            "recovery_start",
            "recovery_decrement",
            "skip_failed_games",
            "rules",
        )
    }

    def load_reusable_structural(
        candidate: Path,
    ) -> dict[str, dict[str, Any]]:
        config_path = candidate / "config.json"
        if not config_path.exists():
            return {}
        try:
            candidate_identity = json.loads(
                config_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}
        candidate_config = candidate_identity.get("config") or {}
        candidate_structural_config = {
            key: candidate_config.get(key)
            for key in structural_config
        }
        if (
            candidate_identity.get("game_fingerprint")
            != identity["game_fingerprint"]
            or candidate_structural_config != structural_config
        ):
            return {}

        found: dict[str, dict[str, Any]] = {}
        for left, right in cells:
            name = f"{left}--{right}"
            _meta_left, _meta_right, seed, _policies = cell_metadata[name]
            existing_path = candidate / f"{name}.json"
            if not existing_path.exists():
                return {}
            try:
                payload = json.loads(
                    existing_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                return {}
            if (
                payload.get("game_fingerprint")
                != identity["game_fingerprint"]
                or int(payload.get("games", -1)) != games
                or int(payload.get("seed", -1)) != seed
                or payload.get("deck_a") != decks[left]
                or payload.get("deck_b") != decks[right]
                or payload.get("agent_profile") != config["agent_profile"]
                or payload.get("rules") != asdict(engine.rules)
            ):
                return {}
            found[name] = payload
        return found

    reusable: dict[str, dict[str, Any]] = {}
    reusable_source: Path | None = None
    candidate_dirs = [output]
    candidate_dirs.extend(
        sorted(
            (
                candidate
                for candidate in output.parent.iterdir()
                if candidate.is_dir() and candidate != output
            ),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
    )
    for candidate in candidate_dirs:
        reusable = load_reusable_structural(candidate)
        if len(reusable) == len(cells):
            reusable_source = candidate
            break

    if len(reusable) == len(cells):
        source_label = (
            reusable_source.relative_to(ROOT)
            if reusable_source is not None
            else output.relative_to(ROOT)
        )
        print(
            f"  reusing {len(cells)} complete structural matchup cells "
            f"from {source_label}",
            flush=True,
        )
        for left, right in cells:
            consume_structural_payload(
                left,
                right,
                reusable[f"{left}--{right}"],
                reused=True,
            )
    else:
        reports = simulate_games_batch(
            engine,
            batch_cells,
            jobs=args.jobs,
            common_options=common_simulation_options,
            progress_callback=structural_progress,
        )

        for left, right in cells:
            name = f"{left}--{right}"
            _meta_left, _meta_right, seed, policies = cell_metadata[name]
            report = reports[name]
            payload = {
                **asdict(report),
                "game_fingerprint": identity["game_fingerprint"],
                "experiment_fingerprint": identity["experiment_fingerprint"],
                "seed": seed,
                "rules": asdict(engine.rules),
                "agent_profile": config["agent_profile"],
                "recovery_start": recovery_start,
                "recovery_decrement": recovery_decrement,
                "policy_fingerprints": [
                    policy.get("_policy_fingerprint") if policy else None
                    for policy in policies
                ],
                "deck_a": decks[left],
                "deck_b": decks[right],
                "decisive_games": report.decisive_games,
                "censor_rate": report.censor_rate,
                "failure_rate": report.failure_rate,
                "win_rates": report.win_rates,
                "first_player_win_rate": report.first_player_win_rate,
                "first_player_wilson_95": wilson_interval(
                    report.first_player_wins,
                    report.decisive_games,
                ),
                "simulation_variant": {
                    **engine.rules.simulation_metadata(),
                    "deck_sizes": [len(decks[left]), len(decks[right])],
                    "card_file": "cards/cards.json",
                },
            }
            save(name, payload)
            save(f"{name}-health", analyze_simulation(payload, data))
            consume_structural_payload(left, right, payload)

    playability = build_playability_report(simulations)
    save("playability", playability)

    aggregate_selfplay = aggregate_simulations_for_health(
        list(selfplay_simulations.values())
    )
    aggregate_health = analyze_simulation(aggregate_selfplay, data)
    save("aggregate-selfplay", aggregate_selfplay)
    save("aggregate-health", aggregate_health)

    causal_payload: dict[str, Any] | None = None
    targeted_payload: dict[str, Any] | None = None
    if run_card_screen:
        print(
            f"[2/4] Broad paired card screen: {len(data['cards'])} cards x "
            f"{args.contexts} contexts x {args.games_per_context} samples",
            flush=True,
        )
        def broad_progress(
            completed: int,
            total: int,
            row: dict[str, Any],
        ) -> None:
            effect = row.get("delta_win_probability")
            effect_text = "—" if effect is None else f"{float(effect):+.1%}"
            print(
                f"  [{completed:>2}/{total}] {row['title']}: "
                f"ΔWP {effect_text}, {row.get('samples', 0)} resolved pairs, "
                f"{row.get('censored_pairs', 0)} censored",
                flush=True,
            )

        causal = run_counterfactual_card_sweep(
            data,
            contexts=args.contexts,
            games_per_context=args.games_per_context,
            seed=args.seed,
            bootstrap_resamples=2000,
            jobs=args.jobs,
            progress_callback=broad_progress,
        )
        causal_payload = {
            **causal,
            "game_fingerprint": identity["game_fingerprint"],
        }
        save("counterfactual", causal_payload)
        print(
            "Broad screen complete: "
            f"{causal_payload['resolved_paired_samples']} resolved paired "
            f"samples, {causal_payload['censored_paired_samples']} censored "
            f"pairs ({causal_payload['pair_censor_rate']:.1%}).",
            flush=True,
        )

        if not skip_online_validation:
            print(
                f"[3/4] Strategic confirmation: online MCCFR, up to "
                f"{target_max_cards} suspicious cards, "
                f"{target_contexts} x {target_games_per_context} paired samples, "
                f"{online_iterations} iterations / depth {online_depth}",
                flush=True,
            )
            def targeted_progress(
                completed: int,
                total: int,
                row: dict[str, Any],
            ) -> None:
                online = row.get("online", {})
                effect = online.get("effect")
                effect_text = "—" if effect is None else f"{float(effect):+.1%}"
                print(
                    f"  [{completed:>2}/{total}] {row['title']}: "
                    f"online ΔWP {effect_text}, {row['confirmation']}, "
                    f"{online.get('samples', 0)} resolved pairs, "
                    f"{online.get('censored_pairs', 0)} censored",
                    flush=True,
                )

            targeted = run_targeted_online_validation(
                data,
                causal_payload,
                contexts=target_contexts,
                games_per_context=target_games_per_context,
                online_iterations=online_iterations,
                online_depth=online_depth,
                max_cards=target_max_cards,
                max_pairs=0,
                max_triples=0,
                minimum_abs_effect=target_min_effect,
                bootstrap_resamples=1000,
                force_top=False,
                jobs=args.jobs,
                progress_callback=targeted_progress,
            )
            targeted_payload = {
                **targeted,
                "game_fingerprint": identity["game_fingerprint"],
            }
            save("targeted-online-counterfactual", targeted_payload)
            selected = int(
                targeted_payload.get("selection", {}).get(
                    "targets_selected",
                    0,
                )
            )
            confirmations = {
                state: sum(
                    row.get("confirmation") == state
                    for row in targeted_payload.get("targets", [])
                )
                for state in (
                    "confirmed",
                    "reversed",
                    "direction_agrees",
                    "inconclusive",
                )
            }
            print(
                "Online MCCFR complete: "
                f"{selected} targets - "
                + ", ".join(
                    f"{name} {count}"
                    for name, count in confirmations.items()
                    if count
                ),
                flush=True,
            )
        else:
            print(
                "[3/4] Strategic confirmation skipped by request.",
                flush=True,
            )

    total_games = games * len(cells)
    policy_sources: Counter[str] = Counter()
    for payload in selfplay_simulations.values():
        policy_sources.update(
            payload.get("telemetry", {}).get("policy_sources", {})
        )
    fallback_decisions = sum(
        int(policy_sources.get(source.value, 0))
        for source in (
            PolicySource.FALLBACK,
            PolicySource.GUARD_FALLBACK,
        )
    )
    mccfr_decisions = int(policy_sources.get(PolicySource.MCCFR.value, 0))
    covered_policy_decisions = mccfr_decisions + fallback_decisions
    policy_coverage = {
        "sources": dict(sorted(policy_sources.items())),
        "mccfr_decisions": mccfr_decisions,
        "fallback_decisions": fallback_decisions,
        "fallback_rate": (
            fallback_decisions / covered_policy_decisions
            if covered_policy_decisions
            else None
        ),
        "mccfr_coverage_rate": (
            mccfr_decisions / covered_policy_decisions
            if covered_policy_decisions
            else None
        ),
    }

    profile_policy_fingerprints = sorted({
        fingerprint
        for payload in selfplay_simulations.values()
        for fingerprint in payload.get("policy_fingerprints", [])
        if fingerprint
    })
    summary_payload = {
        **identity,
        "cells": len(cells),
        "simulation_games": total_games,
        "completed_simulation_games": total_games - total_failed,
        "decisive_simulation_games": (
            total_games - total_draws - total_censored - total_failed
        ),
        "draw_simulation_games": total_draws,
        "censored_simulation_games": total_censored,
        "failed_simulation_games": total_failed,
        "aggregate_health_games": aggregate_selfplay["games"],
        "aggregate_health_decks": sorted(selfplay_simulations),
        "policy_coverage": policy_coverage,
        "policy_fingerprints": profile_policy_fingerprints,
        "evidence_pipeline": {
            "structural_play": {
                "policy": agent_name,
                "agent_profile": config["agent_profile"],
                "recovery_start": recovery_start,
                "recovery_decrement": recovery_decrement,
                "purpose": (
                    "Structural, pacing, exposure and matchup "
                    "screening; not a strong-play claim."
                ),
                "attempted_games": total_games,
            },
            "broad_card_screen": (
                {
                    "policy": causal_payload.get("policy"),
                    "purpose": (
                        "Paired real-card versus neutral-baseline screening "
                        "under a fixed cheap policy."
                    ),
                    "cards": len(causal_payload.get("cards", [])),
                    "resolved_paired_samples": causal_payload.get(
                        "resolved_paired_samples",
                        0,
                    ),
                    "censored_paired_samples": causal_payload.get(
                        "censored_paired_samples",
                        0,
                    ),
                }
                if causal_payload is not None
                else None
            ),
            "strategic_confirmation": (
                {
                    "policy": "online_mccfr",
                    "purpose": (
                        "Targeted re-solving of suspicious paired card signals "
                        "using the exact same contexts and interventions."
                    ),
                    "targets": len(targeted_payload.get("targets", [])),
                    "iterations": targeted_payload.get("online_iterations"),
                    "depth": targeted_payload.get("online_depth"),
                }
                if targeted_payload is not None
                else None
            ),
        },
        "interpretation": (
            f"Evidence is hierarchical. {agent_name} self-play describes "
            "structure and exposure for the selected arithmetic recovery formula. "
            "Heuristic paired replacements are a "
            "screen for candidate card effects. A suspicious card is only "
            "treated as strategically confirmed when targeted online-MCCFR "
            "validation agrees. Censored games and paired samples remain "
            "structural evidence but are excluded from outcome estimates."
        ),
    }
    save("summary", summary_payload)

    if publish_lab:
        print("[4/4] Publishing Balance Lab snapshot.", flush=True)
        artifacts = ROOT / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)

        def publish(name: str, payload: dict[str, Any]) -> None:
            (artifacts / name).write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )

        progression_profiles = {
            "game_fingerprint": identity["game_fingerprint"],
            "_label": "Six canonical reference-deck progression profiles",
            "agent": agent_name,
            "agent_profile": config["agent_profile"],
            "recovery_start": recovery_start,
            "recovery_decrement": recovery_decrement,
            "recovery_floor": rules.command_recovery_floor,
            "rules": rules.as_dict(),
            "progression_scope": (
                "Detailed progression is stratified by all canonical same-deck "
                "reference profiles; no single deck is treated as representative "
                "of the whole game."
            ),
            "profiles": {
                name: {
                    "label": name.replace("-", " ").replace("-", " ").title(),
                    "games": payload["games"],
                    "decisive_games": payload["decisive_games"],
                    "censored_games": payload["censored_games"],
                    "censor_rate": payload["censor_rate"],
                    "policy_sources": payload.get("telemetry", {}).get("policy_sources", {}),
                    "policy_fingerprints": payload.get("policy_fingerprints", []),
                    "seed": payload.get("seed"),
                    "game_outcomes": payload.get("game_outcomes", []),
                    "decisions": payload.get("telemetry", {}).get("decisions", {}),
                    "progression": payload.get("telemetry", {}).get("progression"),
                }
                for name, payload in sorted(selfplay_simulations.items())
            },
        }
        progression_source = next(iter(selfplay_simulations.values()))
        progression_source = {
            **progression_source,
            "_label": "Reference-deck progression fallback",
            "progression_scope": progression_profiles["progression_scope"],
        }
        aggregate_selfplay = {
            **aggregate_selfplay,
            "_label": f"Six canonical same-deck {agent_name} self-play aggregate",
        }

        comparison_key = (
            f"{agent_name}--recovery-{recovery_start}-{recovery_decrement}"
        )
        comparisons_path = artifacts / "balance-comparisons.json"
        comparisons: dict[str, Any] = {
            "schema_version": 1,
            "game_fingerprint": identity["game_fingerprint"],
            "profiles": {},
        }
        if comparisons_path.exists():
            existing = json.loads(
                comparisons_path.read_text(encoding="utf-8")
            )
            if (
                existing.get("game_fingerprint")
                == identity["game_fingerprint"]
            ):
                comparisons = existing
        comparisons.setdefault("profiles", {})[comparison_key] = {
            "agent": agent_name,
            "recovery_start": recovery_start,
            "recovery_decrement": recovery_decrement,
            "recovery_floor": rules.command_recovery_floor,
            "rules": rules.as_dict(),
            "agent_profile": config["agent_profile"],
            "summary": summary_payload,
            "playability": playability,
            "aggregate_selfplay": aggregate_selfplay,
            "aggregate_health": aggregate_health,
            "progression_profiles": progression_profiles,
        }
        publish("balance-comparisons.json", comparisons)

        canonical_lab_profile = (
            agent_name == "ismcts"
            and rules == GameRules.standard()
        )
        if canonical_lab_profile:
            publish("balance-report.json", static_payload)
            publish("balance-health.json", aggregate_health)
            publish("balance-selfplay.json", aggregate_selfplay)
            publish("progression-selfplay.json", progression_source)
            publish("progression-profiles.json", progression_profiles)
            publish("playability-report.json", playability)
            publish("balance-run-summary.json", summary_payload)
            if causal_payload is not None:
                publish("counterfactual-balance.json", causal_payload)
            if targeted_payload is not None:
                publish(
                    "targeted-online-counterfactual.json",
                    targeted_payload,
                )

        else:
            print(
                "Stored comparison profile "
                f"{comparison_key}; canonical balance evidence left unchanged.",
                flush=True,
            )

        # Rebuild the single Lab surface after every published comparison when
        # a canonical base snapshot is available. This lets a sequence of
        # heuristic/ISMCTS and current/candidate runs accumulate side by side
        # without replacing the canonical card-balance evidence.
        canonical_health = artifacts / "balance-health.json"
        canonical_report = artifacts / "balance-report.json"
        canonical_base_is_current = (
            artifact_matches_game_fingerprint(
                canonical_health,
                identity["game_fingerprint"],
            )
            and artifact_matches_game_fingerprint(
                canonical_report,
                identity["game_fingerprint"],
            )
        )
        if canonical_base_is_current:
            subprocess.run(
                [sys.executable, str(ROOT / "tools" / "build_lab_report.py")],
                cwd=ROOT,
                check=True,
            )
        elif not canonical_lab_profile:
            print(
                "Skipped Lab rebuild: canonical health/static evidence is "
                "missing or stale for the current game fingerprint. The "
                "comparison profile was still published.",
                flush=True,
            )

    print(f"Balance artifacts: {output}")
    return output

def run_command_matrix(args: argparse.Namespace) -> list[Path]:
    """Compare simple arithmetic Command-recovery formulas with ISMCTS."""
    outputs: list[Path] = []
    print(
        "Command matrix: ISMCTS across arithmetic (start, decrement) recovery "
        "pairs. Collapse-at-zero and recovery floor 1 remain fixed; only the "
        "two human-memory parameters vary. Heuristic self-play is intentionally "
        "excluded because it cannot plan across Battles and is not evidence "
        "about long-term Command economy behavior.",
        flush=True,
    )
    for recovery_start, recovery_decrement in COMMAND_RECOVERY_CANDIDATES:
        cell = argparse.Namespace(**vars(args))
        cell.command_matrix = False
        cell.agent = "ismcts"
        cell.recovery_start = recovery_start
        cell.recovery_decrement = recovery_decrement
        cell.skip_card_screen = True
        cell.publish_lab = True
        print(
            f"\n=== ISMCTS / recovery start {recovery_start} "
            f"/ decrement {recovery_decrement} ===",
            flush=True,
        )
        outputs.append(balance_run(cell))
    return outputs


def run_command(
    command: list[str],
    *,
    capture: bool = False,
    echo: bool | None = None,
) -> subprocess.CompletedProcess[str]:
    if echo is None:
        echo = not capture
    if echo:
        print(f"$ {' '.join(command)}", flush=True)
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
        )
    except subprocess.CalledProcessError as exc:
        if capture and exc.stdout:
            print(exc.stdout, end="" if exc.stdout.endswith("\n") else "\n")
        raise


def _read_progress_state(path: Path, maximum: int) -> dict[str, Any]:
    fallback = {
        "completed": 0,
        "total": maximum,
        "wins": [0, 0],
    }
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return fallback

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return fallback

    if not isinstance(payload, dict):
        return fallback
    completed = payload.get("completed", 0)
    wins = payload.get("wins", [0, 0])
    if not isinstance(completed, int):
        completed = 0
    if (
        not isinstance(wins, list)
        or len(wins) != 2
        or not all(isinstance(value, int) and value >= 0 for value in wins)
    ):
        wins = [0, 0]
    return {
        "completed": max(0, min(maximum, completed)),
        "total": maximum,
        "wins": wins,
    }


def _read_progress_count(path: Path, maximum: int) -> int:
    return int(_read_progress_state(path, maximum)["completed"])


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@contextmanager
def _skip_key_reader():
    """Yield a non-blocking single-key skip reader for interactive POSIX terminals."""
    if (
        termios is None
        or tty is None
        or not sys.stdin.isatty()
        or not sys.stdout.isatty()
    ):
        yield lambda: False
        return

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    tty.setcbreak(fd)

    def requested() -> bool:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return False
        return sys.stdin.read(1).lower() == "s"

    try:
        yield requested
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def _run_command_until_stop(
    command: list[str],
    stop_event: threading.Event,
) -> bool:
    """Run one simulation subprocess, terminating it promptly when skipped."""
    if stop_event.is_set():
        return False

    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        while process.poll() is None:
            if stop_event.wait(0.1):
                process.terminate()
                try:
                    process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return False

        if process.returncode:
            log.seek(0)
            output = log.read()
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            raise subprocess.CalledProcessError(process.returncode, command)
    return True


def _run_cells_with_live_progress(
    cells: list[tuple[str, str, Path, Path, list[str]]],
    *,
    jobs: int,
    games_per_cell: int,
    run_cell,
    format_result,
    table_header: str,
    score_labels: tuple[str, str],
    format_progress,
) -> list[Any]:
    """Run parallel cells with a live result table and interactive skip."""
    total_games = len(cells) * games_per_cell
    progress_paths = [cell[3] for cell in cells]
    started = time.perf_counter()
    results: list[Any] = []
    stop_event = threading.Event()
    skipped = False
    previous_lines = 0
    interactive = sys.stdout.isatty()

    def clear_display() -> None:
        nonlocal previous_lines
        if not interactive or previous_lines <= 0:
            return
        sys.stdout.write("\r\x1b[2K")
        for _ in range(previous_lines - 1):
            sys.stdout.write("\x1b[1A\r\x1b[2K")
        previous_lines = 0

    def render(pending_count: int, *, stopping: bool = False) -> None:
        nonlocal previous_lines
        states = [
            _read_progress_state(path, games_per_cell)
            for path in progress_paths
        ]
        completed = sum(int(state["completed"]) for state in states)
        fraction = completed / total_games if total_games else 1.0
        width = 20
        filled = min(width, int(width * fraction))
        bar = "#" * filled + "-" * (width - filled)
        elapsed = time.perf_counter() - started
        eta = (
            elapsed * (total_games - completed) / completed
            if completed and not stopping
            else None
        )
        eta_text = _format_duration(eta) if eta is not None else "--:--"

        rows: list[str] = []
        score_a = 0
        score_b = 0
        for cell, state in zip(cells, states):
            row, a_wins, b_wins = format_progress(cell, state)
            rows.append(row)
            score_a += a_wins
            score_b += b_wins

        status = (
            "Stopping current experiment..."
            if stopping
            else "Press s to skip this experiment"
        )
        lines = [
            f"Live results - {status}",
            table_header,
            *rows,
            (
                f"TOTAL {score_labels[0]} {score_a} - "
                f"{score_labels[1]} {score_b}"
            ),
            (
                f"[{bar}] {completed}/{total_games} {fraction:5.1%} "
                f"| {_format_duration(elapsed)} | ETA {eta_text} "
                f"| {pending_count} active"
            ),
        ]

        if interactive:
            clear_display()
            sys.stdout.write("\n".join(lines))
            sys.stdout.flush()
            previous_lines = len(lines)
        elif completed == total_games or stopping:
            print("\n".join(lines), flush=True)

    with _skip_key_reader() as skip_requested:
        with ThreadPoolExecutor(max_workers=min(jobs, len(cells))) as pool:
            future_to_cell = {
                pool.submit(run_cell, cell, stop_event): cell
                for cell in cells
            }
            pending = set(future_to_cell)
            render(len(pending))
            while pending:
                if not skipped and skip_requested():
                    skipped = True
                    stop_event.set()
                    render(len(pending), stopping=True)

                done, pending = wait(
                    pending,
                    timeout=0.5,
                    return_when=FIRST_COMPLETED,
                )
                for future in done:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                        if not interactive:
                            print(format_result(result), flush=True)

                if not skipped:
                    render(len(pending))
                elif pending:
                    render(len(pending), stopping=True)

    if interactive:
        if not skipped:
            render(0)
        clear_display()
        if not skipped:
            # Preserve the final completed table in scrollback.
            states = [
                _read_progress_state(path, games_per_cell)
                for path in progress_paths
            ]
            print("Final cell results")
            print(table_header)
            for cell, state in zip(cells, states):
                row, _a_wins, _b_wins = format_progress(cell, state)
                print(row)
        else:
            print("Current experiment skipped.")

    if skipped:
        states = [
            _read_progress_state(path, games_per_cell)
            for path in progress_paths
        ]
        score_a = 0
        score_b = 0
        completed = 0
        for cell, state in zip(cells, states):
            _row, a_wins, b_wins = format_progress(cell, state)
            score_a += int(a_wins)
            score_b += int(b_wins)
            completed += int(state["completed"])
        raise ExperimentSkipped(
            "user requested skip",
            partial={
                "score_a": score_a,
                "score_b": score_b,
                "completed": completed,
                "total": total_games,
            },
        )
    return results


def require_cython() -> None:
    try:
        from longwar.native_search import ismcts_backend
        ismcts_backend()
    except (ImportError, RuntimeError) as exc:
        raise SystemExit(
            "Canonical Cython search is unavailable or stale.\n"
            "Run: make native-build"
        ) from exc
    print("Canonical Cython engine/search extension: OK")


def normalized_payload(path: Path) -> dict[str, Any]:
    """Strip backend-internal diagnostics before semantic parity checks.

    Python and packed Cython deliberately have different node accounting and
    may assign different numeric score gaps while still choosing the same
    actions. Those are performance/search diagnostics, not game outcomes.
    Search depth remains part of parity.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)

    strategic = payload.get("strategic_config", {})
    strategic.pop("backend_requested", None)

    telemetry = payload.get("telemetry", {})
    telemetry.pop("search_backends", None)

    for stats in telemetry.get("decisions", {}).values():
        stats.pop("mean_search_nodes", None)
        stats.pop("mean_score_gap", None)
        stats.pop("mean_decision_seconds", None)
        stats.pop("max_decision_seconds", None)
        stats.pop("mean_searched_decision_seconds", None)

    return payload


def first_payload_difference(
    left: object,
    right: object,
    path: str = "$",
) -> tuple[str, object, object] | None:
    if type(left) is not type(right):
        return path, left, right
    if isinstance(left, dict):
        left_keys = set(left)
        right_keys = set(right)
        if left_keys != right_keys:
            return (
                path + ".<keys>",
                sorted(left_keys),
                sorted(right_keys),
            )
        for key in sorted(left):
            difference = first_payload_difference(
                left[key],
                right[key],
                f"{path}.{key}",
            )
            if difference is not None:
                return difference
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return path + ".<length>", len(left), len(right)
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            difference = first_payload_difference(
                left_item,
                right_item,
                f"{path}[{index}]",
            )
            if difference is not None:
                return difference
        return None
    if left != right:
        return path, left, right
    return None


def standard_backend_parity(*, seed: int) -> None:
    """Compare Python/Cython strategic search under current standard rules."""
    print("\nBackend parity: standard rules")
    common = [
        "--games",
        "2",
        "--seed",
        str(seed),
        "--card-file",
        "cards/cards.json",
        "--deck-a",
        DEFAULT_DECK_PATH,
        "--deck-b",
        DEFAULT_DECK_PATH,
        "--agent-a",
        "strategic_heuristic",
        "--agent-b",
        "strategic_heuristic",
        "--strategic-belief-samples",
        "2",
        "--strategic-search-depth",
        "3",
        "--strategic-candidate-width",
        "4",
        "--strategic-node-budget",
        "3000",
    ]
    output = artifact_directory(
        VALIDATION_ROOT,
        experiment_identity({
            "command": "standard-backend-parity",
            "arguments": common,
        }),
    )
    python_output = output / "standard-python.json"
    cython_output = output / "standard-cython.json"

    for backend, destination in (
        ("python", python_output),
        ("cython", cython_output),
    ):
        run_command(
            [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                *common,
                "--strategic-search-backend",
                backend,
                "--output",
                str(destination),
            ],
            capture=True,
        )

    python_payload = normalized_payload(python_output)
    cython_payload = normalized_payload(cython_output)
    if python_payload != cython_payload:
        left = output / "standard-normalized-python.json"
        right = output / "standard-normalized-cython.json"
        left.write_text(
            json.dumps(python_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        right.write_text(
            json.dumps(cython_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        difference = first_payload_difference(
            python_payload,
            cython_payload,
        )
        detail = ""
        if difference is not None:
            diff_path, python_value, cython_value = difference
            detail = (
                f"\nFirst difference: {diff_path}\n"
                f"  python={python_value!r}\n"
                f"  cython={cython_value!r}"
            )
        raise SystemExit(
            "Backend parity FAILED for standard rules."
            + detail
            + "\nNormalized outputs written to:"
            + f"\n  {left}\n  {right}"
        )

    print("Backend parity standard: OK")


def validate() -> None:
    print("The Long War — native search validation")
    print("=" * 45)
    require_cython()

    print("\nFocused current-rules and strategic-search tests")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-n",
            str(DEFAULT_WORKERS),
            "-q",
            "tests/test_engine.py",
            "tests/test_strategic_heuristic.py",
            "tests/test_fast_search_state.py",
            "tests/test_architecture_boundaries.py",
            "tests/test_ismcts.py",
            "tests/test_ismcts_validation.py",
        ],
        capture=True,
    )
    print("Focused current-rules/search tests: OK")

    standard_backend_parity(seed=26092334)

    print("\nVALIDATION PASSED")
    print(
        "Current rules, ISMCTS invariants, architecture boundaries, and "
        "fixed-seed standard-rules Python/Cython parity passed."
    )


def _print_ismcts_cutoffs(cutoffs: dict[str, float | int | None]) -> None:
    iterations = int(cutoffs["iterations"] or 0)
    if not iterations:
        print("ISMCTS rollout cutoffs: no searched iterations")
        return
    print(
        "ISMCTS rollout cutoffs: "
        f"terminal={100.0 * float(cutoffs['terminal_rate']):.1f}% "
        f"Battle-boundary={100.0 * float(cutoffs['battle_boundary_rate']):.1f}% "
        f"depth={100.0 * float(cutoffs['depth_rate']):.1f}% "
        f"| rollout actions/iteration="
        f"{float(cutoffs['mean_rollout_actions_per_iteration']):.2f} "
        f"| iterations={iterations:,}"
    )


def paired_strength_interval(
    outcomes: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Bootstrap decisive deals, keeping the two seat orientations together."""
    from longwar.counterfactual import estimate

    contrasts = []
    censored_pairs = 0
    for orientations in outcomes.values():
        first = {row["seed"]: row for row in orientations["mcts-first"]}
        second = {row["seed"]: row for row in orientations["alpha-first"]}
        if first.keys() != second.keys():
            raise ValueError("Mirrored strength cells must contain identical deal seeds")
        for seed, left in first.items():
            right = second[seed]
            if left.get("winner") is None or right.get("winner") is None:
                censored_pairs += 1
                continue
            contrasts.append(
                int(left["winner"] == 0) + int(right["winner"] == 1) - 1
            )

    if not contrasts:
        return {
            "win_rate": None,
            "ci95": [None, None],
            "independent_deals": 0,
            "censored_pairs": censored_pairs,
            "ci_method": None,
            "resampling_unit": "same-seed mirrored seat pair",
        }

    effect = estimate(contrasts, seed=1701, bootstrap_resamples=2000)
    return {
        "win_rate": (effect.mean + 1) / 2,
        "ci95": [
            max(0.0, (effect.ci95[0] + 1) / 2),
            min(1.0, (effect.ci95[1] + 1) / 2),
        ],
        "independent_deals": len(contrasts),
        "censored_pairs": censored_pairs,
        "ci_method": effect.ci_method,
        "resampling_unit": "same-seed mirrored seat pair",
    }


def benchmark_strength(
    *,
    games_per_orientation: int,
    jobs: int,
    ismcts_iterations: int = DEFAULT_ISMCTS_ITERATIONS,
    alpha_nodes: int = 20_000,
    time_budget_seconds: float = 5.0,
    seed: int = 26092400,
    publish_lab: bool = False,
) -> Path:
    """Mirrored ISMCTS-vs-alpha-beta matches on all canonical reference decks."""
    belief_samples = DEFAULT_ISMCTS_BELIEF_SAMPLES
    rollout_policy = DEFAULT_ISMCTS_ROLLOUT_POLICY
    rollout_depth = DEFAULT_ISMCTS_ROLLOUT_DEPTH
    progressive_widening = DEFAULT_ISMCTS_PROGRESSIVE_WIDENING
    exploration = DEFAULT_ISMCTS_EXPLORATION
    reuse_tree = DEFAULT_ISMCTS_REUSE_TREE
    rollout_epsilon = DEFAULT_ISMCTS_ROLLOUT_EPSILON
    max_tree_nodes = DEFAULT_ISMCTS_MAX_TREE_NODES

    require_cython()
    if games_per_orientation <= 0:
        raise SystemExit("--games must be positive")
    if jobs <= 0:
        raise SystemExit("--jobs must be positive")
    if ismcts_iterations <= 0 or alpha_nodes <= 0:
        raise SystemExit("Search budgets must be positive")
    if belief_samples <= 0:
        raise SystemExit("ISMCTS belief samples must be positive")
    if not 0.0 <= rollout_epsilon <= 1.0:
        raise SystemExit("ISMCTS rollout epsilon must be between 0 and 1")
    if max_tree_nodes is not None and max_tree_nodes <= 0:
        raise SystemExit("ISMCTS max tree nodes must be positive")
    if rollout_depth < 0:
        raise SystemExit("--rollout-depth must be non-negative")
    if time_budget_seconds <= 0.0:
        raise SystemExit("--time-budget-seconds must be positive")

    decks = tuple(CANONICAL_DECK_PATHS)
    c_label = f"{exploration:g}".replace(".", "p")
    tree_label = "reuse" if reuse_tree else "cold"
    parts = ["strength", tree_label, f"c-{c_label}"]
    if progressive_widening > 0.0:
        pw_label = f"{progressive_widening:g}".replace(".", "p")
        parts.append(f"pw-{pw_label}")
    else:
        parts.append("pw-0")
    identity = experiment_identity({
        "games_per_orientation": games_per_orientation, "seed": seed,
        "ismcts_iterations": ismcts_iterations, "alpha_nodes": alpha_nodes,
        "belief_samples": belief_samples,
        "rollout_policy": rollout_policy, "rollout_depth": rollout_depth,
        "rollout_epsilon": rollout_epsilon,
        "max_tree_nodes": max_tree_nodes,
        "exploration": exploration,
        "progressive_widening": progressive_widening, "reuse_tree": reuse_tree,
        "time_budget_seconds": time_budget_seconds,
        "rules": GameRules.standard().as_dict(), "decks": list(decks),
    })
    output_dir = artifact_directory(BENCH_ROOT / "-".join(parts), identity)

    cells: list[tuple[str, str, Path, Path, list[str]]] = []
    for deck_index, deck in enumerate(decks):
        cell_seed = seed + deck_index * games_per_orientation
        deck_path = CANONICAL_DECK_PATHS[deck]
        for orientation, agents, seed_offsets in (
            ("mcts-first", ("ismcts", "strategic_heuristic"), (1, 2)),
            ("alpha-first", ("strategic_heuristic", "ismcts"), (2, 1)),
        ):
            output = output_dir / f"{deck}--{orientation}.json"
            progress = output.with_suffix(".progress")
            progress.unlink(missing_ok=True)
            command = [
                sys.executable,
                str(ROOT / "tools" / "simulate.py"),
                "--games",
                str(games_per_orientation),
                "--jobs",
                "1",
                "--seed",
                str(cell_seed),
                "--card-file",
                "cards/cards.json",
                "--deck-a",
                deck_path,
                "--deck-b",
                deck_path,
                "--agent-a",
                agents[0],
                "--agent-b",
                agents[1],
                "--agent-a-seed-offset",
                str(seed_offsets[0]),
                "--agent-b-seed-offset",
                str(seed_offsets[1]),
                "--ismcts-belief-samples",
                str(belief_samples),
                "--ismcts-iterations",
                str(ismcts_iterations),
                "--ismcts-rollout-depth",
                str(rollout_depth),
                "--ismcts-exploration",
                str(exploration),
                "--ismcts-progressive-widening",
                str(progressive_widening),
                "--ismcts-rollout-policy",
                rollout_policy,
                "--ismcts-rollout-epsilon",
                str(rollout_epsilon),
                "--strategic-belief-samples",
                "4",
                "--strategic-search-depth",
                "32" if time_budget_seconds is not None else "6",
                "--strategic-candidate-width",
                "5",
                "--strategic-node-budget",
                str(alpha_nodes),
                "--strategic-search-backend",
                "cython",
                "--output",
                str(output),
            ]
            if max_tree_nodes is not None:
                command.extend([
                    "--ismcts-max-tree-nodes",
                    str(max_tree_nodes),
                ])
            if time_budget_seconds is not None:
                command.extend([
                    "--ismcts-time-budget-seconds",
                    str(time_budget_seconds),
                    "--strategic-time-budget-seconds",
                    str(time_budget_seconds),
                ])
            command.extend(["--progress-file", str(progress)])
            if not reuse_tree:
                command.append("--ismcts-no-tree-reuse")
            cells.append((deck, orientation, output, progress, command))

    budget_label = (
        f"{time_budget_seconds:g}s/searched move"
        if time_budget_seconds is not None
        else f"{ismcts_iterations:,} iters vs {alpha_nodes:,} nodes"
    )
    print(
        f"ISMCTS vs alpha-beta | {len(cells) * games_per_orientation} games | "
        f"{budget_label}"
    )
    print(
        f"ISMCTS c={exploration:g} pw={progressive_widening:g} "
        f"{'reuse' if reuse_tree else 'cold'} "
        f"rollout={rollout_policy}/{rollout_depth}"
    )
    def run_cell(cell, stop_event):
        deck, orientation, output, progress, command = cell
        started = time.perf_counter()
        if not _run_command_until_stop(command, stop_event):
            return None
        elapsed = time.perf_counter() - started
        payload = json.loads(output.read_text(encoding="utf-8"))
        labels = payload["agents"]
        mcts_wins = int(payload["wins"][labels.index("ismcts")])
        alpha_wins = int(payload["wins"][labels.index("strategic_heuristic")])
        return deck, orientation, output, elapsed, mcts_wins, alpha_wins

    def format_result(result) -> str:
        deck, orientation, _output, elapsed, mcts_wins, alpha_wins = result
        return (
            f"{deck:10} {orientation:12} "
            f"{mcts_wins:>2}-{alpha_wins:<2}    {elapsed:7.1f}s"
        )

    def format_progress(cell, state):
        deck, orientation, _output, _progress, _command = cell
        seat_mcts, seat_alpha = (
            (0, 1) if orientation == "mcts-first" else (1, 0)
        )
        mcts_wins = int(state["wins"][seat_mcts])
        alpha_wins = int(state["wins"][seat_alpha])
        completed = int(state["completed"])
        rate = 100.0 * mcts_wins / completed if completed else 0.0
        return (
            f"{deck:10} {orientation:12} "
            f"{completed:>2}/{games_per_orientation:<2} "
            f"{mcts_wins:>3}-{alpha_wins:<3} {rate:5.1f}% MCTS",
            mcts_wins,
            alpha_wins,
        )

    completed_results = _run_cells_with_live_progress(
        cells,
        jobs=jobs,
        games_per_cell=games_per_orientation,
        run_cell=run_cell,
        format_result=format_result,
        table_header="deck       orientation  played   MCTS-AB  MCTS%",
        score_labels=("MCTS", "AB"),
        format_progress=format_progress,
    )
    results = [
        (deck, orientation, output, elapsed)
        for deck, orientation, output, elapsed, _mcts_wins, _alpha_wins
        in completed_results
    ]

    totals = {
        deck: {"mcts": 0, "alpha": 0, "games": 0, "censored": 0}
        for deck in decks
    }
    overall_mcts = 0
    overall_alpha = 0
    paired_outcomes: dict[str, dict[str, list[dict[str, Any]]]] = {}
    wall_sum = 0.0
    resource_totals = {
        "ismcts": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
        "strategic_heuristic": {
            "searched_decisions": 0,
            "decision_seconds": 0.0,
            "search_work": 0.0,
            "timeouts": 0,
        },
    }
    cutoff_totals = {
        "iterations": 0,
        "terminal": 0,
        "battle_boundary": 0,
        "depth": 0,
        "rollout_actions": 0,
    }
    reuse_totals = {
        "searched_decisions": 0,
        "root_reused_decisions": 0,
        "tree_nodes_before_total": 0,
        "tree_nodes_added_total": 0,
        "root_prior_visits_total": 0,
        "tree_nodes_discarded_total": 0,
        "tree_capacity_cutoffs": 0,
    }
    reset_totals: dict[str, int] = {}

    for deck, orientation, output, elapsed in results:
        payload = json.loads(output.read_text(encoding="utf-8"))
        wins = payload["wins"]
        agents = payload["agents"]
        mcts_index = agents.index("ismcts")
        alpha_index = agents.index("strategic_heuristic")
        mcts_wins = int(wins[mcts_index])
        alpha_wins = int(wins[alpha_index])
        totals[deck]["mcts"] += mcts_wins
        totals[deck]["alpha"] += alpha_wins
        censored = int(payload.get("censored_games", 0))
        totals[deck]["censored"] += censored
        totals[deck]["games"] += int(payload["games"]) - censored
        overall_mcts += mcts_wins
        overall_alpha += alpha_wins
        paired_outcomes.setdefault(deck, {})[orientation] = payload["game_outcomes"]
        wall_sum += elapsed
        all_decision_stats = payload.get("telemetry", {}).get("decisions", {})
        for label in ("ismcts", "strategic_heuristic"):
            stats = all_decision_stats.get(label, {})
            all_count = int(stats.get("decisions", 0) or 0)
            searched = int(stats.get("searched_decisions", 0) or 0)
            resource_totals[label]["searched_decisions"] += searched
            resource_totals[label]["decision_seconds"] += searched * float(
                stats.get("mean_searched_decision_seconds", 0.0) or 0.0
            )
            resource_totals[label]["search_work"] += all_count * float(
                stats.get("mean_search_nodes", 0.0) or 0.0
            )
            resource_totals[label]["timeouts"] += int(
                stats.get("timed_out_decisions", 0) or 0
            )
        decision_stats = all_decision_stats.get("ismcts", {})
        cutoffs = decision_stats.get("ismcts_rollout_cutoffs", {})
        for key in cutoff_totals:
            cutoff_totals[key] += int(cutoffs.get(key, 0) or 0)
        reuse = decision_stats.get("ismcts_tree_reuse", {})
        for key in reuse_totals:
            reuse_totals[key] += int(reuse.get(key, 0) or 0)
        for reason, count in reuse.get("tree_resets", {}).items():
            reset_totals[reason] = reset_totals.get(reason, 0) + int(count)

    total_games = overall_mcts + overall_alpha
    paired = paired_strength_interval(paired_outcomes)
    low, high = paired["ci95"]
    rate = overall_mcts / total_games if total_games else 0.0

    print()
    print("Head-to-head result")
    print("===================")
    for deck in decks:
        row = totals[deck]
        deck_rate = row["mcts"] / row["games"] if row["games"] else 0.0
        dlow, dhigh = paired_strength_interval({deck: paired_outcomes[deck]})["ci95"]
        print(
            f"{deck:9}: ISMCTS {row['mcts']:>3}-{row['alpha']:<3} alpha-beta "
            f"| {deck_rate * 100:5.1f}% "
            f"(95% CI {dlow * 100:4.1f}–{dhigh * 100:4.1f}%)"
        )

    print(
        f"OVERALL  : ISMCTS {overall_mcts}-{overall_alpha} alpha-beta "
        f"| {rate * 100:.1f}% "
        f"(95% CI {low * 100:.1f}–{high * 100:.1f}%)"
    )
    print(
        "Interpretation: above 50% favors ISMCTS; the confidence interval "
        "resamples mirrored deal pairs to keep their dependence intact."
    )

    cutoff_iterations = cutoff_totals["iterations"]
    cutoff_summary = {
        **cutoff_totals,
        "terminal_rate": (
            cutoff_totals["terminal"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "battle_boundary_rate": (
            cutoff_totals["battle_boundary"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "depth_rate": (
            cutoff_totals["depth"] / cutoff_iterations
            if cutoff_iterations else None
        ),
        "mean_rollout_actions_per_iteration": (
            cutoff_totals["rollout_actions"] / cutoff_iterations
            if cutoff_iterations else None
        ),
    }
    _print_ismcts_cutoffs(cutoff_summary)

    searched_decisions = reuse_totals["searched_decisions"]
    reuse_summary = {
        **reuse_totals,
        "tree_resets": reset_totals,
        "root_reuse_rate": (
            reuse_totals["root_reused_decisions"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_tree_nodes_before": (
            reuse_totals["tree_nodes_before_total"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_tree_nodes_added": (
            reuse_totals["tree_nodes_added_total"] / searched_decisions
            if searched_decisions else None
        ),
        "mean_root_prior_visits": (
            reuse_totals["root_prior_visits_total"] / searched_decisions
            if searched_decisions else None
        ),
    }
    if searched_decisions:
        print(
            "ISMCTS tree reuse: "
            f"root reused={100.0 * float(reuse_summary['root_reuse_rate']):.1f}% "
            f"| prior root visits/decision="
            f"{float(reuse_summary['mean_root_prior_visits']):.1f} "
            f"| new infosets/decision="
            f"{float(reuse_summary['mean_tree_nodes_added']):.1f} "
            f"| tree infosets before/decision="
            f"{float(reuse_summary['mean_tree_nodes_before']):.1f}"
        )

    resource_summary = {}
    for label, stats in resource_totals.items():
        count = int(stats["searched_decisions"])
        resource_summary[label] = {
            "searched_decisions": count,
            "mean_searched_decision_seconds": (
                stats["decision_seconds"] / count if count else None
            ),
            "mean_search_work": stats["search_work"] / count if count else None,
            "timeout_rate": stats["timeouts"] / count if count else None,
        }
        if count:
            unit = "iterations" if label == "ismcts" else "nodes"
            print(
                f"{label}: "
                f"{resource_summary[label]['mean_searched_decision_seconds']:.3f}s/searched decision, "
                f"{resource_summary[label]['mean_search_work']:,.0f} {unit}, "
                f"timeouts={100.0 * resource_summary[label]['timeout_rate']:.1f}%"
            )

    summary = {
        **identity,
        "rules": GameRules.standard().as_dict(),
        "games_per_orientation": games_per_orientation,
        "ismcts": {
            "belief_samples": belief_samples,
            "iterations": ismcts_iterations,
            "rollout_depth": rollout_depth,
            "rollout_policy": rollout_policy,
            "exploration": exploration,
            "time_budget_seconds": time_budget_seconds,
            "tree_reuse_enabled": reuse_tree,
            "max_tree_nodes": max_tree_nodes,
            "rollout_epsilon": rollout_epsilon,
            "tree_reuse": reuse_summary,
            "progressive_widening": progressive_widening,
            "progressive_widening_alpha": (
                0.5 if progressive_widening > 0 else 0.0
            ),
            "rollout_cutoffs": cutoff_summary,
        },
        "alpha_beta": {
            "belief_samples": 4,
            "max_depth": 32 if time_budget_seconds is not None else 6,
            "beam": 5,
            "node_budget": alpha_nodes,
            "time_budget_seconds": time_budget_seconds,
        },
        "decks": totals,
        "overall": {
            "mcts_wins": overall_mcts,
            "alpha_beta_wins": overall_alpha,
            "games": total_games,
            "mcts_win_rate": rate,
            "paired_uncertainty": paired,
        },
        "resources": resource_summary,
        "sum_cell_wall_seconds": wall_sum,
        "methodology": (
            "Mirrored same-deck seats across every canonical reference deck. "
            "ISMCTS and alpha-beta receive the same wall-clock budget per searched "
            "decision; paired uncertainty resamples mirrored deal pairs."
        ),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Summary: {summary_path}")
    if publish_lab:
        lab_path = ROOT / "artifacts" / "solver-strength.json"
        lab_path.write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Published: {lab_path.relative_to(ROOT)}")
    return summary_path




NARRATIVE_COMMAND_ABLATIONS = (
    ("baseline", ()),
    ("no-baggage-command", ("baggage",)),
    ("no-rallied-discount", ("rallied",)),
    ("no-no-road-command", ("no-road",)),
    ("no-three-command-engines", ("baggage", "rallied", "no-road")),
)


def _narrative_ablation_card_data(
    base_data: dict[str, Any],
    disabled: tuple[str, ...],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Return an in-memory Narrative experiment without mutating canonical data."""
    data = copy.deepcopy(base_data)
    cards = {card["id"]: card for card in data["cards"]}
    overrides: list[dict[str, str]] = []

    if "baggage" in disabled:
        card = cards["the-baggage-was-abandoned"]
        # Remove the optional discard-for-Command transaction entirely. Leaving
        # discard_cards=1 with gain_command=0 would add a strategically pointless
        # discard choice and confound the intended Command-only ablation.
        card["design_rules"]["discard_cards"] = 0
        card["design_rules"]["gain_command"] = 0
        overrides.append({
            "card": card["id"],
            "effect": "disable discard-for-Command gain",
        })

    if "rallied" in disabled:
        card = cards["rallied-behind"]
        for key in ("command", "condition", "cost"):
            card["design_rules"].pop(key, None)
        overrides.append({
            "card": card["id"],
            "effect": "disable catch-up zero-cost discount",
        })

    if "no-road" in disabled:
        card = cards["no-road-was-too-long"]
        card["design_rules"]["gain_command"] = 0
        overrides.append({
            "card": card["id"],
            "effect": "disable recurring Maneuver-into-empty Command gain",
        })

    return data, overrides


def _narrative_ablation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    progression = payload.get("telemetry", {}).get("progression", {})
    resources = progression.get("resources", {})
    match_length = progression.get("match_length", {})
    stalls = progression.get("low_command_stalls", {})
    outcomes = payload.get("game_outcomes", [])
    censor_reasons = Counter(
        row.get("censor_reason")
        for row in outcomes
        if row.get("censored")
    )
    return {
        "games": payload.get("games"),
        "decisive_games": payload.get("decisive_games"),
        "censored_games": payload.get("censored_games"),
        "censor_rate": payload.get("censor_rate"),
        "mean_actions": payload.get("mean_turns"),
        "max_actions": payload.get("max_turns"),
        "resolved_battles_per_match": match_length.get(
            "resolved_battles_per_match"
        ),
        "final_battle_number": match_length.get("final_battle_number"),
        "battle_reach": match_length.get("battle_reach"),
        "battle_8_plus_count": match_length.get("battle_8_plus_count"),
        "battle_12_plus_count": match_length.get("battle_12_plus_count"),
        "command_before_collapse": resources.get("command_before_collapse"),
        "command_before_collapse_buckets": resources.get(
            "command_before_collapse_buckets"
        ),
        "command_at_first_signal": resources.get("command_at_first_signal"),
        "first_signal_command_buckets": resources.get(
            "first_signal_command_buckets"
        ),
        "command_by_source": resources.get("command_by_source", {}),
        "low_positive_streak_length": stalls.get(
            "low_positive_streak_length"
        ),
        "longest_low_positive_streak": stalls.get(
            "longest_low_positive_streak"
        ),
        "censor_reasons": dict(sorted(censor_reasons.items())),
    }


def narrative_ablation_run(args: argparse.Namespace) -> Path:
    """Run the five Narrative/Command mirror diagnostics with identical seeds."""
    from longwar.simulate import simulate_games

    if args.games <= 0 or args.jobs <= 0:
        raise SystemExit("--games and --jobs must be positive")

    base_data = load_card_file(ROOT / "cards" / "cards.json")
    deck_path = ROOT / CANONICAL_DECK_PATHS["narrative"]
    deck = list(json.loads(deck_path.read_text(encoding="utf-8"))["cards"])
    root = ROOT / "artifacts" / "narrative-ablation"
    root.mkdir(parents=True, exist_ok=True)

    profiles: dict[str, Any] = {}
    aggregate_identity = experiment_identity({
        "experiment": "narrative-command-ablation-suite",
        "games": args.games,
        "seed": args.seed,
    })
    for index, (variant, disabled) in enumerate(NARRATIVE_COMMAND_ABLATIONS, 1):
        card_data, overrides = _narrative_ablation_card_data(
            base_data, disabled
        )
        config = {
            "experiment": "narrative-command-ablation",
            "variant": variant,
            "disabled": list(disabled),
            "card_overrides": overrides,
            "games": args.games,
            "seed": args.seed,
            "jobs": args.jobs,
            "agent": "ismcts",
            "rules": GameRules.standard().as_dict(),
            "ismcts": {
                "belief_samples": DEFAULT_ISMCTS_BELIEF_SAMPLES,
                "iterations": DEFAULT_ISMCTS_ITERATIONS,
                "rollout_depth": DEFAULT_ISMCTS_ROLLOUT_DEPTH,
                "exploration": DEFAULT_ISMCTS_EXPLORATION,
                "progressive_widening": DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
                "tree_reuse": DEFAULT_ISMCTS_REUSE_TREE,
                "max_tree_nodes": DEFAULT_ISMCTS_MAX_TREE_NODES,
                "rollout_epsilon": DEFAULT_ISMCTS_ROLLOUT_EPSILON,
                "rollout_policy": DEFAULT_ISMCTS_ROLLOUT_POLICY,
            },
        }
        identity = experiment_identity(config)
        output = root / f"{variant}.json"
        reuse = (
            not args.force
            and output.exists()
            and artifact_matches_game_fingerprint(
                output, identity["game_fingerprint"]
            )
        )
        if reuse:
            existing = json.loads(output.read_text(encoding="utf-8"))
            reuse = (
                existing.get("experiment_fingerprint")
                == identity["experiment_fingerprint"]
                and existing.get("config") == config
            )

        if reuse:
            print(
                f"[Narrative {index}/{len(NARRATIVE_COMMAND_ABLATIONS)}] "
                f"{variant}: reusing current artifact",
                flush=True,
            )
            payload = existing
        else:
            print(
                f"[Narrative {index}/{len(NARRATIVE_COMMAND_ABLATIONS)}] "
                f"{variant}: {args.games} ISMCTS mirror games",
                flush=True,
            )
            engine = GameEngine(card_data, rules=GameRules.standard())
            report = simulate_games(
                engine,
                deck,
                deck,
                games=args.games,
                seed=args.seed,
                jobs=args.jobs,
                agent_names=("ismcts", "ismcts"),
                ismcts_belief_samples=DEFAULT_ISMCTS_BELIEF_SAMPLES,
                ismcts_iterations=DEFAULT_ISMCTS_ITERATIONS,
                ismcts_rollout_depth=DEFAULT_ISMCTS_ROLLOUT_DEPTH,
                ismcts_exploration=DEFAULT_ISMCTS_EXPLORATION,
                ismcts_progressive_widening=DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
                ismcts_reuse_tree=DEFAULT_ISMCTS_REUSE_TREE,
                ismcts_max_tree_nodes=DEFAULT_ISMCTS_MAX_TREE_NODES,
                ismcts_rollout_epsilon=DEFAULT_ISMCTS_ROLLOUT_EPSILON,
                ismcts_rollout_policy=DEFAULT_ISMCTS_ROLLOUT_POLICY,
            )
            payload = {
                **asdict(report),
                **identity,
                "variant": variant,
                "card_overrides": overrides,
                "rules": GameRules.standard().as_dict(),
                "decisive_games": report.decisive_games,
                "censor_rate": report.censor_rate,
            }
            payload["summary"] = _narrative_ablation_summary(payload)
            output.write_text(
                json.dumps(payload, indent=2) + "\n",
                encoding="utf-8",
            )
        profiles[variant] = {
            "variant": variant,
            "card_overrides": overrides,
            "summary": payload.get("summary")
            or _narrative_ablation_summary(payload),
        }

    aggregate = {
        "schema_version": 1,
        **aggregate_identity,
        "deck": "narrative",
        "agent": "ismcts",
        "games_per_variant": args.games,
        "seed": args.seed,
        "methodology": (
            "Five Narrative/Command mirror ISMCTS conditions use identical "
            "seeds. Card effects are disabled only in copied in-memory card "
            "data; canonical cards/cards.json is never modified."
        ),
        "profiles": profiles,
    }
    output = ROOT / "artifacts" / "narrative-command-ablation.json"
    output.write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}", flush=True)
    return output



PASS_RULE_VARIANTS: dict[str, dict[str, object]] = {
    "permanent": {
        "pass_signal_costs_operation": True,
        "pass_closing_rounds": 0,
    },
    "closing-2": {
        "pass_signal_costs_operation": True,
        "pass_closing_rounds": 2,
    },
    "closing-3": {
        "pass_signal_costs_operation": True,
        "pass_closing_rounds": 3,
    },
    "battle-flag": {
        "pass_signal_costs_operation": False,
        "pass_closing_rounds": 0,
    },
}


def pass_variant_run(args: argparse.Namespace) -> Path:
    """Paired Battle-ending experiment with resumable per-deck checkpoints."""
    from statistics import median

    from longwar.simulate import simulate_games

    if args.games <= 0 or args.jobs <= 0:
        raise SystemExit("--games and --jobs must be positive")
    if args.ismcts_iterations <= 0 or args.ismcts_belief_samples <= 0:
        raise SystemExit("ISMCTS budget values must be positive")
    if args.ismcts_rollout_depth < 0:
        raise SystemExit("--ismcts-rollout-depth must be non-negative")
    if (
        args.agent == "ismcts"
        and args.ismcts_iterations < 50_000
        and not args.allow_smoke
    ):
        raise SystemExit(
            "Pass-rule evidence requires at least 50,000 ISMCTS iterations. "
            "Use --allow-smoke only for plumbing/debug runs."
        )

    data = load_card_file(ROOT / "cards" / "cards.json")
    decks = {
        name: json.loads((ROOT / path).read_text(encoding="utf-8"))["cards"]
        for name, path in CANONICAL_DECK_PATHS.items()
    }
    selected = tuple(args.variants)
    unknown = [name for name in selected if name not in PASS_RULE_VARIANTS]
    if unknown:
        raise SystemExit(f"Unknown Pass variants: {unknown}")

    # Worker count is deliberately execution-only. Changing it after an
    # interrupted run must not change the evidence identity or prevent resume.
    config = {
        "experiment": "pass-variants",
        "variants": {
            name: PASS_RULE_VARIANTS[name]
            for name in selected
        },
        "games_per_deck": args.games,
        "seed": args.seed,
        "agent": args.agent,
        "ismcts_iterations": args.ismcts_iterations,
        "ismcts_belief_samples": args.ismcts_belief_samples,
        "ismcts_rollout_depth": args.ismcts_rollout_depth,
        "ismcts_rollout_policy": args.ismcts_rollout_policy,
        "canonical_decks": list(decks),
        "base_rules": GameRules.standard().as_dict(),
        "heuristic_weights": DEFAULT_HEURISTIC_WEIGHTS.as_dict(),
    }
    identity = experiment_identity(config)
    output = artifact_directory(
        ROOT / "artifacts" / "pass-variants",
        identity,
    )

    def cell_summary(payload: dict[str, Any]) -> dict[str, Any]:
        games = int(payload["games"])
        draws = int(payload.get("draws", 0))
        censored = int(payload.get("censored_games", 0))
        failed = int(payload.get("failed_games", 0))
        decisive = int(
            payload.get(
                "decisive_games",
                games - draws - censored - failed,
            )
        )
        outcomes = list(payload.get("game_outcomes", []))
        completed = max(0, games - failed)
        resolved_outcomes = [
            row for row in outcomes if not bool(row.get("censored", False))
        ]
        resolved = len(resolved_outcomes)
        actions = [
            int(row.get("actions_completed", 0))
            for row in resolved_outcomes
        ]
        turn_actions = [
            int(
                row.get(
                    "turn_consuming_actions_completed",
                    row.get("actions_completed", 0),
                )
            )
            for row in resolved_outcomes
        ]
        battles = int(
            payload.get("telemetry", {})
            .get("battles", {})
            .get("count", 0)
            or 0
        )
        passes = payload.get("telemetry", {}).get("passes", {})
        signals = int(
            passes.get("signal_events", passes.get("events", 0))
            or 0
        )
        forced_yields = int(passes.get("forced_yield_events", 0) or 0)
        free_signals = int(passes.get("free_signal_events", 0) or 0)
        decisions = payload.get("telemetry", {}).get("decisions", {})
        agent_decisions = decisions.get(args.agent, {})
        tactics = agent_decisions.get("ismcts_rollout_cutoffs", {})

        return {
            "games": games,
            "completed_games": completed,
            "resolved_games": resolved,
            "decisive_games": decisive,
            "draws": draws,
            "censored_games": censored,
            "failed_games": failed,
            "first_player_wins": int(payload.get("first_player_wins", 0)),
            "actions_total": sum(actions),
            "turn_consuming_actions_total": sum(turn_actions),
            "median_actions": median(actions) if actions else None,
            "median_turn_consuming_actions": (
                median(turn_actions) if turn_actions else None
            ),
            "resolved_battles": battles,
            "signal_events": signals,
            "forced_yield_events": forced_yields,
            "free_signal_events": free_signals,
            "mean_command_at_signal": passes.get("mean_command_at_signal"),
            "signal_with_playable_alternative_rate": passes.get(
                "signal_with_playable_alternative_rate"
            ),
            "decisive_rollout_probes": int(
                tactics.get("decisive_probes", 0) or 0
            ),
            "decisive_rollout_actions": int(
                tactics.get("decisive_actions", 0) or 0
            ),
            "anti_decisive_rollout_probes": int(
                tactics.get("anti_decisive_probes", 0) or 0
            ),
            "anti_decisive_rollout_filtered": int(
                tactics.get("anti_decisive_filtered", 0) or 0
            ),
        }

    rows: list[dict[str, Any]] = []
    for variant_index, name in enumerate(selected):
        overrides = PASS_RULE_VARIANTS[name]
        rules = GameRules.standard().with_overrides(**overrides)
        engine = GameEngine(data, rules=rules)
        variant_dir = output / name
        variant_dir.mkdir(parents=True, exist_ok=True)
        cell_payloads: dict[str, dict[str, Any]] = {}

        print(
            f"[{variant_index + 1}/{len(selected)}] {name}: "
            f"{len(decks) * args.games} games "
            f"({args.ismcts_iterations:,} iterations, "
            f"{args.ismcts_belief_samples} beliefs, "
            f"depth {args.ismcts_rollout_depth}, "
            f"{args.ismcts_rollout_policy})",
            flush=True,
        )

        for deck_index, (deck_name, deck) in enumerate(decks.items()):
            cell_path = variant_dir / f"{deck_name}.json"
            cell_seed = args.seed + deck_index * args.games
            cell_config = {
                "variant": name,
                "deck": deck_name,
                "games": args.games,
                "seed": cell_seed,
                "agent": args.agent,
                "ismcts_iterations": args.ismcts_iterations,
                "ismcts_belief_samples": args.ismcts_belief_samples,
                "ismcts_rollout_depth": args.ismcts_rollout_depth,
                "ismcts_rollout_policy": args.ismcts_rollout_policy,
                "rules": rules.as_dict(),
            }

            payload: dict[str, Any] | None = None
            if cell_path.exists() and not args.force:
                try:
                    candidate = json.loads(cell_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    candidate = None
                if (
                    isinstance(candidate, dict)
                    and candidate.get("game_fingerprint")
                    == identity["game_fingerprint"]
                    and candidate.get("experiment_fingerprint")
                    == identity["experiment_fingerprint"]
                    and candidate.get("cell_config") == cell_config
                ):
                    payload = candidate
                    print(f"  {deck_name}: reuse checkpoint", flush=True)

            if payload is None:
                def progress(
                    completed: int,
                    total: int,
                    _wins: tuple[int, int],
                ) -> None:
                    if completed == total or completed % 2 == 0:
                        print(
                            f"  {deck_name}: {completed}/{total}",
                            flush=True,
                        )

                report = simulate_games(
                    engine,
                    deck,
                    deck,
                    games=args.games,
                    seed=cell_seed,
                    jobs=args.jobs,
                    agent_names=(args.agent, args.agent),
                    ismcts_iterations=args.ismcts_iterations,
                    ismcts_belief_samples=args.ismcts_belief_samples,
                    ismcts_rollout_depth=args.ismcts_rollout_depth,
                    ismcts_rollout_policy=args.ismcts_rollout_policy,
                    progress_callback=progress,
                )
                payload = asdict(report)
                payload.update({
                    "decisive_games": report.decisive_games,
                    "completed_games": report.completed_games,
                    "draw_rate": report.draw_rate,
                    "censor_rate": report.censor_rate,
                    "rules": rules.as_dict(),
                    "variant": name,
                    "deck": deck_name,
                    "game_fingerprint": identity["game_fingerprint"],
                    "experiment_fingerprint": identity["experiment_fingerprint"],
                    "cell_config": cell_config,
                })
                cell_path.write_text(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print(f"  {deck_name}: checkpoint saved", flush=True)

            cell_payloads[deck_name] = payload

        per_deck = {
            deck_name: cell_summary(payload)
            for deck_name, payload in cell_payloads.items()
        }
        aggregate = list(per_deck.values())

        total_games = sum(row["games"] for row in aggregate)
        completed_games = sum(row["completed_games"] for row in aggregate)
        resolved_games = sum(row["resolved_games"] for row in aggregate)
        decisive = sum(row["decisive_games"] for row in aggregate)
        draws = sum(row["draws"] for row in aggregate)
        censored = sum(row["censored_games"] for row in aggregate)
        failed = sum(row["failed_games"] for row in aggregate)
        first_wins = sum(row["first_player_wins"] for row in aggregate)
        actions_total = sum(row["actions_total"] for row in aggregate)
        turn_actions_total = sum(
            row["turn_consuming_actions_total"] for row in aggregate
        )
        battles = sum(row["resolved_battles"] for row in aggregate)
        signals = sum(row["signal_events"] for row in aggregate)
        forced_yields = sum(row["forced_yield_events"] for row in aggregate)
        free_signals = sum(row["free_signal_events"] for row in aggregate)
        all_resolved_outcomes = [
            outcome
            for payload in cell_payloads.values()
            for outcome in payload.get("game_outcomes", [])
            if not bool(outcome.get("censored", False))
        ]
        all_actions = [
            int(outcome.get("actions_completed", 0))
            for outcome in all_resolved_outcomes
        ]
        all_turn_actions = [
            int(
                outcome.get(
                    "turn_consuming_actions_completed",
                    outcome.get("actions_completed", 0),
                )
            )
            for outcome in all_resolved_outcomes
        ]
        command_signal_weight = sum(
            (
                float(row["mean_command_at_signal"])
                * row["signal_events"]
            )
            for row in aggregate
            if row["mean_command_at_signal"] is not None
        )
        playable_signal_weight = sum(
            (
                float(row["signal_with_playable_alternative_rate"])
                * row["signal_events"]
            )
            for row in aggregate
            if row["signal_with_playable_alternative_rate"] is not None
        )
        resolved = decisive + draws
        row = {
            "variant": name,
            "rules": rules.as_dict(),
            "games": total_games,
            "decisive_games": decisive,
            "draws": draws,
            "censored_games": censored,
            "failed_games": failed,
            "first_player_wins": first_wins,
            "first_player_win_rate_decisive": (
                first_wins / decisive if decisive else None
            ),
            "first_player_win_rate_95ci": (
                wilson_interval(first_wins, decisive)
                if decisive else None
            ),
            "draw_rate_resolved": (
                draws / resolved if resolved else None
            ),
            "draw_rate_95ci": (
                wilson_interval(draws, resolved)
                if resolved else None
            ),
            "censor_rate": (
                censored / total_games if total_games else None
            ),
            "censor_rate_95ci": (
                wilson_interval(censored, total_games)
                if total_games else None
            ),
            "resolved_games": resolved_games,
            "mean_engine_actions_per_resolved_game": (
                actions_total / resolved_games if resolved_games else None
            ),
            "median_engine_actions_per_resolved_game": (
                median(all_actions) if all_actions else None
            ),
            "mean_turn_consuming_actions_per_resolved_game": (
                turn_actions_total / resolved_games
                if resolved_games else None
            ),
            "median_turn_consuming_actions_per_resolved_game": (
                median(all_turn_actions) if all_turn_actions else None
            ),
            "resolved_battles": battles,
            "mean_battles_per_game": (
                battles / total_games if total_games else None
            ),
            "signal_events": signals,
            "forced_yield_events": forced_yields,
            "free_signal_events": free_signals,
            "mean_signals_per_battle": (
                signals / battles if battles else None
            ),
            "mean_forced_yields_per_battle": (
                forced_yields / battles if battles else None
            ),
            "mean_command_at_signal": (
                command_signal_weight / signals if signals else None
            ),
            "signal_with_playable_alternative_rate": (
                playable_signal_weight / signals if signals else None
            ),
            "decisive_rollout_probes": sum(
                row["decisive_rollout_probes"] for row in aggregate
            ),
            "decisive_rollout_actions": sum(
                row["decisive_rollout_actions"] for row in aggregate
            ),
            "anti_decisive_rollout_probes": sum(
                row["anti_decisive_rollout_probes"] for row in aggregate
            ),
            "anti_decisive_rollout_filtered": sum(
                row["anti_decisive_rollout_filtered"] for row in aggregate
            ),
            "decks": per_deck,
        }
        rows.append(row)

        print(
            "  "
            f"decisive={decisive}, draws={draws}, censored={censored}, "
            f"turn-actions={row['mean_turn_consuming_actions_per_resolved_game']:.1f}, "
            f"Battles={row['mean_battles_per_game']:.2f}",
            flush=True,
        )

    evidence_grade = (
        "smoke"
        if args.agent == "ismcts" and args.ismcts_iterations < 50_000
        else "comparative-screen"
    )
    payload = {
        **identity,
        "schema_version": 2,
        "evidence_grade": evidence_grade,
        "execution": {"jobs": args.jobs},
        "paired_by": (
            "same canonical mirror deck, seat alternation, initial game seed, "
            "and agent seed schedule across variants"
        ),
        "variants": rows,
    }
    path = output / "summary.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path}", flush=True)
    return path

def _prepare_ismcts_speed_position(
    engine: GameEngine,
    state,
    *,
    position: str,
) -> None:
    if position == "opening":
        return
    if position != "pass-active":
        raise ValueError(f"unknown benchmark position: {position}")

    for _ in range(128):
        if state.phase is Phase.COMPLETE:
            raise RuntimeError("benchmark setup reached a terminal game")

        legal = engine.legal_actions(state)
        pass_action = next(
            (action for action in legal if isinstance(action, Pass)),
            None,
        )
        if pass_action is not None and (
            min(state.operations_this_battle) >= 1
            or all(isinstance(action, Pass) for action in legal)
        ):
            engine.apply(state, pass_action)
            if (
                len(state.pass_order) != 1
                or sum(player.passed for player in state.players) != 1
            ):
                raise RuntimeError("failed to create one-signal benchmark state")
            if (
                engine.rules.pass_closing_rounds > 0
                and state.pass_closing_turns_remaining <= 0
            ):
                raise RuntimeError(
                    "closing-window benchmark did not start its countdown"
                )
            return

        action = next(
            (action for action in legal if not isinstance(action, Pass)),
            legal[0],
        )
        engine.apply(state, action)

    raise RuntimeError("could not construct pass-active benchmark state")


def benchmark_ismcts_speed(args: argparse.Namespace) -> Path:
    """Benchmark one fixed ISMCTS decision with the exact simulation deck prior."""
    require_cython()
    data = load_card_file(ROOT / "cards" / "cards.json")
    rules = GameRules.standard().with_overrides(
        pass_closing_rounds=args.closing_rounds,
    )
    engine = GameEngine(data, rules=rules)
    deck = list(
        json.loads(
            (ROOT / args.deck).read_text(encoding="utf-8")
        )["cards"]
    )
    engine.validate_deck(deck)

    state = engine.new_game(
        deck,
        deck,
        seed=args.seed,
        first_player=0,
        opening_bonus=False,
    )
    _prepare_ismcts_speed_position(
        engine,
        state,
        position=args.position,
    )

    priors = (
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="benchmark-p0")],
        ),
        HypothesisDeckPrior(
            engine,
            [DeckHypothesis(tuple(deck), label="benchmark-p1")],
        ),
    )

    rows: list[dict[str, Any]] = []
    for belief_samples in args.belief_samples:
        for rollout_depth in args.depths:
            for iterations in args.iterations:
                samples: list[dict[str, Any]] = []
                for repeat in range(args.repeats):
                    agent = ISMCTSAgent(
                        engine,
                        args.seed + repeat,
                        priors=priors,
                        belief_samples=belief_samples,
                        iterations=iterations,
                        rollout_depth=rollout_depth,
                        rollout_policy=args.rollout_policy,
                        reuse_tree=False,
                    )
                    started = time.perf_counter()
                    agent.choose(engine, state)
                    elapsed = time.perf_counter() - started
                    decision = dict(agent.last_decision)
                    completed = int(decision.get("ismcts_iterations", 0))
                    search_seconds = float(
                        decision.get("ismcts_search_seconds", 0.0) or 0.0
                    )
                    samples.append({
                        "repeat": repeat,
                        "decision_seconds": elapsed,
                        "setup_seconds": float(
                            decision.get("ismcts_setup_seconds", 0.0) or 0.0
                        ),
                        "search_seconds": search_seconds,
                        "completed_iterations": completed,
                        "iterations_per_second": (
                            completed / search_seconds
                            if search_seconds > 0.0
                            else None
                        ),
                        "rollout_actions": int(
                            decision.get("ismcts_rollout_actions", 0) or 0
                        ),
                        "decisive_probes": int(
                            decision.get(
                                "ismcts_decisive_rollout_probes", 0
                            )
                            or 0
                        ),
                        "anti_decisive_probes": int(
                            decision.get(
                                "ismcts_anti_decisive_rollout_probes", 0
                            )
                            or 0
                        ),
                    })
                    agent.release_search_memory()

                mean_search = sum(
                    sample["search_seconds"] for sample in samples
                ) / len(samples)
                mean_rate = sum(
                    float(sample["iterations_per_second"] or 0.0)
                    for sample in samples
                ) / len(samples)
                row = {
                    "iterations": iterations,
                    "belief_samples": belief_samples,
                    "rollout_depth": rollout_depth,
                    "rollout_policy": args.rollout_policy,
                    "mean_search_seconds": mean_search,
                    "mean_iterations_per_second": mean_rate,
                    "samples": samples,
                }
                rows.append(row)
                mean_anti_probes = sum(
                    sample["anti_decisive_probes"] for sample in samples
                ) / len(samples)
                mean_completed = sum(
                    sample["completed_iterations"] for sample in samples
                ) / len(samples)
                probes_per_iteration = (
                    mean_anti_probes / mean_completed
                    if mean_completed > 0
                    else 0.0
                )
                print(
                    f"{iterations:>7,} iters | beliefs={belief_samples:>2} | "
                    f"depth={rollout_depth:>2} | "
                    f"{mean_search:>7.3f}s | {mean_rate:>9,.0f} iter/s | "
                    f"anti-probes/iter={probes_per_iteration:.2f}",
                    flush=True,
                )

    benchmark_config = {
        "benchmark": "ismcts-fixed-position",
        "position": args.position,
        "closing_rounds": args.closing_rounds,
        "deck": str(args.deck),
        "seed": args.seed,
        "iterations": list(args.iterations),
        "belief_samples": list(args.belief_samples),
        "depths": list(args.depths),
        "rollout_policy": args.rollout_policy,
        "repeats": args.repeats,
    }
    payload = {
        **experiment_identity(benchmark_config),
        **benchmark_config,
        "rows": rows,
    }
    BENCH_ROOT.mkdir(parents=True, exist_ok=True)
    path = BENCH_ROOT / "ismcts-speed.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path}", flush=True)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local validation, canonical AI sanity checks, and gameplay analysis."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate-data", help="Validate all shipped card sets and decks.")

    balance = sub.add_parser(
        "balance",
        help="Canonical static, playability and paired balance pipeline.",
    )
    balance.add_argument(
        "--preset",
        choices=("quick", "deep", "exhaustive"),
        default="quick",
    )
    balance.add_argument(
        "--agent",
        choices=(
            "heuristic",
            "strategic_heuristic",
            "ismcts",
            "random",
            "mccfr",
            "online_mccfr",
        ),
        default="heuristic",
        help="Agent used for structural/progression self-play.",
    )
    balance.add_argument(
        "--recovery-start",
        type=int,
        default=GameRules.standard().command_recovery_start,
        help="Base Command recovery in Battle I for the arithmetic recovery rule.",
    )
    balance.add_argument(
        "--recovery-decrement",
        type=int,
        default=GameRules.standard().command_recovery_decrement,
        help="Amount subtracted from base Command recovery after each Battle.",
    )
    balance.add_argument(
        "--command-matrix",
        action="store_true",
        help=(
            "Run planning-capable ISMCTS comparisons across the configured "
            "arithmetic (recovery start, decrement) candidate grid. Collapse "
            "at zero and the recovery floor remain fixed."
        ),
    )
    balance.add_argument(
        "--skip-card-screen",
        action="store_true",
        help=(
            "Skip the heuristic all-card A/B screen and targeted online-MCCFR "
            "stage. Useful for agent/recovery progression comparisons."
        ),
    )
    balance.add_argument(
        "--games",
        type=int,
        help=(
            "Structural games per matchup cell. Defaults depend on agent "
            "(heuristic: quick 8/deep 250/exhaustive 2000; search agents use "
            "smaller defaults). "
            "This does not change paired card-screen sample counts."
        ),
    )
    balance.add_argument("--seed", type=int, default=1701)
    balance.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel worker processes for long-running simulation work (default: {DEFAULT_WORKERS}).",
    )
    balance.add_argument(
        "--skip-failed-games",
        action="store_true",
        help=(
            "Record and exclude individual simulation failures instead of "
            "aborting the whole balance run."
        ),
    )
    balance.add_argument(
        "--contexts",
        type=int,
        default=3,
        help="Legal deck contexts per card in the broad paired A/B screen.",
    )
    balance.add_argument(
        "--games-per-context",
        type=int,
        default=4,
        help="Paired samples per context/card in the broad A/B screen.",
    )
    balance.add_argument(
        "--ismcts-belief-samples",
        type=int,
        default=DEFAULT_ISMCTS_BELIEF_SAMPLES,
        help="Belief determinizations per ISMCTS decision in balance runs.",
    )
    balance.add_argument(
        "--ismcts-iterations",
        type=int,
        default=DEFAULT_ISMCTS_ITERATIONS,
        help="ISMCTS iterations per searched decision in balance runs.",
    )
    balance.add_argument(
        "--ismcts-time-budget-seconds",
        type=float,
    )
    balance.add_argument(
        "--ismcts-rollout-depth",
        type=int,
        default=DEFAULT_ISMCTS_ROLLOUT_DEPTH,
    )
    balance.add_argument(
        "--ismcts-tree-depth-limit",
        type=int,
        default=96,
    )
    balance.add_argument(
        "--ismcts-exploration",
        type=float,
        default=DEFAULT_ISMCTS_EXPLORATION,
    )
    balance.add_argument(
        "--ismcts-progressive-widening",
        type=float,
        default=DEFAULT_ISMCTS_PROGRESSIVE_WIDENING,
    )
    balance.add_argument(
        "--ismcts-no-tree-reuse",
        action="store_true",
    )
    balance.add_argument(
        "--ismcts-max-tree-nodes",
        type=int,
        default=DEFAULT_ISMCTS_MAX_TREE_NODES,
    )
    balance.add_argument(
        "--ismcts-rollout-epsilon",
        type=float,
        default=DEFAULT_ISMCTS_ROLLOUT_EPSILON,
    )
    balance.add_argument(
        "--ismcts-rollout-policy",
        choices=("greedy", "cheap", "random", "decisive"),
        default=DEFAULT_ISMCTS_ROLLOUT_POLICY,
    )
    balance.add_argument(
        "--strategic-belief-samples",
        type=int,
        default=3,
    )
    balance.add_argument(
        "--strategic-rollout-plies",
        type=int,
        default=5,
    )
    balance.add_argument(
        "--strategic-candidate-width",
        type=int,
        default=6,
    )
    balance.add_argument(
        "--strategic-node-budget",
        type=int,
        default=20000,
    )
    balance.add_argument(
        "--strategic-time-budget-seconds",
        type=float,
    )
    balance.add_argument(
        "--online-agent-iterations",
        type=int,
        default=16,
        help="Online-MCCFR iterations when it is the structural agent.",
    )
    balance.add_argument(
        "--online-agent-depth",
        type=int,
        default=2,
        help="Online-MCCFR depth when it is the structural agent.",
    )
    balance.add_argument(
        "--online-iterations",
        type=int,
        default=16,
        help="Online-MCCFR iterations per non-forced decision in targeted validation.",
    )
    balance.add_argument(
        "--online-depth",
        type=int,
        default=2,
        help="Online-MCCFR resolve depth for targeted validation.",
    )
    balance.add_argument(
        "--target-max-cards",
        type=int,
        default=8,
        help="Maximum suspicious card signals to confirm with online MCCFR.",
    )
    balance.add_argument(
        "--target-min-effect",
        type=float,
        default=0.05,
        help="Minimum absolute broad ΔWP that can nominate a card for validation.",
    )
    balance.add_argument(
        "--target-contexts",
        type=int,
        help="Optional subset of broad contexts for online-MCCFR validation.",
    )
    balance.add_argument(
        "--target-games-per-context",
        type=int,
        help="Optional subset of broad games/context for online-MCCFR validation.",
    )
    balance.add_argument(
        "--skip-online-validation",
        action="store_true",
        help="Run the broad deep screen without targeted online-MCCFR confirmation.",
    )
    balance.add_argument(
        "--publish-lab",
        action="store_true",
        help=(
            "Publish this run as the root Balance Lab snapshot. Intended for "
            "CI observational/progression refreshes; ordinary quick runs do "
            "not overwrite the serious Lab."
        ),
    )

    pass_variants = sub.add_parser(
        "pass-variants",
        help="Compare current Battle-ending Pass/flag variants on paired seeds.",
    )
    pass_variants.add_argument(
        "--games",
        type=int,
        default=8,
        help="Games per canonical mirror deck and variant (default: 8).",
    )
    pass_variants.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Parallel game workers (default: {DEFAULT_WORKERS}).",
    )
    pass_variants.add_argument("--seed", type=int, default=26100100)
    pass_variants.add_argument(
        "--agent",
        choices=("heuristic", "ismcts"),
        default="ismcts",
    )
    pass_variants.add_argument(
        "--ismcts-iterations",
        type=int,
        default=50_000,
        help="ISMCTS iterations per decision; 50,000 is the evidence floor.",
    )
    pass_variants.add_argument(
        "--ismcts-belief-samples",
        type=int,
        default=12,
    )
    pass_variants.add_argument(
        "--ismcts-rollout-depth",
        type=int,
        default=12,
        help=(
            "Rollout plies after tree expansion. Twelve leaves room for the "
            "full 3-round closing window plus intermediate effect choices."
        ),
    )
    pass_variants.add_argument(
        "--ismcts-rollout-policy",
        choices=("greedy", "cheap", "random", "decisive"),
        default="decisive",
    )
    pass_variants.add_argument(
        "--allow-smoke",
        action="store_true",
        help="Permit sub-50k ISMCTS budgets for plumbing only.",
    )
    pass_variants.add_argument(
        "--force",
        action="store_true",
        help="Ignore compatible per-deck checkpoints and rerun every cell.",
    )
    pass_variants.add_argument(
        "--variants",
        nargs="+",
        default=list(PASS_RULE_VARIANTS),
        choices=tuple(PASS_RULE_VARIANTS),
    )

    ablation = sub.add_parser(
        "narrative-ablation",
        help="Diagnose Narrative/Command Command-economy tails with five ISMCTS ablations.",
    )
    ablation.add_argument("--games", type=int, default=24)
    ablation.add_argument("--jobs", type=int, default=DEFAULT_WORKERS)
    ablation.add_argument("--seed", type=int, default=1773)
    ablation.add_argument(
        "--force", action="store_true",
        help="Regenerate current-fingerprint ablation artifacts instead of reusing them.",
    )

    sub.add_parser(
        "validate",
        help="Run focused tests plus exact Python/Cython simulation parity.",
    )

    speed = sub.add_parser(
        "ismcts-speed",
        help="Benchmark fixed-position native ISMCTS throughput.",
    )
    speed.add_argument(
        "--iterations",
        type=int,
        nargs="+",
        default=[20_000, 50_000],
    )
    speed.add_argument(
        "--belief-samples",
        type=int,
        nargs="+",
        default=[6, 12],
    )
    speed.add_argument(
        "--depths",
        type=int,
        nargs="+",
        default=[8, 12],
    )
    speed.add_argument(
        "--rollout-policy",
        choices=("greedy", "cheap", "random", "decisive"),
        default="decisive",
    )
    speed.add_argument(
        "--position",
        choices=("opening", "pass-active"),
        default="pass-active",
    )
    speed.add_argument(
        "--closing-rounds",
        type=int,
        default=3,
    )
    speed.add_argument(
        "--deck",
        type=Path,
        default=Path(DEFAULT_DECK_PATH),
    )
    speed.add_argument("--seed", type=int, default=26100100)
    speed.add_argument("--repeats", type=int, default=1)

    strength = sub.add_parser(
        "strength-bench",
        help="Sanity-check canonical ISMCTS against alpha-beta.",
    )
    strength.add_argument(
        "--games",
        type=int,
        default=24,
        help=(
            "Games per deck/orientation. Default 24 gives 192 games total "
            "and 96 mirrored deal pairs."
        ),
    )
    strength.add_argument("--jobs", type=int, default=DEFAULT_WORKERS)
    strength.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ISMCTS_ITERATIONS,
        help="Fallback work ceiling; wall-clock time is the comparison budget.",
    )
    strength.add_argument("--alpha-nodes", type=int, default=20_000)
    strength.add_argument(
        "--time-budget-seconds",
        type=float,
        default=5.0,
        help="Equal wall-clock search budget per non-forced decision.",
    )
    strength.add_argument("--seed", type=int, default=26092400)
    strength.add_argument(
        "--publish-lab",
        action="store_true",
        help="Publish the current benchmark as artifacts/solver-strength.json.",
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()
    if args.command == "validate-data":
        validate_data()
    elif args.command == "balance":
        if args.command_matrix:
            run_command_matrix(args)
        else:
            balance_run(args)
    elif args.command == "pass-variants":
        pass_variant_run(args)
    elif args.command == "narrative-ablation":
        narrative_ablation_run(args)
    elif args.command == "validate":
        validate()
    elif args.command == "ismcts-speed":
        benchmark_ismcts_speed(args)
    elif args.command == "strength-bench":
        benchmark_strength(
            games_per_orientation=args.games,
            jobs=args.jobs,
            ismcts_iterations=args.iterations,
            alpha_nodes=args.alpha_nodes,
            time_budget_seconds=args.time_budget_seconds,
            seed=args.seed,
            publish_lab=args.publish_lab,
        )
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
