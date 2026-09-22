from __future__ import annotations

from Cython.Build import cythonize
from setuptools import Extension, setup


extensions = [
    Extension(
        "longwar._mccfr_accel",
        ["src/longwar/_mccfr_accel.pyx"],
    )
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
        },
    ),
)
