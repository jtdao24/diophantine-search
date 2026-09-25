"""Apply each reusable conformance check to every accepted solver."""

import pytest

from diophantine_search.testing.three_cubes_conformance import (
    check_bound_monotonicity,
    check_golden,
    check_known_solutions,
    check_negation,
    check_planted,
    check_rejects_non_instance,
    check_trivial_counts,
)


def _golden(golden_sets, name):
    return next(golden for golden in golden_sets if golden.name == name)


def test_rejects_non_instance(solver):
    check_rejects_non_instance(solver)


def test_known_solutions(solver, known_solutions):
    check_known_solutions(solver, known_solutions)


def test_planted(solver):
    check_planted(solver)


def test_negation(solver):
    check_negation(solver)


def test_bound_monotonicity(solver):
    check_bound_monotonicity(solver)


def test_trivial_counts(solver):
    check_trivial_counts(solver)


def test_golden_fast(solver, golden_sets):
    check_golden(solver, _golden(golden_sets, "fast"))


@pytest.mark.slow
def test_golden_wide(solver, golden_sets):
    check_golden(solver, _golden(golden_sets, "wide"))


@pytest.mark.slow
def test_golden_slow(solver, golden_sets):
    check_golden(solver, _golden(golden_sets, "slow"))
