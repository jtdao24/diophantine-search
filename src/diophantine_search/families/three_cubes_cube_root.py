"""Exact cube-root row search using the lemmas in spec §9.

Canonical solutions satisfy proven bounds on x and y. Each surviving (x, y)
row determines at most one z, while a modular table removes rows whose remaining
value cannot be a cube.
"""

from collections.abc import Callable
from functools import lru_cache

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    Triple,
)
from diophantine_search.families.three_cubes_modular import (
    DEFAULT_MODULUS,
    MAX_MODULUS,
    cube_residues,
    is_excluded_mod_9,
)
from diophantine_search.intmath import exact_cube_root, icbrt_ceil, icbrt_floor

MAX_TABLE_ENTRIES = 5_000_000


def _require_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")


def _require_bound(bound: int) -> None:
    _require_int(bound, "bound")
    if bound < 0:
        raise ValueError("bound must be nonnegative")


@lru_cache(maxsize=32)
def y_class_table(modulus: int) -> tuple[tuple[int, ...], ...]:
    """Return y classes whose complementary residue can be a cube."""

    residues = cube_residues(modulus)
    if modulus * len(residues) > MAX_TABLE_ENTRIES:
        raise ValueError(
            f"y-class table exceeds {MAX_TABLE_ENTRIES} entries"
        )

    table: list[list[int]] = [[] for _ in range(modulus)]
    for c in range(modulus):
        c_cubed = c**3
        for cube_residue in residues:
            table[(c_cubed + cube_residue) % modulus].append(c)
    return tuple(tuple(sorted(entry)) for entry in table)


def x_upper(k: int, bound: int) -> int:
    """Return the proven inclusive upper bound for canonical x."""

    _require_int(k, "k")
    _require_bound(bound)
    return min(bound, icbrt_floor(k // 3))


def row_bounds(k: int, bound: int, x: int) -> tuple[int, int]:
    """Return the proven inclusive y bounds for a fixed x row."""

    _require_int(k, "k")
    _require_bound(bound)
    _require_int(x, "x")
    rest = k - x**3
    return (
        max(x, icbrt_ceil(rest - bound**3)),
        min(bound, icbrt_floor(rest // 2)),
    )


def _search_rows(
    instance: SearchInstance,
    modulus: int,
    y_classes: tuple[tuple[int, ...], ...],
    x_upper_fn: Callable[[int, int], int],
    row_bounds_fn: Callable[[int, int, int], tuple[int, int]],
) -> SearchResult:
    """Run the cube-root core loop with injected bounds and residue classes."""

    bound = instance.bound
    cubes = [value**3 for value in range(-bound, bound + 1)]
    solutions: list[Triple] = []
    triples_checked = 0

    for x in range(-bound, x_upper_fn(instance.k, bound) + 1):
        lo, hi = row_bounds_fn(instance.k, bound, x)
        if lo > hi:
            continue
        rest = instance.k - cubes[x + bound]
        candidates = []
        for y_class in y_classes[rest % modulus]:
            first_y = lo + (y_class - lo) % modulus
            candidates.extend(range(first_y, hi + 1, modulus))
        candidates.sort()
        for y in candidates:
            triples_checked += 1
            z = exact_cube_root(rest - cubes[y + bound])
            if z is not None and y <= z <= bound:
                solutions.append((x, y, z))

    return SearchResult(instance, tuple(solutions), triples_checked)


def cube_root_search(
    instance: SearchInstance,
    modulus: int = DEFAULT_MODULUS,
) -> SearchResult:
    """Search bounded canonical rows using exact integer cube roots."""

    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    y_classes = y_class_table(modulus)
    if is_excluded_mod_9(instance.k):
        return SearchResult(instance, (), 0)
    return _search_rows(instance, modulus, y_classes, x_upper, row_bounds)
