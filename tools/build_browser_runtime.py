"""Build the canonical engine for static Pages; cache all products in artifacts/."""
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


def source_fingerprint() -> str:
    digest = hashlib.sha256(f"{PYODIDE_VERSION}:{BUILD_VERSION}".encode())
    sources = [ROOT / "setup.py", ROOT / "pyproject.toml", Path(__file__)]
    sources.extend(p for p in (ROOT / "src" / "longwar").rglob("*")
                   if p.suffix in {".py", ".pyx", ".pxi"})
    for path in sorted(sources):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def ensure_browser_runtime() -> Path:
    runtime = OUTPUT / "runtime"
    manifest = runtime / "longwar-runtime.json"
    fingerprint = source_fingerprint()
    if manifest.exists():
        data = json.loads(manifest.read_text())
        if (data.get("source_fingerprint") == fingerprint
                and (runtime / data["wheel"]).is_file()
                and (runtime / "pyodide.asm.wasm").is_file()):
            print("Canonical browser runtime is current", flush=True)
            return runtime
    if sys.version_info[:2] != (3, 14):
        raise SystemExit("The browser build targets Python 3.14. Run make browser-build with Python 3.14 active.")

    # Cross compilation never shares native build directories or host .so files.
    build_env = ROOT / "artifacts" / "wasm-venv"
    pyodide = build_env / "bin" / "pyodide"
    if not pyodide.exists():
        venv.EnvBuilder(with_pip=True).create(build_env)
        subprocess.run([str(build_env / "bin" / "python"), "-m", "pip", "install",
                        f"pyodide-build=={BUILD_VERSION}"], check=True)
    subprocess.run([str(pyodide), "xbuildenv", "install", PYODIDE_VERSION], check=True)
    source = OUTPUT / "build-source"
    if source.exists():
        shutil.rmtree(source)
    source.mkdir(parents=True)
    for name in ("pyproject.toml", "setup.py"):
        shutil.copy2(ROOT / name, source / name)
    shutil.copytree(ROOT / "src" / "longwar", source / "src" / "longwar",
                    ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.c", "*.pyc"))
    wheels = OUTPUT / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(pyodide), "build", str(source), "--outdir", str(wheels)], check=True)
    wheel = next(wheels.glob("longwar-*.whl"))

    archive = OUTPUT / f"pyodide-{PYODIDE_VERSION}.tgz"
    if not archive.exists():
        urllib.request.urlretrieve(
            f"https://registry.npmjs.org/pyodide/-/pyodide-{PYODIDE_VERSION}.tgz", archive)
    unpacked = OUTPUT / "npm"
    with tarfile.open(archive) as package:
        package.extractall(unpacked, filter="data")
    if runtime.exists():
        shutil.rmtree(runtime)
    shutil.copytree(unpacked / "package", runtime)
    shutil.copy2(wheel, runtime / wheel.name)
    manifest.write_text(json.dumps({"pyodide_version": PYODIDE_VERSION,
                                    "source_fingerprint": fingerprint,
                                    "wheel": wheel.name}, indent=2) + "\n")
    print(f"Built canonical browser runtime: {runtime}", flush=True)
    return runtime


if __name__ == "__main__":
    ensure_browser_runtime()
