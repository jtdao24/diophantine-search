"""Reusable conformance checks for three-cubes solvers."""

import random
from collections.abc import Callable, Iterable

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    Triple,
    canonicalize,
    in_domain,
    is_trivial,
    negate,
    sum_of_cubes,
    validate_result,
)
from diophantine_search.testing.three_cubes_golden import GoldenSet

Solver = Callable[[SearchInstance], SearchResult]


def _result(solver: Solver, instance: SearchInstance) -> SearchResult:
    try:
        result = solver(instance)
    except Exception as error:
        raise AssertionError(
            f"solver raised {type(error).__name__} for "
            f"k={instance.k} bound={instance.bound}"
        ) from error
    try:
        validate_result(result)
    except (TypeError, ValueError) as error:
        raise AssertionError(
            f"invalid result for k={instance.k} bound={instance.bound}: {error}"
        ) from error
    assert result.instance == instance, (
        f"wrong instance for k={instance.k} bound={instance.bound}"
    )
    return result


def check_rejects_non_instance(solver: Solver) -> None:
    """Check that the solver rejects a raw ``(k, bound)`` tuple."""

    try:
        result = solver((3, 5))
    except TypeError:
        return
    except Exception as error:
        raise AssertionError(
            f"wrong exception for k=3 bound=5: {type(error).__name__}"
        ) from error
    try:
        validate_result(result)
    except (TypeError, ValueError) as error:
        raise AssertionError(f"invalid result for k=3 bound=5: {error}") from error
    raise AssertionError("solver accepted a non-instance for k=3 bound=5")


def check_known_solutions(
    solver: Solver,
    known: Iterable[tuple[int, Triple]],
    max_bound: int = 30,
) -> None:
    """Check that in-range published solutions are found."""

    for k, triple in known:
        bound = max(abs(value) for value in triple)
        if bound <= max_bound:
            instance = SearchInstance(k, bound)
            result = _result(solver, instance)
            expected = canonicalize(triple)
            assert expected in result.solutions, (
                f"missing known solution for k={k} bound={bound}: {expected}"
            )


def check_planted(
    solver: Solver,
    *,
    seed: int = 20260924,
    count: int = 200,
    max_bound: int = 30,
) -> None:
    """Plant random triples and require the solver to recover them."""

    rng = random.Random(seed)
    for _ in range(count):
        bound = rng.randint(0, max_bound)
        triple = tuple(rng.randint(-bound, bound) for _ in range(3))
        k = sum_of_cubes(triple)
        instance = SearchInstance(k, bound)
        result = _result(solver, instance)
        expected = canonicalize(triple)
        assert expected in result.solutions, (
            f"missing planted solution for k={k} bound={bound}: {expected}"
        )


def _sample_k(rng: random.Random, index: int, bound: int) -> int:
    if index % 2 == 0:
        triple = tuple(rng.randint(-bound, bound) for _ in range(3))
        return sum_of_cubes(triple)
    limit = 3 * bound**3
    return rng.randint(-limit, limit)


def check_negation(
    solver: Solver,
    *,
    seed: int = 20260925,
    count: int = 100,
    max_bound: int = 12,
) -> None:
    """Check the solution-set symmetry between k and -k."""

    rng = random.Random(seed)
    for index in range(count):
        bound = rng.randint(0, max_bound)
        k = _sample_k(rng, index, bound)
        result = _result(solver, SearchInstance(k, bound))
        negated = _result(solver, SearchInstance(-k, bound))
        expected = tuple(sorted(negate(triple) for triple in result.solutions))
        assert negated.solutions == expected, (
            f"negation mismatch for k={k} bound={bound}"
        )


def check_bound_monotonicity(
    solver: Solver,
    *,
    seed: int = 20260926,
    count: int = 100,
    max_bound: int = 12,
) -> None:
    """Check that increasing the bound only adds boundary solutions."""

    rng = random.Random(seed)
    for index in range(count):
        bound = rng.randint(0, max_bound)
        k = _sample_k(rng, index, bound)
        result = _result(solver, SearchInstance(k, bound))
        larger = _result(solver, SearchInstance(k, bound + 1))
        restricted = tuple(
            triple
            for triple in larger.solutions
            if in_domain(triple, bound)
        )
        assert result.solutions == restricted, (
            f"bound mismatch for k={k} bound={bound}"
        )


def check_trivial_counts(solver: Solver, *, max_bound: int = 8) -> None:
    """Check the exact count of trivial solutions for cube and non-cube k."""

    candidates = set(range(-300, 301))
    candidates.update(n**3 for n in range(-12, 13))
    for bound in range(max_bound + 1):
        in_range_cubes = {n**3 for n in range(-bound, bound + 1)}
        for k in sorted(candidates):
            result = _result(solver, SearchInstance(k, bound))
            actual = sum(is_trivial(triple) for triple in result.solutions)
            expected = bound + 1 if k in in_range_cubes else 0
            assert actual == expected, (
                f"trivial count mismatch for k={k} bound={bound}: "
                f"expected {expected}, got {actual}"
            )


def check_golden(solver: Solver, golden: GoldenSet) -> None:
    """Compare every k in a golden set with a solver result."""

    for k in range(golden.k_min, golden.k_max + 1):
        instance = SearchInstance(k, golden.bound)
        result = _result(solver, instance)
        assert result.solutions == golden.results[k], (
            f"golden mismatch for k={k} bound={golden.bound}"
        )


def check_solver(
    solver: Solver,
    known: Iterable[tuple[int, Triple]],
    golden_sets: Iterable[GoldenSet],
) -> None:
    """Run all conformance checks, cheapest first and golden sets last."""

    check_rejects_non_instance(solver)
    check_known_solutions(solver, known)
    check_planted(solver)
    check_negation(solver)
    check_bound_monotonicity(solver)
    check_trivial_counts(solver)
    for golden in golden_sets:
        check_golden(solver, golden)
