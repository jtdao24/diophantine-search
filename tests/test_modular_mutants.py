"""Prove conformance checks detect modular residue-class defects."""

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
)
from diophantine_search.families.three_cubes_modular import (
    _search_with_classes,
    cube_root_classes,
    is_excluded_mod_9,
    modular_search,
)
from diophantine_search.testing.three_cubes_conformance import check_solver

MODULUS = 819
CLASSES = cube_root_classes(MODULUS)
MISSING_CLASS = tuple(
    members[:-1] if len(members) > 1 else members for members in CLASSES
)
NEGATED_RESIDUE = tuple(
    CLASSES[(-residue) % MODULUS] for residue in range(MODULUS)
)
SHIFTED_CLASSES = tuple(
    tuple((c + 1) % MODULUS for c in CLASSES[residue])
    for residue in range(MODULUS)
)


def _search(instance, classes):
    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    if is_excluded_mod_9(instance.k):
        return SearchResult(instance, (), 0)
    return _search_with_classes(instance, MODULUS, classes)


def correct_classes(instance):
    return _search(instance, CLASSES)


def missing_class(instance):
    return _search(instance, MISSING_CLASS)


def negated_residue(instance):
    return _search(instance, NEGATED_RESIDUE)


def shifted_classes(instance):
    return _search(instance, SHIFTED_CLASSES)


def wrong_exclusion(instance):
    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    if instance.k % 9 == 3:
        return SearchResult(instance, (), 0)
    return modular_search(instance)


MUTANTS = {
    "missing_class": missing_class,
    "negated_residue": negated_residue,
    "shifted_classes": shifted_classes,
    "wrong_exclusion": wrong_exclusion,
}


@pytest.fixture(scope="session")
def fast_golden_only(golden_sets):
    return tuple(golden for golden in golden_sets if golden.name == "fast")


def test_correct_classes_pass_conformance(known_solutions, fast_golden_only):
    check_solver(correct_classes, known_solutions, fast_golden_only)


@pytest.mark.parametrize("mutant", tuple(MUTANTS.values()), ids=tuple(MUTANTS))
def test_modular_mutant_is_detected(mutant, known_solutions, fast_golden_only):
    with pytest.raises((AssertionError, ValueError)):
        check_solver(mutant, known_solutions, fast_golden_only)
