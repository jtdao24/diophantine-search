"""Unoptimized reference oracle for the sum of three cubes.

This search must not be optimized further. Future solvers must return identical
``SearchResult.solutions``.
"""

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    Triple,
)


def brute_force_search(instance: SearchInstance) -> SearchResult:
    """Evaluate every canonical triple in the domain exactly once."""

    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")

    bound = instance.bound
    cubes = [value**3 for value in range(-bound, bound + 1)]
    solutions: list[Triple] = []
    triples_checked = 0

    for x in range(-bound, bound + 1):
        x_cubed = cubes[x + bound]
        for y in range(x, bound + 1):
            triples_checked += bound - y + 1
            xy_sum = x_cubed + cubes[y + bound]
            for z in range(y, bound + 1):
                if xy_sum + cubes[z + bound] == instance.k:
                    solutions.append((x, y, z))

    return SearchResult(instance, tuple(solutions), triples_checked)
