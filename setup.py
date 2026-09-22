from __future__ import annotations

from Cython.Build import cythonize
from setuptools import Extension, setup


extensions = [
    Extension(
        "longwar._mccfr_accel",
        ["src/longwar/_mccfr_accel.pyx"],
    ),
    # Compile the actual search hot path as well as the generic CFR loop.
    # The .py sources remain canonical and are what the Pyodide bundle ships;
    # CPython prefers these extension modules when they are available.
    Extension(
        "longwar.game.model",
        ["src/longwar/game/model.py"],
    ),
    Extension(
        "longwar.game.engine",
        ["src/longwar/game/engine.py"],
    ),
    Extension(
        "longwar.agents.heuristic_agent",
        ["src/longwar/agents/heuristic_agent.py"],
    ),
    Extension(
        "longwar.mccfr",
        ["src/longwar/mccfr.py"],
    ),
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
            "infer_types": True,
        },
    ),
)
