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
- A modular-pruning solver that skips triples ruled out by cube residues
  (default modulus 819 = 7·9·13). On the default test range it checks about
  0.14% of the brute-force triples and returns exactly the same solutions.
- A cube-root row solver: for each (x, y) pair within proven bounds, it
  computes the only possible z with an exact integer cube root, and uses cube
  residues to skip pairs that cannot work. This takes the search from order
  B³ candidate triples to order B² candidate rows.
- A native C++ version of the cube-root row solver, called from Python. It
  returns the same solutions as the Python version, and the same row counts at
  the same modulus. It can split one search across threads, and its results do
  not depend on the thread count.
- A conformance suite that any solver must pass, backed by independently
  generated golden data and mutant solvers that prove the checks catch bugs.
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

### Building the native solver (optional)

Everything else works without this step; the native tests are skipped if the
library has not been built. It needs CMake and a C++20 compiler.

```text
cmake -S native -B build/native -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++
cmake --build build/native
```

To make a missing library a test failure instead of a skip, set
`DIOPHANTINE_REQUIRE_NATIVE=1`. To use a library somewhere else, set
`DIOPHANTINE_NATIVE_LIB` to its path.

An optional stress program compares thread counts directly, without Python:

```text
cmake -S native -B build/stress -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ -DDS_BUILD_STRESS=ON
cmake --build build/stress
build/stress/stress_three_cubes
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

Choose a solver with `--solver`. All solvers return exactly the same
solutions:

| Solver | What it does | `--modulus` |
|---|---|---|
| `brute-force` (default) | Checks every sorted triple in the box | not allowed |
| `modular` | Skips triples ruled out by cube residues | 1 to 100,000, default 819 |
| `cube-root` | Solves for z in each surviving (x, y) row | 1 to 100,000, default 819 |
| `native` | The same row search in C++ (must be built first) | 1 to 100,000, default 15561 |

```text
$ python -m diophantine_search three-cubes --k 3 --bound 5 --solver modular
-5 4 4
1 1 1
# k=3 bound=5 solutions=2 triples_checked=2

$ python -m diophantine_search three-cubes --k 29 --bound 1000 --solver cube-root
-233 -69 235
-20 13 18
-3 -2 4
1 1 3
# k=29 bound=1000 solutions=4 triples_checked=58493
```

For the `cube-root` and `native` solvers, `triples_checked` counts candidate
(x, y) rows, each with one exact cube test. Compare solvers by time, not by
this count.

Some moduli make these two solvers build a large lookup table the first time
they are used; the table size is capped, and moduli that would exceed the cap
are rejected.

The `native` solver uses 64-bit integers, so it requires
`|k| + 3B³ ≤ 2⁶³ − 1`, which means B ≤ 1,454,083. Anything outside that range is
an error, never a wrong answer.

The `native` solver runs on one thread unless you add `--threads N` (1 to 256).
Solutions, their order, and `triples_checked` are the same at any thread count.
Starting threads has a cost, so small searches can be slower with many threads:

```text
$ python -m diophantine_search three-cubes --k 29 --bound 1000 --solver native --threads 8
-233 -69 235
-20 13 18
-3 -2 4
1 1 3
# k=29 bound=1000 solutions=4 triples_checked=18011
```

The pruning rules and their proofs are in sections 8 to 11 of the
[spec](docs/three-cubes-spec.md).

## Tests

```text
python -m pytest              # default suite, a few seconds
python -m pytest -m slow      # slow tier only (larger golden sets), under a minute
python -m pytest -m ""        # everything
```

### Conformance

Every solver is checked against golden data: the exact solution set for every
k in a range, generated by an independent enumeration that shares no code
with the solvers. It also must pass property checks: planted solutions,
negation symmetry, monotonicity in B, and exact trivial-solution counts. See
section 7 of the [spec](docs/three-cubes-spec.md).

To test a new solver, add it to `SOLVERS` in `tests/conftest.py`. It must pass
every check, including the slow tier.

The golden data is generated, never hand-edited:

```text
python -m diophantine_search.testing.three_cubes_golden tests/data/three_cubes_golden.json
```

## Benchmarks

Performance numbers come from fixed benchmark suites, not one-off timings.
Every case is checked against a reference before it is timed, and each case is
timed both cold (lookup tables rebuilt every run) and warm (tables already
built).

```text
python -m diophantine_search.bench run --suite quick
python -m diophantine_search.bench run --suite standard --output benchmarks/results/<file>.json
python -m diophantine_search.bench compare old.json new.json
python -m diophantine_search.bench profile --solver cube-root --k 33 --bound 3000
```

Suites: `smoke`, `quick`, `standard`, `modulus-sweep`, `native`, `native-sweep`,
and `native-threads` (the last three need the native library). The timing protocol,
suite definitions, and rules for recording results are in
[docs/benchmarking.md](docs/benchmarking.md). Any performance claim in this
project must cite a committed results file under `benchmarks/results/`.

### Results

Recorded at commit `478fea2` on one machine (CPython 3.12.10, Windows 11,
20 CPUs). Times are medians of warm runs unless noted. They are only comparable
with runs from the same environment.

From [the standard suite](benchmarks/results/2026-09-30-standard-478fea2.json):

- At B = 200, the modular solver is 14–24× faster than brute force (median
  22.8× across the 8 targets).
- Summed over the 8 targets, the cube-root solver searches B = 1000 in 92 ms,
  while the modular solver needs 1,776 ms for the smaller B = 800.
- At B = 10,000, the cube-root solver takes 0.33 s (k = 3) to 3.5 s (k = 29)
  per target. The spread comes from how many rows survive the residue filter.

From [the modulus sweep](benchmarks/results/2026-09-30-modulus-sweep-478fea2.json),
summed over k = 3, 33, 42:

| Solver | Situation | Best modulus | 819 compared with best |
|---|---|---|---|
| cube-root | cold, B ≤ 3000 | 819 | best |
| cube-root | cold, B = 10,000 | 3276 | 1.34× slower |
| cube-root | warm, B = 10,000 | 15561 | 2.59× slower |
| modular | B = 200, 400 | 3276 or 6552 | 3–8% slower |

The Python solvers keep 819 as their default.

From [the native suite](benchmarks/results/2026-11-04-native-66d8927.json),
recorded at commit `66d8927` on the same machine, compared with the Python
cube-root solver in the standard suite above, both at m = 819:

| Bound | Median speedup across the 8 targets | Range |
|---|---|---|
| B = 1,000 | 54.5× | 40–80× |
| B = 3,000 | 72.4× | 64–101× |
| B = 10,000 | 77.8× | 69–105× |

Row counts and solution counts match Python in every shared case. At
B = 100,000 and m = 819, the native solver takes 0.44 s (k = 3) to 2.8 s (k = 29)
per target.

From [the native sweep](benchmarks/results/2026-11-05-native-sweep-66d8927.json),
summed over k = 3, 29, 33, 42, the native solver's default of 15561 compares
with 819 as follows:

| Bound | Warm | Cold |
|---|---|---|
| B = 10,000 | 1.81× faster | 2.25× slower (one-time table build) |
| B = 100,000 | 1.50× faster | 1.46× faster |

## Layout

```text
docs/three-cubes-spec.md                    correctness contract
docs/benchmarking.md                        benchmark protocol and rules
native/                                     C++ row search and its build file
src/diophantine_search/families/
    three_cubes.py                          definitions, result types, validation
    three_cubes_brute_force.py              reference search
    three_cubes_modular.py                  modular-pruning solver
    three_cubes_cube_root.py                cube-root row solver
    three_cubes_native.py                   Python binding for the C++ solver
src/diophantine_search/intmath.py           exact integer cube roots
src/diophantine_search/testing/
    three_cubes_golden.py                   golden data generator and loader
    three_cubes_conformance.py              reusable solver checks
src/diophantine_search/bench/               benchmark runner, compare, profile
src/diophantine_search/__main__.py          command-line tool
tests/conftest.py                           solvers under test
tests/data/three_cubes_known.json           verified known solutions
tests/data/three_cubes_golden.json          generated golden data
tests/                                      test suite
```
