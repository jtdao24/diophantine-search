"""Command-line entry point for Diophantine searches."""

import argparse

from diophantine_search.families.three_cubes import SearchInstance, is_trivial
from diophantine_search.families.three_cubes_brute_force import brute_force_search


def main(argv: list[str] | None = None) -> int:
    """Run a search selected from the command line."""

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="family", required=True)
    three_cubes = subparsers.add_parser("three-cubes")
    three_cubes.add_argument("--k", type=int, required=True)
    three_cubes.add_argument("--bound", type=int, required=True)

    args = parser.parse_args(argv)
    if args.bound < 0:
        parser.error("--bound must be nonnegative")

    result = brute_force_search(SearchInstance(args.k, args.bound))
    for triple in result.solutions:
        suffix = " trivial" if is_trivial(triple) else ""
        print(*triple, end=f"{suffix}\n")

    print(
        f"# k={args.k} bound={args.bound} "
        f"solutions={len(result.solutions)} "
        f"triples_checked={result.triples_checked}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
