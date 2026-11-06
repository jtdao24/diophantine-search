"""ctypes binding for native row search under the contract in spec §10."""

from __future__ import annotations

import ctypes
from functools import lru_cache
import os
from pathlib import Path
import sys

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
)
from diophantine_search.families.three_cubes_cube_root import (
    MAX_TABLE_ENTRIES,
)
from diophantine_search.families.three_cubes_modular import (
    cube_residues,
)

NATIVE_MAX_BOUND = 1_454_083
NATIVE_MAX_THREADS = 256
# Selected by benchmarks/results/2026-11-05-native-sweep-66d8927.json.
NATIVE_DEFAULT_MODULUS = 15_561
_MAX_INT64 = 2**63 - 1
_BUILD_COMMANDS = (
    "cmake -S native -B build/native -G Ninja -DCMAKE_BUILD_TYPE=Release "
    "-DCMAKE_CXX_COMPILER=clang++\n"
    "cmake --build build/native"
)


class NativeLibraryError(RuntimeError):
    """Report an unavailable or incompatible native search library."""


def library_path() -> Path | None:
    """Return the configured native library path when it is a file."""

    if "DIOPHANTINE_NATIVE_LIB" in os.environ:
        configured = Path(os.environ["DIOPHANTINE_NATIVE_LIB"])
        return configured if configured.is_file() else None

    if sys.platform == "win32":
        suffix = ".dll"
    elif sys.platform == "darwin":
        suffix = ".dylib"
    else:
        suffix = ".so"
    candidate = (
        Path(__file__).resolve().parents[3]
        / "build"
        / "native"
        / f"diophantine_native{suffix}"
    )
    return candidate if candidate.is_file() else None


@lru_cache(maxsize=1)
def _load_library() -> ctypes.CDLL:
    """Load and configure the native ABI once."""

    path = library_path()
    if path is None:
        raise NativeLibraryError(
            "native library is unavailable; build it with:\n" + _BUILD_COMMANDS
        )
    try:
        library = ctypes.CDLL(str(path.resolve()))
    except OSError as error:
        raise NativeLibraryError(
            f"cannot load native library {path}: {error}\n"
            f"Build it with:\n{_BUILD_COMMANDS}"
        ) from error

    try:
        library.ds_abi_version.argtypes = []
        library.ds_abi_version.restype = ctypes.c_int
        if library.ds_abi_version() != 2:
            raise NativeLibraryError(
                f"native library {path} has an incompatible ABI; rebuild with:\n"
                f"{_BUILD_COMMANDS}"
            )

        pointer = ctypes.POINTER(ctypes.c_int64)
        library.ds_cube_root_search.argtypes = [
            ctypes.c_int64,
            ctypes.c_int64,
            ctypes.c_int64,
            ctypes.c_int64,
            pointer,
            ctypes.c_int64,
            pointer,
            pointer,
        ]
        library.ds_cube_root_search.restype = ctypes.c_int
        library.ds_clear_cache.argtypes = []
        library.ds_clear_cache.restype = None
        library.ds_icbrt_floor.argtypes = [ctypes.c_int64]
        library.ds_icbrt_floor.restype = ctypes.c_int64
        library.ds_icbrt_ceil.argtypes = [ctypes.c_int64]
        library.ds_icbrt_ceil.restype = ctypes.c_int64
    except AttributeError as error:
        raise NativeLibraryError(
            f"native library {path} has an incompatible ABI"
        ) from error
    return library


def is_available() -> bool:
    """Return whether the configured native library exists and loads."""

    if library_path() is None:
        return False
    try:
        _load_library()
    except NativeLibraryError:
        return False
    return True


@lru_cache(maxsize=32, typed=True)
def _validate_modulus(modulus: int) -> None:
    residues = cube_residues(modulus)
    if modulus * len(residues) > MAX_TABLE_ENTRIES:
        raise ValueError(f"y-class table exceeds {MAX_TABLE_ENTRIES} entries")


def _validate_range(instance: SearchInstance) -> None:
    # ctypes converts Python integers modulo the C width. Validate first so an
    # oversized k cannot silently wrap and search a different equation.
    if (
        instance.bound > NATIVE_MAX_BOUND
        or abs(instance.k) + 3 * instance.bound**3 > _MAX_INT64
    ):
        raise ValueError(
            "instance is outside the native range: require bound <= "
            f"{NATIVE_MAX_BOUND} and |k| + 3*bound**3 <= 2**63 - 1"
        )


def _call_search(
    library: ctypes.CDLL,
    instance: SearchInstance,
    modulus: int,
    threads: int,
    capacity: int,
) -> tuple[int, ctypes.Array[ctypes.c_int64], int, int]:
    output = (ctypes.c_int64 * (3 * capacity))()
    count = ctypes.c_int64()
    checked = ctypes.c_int64()
    status = library.ds_cube_root_search(
        instance.k,
        instance.bound,
        modulus,
        threads,
        output,
        capacity,
        ctypes.byref(count),
        ctypes.byref(checked),
    )
    return status, output, int(count.value), int(checked.value)


def native_search(
    instance: SearchInstance,
    modulus: int = NATIVE_DEFAULT_MODULUS,
    threads: int = 1,
) -> SearchResult:
    """Run native row search with Python-equivalent results and row counts."""

    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    _validate_modulus(modulus)
    if not isinstance(threads, int) or isinstance(threads, bool):
        raise TypeError("threads must be an int")
    if not 1 <= threads <= NATIVE_MAX_THREADS:
        raise ValueError(f"threads must be in [1, {NATIVE_MAX_THREADS}]")
    _validate_range(instance)
    library = _load_library()

    status, output, count, checked = _call_search(
        library, instance, modulus, threads, 1024
    )
    if status == 1:
        status, output, count, checked = _call_search(
            library, instance, modulus, threads, count
        )
    if status == 2:
        raise ValueError("native library rejected the search arguments")
    if status == 3:
        raise MemoryError("native library could not allocate search memory")
    if status != 0:
        raise NativeLibraryError(f"native library returned status {status}")

    solutions = tuple(
        (
            int(output[3 * index]),
            int(output[3 * index + 1]),
            int(output[3 * index + 2]),
        )
        for index in range(count)
    )
    return SearchResult(instance, solutions, checked)


def clear_native_cache() -> None:
    """Clear the native table cache, or do nothing when unavailable."""

    _validate_modulus.cache_clear()
    if library_path() is None:
        return
    try:
        library = _load_library()
    except NativeLibraryError:
        return
    library.ds_clear_cache()
