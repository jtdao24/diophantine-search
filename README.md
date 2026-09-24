# diophantine-search

A computational number theory engine for finding integer solutions to hard
polynomial equations, starting with sums of three cubes:

    x³ + y³ + z³ = k,    x, y, z, k ∈ ℤ

The project is built for correctness first. Every solver must return exactly
the same solutions as a brute-force reference search. Every speedup must be
backed by a mathematical argument and a reproducible benchmark.

## Current status

- Exact definitions: solution checking, sorted (canonical) form, trivial
  solutions, and negation symmetry.
- A brute-force reference search over the box `max(|x|, |y|, |z|) ≤ B`.
- A command-line tool.

The full correctness contract is in [docs/three-cubes-spec.md](docs/three-cubes-spec.md).

## Setup

Requires Python 3.11+. No runtime dependencies.

```text
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -e . pytest
```

## Usage

```text
$ python -m diophantine_search three-cubes --k 3 --bound 5
-5 4 4
1 1 1
# k=3 bound=5 solutions=2 triples_checked=286
```

Each solution is printed once, in ascending order. Solutions where two
coordinates cancel (only possible when k is a perfect cube) are marked
`trivial`. The last line summarizes the search, including how many candidate
triples were checked.

## Tests

```text
python -m pytest
```

## Layout

```text
docs/three-cubes-spec.md                    correctness contract
src/diophantine_search/families/
    three_cubes.py                          definitions and result types
    three_cubes_brute_force.py              reference search
src/diophantine_search/__main__.py          command-line tool
tests/data/three_cubes_known.json           verified known solutions
tests/                                      test suite
```
