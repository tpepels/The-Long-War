"""Solve independent games using the actual optimized Cython search loops.

The native_solver_kernels test extension includes _alpha_beta_core.pxi,
_ismcts_core.pxi and _mccfr_core.pxi directly. It replaces ONLY the
game-specific inlined _sg_* adapter with the rules of two tiny games.
"""
from __future__ import annotations

import pytest

from longwar.mccfr_verification import (
    KNOWN_P0_VALUE,
    expected_value,
    exploitability,
)

native = pytest.importorskip("native_solver_kernels")
pytestmark = pytest.mark.algorithm


@pytest.mark.parametrize("stones", range(1, 13))
@pytest.mark.parametrize("actor,root_player", ((0, 0), (0, 1), (1, 0), (1, 1)))
def test_optimized_native_alpha_beta_matches_mathematical_nim(
    stones, actor, root_player,
):
    """Taking 1 or 2: multiples of 3 are losing for the player to move."""
    player_to_move_wins = stones % 3 != 0
    root_wins = player_to_move_wins if actor == root_player else not player_to_move_wins
    expected = 1.0 if root_wins else -1.0
    assert native.solve_nim_alpha_beta(
        stones, actor=actor, root_player=root_player,
    ) == pytest.approx(expected)


@pytest.mark.parametrize("seed", (1, 7, 31, 101))
@pytest.mark.parametrize(
    "stones,winning_action",
    ((1, 1), (2, 2), (4, 1), (5, 2), (7, 1)),
)
def test_optimized_native_ismcts_finds_analytic_nim_move(
    stones, winning_action, seed,
):
    result = native.solve_nim_ismcts(stones, seed=seed, iterations=1600)
    assert result["action"] == winning_action, result
    assert result["iterations"] == 1600
    assert result["root_total_visits"] == 1600


@pytest.mark.parametrize("seed", (2, 17, 51, 20261009))
def test_optimized_native_ismcts_respects_hidden_expected_value(seed):
    # A hidden +/-1 coin makes "risky" worth 0 on average.
    # The observable safe option pays +0.4, and is strictly preferable.
    result = native.solve_hidden_ismcts(seed=seed, iterations=4000)
    assert result["action"] == 1, result
    assert result["root_total_visits"] == 4000


@pytest.mark.parametrize("seed", (20260921, 20261009))
def test_optimized_native_mccfr_solves_kuhn_poker(seed):
    policy = native.solve_kuhn_mccfr(iterations=30000, seed=seed)
    value = expected_value(policy)
    exp, _, _ = exploitability(policy)
    assert len(policy) == 12, policy
    assert value == pytest.approx(KNOWN_P0_VALUE, abs=0.045)
    assert exp < 0.09, {"exploitability": exp, "value": value, "policy": policy}


def test_oracle_harness_includes_unmodified_native_kernels():
    from pathlib import Path

    source = (Path(__file__).parent / "native_solver_kernels.pyx").read_text()
    for kernel in (
        "_alpha_beta_core.pxi",
        "_ismcts_core.pxi",
        "_mccfr_core.pxi",
    ):
        assert f'include "{kernel}"' in source
    # Catch accidental substitution with a reference/Python fallback.
    assert "from longwar.algorithms" not in source
