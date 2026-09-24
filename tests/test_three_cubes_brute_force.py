"""Tests for the brute-force three-cubes reference search."""

from itertools import product
from math import comb

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    in_domain,
    is_canonical,
    is_solution,
    is_trivial,
    negate,
)
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)


def assert_invariants(result, instance):
    assert result.instance is instance
    assert result.triples_checked == comb(2 * instance.bound + 3, 3)
    assert all(
        left < right
        for left, right in zip(result.solutions, result.solutions[1:])
    )
    for triple in result.solutions:
        assert is_solution(instance.k, triple)
        assert is_canonical(triple)
        assert in_domain(triple, instance.bound)


def test_independent_cross_check():
    for bound in (0, 1, 2, 5, 7):
        values = range(-bound, bound + 1)
        for k in range(-40, 41):
            instance = SearchInstance(k, bound)
            result = brute_force_search(instance)
            expected = tuple(
                sorted(
                    {
                        tuple(sorted(triple))
                        for triple in product(values, repeat=3)
                        if sum(value**3 for value in triple) == k
                    }
                )
            )
            assert result.solutions == expected
            assert_invariants(result, instance)


@pytest.mark.parametrize(
    ("k", "bound", "expected"),
    [
        (3, 5, ((-5, 4, 4), (1, 1, 1))),
        (-3, 5, ((-4, -4, 5), (-1, -1, -1))),
        (2, 7, ((-6, -5, 7), (0, 1, 1))),
        (29, 5, ((-3, -2, 4), (1, 1, 3))),
        (6, 5, ((-1, -1, 2),)),
        (10, 5, ((-3, -3, 4), (1, 1, 2))),
        (
            8,
            4,
            ((-4, 2, 4), (-3, 2, 3), (-2, 2, 2), (-1, 1, 2), (0, 0, 2)),
        ),
        (0, 4, ((-4, 0, 4), (-3, 0, 3), (-2, 0, 2), (-1, 0, 1), (0, 0, 0))),
        (
            1,
            12,
            (
                (-12, 1, 12),
                (-12, 9, 10),
                (-11, 1, 11),
                (-10, 1, 10),
                (-9, 1, 9),
                (-8, -6, 9),
                (-8, 1, 8),
                (-7, 1, 7),
                (-6, 1, 6),
                (-5, 1, 5),
                (-4, 1, 4),
                (-3, 1, 3),
                (-2, 1, 2),
                (-1, 1, 1),
                (0, 0, 1),
            ),
        ),
    ],
)
def test_exact_outputs(k, bound, expected):
    instance = SearchInstance(k, bound)
    result = brute_force_search(instance)
    assert result.solutions == expected
    assert_invariants(result, instance)

    if k == 8:
        assert all(is_trivial(triple) for triple in result.solutions)
    if k == 1:
        assert tuple(
            triple for triple in result.solutions if not is_trivial(triple)
        ) == ((-12, 9, 10), (-8, -6, 9))


@pytest.mark.parametrize(
    ("k", "expected"),
    [(0, ((0, 0, 0),)), (1, ())],
)
def test_bound_zero(k, expected):
    instance = SearchInstance(k, 0)
    result = brute_force_search(instance)
    assert result.solutions == expected
    assert_invariants(result, instance)


def test_zero_family():
    for bound in range(16):
        instance = SearchInstance(0, bound)
        result = brute_force_search(instance)
        assert result.solutions == tuple(
            (-t, 0, t) for t in range(bound, -1, -1)
        )
        assert_invariants(result, instance)


def test_mod_nine_impossibility():
    for k in range(-60, 61):
        if k % 9 in {4, 5}:
            instance = SearchInstance(k, 8)
            result = brute_force_search(instance)
            assert result.solutions == ()
            assert_invariants(result, instance)


def test_negation_symmetry():
    for k in range(-30, 31):
        instance = SearchInstance(k, 6)
        negated_instance = SearchInstance(-k, 6)
        result = brute_force_search(instance)
        negated_result = brute_force_search(negated_instance)
        assert negated_result.solutions == tuple(
            sorted(negate(triple) for triple in result.solutions)
        )
        assert_invariants(result, instance)
        assert_invariants(negated_result, negated_instance)


def test_invalid_instance():
    with pytest.raises(TypeError):
        brute_force_search((3, 5))
