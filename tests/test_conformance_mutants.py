"""Prove that the conformance suite detects representative solver defects."""

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    is_trivial,
)
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.testing.three_cubes_conformance import check_solver


def _with_solutions(instance, result, solutions):
    return SearchResult(instance, tuple(solutions), result.triples_checked)


def drop_boundary(instance):
    result = brute_force_search(instance)
    return _with_solutions(
        instance,
        result,
        (
            triple
            for triple in result.solutions
            if max(abs(value) for value in triple) != instance.bound
        ),
    )


def drop_trivial(instance):
    result = brute_force_search(instance)
    return _with_solutions(
        instance,
        result,
        (triple for triple in result.solutions if not is_trivial(triple)),
    )


def reversed_order(instance):
    result = brute_force_search(instance)
    return _with_solutions(instance, result, reversed(result.solutions))


def extra_invalid(instance):
    result = brute_force_search(instance)
    solutions = result.solutions
    if instance.k != 0:
        solutions += ((0, 0, 0),)
    return _with_solutions(instance, result, solutions)


def ignores_sign(instance):
    result = brute_force_search(SearchInstance(abs(instance.k), instance.bound))
    return _with_solutions(instance, result, result.solutions)


def off_by_one_bound(instance):
    reduced = SearchInstance(instance.k, max(instance.bound - 1, 0))
    result = brute_force_search(reduced)
    return _with_solutions(instance, result, result.solutions)


MUTANTS = {
    "drop_boundary": drop_boundary,
    "drop_trivial": drop_trivial,
    "reversed_order": reversed_order,
    "extra_invalid": extra_invalid,
    "ignores_sign": ignores_sign,
    "off_by_one_bound": off_by_one_bound,
}


@pytest.fixture(scope="session")
def golden_sets_fast_only(golden_sets):
    return tuple(golden for golden in golden_sets if golden.name == "fast")


def test_brute_force_passes_full_suite(
    known_solutions, golden_sets_fast_only
):
    check_solver(
        brute_force_search,
        known_solutions,
        golden_sets_fast_only,
    )


@pytest.mark.parametrize("mutant", tuple(MUTANTS.values()), ids=tuple(MUTANTS))
def test_mutant_is_detected(mutant, known_solutions, golden_sets_fast_only):
    with pytest.raises((AssertionError, ValueError)):
        check_solver(mutant, known_solutions, golden_sets_fast_only)
