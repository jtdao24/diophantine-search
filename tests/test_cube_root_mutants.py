"""Prove conformance checks detect cube-root row-search defects."""

import pytest

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
)
from diophantine_search.families.three_cubes_cube_root import (
    _search_rows,
    row_bounds,
    x_upper,
    y_class_table,
)
from diophantine_search.families.three_cubes_modular import is_excluded_mod_9
from diophantine_search.testing.three_cubes_conformance import check_solver

MODULUS = 819
TABLE = y_class_table(MODULUS)
SHIFTED_TABLE = tuple(
    tuple((c + 1) % MODULUS for c in TABLE[s]) for s in range(MODULUS)
)


def _run(instance, table, x_upper_fn=x_upper, row_bounds_fn=row_bounds):
    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    if is_excluded_mod_9(instance.k):
        return SearchResult(instance, (), 0)
    return _search_rows(
        instance,
        MODULUS,
        table,
        x_upper_fn,
        row_bounds_fn,
    )


def correct_rows(instance):
    return _run(instance, TABLE)


def _hi_minus_one(k, bound, x):
    lo, hi = row_bounds(k, bound, x)
    return lo, hi - 1


def y_hi_minus_one(instance):
    return _run(instance, TABLE, row_bounds_fn=_hi_minus_one)


def _lo_plus_one(k, bound, x):
    lo, hi = row_bounds(k, bound, x)
    return lo + 1, hi


def y_lo_plus_one(instance):
    return _run(instance, TABLE, row_bounds_fn=_lo_plus_one)


def _x_hi_minus_one(k, bound):
    return x_upper(k, bound) - 1


def x_hi_minus_one(instance):
    return _run(instance, TABLE, x_upper_fn=_x_hi_minus_one)


def shifted_y_classes(instance):
    return _run(instance, SHIFTED_TABLE)


MUTANTS = {
    "y_hi_minus_one": y_hi_minus_one,
    "y_lo_plus_one": y_lo_plus_one,
    "x_hi_minus_one": x_hi_minus_one,
    "shifted_y_classes": shifted_y_classes,
}


@pytest.fixture(scope="session")
def fast_golden_only(golden_sets):
    return tuple(golden for golden in golden_sets if golden.name == "fast")


def test_correct_rows_pass_conformance(known_solutions, fast_golden_only):
    check_solver(correct_rows, known_solutions, fast_golden_only)


@pytest.mark.parametrize("mutant", tuple(MUTANTS.values()), ids=tuple(MUTANTS))
def test_cube_root_mutant_is_detected(
    mutant, known_solutions, fast_golden_only
):
    with pytest.raises((AssertionError, ValueError)):
        check_solver(mutant, known_solutions, fast_golden_only)
