"""Tests for the exact cube-root row solver."""

import pytest

from diophantine_search.families.three_cubes import SearchInstance
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.families.three_cubes_cube_root import (
    cube_root_search,
    row_bounds,
    x_upper,
    y_class_table,
)
from diophantine_search.families.three_cubes_modular import (
    MAX_MODULUS,
    cube_residues,
    modular_search,
)

TABLE_MODULI = (*range(1, 61), 63, 819)
SEARCH_MODULI = (1, 2, 4, 7, 8, 9, 13, 27, 63, 819)


@pytest.mark.parametrize("modulus", TABLE_MODULI)
def test_y_class_table_definition(modulus):
    table = y_class_table(modulus)
    residues = cube_residues(modulus)
    assert len(table) == modulus
    for s, classes in enumerate(table):
        assert classes == tuple(sorted(classes))
        for c in range(modulus):
            assert (c in classes) == ((s - c**3) % modulus in residues)


def test_y_class_table_cap():
    assert len(y_class_table(15_561)) == 15_561
    with pytest.raises(ValueError):
        y_class_table(43_010)


def test_bounds_contain_every_brute_force_solution():
    for bound in range(9):
        for k in range(-300, 301):
            result = brute_force_search(SearchInstance(k, bound))
            for x, y, _ in result.solutions:
                lo, hi = row_bounds(k, bound, x)
                assert x <= x_upper(k, bound)
                assert lo <= y <= hi


def test_solutions_match_brute_force():
    for k in range(-40, 41):
        for bound in (0, 1, 2, 5, 7, 12):
            instance = SearchInstance(k, bound)
            expected = brute_force_search(instance).solutions
            for modulus in SEARCH_MODULI:
                assert cube_root_search(instance, modulus).solutions == expected


@pytest.mark.parametrize("k", [1, 2, 3, 29, 30, 33, 42, 52, 74])
def test_bound_60_matches_modular_search(k):
    instance = SearchInstance(k, 60)
    assert cube_root_search(instance).solutions == modular_search(instance).solutions


def _independent_count(k, bound, modulus):
    if k % 9 in {4, 5}:
        return 0
    residues = cube_residues(modulus)
    count = 0
    for x in range(-bound, bound + 1):
        for y in range(x, bound + 1):
            rest = k - x**3
            if (
                2 * y**3 <= rest
                and x**3 + y**3 + bound**3 >= k
                and (rest - y**3) % modulus in residues
            ):
                count += 1
    return count


def test_triples_checked_matches_independent_count():
    for k in range(-20, 21):
        for bound in (0, 3, 6, 10):
            instance = SearchInstance(k, bound)
            for modulus in (1, 9, 63, 819):
                assert cube_root_search(instance, modulus).triples_checked == (
                    _independent_count(k, bound, modulus)
                )


@pytest.mark.parametrize("k", [-14, -13, -5, -4, 4, 5, 13, 14])
def test_mod_nine_exclusion_checks_no_rows(k):
    assert k % 9 in {4, 5}
    for modulus in SEARCH_MODULI:
        result = cube_root_search(SearchInstance(k, 10), modulus)
        assert result.solutions == ()
        assert result.triples_checked == 0


def test_divisible_moduli_never_increase_work():
    for k in range(-30, 31):
        instance = SearchInstance(k, 10)
        counts = [
            cube_root_search(instance, modulus).triples_checked
            for modulus in (1, 3, 9, 63, 819)
        ]
        assert all(left >= right for left, right in zip(counts, counts[1:]))


@pytest.mark.parametrize(
    ("modulus", "expected"),
    [(1, 121_664), (9, 52_796), (63, 23_188), (819, 9_109)],
)
def test_pinned_triples_checked_totals(modulus, expected):
    actual = sum(
        cube_root_search(SearchInstance(k, 30), modulus).triples_checked
        for k in range(-100, 101)
    )
    assert actual == expected


@pytest.mark.parametrize("modulus", [0, -1, MAX_MODULUS + 1, 43_010])
def test_search_rejects_invalid_modulus(modulus):
    with pytest.raises(ValueError):
        cube_root_search(SearchInstance(3, 5), modulus)


@pytest.mark.parametrize("modulus", [1.0, True])
def test_search_rejects_non_integer_modulus(modulus):
    with pytest.raises(TypeError):
        cube_root_search(SearchInstance(3, 5), modulus)


def test_search_rejects_non_instance_before_modulus():
    with pytest.raises(TypeError):
        cube_root_search((3, 5), 0)
