"""Tests for the three-cubes core definitions."""

import json
from itertools import permutations, product
from math import comb
from pathlib import Path

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    canonicalize,
    in_domain,
    is_canonical,
    is_solution,
    is_trivial,
    negate,
    orbit_size,
    sum_of_cubes,
)


def _known_solutions():
    path = Path(__file__).parent / "data" / "three_cubes_known.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["family"] == "three_cubes"
    return [
        (int(row["k"]), (int(row["x"]), int(row["y"]), int(row["z"])))
        for row in data["solutions"]
    ]


@pytest.mark.parametrize(("k", "triple"), _known_solutions())
def test_known_solutions_as_stored_and_canonical(k, triple):
    assert is_solution(k, triple)
    assert is_solution(k, canonicalize(triple))


@pytest.mark.parametrize(("k", "triple"), _known_solutions())
def test_changing_one_coordinate_breaks_solution(k, triple):
    for index in range(3):
        for change in (-1, 1):
            changed = list(triple)
            changed[index] += change
            assert not is_solution(k, tuple(changed))


@pytest.mark.parametrize(("k", "triple"), _known_solutions())
def test_permutation_and_canonicalization(k, triple):
    expected = canonicalize(triple)
    assert is_canonical(expected)
    assert canonicalize(expected) == expected
    for permutation in permutations(triple):
        assert canonicalize(permutation) == expected


@pytest.mark.parametrize(("k", "triple"), _known_solutions())
def test_negation(k, triple):
    assert is_solution(k, triple) == is_solution(-k, negate(triple))
    canonical = canonicalize(triple)
    assert is_canonical(negate(canonical))
    assert negate(negate(triple)) == triple


@pytest.mark.parametrize(
    ("triple", "expected"),
    [((1, 2, 3), 6), ((4, 4, -5), 3), ((1, 1, 1), 1)],
)
def test_orbit_size_examples(triple, expected):
    assert orbit_size(triple) == expected


@pytest.mark.parametrize("bound", range(6))
def test_canonical_counts_and_orbits(bound):
    values = range(-bound, bound + 1)
    canonical = [
        triple for triple in product(values, repeat=3) if is_canonical(triple)
    ]
    assert len(canonical) == comb(2 * bound + 3, 3)
    assert sum(orbit_size(triple) for triple in canonical) == (2 * bound + 1) ** 3


@pytest.mark.parametrize(
    ("triple", "expected"),
    [((-3, 0, 3), True), ((-12, 9, 10), False), ((-2, 2, 5), True)],
)
def test_trivial_examples(triple, expected):
    assert is_trivial(triple) is expected


@pytest.mark.parametrize(
    "function",
    [
        sum_of_cubes,
        lambda t: is_solution(1, t),
        lambda t: in_domain(t, 1),
        canonicalize,
        is_canonical,
        is_trivial,
        orbit_size,
        negate,
    ],
)
@pytest.mark.parametrize("triple", [(True, 1, 1), (1.0, 1, 1), ("1", 1, 1)])
def test_bad_triple_elements(function, triple):
    with pytest.raises(TypeError):
        function(triple)


@pytest.mark.parametrize(
    "function",
    [
        sum_of_cubes,
        lambda t: is_solution(1, t),
        lambda t: in_domain(t, 1),
        canonicalize,
        is_canonical,
        is_trivial,
        orbit_size,
        negate,
    ],
)
@pytest.mark.parametrize("triple", [(1, 2), (1, 2, 3, 4)])
def test_bad_triple_lengths(function, triple):
    with pytest.raises(ValueError):
        function(triple)


@pytest.mark.parametrize(
    "call",
    [
        lambda: is_solution(True, (1, 1, 1)),
        lambda: is_solution(3.0, (1, 1, 1)),
        lambda: in_domain((1, 1, 1), 2.0),
        lambda: in_domain((1, 1, 1), True),
        lambda: SearchInstance(k=True, bound=1),
        lambda: SearchInstance(k=1, bound=1.0),
    ],
)
def test_bad_scalar_types(call):
    with pytest.raises(TypeError):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: in_domain((1, 1, 1), -1),
        lambda: SearchInstance(k=1, bound=-1),
    ],
)
def test_negative_bounds(call):
    with pytest.raises(ValueError):
        call()


def test_search_instance_and_domain_boundary():
    assert SearchInstance(k=3, bound=1) == SearchInstance(k=3, bound=1)
    assert in_domain((-1, 0, 1), 1)
    assert not in_domain((-2, 0, 1), 1)
