"""Executable mathematical facts from the three-cubes specification."""

from itertools import product

from diophantine_search.families.three_cubes import (
    canonicalize,
    is_canonical,
    is_trivial,
    sum_of_cubes,
)


def test_cube_residues_mod_nine():
    assert {n**3 % 9 for n in range(-100, 101)} == {0, 1, 8}


def test_no_forbidden_cube_sums_mod_nine():
    for triple in product(range(-8, 9), repeat=3):
        assert sum_of_cubes(triple) % 9 not in {4, 5}


def test_zero_solutions_in_domain_ten():
    found = sorted(
        triple
        for triple in product(range(-10, 11), repeat=3)
        if is_canonical(triple) and sum_of_cubes(triple) == 0
    )
    assert found == [(-t, 0, t) for t in range(10, -1, -1)]


def test_trivial_solutions_have_cube_target():
    for triple in product(range(-8, 9), repeat=3):
        if is_canonical(triple) and is_trivial(triple):
            assert sum_of_cubes(triple) in {value**3 for value in triple}


def test_parametric_family_for_one():
    for t in range(-50, 51):
        triple = (9 * t**4, 3 * t - 9 * t**4, 1 - 9 * t**3)
        assert sum_of_cubes(canonicalize(triple)) == 1


def test_parametric_family_for_two():
    for t in range(-50, 51):
        triple = (1 + 6 * t**3, 1 - 6 * t**3, -6 * t**2)
        assert sum_of_cubes(canonicalize(triple)) == 2
