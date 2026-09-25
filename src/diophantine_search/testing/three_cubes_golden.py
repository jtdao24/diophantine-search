"""Generate and load independent golden data for three-cubes solvers."""

import argparse
import json
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Iterable

from diophantine_search.families.three_cubes import Triple


@dataclass(frozen=True)
class GoldenSet:
    """Expected solutions for every k in an inclusive range."""

    name: str
    bound: int
    k_min: int
    k_max: int
    results: dict[int, tuple[Triple, ...]]


GOLDEN_SPECS = (
    ("fast", 30, -100, 100),
    ("wide", 30, -1000, 1000),
    ("slow", 100, -100, 100),
)


def _require_int(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")


def independent_solution_table(
    bound: int, k_min: int, k_max: int
) -> dict[int, tuple[Triple, ...]]:
    """Enumerate ordered triples independently and canonicalize the matches."""

    _require_int(bound, "bound")
    _require_int(k_min, "k_min")
    _require_int(k_max, "k_max")
    if bound < 0:
        raise ValueError("bound must be nonnegative")
    if k_min > k_max:
        raise ValueError("k_min must be at most k_max")

    matches: dict[int, set[Triple]] = {
        k: set() for k in range(k_min, k_max + 1)
    }
    values = range(-bound, bound + 1)
    cubes = {value: value**3 for value in values}
    for triple in product(values, repeat=3):
        x, y, z = triple
        k = cubes[x] + cubes[y] + cubes[z]
        if k_min <= k <= k_max:
            matches[k].add(tuple(sorted(triple)))

    return {k: tuple(sorted(matches[k])) for k in range(k_min, k_max + 1)}


def build_golden_sets(specs=GOLDEN_SPECS) -> tuple[GoldenSet, ...]:
    """Build independent golden sets from ``(name, bound, k_min, k_max)`` specs."""

    return tuple(
        GoldenSet(
            name=name,
            bound=bound,
            k_min=k_min,
            k_max=k_max,
            results=independent_solution_table(bound, k_min, k_max),
        )
        for name, bound, k_min, k_max in specs
    )


def render_golden(sets: Iterable[GoldenSet]) -> str:
    """Render golden sets as deterministic UTF-8 JSON with one result per line."""

    golden_sets = tuple(sets)
    lines = [
        "{",
        '  "family": "three_cubes",',
        '  "format_version": "1",',
        '  "method": "ordered enumeration of D(B), canonicalize, deduplicate",',
        '  "sets": [',
    ]
    for set_index, golden in enumerate(golden_sets):
        lines.extend(
            [
                "    {",
                f'      "name": {json.dumps(golden.name, ensure_ascii=False)},',
                f'      "bound": "{golden.bound}",',
                f'      "k_min": "{golden.k_min}",',
                f'      "k_max": "{golden.k_max}",',
                '      "results": [',
            ]
        )
        for k in range(golden.k_min, golden.k_max + 1):
            record = {
                "k": str(k),
                "solutions": [
                    [str(value) for value in triple]
                    for triple in golden.results[k]
                ],
            }
            suffix = "," if k < golden.k_max else ""
            lines.append(
                "        "
                + json.dumps(record, ensure_ascii=False, separators=(", ", ": "))
                + suffix
            )
        set_suffix = "," if set_index + 1 < len(golden_sets) else ""
        lines.extend(["      ]", f"    }}{set_suffix}"])
    lines.extend(["  ]", "}"])
    return "\n".join(lines) + "\n"


def _require_keys(mapping, keys, location: str) -> None:
    if not isinstance(mapping, dict) or not keys <= mapping.keys():
        missing = sorted(keys - mapping.keys()) if isinstance(mapping, dict) else keys
        raise ValueError(f"missing keys in {location}: {missing}")


def _parse_decimal(value, location: str) -> int:
    if not isinstance(value, str):
        raise ValueError(f"{location} must be a decimal string")
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{location} must be a decimal string") from error
    if str(parsed) != value:
        raise ValueError(f"{location} must be a canonical decimal string")
    return parsed


def load_golden(path) -> tuple[GoldenSet, ...]:
    """Load golden data and validate its format and complete k coverage."""

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid golden file: {error}") from error

    _require_keys(
        data,
        {"family", "format_version", "method", "sets"},
        "golden file",
    )
    if data["family"] != "three_cubes":
        raise ValueError("wrong golden family")
    if data["format_version"] != "1":
        raise ValueError("wrong golden format_version")
    if not isinstance(data["sets"], list):
        raise ValueError("golden sets must be a list")

    loaded = []
    set_keys = {"name", "bound", "k_min", "k_max", "results"}
    result_keys = {"k", "solutions"}
    for set_index, raw_set in enumerate(data["sets"]):
        location = f"set {set_index}"
        _require_keys(raw_set, set_keys, location)
        if not isinstance(raw_set["name"], str):
            raise ValueError(f"{location} name must be a string")
        bound = _parse_decimal(raw_set["bound"], f"{location} bound")
        k_min = _parse_decimal(raw_set["k_min"], f"{location} k_min")
        k_max = _parse_decimal(raw_set["k_max"], f"{location} k_max")
        if bound < 0 or k_min > k_max:
            raise ValueError(f"invalid range in {location}")
        if not isinstance(raw_set["results"], list):
            raise ValueError(f"{location} results must be a list")

        observed = []
        results = {}
        for result_index, raw_result in enumerate(raw_set["results"]):
            result_location = f"{location} result {result_index}"
            _require_keys(raw_result, result_keys, result_location)
            k = _parse_decimal(raw_result["k"], f"{result_location} k")
            if not isinstance(raw_result["solutions"], list):
                raise ValueError(f"{result_location} solutions must be a list")
            triples = []
            for solution_index, raw_triple in enumerate(raw_result["solutions"]):
                triple_location = (
                    f"{result_location} solution {solution_index}"
                )
                if not isinstance(raw_triple, list) or len(raw_triple) != 3:
                    raise ValueError(f"{triple_location} must have three values")
                triples.append(
                    tuple(
                        _parse_decimal(value, triple_location)
                        for value in raw_triple
                    )
                )
            observed.append(k)
            results[k] = tuple(triples)

        expected = list(range(k_min, k_max + 1))
        if observed != expected:
            raise ValueError(
                f"{location} must list every k exactly once in ascending order"
            )
        loaded.append(
            GoldenSet(raw_set["name"], bound, k_min, k_max, results)
        )
    return tuple(loaded)


def main(argv: list[str] | None = None) -> int:
    """Generate all configured golden sets at the requested output path."""

    parser = argparse.ArgumentParser()
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args(argv)
    with args.output_path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(render_golden(build_golden_sets()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
