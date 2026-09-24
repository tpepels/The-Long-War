"""AI agents.

Keep package import lightweight: individual consumers import only the agent they
need. Package-level attributes remain available lazily for compatibility.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "HeuristicAgent",
    "StrategicHeuristicAgent",
    "ISMCTSAgent",
    "RandomAgent",
]


def __getattr__(name: str) -> Any:
    if name == "HeuristicAgent":
        from .heuristic_agent import HeuristicAgent
        return HeuristicAgent
    if name == "StrategicHeuristicAgent":
        from .strategic_heuristic_agent import StrategicHeuristicAgent
        return StrategicHeuristicAgent
    if name == "ISMCTSAgent":
        from .ismcts_agent import ISMCTSAgent
        return ISMCTSAgent
    if name == "RandomAgent":
        from .random_agent import RandomAgent
        return RandomAgent
    raise AttributeError(name)
