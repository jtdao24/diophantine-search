"""Shared solver and data fixtures for conformance tests."""

from functools import partial
import json
from pathlib import Path

import pytest

from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.families.three_cubes_cube_root import cube_root_search
from diophantine_search.families.three_cubes_modular import modular_search
from diophantine_search.families.three_cubes_native import (
    is_available,
    library_path,
    native_search,
)
from diophantine_search.testing.three_cubes_golden import load_golden

SOLVERS = {
    "brute_force": brute_force_search,
    "modular": modular_search,
    "modular_m63": partial(modular_search, modulus=63),
    "modular_m9": partial(modular_search, modulus=9),
    "cube_root": cube_root_search,
    "cube_root_m1": partial(cube_root_search, modulus=1),
    "cube_root_m63": partial(cube_root_search, modulus=63),
}
if is_available():
    SOLVERS.update(
        {
            "native": native_search,
            "native_m63": partial(native_search, modulus=63),
            "native_m1": partial(native_search, modulus=1),
            "native_m819": partial(native_search, modulus=819),
            "native_t4": partial(native_search, threads=4),
            "native_t20": partial(native_search, threads=20),
        }
    )
DATA = Path(__file__).parent / "data"


def pytest_report_header(config):
    """Report whether conformance includes the native shared library."""

    del config
    path = library_path()
    if path is not None and is_available():
        return f"native library: {path}"
    return "native library: not built"


@pytest.fixture(params=tuple(SOLVERS.values()), ids=tuple(SOLVERS))
def solver(request):
    """Return each accepted solver with a stable pytest id."""

    return request.param


@pytest.fixture(scope="session")
def known_solutions():
    """Load known solutions as exact integers while preserving coordinates."""

    data = json.loads(
        (DATA / "three_cubes_known.json").read_text(encoding="utf-8")
    )
    return tuple(
        (
            int(record["k"]),
            (int(record["x"]), int(record["y"]), int(record["z"])),
        )
        for record in data["solutions"]
    )


@pytest.fixture(scope="session")
def golden_sets():
    """Load the independently generated golden solution sets."""

    return load_golden(DATA / "three_cubes_golden.json")
