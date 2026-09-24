"""Core definitions for the sum of three cubes; see the three-cubes spec."""

from dataclasses import dataclass

Triple = tuple[int, int, int]


def _integer(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int, not bool or another type")


def _bound(value: int) -> None:
    _integer(value, "bound")
    if value < 0:
        raise ValueError("bound must be nonnegative")


def _triple(t: Triple) -> None:
    if len(t) != 3:
        raise ValueError("triple must have length 3")
    _integer(t[0], "triple element")
    _integer(t[1], "triple element")
    _integer(t[2], "triple element")


@dataclass(frozen=True)
class SearchInstance:
    """A search instance (k, B); see spec §1."""

    k: int
    bound: int

    def __post_init__(self) -> None:
        _integer(self.k, "k")
        _bound(self.bound)


def sum_of_cubes(t: Triple) -> int:
    """Compute the exact cube sum; see spec §2."""

    _triple(t)
    x, y, z = t
    return x**3 + y**3 + z**3


def is_solution(k: int, t: Triple) -> bool:
    """Check the equation exactly; see spec §2."""

    _integer(k, "k")
    return sum_of_cubes(t) == k


def in_domain(t: Triple, bound: int) -> bool:
    """Check membership in D(B); see spec §1."""

    _triple(t)
    _bound(bound)
    return max(abs(t[0]), abs(t[1]), abs(t[2])) <= bound


def canonicalize(t: Triple) -> Triple:
    """Sort a triple into canonical order; see spec §2."""

    _triple(t)
    return tuple(sorted(t))


def is_canonical(t: Triple) -> bool:
    """Check ascending canonical order; see spec §2."""

    _triple(t)
    return t[0] <= t[1] <= t[2]


def is_trivial(t: Triple) -> bool:
    """Check for an opposite pair; see spec §2."""

    _triple(t)
    x, y, z = t
    return x + y == 0 or x + z == 0 or y + z == 0


def orbit_size(t: Triple) -> int:
    """Count distinct coordinate permutations; see spec §2."""

    _triple(t)
    return {1: 1, 2: 3, 3: 6}[len(set(t))]


def negate(t: Triple) -> Triple:
    """Negate and reverse coordinates; see spec §2."""

    _triple(t)
    x, y, z = t
    return -z, -y, -x