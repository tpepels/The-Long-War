from __future__ import annotations

import hashlib
from pathlib import Path
from types import ModuleType
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "longwar"
GENERATED_NAME = "_native_source_fingerprint.generated.pxi"
FNV_OFFSET = 14695981039346656037
FNV_PRIME = 1099511628211
FNV_MASK = (1 << 64) - 1


def native_source_paths() -> tuple[Path, ...]:
    paths = [
        path
        for pattern in ("_*.pxi", "_*.pyx")
        for path in PACKAGE.glob(pattern)
        if path.name != GENERATED_NAME
    ]
    return tuple(sorted(set(paths)))


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _fnv_feed(value: int, data: bytes) -> int:
    for byte in data:
        value ^= byte
        value = (value * FNV_PRIME) & FNV_MASK
    return value


def fingerprint_paths(paths: Iterable[Path]) -> str:
    value = FNV_OFFSET
    for path in sorted(set(paths)):
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        value = _fnv_feed(value, relative)
        value = _fnv_feed(value, b"\0")
        value = _fnv_feed(value, _git_blob_sha(path).encode("ascii"))
        value = _fnv_feed(value, b"\0")
    return f"{value:016x}"


def current_native_source_fingerprint() -> str:
    return fingerprint_paths(native_source_paths())


def assert_native_module_current(module: ModuleType) -> ModuleType:
    if not bool(getattr(module, "NATIVE_SOURCE_CHECKABLE", True)):
        return module
    compiled = getattr(module, "NATIVE_SOURCE_FINGERPRINT", None)
    current = current_native_source_fingerprint()
    if compiled != current:
        raise RuntimeError(
            "The loaded Cython extension does not match the current native "
            "source. Run: make native-build"
        )
    return module
