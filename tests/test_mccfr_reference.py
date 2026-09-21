from __future__ import annotations

import pytest

from longwar.mccfr_verification import verify_kuhn

pytestmark = pytest.mark.algorithm


def test_shared_external_sampling_solver_converges_on_kuhn_poker() -> None:
    report = verify_kuhn(
        iterations=30_000,
        seed=20260921,
        max_value_error=0.035,
        max_exploitability=0.07,
    )
    assert report["passed"], report
    assert report["information_sets"] == 12
