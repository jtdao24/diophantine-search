"""Command-line interface for three-cubes benchmarks."""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path
from typing import Any

from diophantine_search.bench.compare import compare_runs
from diophantine_search.bench.runner import (
    BenchmarkError,
    SUITES,
    SolverConfig,
    dump_run,
    load_run,
    run_suite,
)
from diophantine_search.families.three_cubes import SearchInstance
from diophantine_search.families.three_cubes_modular import DEFAULT_MODULUS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m diophantine_search.bench")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run a fixed benchmark suite")
    run.add_argument("--suite", required=True, choices=tuple(SUITES))
    run.add_argument("--repeats", type=int)
    run.add_argument("--output", type=Path)
    run.add_argument("--force", action="store_true")

    compare = commands.add_parser("compare", help="compare two result files")
    compare.add_argument("old", type=Path)
    compare.add_argument("new", type=Path)

    profile = commands.add_parser("profile", help="profile one solver call")
    profile.add_argument(
        "--solver",
        required=True,
        choices=("brute-force", "modular", "cube-root"),
    )
    profile.add_argument("--modulus", type=int)
    profile.add_argument("--k", required=True, type=int)
    profile.add_argument("--bound", required=True, type=int)
    profile.add_argument("--top", type=int, default=15)
    return parser


def _print_run(document: dict[str, Any]) -> None:
    print(
        f"{'solver':<22} {'k':>5} {'B':>6} {'mode':<5} "
        f"{'median ms':>10} {'min ms':>10} {'checked':>12} {'unit':<7}"
        .rstrip()
    )
    for record in document["results"]:
        print(
            f"{record['solver']:<22} {record['k']:>5} {record['bound']:>6} "
            f"{record['mode']:<5} {record['median_ns'] / 1_000_000:>10.3f} "
            f"{record['min_ns'] / 1_000_000:>10.3f} "
            f"{record['triples_checked']:>12} {record['count_unit']:<7}"
            .rstrip()
        )


def _run_command(
    parser: argparse.ArgumentParser, arguments: argparse.Namespace
) -> int:
    if arguments.repeats is not None and arguments.repeats < 1:
        parser.error("--repeats must be at least 1")
    if (
        arguments.output is not None
        and arguments.output.exists()
        and not arguments.force
    ):
        parser.error(f"output path already exists: {arguments.output}")

    started = time.perf_counter()
    try:
        document = run_suite(
            SUITES[arguments.suite],
            repeats=arguments.repeats,
        )
    except BenchmarkError as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - started

    _print_run(document)
    print(f"Total wall time: {elapsed:.3f} s")
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            dump_run(document), encoding="utf-8", newline="\n"
        )
    return 0


def _compare_command(arguments: argparse.Namespace) -> int:
    comparison = compare_runs(load_run(arguments.old), load_run(arguments.new))
    print(
        f"{'solver':<22} {'k':>5} {'B':>6} {'mode':<5} "
        f"{'old ms':>10} {'new ms':>10} {'speedup':>9}"
        .rstrip()
    )
    for match in comparison["matches"]:
        print(
            f"{match['solver']:<22} {match['k']:>5} {match['bound']:>6} "
            f"{match['mode']:<5} "
            f"{match['old_median_ns'] / 1_000_000:>10.3f} "
            f"{match['new_median_ns'] / 1_000_000:>10.3f} "
            f"{match['speedup']:>8.2f}x"
            .rstrip()
        )
    for key in comparison["only_in_old"]:
        print(f"warning: only in old: {key}")
    for key in comparison["only_in_new"]:
        print(f"warning: only in new: {key}")
    if comparison["environment_differences"]:
        differences = ", ".join(comparison["environment_differences"])
        print(f"warning: environment differences: {differences}")
    return 0


def _profile_command(
    parser: argparse.ArgumentParser, arguments: argparse.Namespace
) -> int:
    if arguments.top < 1:
        parser.error("--top must be at least 1")
    modulus = arguments.modulus
    if arguments.solver != "brute-force" and modulus is None:
        modulus = DEFAULT_MODULUS
    try:
        solver = SolverConfig(arguments.solver, modulus)
        instance = SearchInstance(arguments.k, arguments.bound)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    profiler = cProfile.Profile()
    profiler.enable()
    result = solver.run(instance)
    profiler.disable()
    pstats.Stats(profiler, stream=sys.stdout).sort_stats("tottime").print_stats(
        arguments.top
    )
    print(
        f"# k={instance.k} bound={instance.bound} "
        f"solutions={len(result.solutions)} "
        f"triples_checked={result.triples_checked}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark command-line interface."""

    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "run":
        return _run_command(parser, arguments)
    if arguments.command == "compare":
        return _compare_command(arguments)
    return _profile_command(parser, arguments)


if __name__ == "__main__":
    raise SystemExit(main())
