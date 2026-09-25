"""Core definitions for the sum of three cubes; see the three-cubes spec."""

from dataclasses import dataclass
from math import comb

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


@dataclass(frozen=True)
class SearchResult:
    """A search result; see spec §3.

    triples_checked measures search-space size for comparing later pruning
    strategies; it is not a timing measure.
    """

    instance: SearchInstance
    solutions: tuple[Triple, ...]
    triples_checked: int


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


def validate_result(result: SearchResult) -> None:
    """Check result soundness without trusting its solver; see spec §3."""

    if not isinstance(result, SearchResult):
        raise TypeError("result must be a SearchResult")
    if not isinstance(result.instance, SearchInstance):
        raise TypeError("result.instance must be a SearchInstance")
    if not isinstance(result.solutions, tuple):
        raise TypeError("result.solutions must be a tuple")

    maximum = comb(2 * result.instance.bound + 3, 3)
    if (
        not isinstance(result.triples_checked, int)
        or isinstance(result.triples_checked, bool)
        or not 0 <= result.triples_checked <= maximum
    ):
        raise ValueError(
            f"triples_checked must be an int in [0, {maximum}]"
        )

    previous: Triple | None = None
    for triple in result.solutions:
        try:
            _triple(triple)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid solution {triple!r}: {error}") from error

        normalized = tuple(triple)
        if not is_canonical(normalized):
            raise ValueError(f"solution {triple!r} is not canonical")
        if not in_domain(normalized, result.instance.bound):
            raise ValueError(f"solution {triple!r} is outside the domain")
        if not is_solution(result.instance.k, normalized):
            raise ValueError(f"solution {triple!r} has the wrong cube sum")
        if previous is not None and normalized <= previous:
            raise ValueError(
                f"solution {triple!r} is not strictly increasing"
            )
        previous = normalized
