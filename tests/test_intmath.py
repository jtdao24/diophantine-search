"""Tests for exact integer cube-root helpers."""

import json
import random
from pathlib import Path

import pytest

from diophantine_search.intmath import exact_cube_root, icbrt_ceil, icbrt_floor


def _assert_floor_and_ceil(n):
    floor = icbrt_floor(n)
    ceil = icbrt_ceil(n)
    assert floor**3 <= n < (floor + 1) ** 3
    assert (ceil - 1) ** 3 < n <= ceil**3


def test_floor_and_ceil_small_range():
    for n in range(-20_000, 20_001):
        _assert_floor_and_ceil(n)


def test_exact_roots_and_neighbors():
    for m in range(-2_000, 2_001):
        cube = m**3
        assert exact_cube_root(cube) == m
        if abs(m) >= 2:
            assert exact_cube_root(cube - 1) is None
            assert exact_cube_root(cube + 1) is None


def test_large_random_integers():
    rng = random.Random(20260929)
    for _ in range(2_000):
        m = rng.randint(-(10**40), 10**40)
        cube = m**3
        for n in (cube - 1, cube, cube + 1):
            _assert_floor_and_ceil(n)
    for _ in range(2_000):
        _assert_floor_and_ceil(rng.randint(-(10**120), 10**120))


def test_known_solution_coordinates_have_exact_roots():
    path = Path(__file__).parent / "data" / "three_cubes_known.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for record in data["solutions"]:
        for coordinate in ("x", "y", "z"):
            value = int(record[coordinate])
            assert exact_cube_root(value**3) == value


@pytest.mark.parametrize("value", [True, 1.0, "8"])
@pytest.mark.parametrize(
    "function", [icbrt_floor, icbrt_ceil, exact_cube_root]
)
def test_rejects_non_integers(function, value):
    with pytest.raises(TypeError):
        function(value)
