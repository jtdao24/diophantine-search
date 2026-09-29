"""Shared solver and data fixtures for conformance tests."""

from functools import partial
import json
from pathlib import Path

import pytest

from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.families.three_cubes_modular import modular_search
from diophantine_search.testing.three_cubes_golden import load_golden

SOLVERS = {
    "brute_force": brute_force_search,
    "modular": modular_search,
    "modular_m63": partial(modular_search, modulus=63),
    "modular_m9": partial(modular_search, modulus=9),
}
DATA = Path(__file__).parent / "data"


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
