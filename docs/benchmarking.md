# Benchmarking the three-cubes solvers

The benchmark runner provides fixed workloads, verifies every result before it
starts timing, and records enough context to compare runs made under the same
conditions. It uses only the Python standard library.

## Timing protocol

Before timing a suite, the runner executes every case, validates its result, and
compares its solutions with a reference. It caches references by `(k, B)` during
that verification pass. A failed validation or comparison stops the suite before
any timed case begins and before an output file is written.

Each case runs in both modes, with cold first and warm second:

- **Cold:** before every timed repeat, clear both solver caches and run garbage
  collection.
- **Warm:** clear both caches once, make one untimed warm-up call, and then time
  every repeat against the populated caches.

Garbage collection is disabled around each timed solver call and enabled again
afterward. The runner measures elapsed time with `time.perf_counter_ns`. It
records every repeat, the minimum, and the median rounded down to an integer.
Candidate counts must remain identical across repeats.

For bounds up to and including 200, the reference is the brute-force solver. For
larger bounds, the reference is the cube-root solver with modulus 9. Above 200,
the reference therefore shares the row algorithm with cube-root benchmark cases,
but it does not share their default residue table. Algorithm correctness is
covered independently by the conformance suite.

## Fixed suites

Every combination below runs once in cold mode and once in warm mode.

| Suite | Targets `k` | Solvers and bounds | Repeats |
| --- | --- | --- | ---: |
| `smoke` | 3, 29 | brute-force, modular m=819, and cube-root m=819 at B=5,10 | 1 |
| `quick` | 3, 29, 30, 33, 42, 52 | brute-force at B=100; modular m=819 at B=100,400; cube-root m=819 at B=100,400,3000 | 5 |
| `standard` | 3, 29, 30, 33, 42, 52, 74, 114 | brute-force at B=100,200; modular m=819 at B=200,400,800; cube-root m=819 at B=1000,3000,10000 | 5 |
| `modulus-sweep` | 3, 33, 42 | cube-root with m=63,819,3276,6552,15561 at B=1000,3000,10000; modular with m=63,819,3276,6552 at B=200,400 | 3 |

Cases retain the listed solver order, then target order, then bound order.

## Commands

Run a suite and optionally save its self-describing JSON document:

```console
python -m diophantine_search.bench run --suite quick
python -m diophantine_search.bench run --suite quick --output benchmarks/results/2026-09-30-quick-a1b2c3d.json
```

Use `--repeats N` to override a suite's repeat count. Existing output paths are
protected unless `--force` is supplied.

Compare two saved runs:

```console
python -m diophantine_search.bench compare old.json new.json
```

Profile one call and show the functions with the highest total internal time:

```console
python -m diophantine_search.bench profile --solver cube-root --k 33 --bound 3000
python -m diophantine_search.bench profile --solver modular --modulus 63 --k 3 --bound 400 --top 25
```

Store committed results as
`benchmarks/results/<YYYY-MM-DD>-<suite>-<short commit>.json`, where
`<YYYY-MM-DD>` is the local date of the run; `environment.timestamp_utc` records
the exact time in UTC. Produce results from a tree whose tracked files have no
uncommitted changes (`git_dirty` is false; untracked files are ignored). Compare
runs only when their environment metadata describes the same environment. Any
performance claim in project documentation must cite a committed result file.
