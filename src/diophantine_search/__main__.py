"""Command-line entry point for Diophantine searches."""

import argparse

from diophantine_search.families.three_cubes import SearchInstance, is_trivial
from diophantine_search.families.three_cubes_brute_force import brute_force_search
from diophantine_search.families.three_cubes_cube_root import (
    cube_root_search,
    y_class_table,
)
from diophantine_search.families.three_cubes_modular import (
    DEFAULT_MODULUS,
    MAX_MODULUS,
    modular_search,
)


def main(argv: list[str] | None = None) -> int:
    """Run a search selected from the command line."""

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="family", required=True)
    three_cubes = subparsers.add_parser("three-cubes")
    three_cubes.add_argument("--k", type=int, required=True)
    three_cubes.add_argument("--bound", type=int, required=True)
    three_cubes.add_argument(
        "--solver",
        choices=("brute-force", "modular", "cube-root"),
        default="brute-force",
    )
    three_cubes.add_argument("--modulus", type=int, default=None)

    args = parser.parse_args(argv)
    if args.bound < 0:
        parser.error("--bound must be nonnegative")

    instance = SearchInstance(args.k, args.bound)
    if args.solver == "brute-force":
        if args.modulus is not None:
            parser.error("--modulus requires --solver modular or cube-root")
        result = brute_force_search(instance)
    elif args.solver == "modular":
        modulus = DEFAULT_MODULUS if args.modulus is None else args.modulus
        if not 1 <= modulus <= MAX_MODULUS:
            parser.error(f"--modulus must be in [1, {MAX_MODULUS}]")
        result = modular_search(instance, modulus)
    else:
        modulus = DEFAULT_MODULUS if args.modulus is None else args.modulus
        try:
            y_class_table(modulus)
        except (TypeError, ValueError) as error:
            parser.error(str(error))
        result = cube_root_search(instance, modulus)
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
