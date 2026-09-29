"""Tests for proven modular pruning of the three-cubes search."""

from math import comb

import pytest

from diophantine_search.families.three_cubes import SearchInstance
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.families.three_cubes_modular import (
    MAX_MODULUS,
    cube_residues,
    cube_root_classes,
    modular_search,
)

MODULI = (1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 27, 63, 819)


@pytest.mark.parametrize(
    ("modulus", "expected"),
    [
        (4, {0, 1, 3}),
        (7, {0, 1, 6}),
        (9, {0, 1, 8}),
        (13, {0, 1, 5, 8, 12}),
    ],
)
def test_cube_residue_examples(modulus, expected):
    assert cube_residues(modulus) == expected


def test_cube_residue_surjectivity_through_40():
    expected = {1, 2, 3, 5, 6, 10, 11, 15, 17, 22, 23, 29, 30, 33, 34}
    actual = {
        modulus
        for modulus in range(1, 41)
        if cube_residues(modulus) == frozenset(range(modulus))
    }
    assert actual == expected


@pytest.mark.parametrize("modulus", (*range(1, 61), 63, 819))
def test_cube_root_classes_partition_residues(modulus):
    classes = cube_root_classes(modulus)
    assert len(classes) == modulus
    assert all(tuple(sorted(members)) == members for members in classes)
    seen = []
    for residue, members in enumerate(classes):
        for c in members:
            assert c**3 % modulus == residue
            seen.append(c)
    assert sorted(seen) == list(range(modulus))


def test_cube_mod_nine_depends_only_on_class_mod_three():
    for n in range(-60, 61):
        assert n**3 % 9 == (n % 3) ** 3 % 9


def test_solutions_match_brute_force():
    for k in range(-40, 41):
        for bound in (0, 1, 2, 5, 7):
            instance = SearchInstance(k, bound)
            expected = brute_force_search(instance).solutions
            for modulus in MODULI:
                assert modular_search(instance, modulus).solutions == expected


def _independent_count(k, bound, modulus):
    if k % 9 in {4, 5}:
        return 0
    count = 0
    for x in range(-bound, bound + 1):
        for y in range(x, bound + 1):
            for z in range(y, bound + 1):
                if (z**3 - (k - x**3 - y**3)) % modulus == 0:
                    count += 1
    return count


def test_triples_checked_matches_independent_count():
    for k in range(-20, 21):
        for bound in (0, 3, 6):
            instance = SearchInstance(k, bound)
            for modulus in (1, 7, 9, 63, 819):
                assert modular_search(instance, modulus).triples_checked == (
                    _independent_count(k, bound, modulus)
                )


def test_modulus_one_checks_every_canonical_triple():
    for k in range(-12, 13):
        if k % 9 not in {4, 5}:
            for bound in (0, 1, 5, 8):
                result = modular_search(SearchInstance(k, bound), 1)
                assert result.triples_checked == comb(2 * bound + 3, 3)


@pytest.mark.parametrize("k", [-14, -13, -5, -4, 4, 5, 13, 14])
def test_mod_nine_exclusion_checks_no_triples(k):
    assert k % 9 in {4, 5}
    for modulus in MODULI:
        result = modular_search(SearchInstance(k, 8), modulus)
        assert result.solutions == ()
        assert result.triples_checked == 0


def test_divisible_moduli_never_increase_work():
    for k in range(-30, 31):
        instance = SearchInstance(k, 8)
        for chain in ((1, 3, 9, 63, 819), (1, 7, 63)):
            counts = [
                modular_search(instance, modulus).triples_checked
                for modulus in chain
            ]
            assert all(left >= right for left, right in zip(counts, counts[1:]))


@pytest.mark.parametrize(
    ("modulus", "expected"),
    [(1, 6_234_627), (9, 901_453), (63, 131_307), (819, 11_043)],
)
def test_pinned_triples_checked_totals(modulus, expected):
    actual = sum(
        modular_search(SearchInstance(k, 30), modulus).triples_checked
        for k in range(-100, 101)
    )
    assert actual == expected


@pytest.mark.parametrize("modulus", [0, -1, MAX_MODULUS + 1])
@pytest.mark.parametrize("function", [cube_residues, cube_root_classes])
def test_residue_functions_reject_out_of_range_modulus(function, modulus):
    with pytest.raises(ValueError):
        function(modulus)


@pytest.mark.parametrize("modulus", [1.0, True])
@pytest.mark.parametrize("function", [cube_residues, cube_root_classes])
def test_residue_functions_reject_non_integer_modulus(function, modulus):
    with pytest.raises(TypeError):
        function(modulus)


@pytest.mark.parametrize("modulus", [0, -1, MAX_MODULUS + 1])
def test_search_rejects_out_of_range_modulus(modulus):
    with pytest.raises(ValueError):
        modular_search(SearchInstance(3, 5), modulus)


@pytest.mark.parametrize("modulus", [1.0, True])
def test_search_rejects_non_integer_modulus(modulus):
    with pytest.raises(TypeError):
        modular_search(SearchInstance(3, 5), modulus)


def test_search_rejects_non_instance_first():
    with pytest.raises(TypeError):
        modular_search((3, 5), 0)
