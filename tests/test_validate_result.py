"""Tests for solver-independent SearchResult validation."""

from math import comb

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    validate_result,
)
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)


def test_brute_force_results_validate():
    for instance in (SearchInstance(0, 0), SearchInstance(3, 5), SearchInstance(2, 7)):
        assert validate_result(brute_force_search(instance)) is None


@pytest.mark.parametrize(
    ("instance", "solutions", "offending"),
    [
        (SearchInstance(1, 1), ((1, 0, 0),), (1, 0, 0)),
        (SearchInstance(0, 1), ((-2, 0, 2),), (-2, 0, 2)),
        (SearchInstance(1, 1), ((0, 0, 0),), (0, 0, 0)),
        (SearchInstance(1, 1), ((0, 0, 1), (0, 0, 1)), (0, 0, 1)),
        (SearchInstance(3, 5), ((1, 1, 1), (-5, 4, 4)), (-5, 4, 4)),
    ],
)
def test_bad_solution_entries_raise_value_error(instance, solutions, offending):
    result = SearchResult(instance, solutions, 0)
    with pytest.raises(ValueError, match="solution") as error:
        validate_result(result)
    assert repr(offending) in str(error.value)


@pytest.mark.parametrize("triples_checked", [-1, True])
def test_bad_triples_checked_raises_value_error(triples_checked):
    result = SearchResult(SearchInstance(0, 1), (), triples_checked)
    with pytest.raises(ValueError, match="triples_checked"):
        validate_result(result)


def test_too_many_triples_checked_raises_value_error():
    instance = SearchInstance(0, 1)
    maximum = comb(2 * instance.bound + 3, 3)
    with pytest.raises(ValueError, match="triples_checked"):
        validate_result(SearchResult(instance, (), maximum + 1))


def test_solutions_must_be_a_tuple():
    with pytest.raises(TypeError, match="solutions"):
        validate_result(SearchResult(SearchInstance(0, 0), [], 0))


def test_result_must_be_a_search_result():
    with pytest.raises(TypeError, match="SearchResult"):
        validate_result(None)
