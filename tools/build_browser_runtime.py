"""Build the minimal canonical game runtime for static Pages."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "browser"
PYODIDE_VERSION = "314.0.7"
BUILD_VERSION = "0.39.1"
BUILD_LOG = OUTPUT / "browser-build.log"


def _run_logged(command: list[str]) -> None:
    """Run noisy build tooling into one log; show only a useful tail on failure."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with BUILD_LOG.open("a", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        try:
            lines = BUILD_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = "\n".join(lines[-80:])
        except OSError:
            tail = "(build log unavailable)"
        print(f"Browser build failed. Last log lines:\n{tail}", file=sys.stderr)
        raise SystemExit(result.returncode)


# Python modules required by browser play. Keep analysis/training/simulation and
# non-production agents out of the browser wheel.
BROWSER_PYTHON_FILES = (
    "__init__.py",
    "cards.py",
    "rules.py",
    "heuristics.py",
    "web_api.py",
    "game/__init__.py",
    "game/actions.py",
    "game/engine.py",
    "game/model.py",
    "agents/__init__.py",
    "agents/heuristic_agent.py",
)

# _fast_search currently contains the canonical engine plus bundled native
# search cores. Splitting that extension is separate cleanup work, so its
# include files remain required source inputs for the browser build.
BROWSER_NATIVE_FILES = (
    "_fast_search.pyx",
    "_heuristic_core.pxi",
    "_alpha_beta_core.pxi",
    "_ismcts_core.pxi",
    "_mccfr_core.pxi",
)

_BROWSER_SETUP = """from Cython.Build import cythonize
from setuptools import Extension, setup

setup(
    ext_modules=cythonize(
        [Extension("longwar._fast_search", ["src/longwar/_fast_search.pyx"])],
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
"""


def browser_source_paths() -> tuple[Path, ...]:
    package = ROOT / "src" / "longwar"
    return tuple(
        package / relative
        for relative in (*BROWSER_PYTHON_FILES, *BROWSER_NATIVE_FILES)
    )


def source_fingerprint() -> str:
    digest = hashlib.sha256(f"{PYODIDE_VERSION}:{BUILD_VERSION}".encode())
    sources = [
        ROOT / "pyproject.toml",
        Path(__file__),
        *browser_source_paths(),
    ]
    for path in sorted(sources):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare_browser_source(source: Path) -> None:
    """Create a build tree containing only the modules browser play imports."""
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    shutil.copy2(ROOT / "pyproject.toml", source / "pyproject.toml")
    (source / "setup.py").write_text(_BROWSER_SETUP, encoding="utf-8")

    package_root = source / "src" / "longwar"
    real_package = ROOT / "src" / "longwar"
    for relative in (*BROWSER_PYTHON_FILES, *BROWSER_NATIVE_FILES):
        src = real_package / relative
        dest = package_root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def ensure_browser_runtime() -> Path:
    runtime = OUTPUT / "runtime"
    manifest = runtime / "longwar-runtime.json"
    fingerprint = source_fingerprint()
    if manifest.exists():
        data = json.loads(manifest.read_text())
        if (
            data.get("source_fingerprint") == fingerprint
            and (runtime / data["wheel"]).is_file()
            and (runtime / "pyodide.asm.wasm").is_file()
        ):
            print("Canonical browser runtime is current", flush=True)
            return runtime

    if sys.version_info[:2] != (3, 14):
        raise SystemExit(
            "The browser build targets Python 3.14. "
            "Run make browser-build with Python 3.14 active."
        )

    # Cross compilation never shares native build directories or host .so files.
    build_env = ROOT / "artifacts" / "wasm-venv"
    pyodide = build_env / "bin" / "pyodide"
    if not pyodide.exists():
        venv.EnvBuilder(with_pip=True).create(build_env)
        _run_logged(
            [
                str(build_env / "bin" / "python"),
                "-m",
                "pip",
                "install",
                f"pyodide-build=={BUILD_VERSION}",
            ]
        )
    _run_logged([str(pyodide), "xbuildenv", "install", PYODIDE_VERSION])

    source = OUTPUT / "build-source"
    prepare_browser_source(source)

    wheels = OUTPUT / "wheels"
    if wheels.exists():
        shutil.rmtree(wheels)
    wheels.mkdir(parents=True, exist_ok=True)
    BUILD_LOG.write_text(
        "The Long War browser build\n"
        f"Pyodide {PYODIDE_VERSION}, pyodide-build {BUILD_VERSION}\n",
        encoding="utf-8",
    )
    _run_logged([str(pyodide), "build", str(source), "--outdir", str(wheels)])
    wheel = next(wheels.glob("longwar-*.whl"))

    archive = OUTPUT / f"pyodide-{PYODIDE_VERSION}.tgz"
    if not archive.exists():
        urllib.request.urlretrieve(
            f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz",
            archive,
        )
    unpacked = OUTPUT / "npm"
    with tarfile.open(archive) as package:
        package.extractall(unpacked, filter="data")
    if runtime.exists():
        shutil.rmtree(runtime)
    shutil.copytree(unpacked / "package", runtime)
    shutil.copy2(wheel, runtime / wheel.name)
    manifest.write_text(
        json.dumps(
            {
                "pyodide_version": PYODIDE_VERSION,
                "source_fingerprint": fingerprint,
                "wheel": wheel.name,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        f"Built canonical browser runtime: {runtime} "
        f"(build log: {BUILD_LOG.relative_to(ROOT)})",
        flush=True,
    )
    return runtime


if __name__ == "__main__":
    ensure_browser_runtime()
