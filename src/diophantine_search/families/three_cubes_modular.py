"""Modular pruning for three cubes using the lemma in spec §8.

If ``x³ + y³ + z³ = k``, then ``z³`` lies in the residue class
``k - x³ - y³`` modulo every positive modulus. Therefore only cube-root
classes for that residue can contain a solution.
"""

from functools import lru_cache

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    Triple,
)

DEFAULT_MODULUS = 819
MAX_MODULUS = 100_000


def _validate_modulus(modulus: int) -> None:
    if not isinstance(modulus, int) or isinstance(modulus, bool):
        raise TypeError("modulus must be an int")
    if not 1 <= modulus <= MAX_MODULUS:
        raise ValueError(f"modulus must be in [1, {MAX_MODULUS}]")


def cube_residues(modulus: int) -> frozenset[int]:
    """Return all cube residues for a validated positive modulus."""

    _validate_modulus(modulus)
    return frozenset(c**3 % modulus for c in range(modulus))


@lru_cache(maxsize=32)
def cube_root_classes(modulus: int) -> tuple[tuple[int, ...], ...]:
    """Return the sorted cube-root classes indexed by residue."""

    _validate_modulus(modulus)
    classes: list[list[int]] = [[] for _ in range(modulus)]
    for c in range(modulus):
        classes[c**3 % modulus].append(c)
    return tuple(tuple(class_members) for class_members in classes)


def is_excluded_mod_9(k: int) -> bool:
    """Return whether k is impossible for a sum of three cubes modulo 9."""

    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an int")
    return k % 9 in {4, 5}


def _search_with_classes(
    instance: SearchInstance,
    modulus: int,
    classes: tuple[tuple[int, ...], ...],
) -> SearchResult:
    """Run the modular core loop with supplied cube-root classes."""

    bound = instance.bound
    cubes = [value**3 for value in range(-bound, bound + 1)]
    residues = [cube % modulus for cube in cubes]
    solutions: list[Triple] = []
    triples_checked = 0

    for x in range(-bound, bound + 1):
        x_index = x + bound
        x_cubed = cubes[x_index]
        x_residue = residues[x_index]
        for y in range(x, bound + 1):
            y_index = y + bound
            residue = (instance.k - x_residue - residues[y_index]) % modulus
            row_hits: list[Triple] = []
            for cube_class in classes[residue]:
                first_z = y + (cube_class - y) % modulus
                for z in range(first_z, bound + 1, modulus):
                    triples_checked += 1
                    if x_cubed + cubes[y_index] + cubes[z + bound] == instance.k:
                        row_hits.append((x, y, z))
            row_hits.sort(key=lambda triple: triple[2])
            solutions.extend(row_hits)

    return SearchResult(instance, tuple(solutions), triples_checked)


def modular_search(
    instance: SearchInstance,
    modulus: int = DEFAULT_MODULUS,
) -> SearchResult:
    """Search all modularly admissible canonical triples exactly."""

    if not isinstance(instance, SearchInstance):
        raise TypeError("instance must be a SearchInstance")
    _validate_modulus(modulus)
    if is_excluded_mod_9(instance.k):
        return SearchResult(instance, (), 0)
    return _search_with_classes(instance, modulus, cube_root_classes(modulus))
