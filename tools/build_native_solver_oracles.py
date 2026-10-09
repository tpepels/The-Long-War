"""Compile the actual native kernels against a tiny, independent solved game.

This extension is for tests only and is never imported by the production
search agent. The .pyx includes the exact production Cython kernel .pxi files,
so differences in the search recursion or UCT/regret update affect this test.
"""
from __future__ import annotations

from pathlib import Path
from setuptools import Extension, setup
from Cython.Build import cythonize

ROOT = Path(__file__).resolve().parents[1]
ext = Extension(
    "native_solver_kernels",
    [str(ROOT / "tests" / "native_solver_kernels.pyx")],
)

setup(
    name="longwar-native-solved-game-oracles",
    ext_modules=cythonize(
        [ext],
        include_path=[str(ROOT / "src" / "longwar")],
        compiler_directives={"language_level": 3},
        force=True,
    ),
    script_args=["build_ext", "--inplace"],
)
