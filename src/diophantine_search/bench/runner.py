"""Benchmark execution and serialization.

Each suite is verified in full before timing starts. A cold timed call clears
the solver caches and collects garbage before running. A warm case clears the
caches once, performs one untimed warm-up call, and then runs all timed calls
against the populated caches. Garbage collection is disabled only around each
timed solver call. Timings use ``time.perf_counter_ns``.
"""

from __future__ import annotations

import gc
import json
import os
import platform
import statistics
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
    Triple,
    validate_result,
)
from diophantine_search.families.three_cubes_brute_force import (
    brute_force_search,
)
from diophantine_search.families.three_cubes_cube_root import (
    MAX_TABLE_ENTRIES,
    cube_root_search,
    y_class_table,
)
from diophantine_search.families.three_cubes_modular import (
    cube_residues,
    cube_root_classes,
    modular_search,
)


class BenchmarkError(Exception):
    """Report a correctness or repeatability failure during benchmarking."""


@dataclass(frozen=True)
class SolverConfig:
    """A solver and its fixed modulus, if applicable."""

    name: str
    modulus: int | None

    def __post_init__(self) -> None:
        if self.name not in {"brute-force", "modular", "cube-root"}:
            raise ValueError(f"unknown solver {self.name!r}")
        if (self.name == "brute-force") != (self.modulus is None):
            raise ValueError("modulus must be None exactly for brute-force")
        if self.name == "modular":
            cube_residues(self.modulus)
        elif self.name == "cube-root":
            residues = cube_residues(self.modulus)
            if self.modulus * len(residues) > MAX_TABLE_ENTRIES:
                raise ValueError(
                    f"y-class table exceeds {MAX_TABLE_ENTRIES} entries"
                )

    @property
    def label(self) -> str:
        """Return the stable display and result label."""

        if self.modulus is None:
            return self.name
        return f"{self.name}[m={self.modulus}]"

    @property
    def count_unit(self) -> str:
        """Return the unit measured by ``triples_checked``."""

        return "rows" if self.name == "cube-root" else "triples"

    def run(self, instance: SearchInstance) -> SearchResult:
        """Run this solver configuration on an instance."""

        if self.name == "brute-force":
            return brute_force_search(instance)
        if self.name == "modular":
            return modular_search(instance, self.modulus)
        return cube_root_search(instance, self.modulus)


def clear_solver_caches() -> None:
    """Clear all caches that can affect solver timing."""

    cube_root_classes.cache_clear()
    y_class_table.cache_clear()


@dataclass(frozen=True)
class Case:
    """One solver, target, and bound combination."""

    solver: SolverConfig
    k: int
    bound: int


@dataclass(frozen=True)
class Suite:
    """An ordered collection of benchmark cases."""

    name: str
    description: str
    cases: tuple[Case, ...]
    repeats: int


def _cases(
    solvers: tuple[tuple[SolverConfig, tuple[int, ...]], ...],
    targets: tuple[int, ...],
) -> tuple[Case, ...]:
    return tuple(
        Case(solver, k, bound)
        for solver, bounds in solvers
        for k in targets
        for bound in bounds
    )


_BRUTE_FORCE = SolverConfig("brute-force", None)
_MODULAR_819 = SolverConfig("modular", 819)
_CUBE_ROOT_819 = SolverConfig("cube-root", 819)

SUITES: dict[str, Suite] = {
    "smoke": Suite(
        "smoke",
        "Small end-to-end benchmark for validation and tooling checks.",
        _cases(
            (
                (_BRUTE_FORCE, (5, 10)),
                (_MODULAR_819, (5, 10)),
                (_CUBE_ROOT_819, (5, 10)),
            ),
            (3, 29),
        ),
        1,
    ),
    "quick": Suite(
        "quick",
        "Routine comparison across practical development bounds.",
        _cases(
            (
                (_BRUTE_FORCE, (100,)),
                (_MODULAR_819, (100, 400)),
                (_CUBE_ROOT_819, (100, 400, 3000)),
            ),
            (3, 29, 30, 33, 42, 52),
        ),
        5,
    ),
    "standard": Suite(
        "standard",
        "Full solver comparison across representative targets and bounds.",
        _cases(
            (
                (_BRUTE_FORCE, (100, 200)),
                (_MODULAR_819, (200, 400, 800)),
                (_CUBE_ROOT_819, (1000, 3000, 10000)),
            ),
            (3, 29, 30, 33, 42, 52, 74, 114),
        ),
        5,
    ),
    "modulus-sweep": Suite(
        "modulus-sweep",
        "Comparison of fixed moduli for both pruning solvers.",
        _cases(
            tuple(
                (SolverConfig("cube-root", modulus), (1000, 3000, 10000))
                for modulus in (63, 819, 3276, 6552, 15561)
            )
            + tuple(
                (SolverConfig("modular", modulus), (200, 400))
                for modulus in (63, 819, 3276, 6552)
            ),
            (3, 33, 42),
        ),
        3,
    ),
}


def reference_solutions(k: int, bound: int) -> tuple[str, tuple[Triple, ...]]:
    """Return the named reference solution set for an instance."""

    instance = SearchInstance(k, bound)
    if bound <= 200:
        return "brute-force", brute_force_search(instance).solutions
    return "cube-root[m=9]", cube_root_search(instance, modulus=9).solutions


def _timed_run(case: Case) -> tuple[int, SearchResult]:
    instance = SearchInstance(case.k, case.bound)
    gc.collect()
    gc.disable()
    try:
        started = time.perf_counter_ns()
        result = case.solver.run(instance)
        elapsed = time.perf_counter_ns() - started
    finally:
        gc.enable()
    return elapsed, result


def time_case(case: Case, mode: str, repeats: int) -> dict[str, Any]:
    """Time one case under the cold or warm cache protocol."""

    if mode not in {"cold", "warm"}:
        raise ValueError(f"unknown timing mode {mode!r}")
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    expected_checked: int | None = None
    if mode == "warm":
        clear_solver_caches()
        warmup = case.solver.run(SearchInstance(case.k, case.bound))
        expected_checked = warmup.triples_checked

    times_ns: list[int] = []
    solutions_count = 0
    for _ in range(repeats):
        if mode == "cold":
            clear_solver_caches()
        elapsed, result = _timed_run(case)
        if expected_checked is None:
            expected_checked = result.triples_checked
        elif result.triples_checked != expected_checked:
            raise BenchmarkError(
                f"{case.solver.label} k={case.k} B={case.bound} produced "
                "inconsistent triples_checked values"
            )
        if not times_ns:
            solutions_count = len(result.solutions)
        times_ns.append(elapsed)

    return {
        "times_ns": times_ns,
        "min_ns": min(times_ns),
        "median_ns": int(statistics.median(times_ns)),
        "triples_checked": expected_checked,
        "solutions_count": solutions_count,
    }


def _case_name(case: Case) -> str:
    return f"{case.solver.label} k={case.k} B={case.bound}"


def run_suite(
    suite: Suite,
    *,
    repeats: int | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Verify every case, then benchmark every case in cold and warm modes."""

    actual_repeats = suite.repeats if repeats is None else repeats
    if actual_repeats < 1:
        raise ValueError("repeats must be at least 1")

    references: dict[tuple[int, int], tuple[str, tuple[Triple, ...]]] = {}
    case_references: list[str] = []
    for case in suite.cases:
        key = (case.k, case.bound)
        try:
            reference = references.get(key)
            if reference is None:
                reference = reference_solutions(*key)
                references[key] = reference
            result = case.solver.run(SearchInstance(case.k, case.bound))
            validate_result(result)
            if result.solutions != reference[1]:
                raise ValueError("solutions differ from the reference")
        except Exception as error:
            raise BenchmarkError(
                f"verification failed for {_case_name(case)}: {error}"
            ) from error
        case_references.append(reference[0])

    records: list[dict[str, Any]] = []
    for case, reference_name in zip(suite.cases, case_references):
        for mode in ("cold", "warm"):
            timing = time_case(case, mode, actual_repeats)
            record = {
                "solver": case.solver.label,
                "modulus": case.solver.modulus,
                "k": case.k,
                "bound": case.bound,
                "mode": mode,
                "times_ns": timing["times_ns"],
                "min_ns": timing["min_ns"],
                "median_ns": timing["median_ns"],
                "triples_checked": timing["triples_checked"],
                "count_unit": case.solver.count_unit,
                "solutions_count": timing["solutions_count"],
                "reference": reference_name,
            }
            records.append(record)
            if progress is not None:
                progress(record)

    return {
        "schema_version": "1",
        "suite": suite.name,
        "repeats": actual_repeats,
        "environment": environment_metadata(),
        "results": records,
    }


def _git_command(arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        completed = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed if completed.returncode == 0 else None


def environment_metadata() -> dict[str, Any]:
    """Collect interpreter, machine, clock, and repository metadata."""

    commit_result = _git_command(["git", "rev-parse", "HEAD"])
    status_result = _git_command(["git", "status", "--porcelain"])
    return {
        "python_version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "git_commit": (
            commit_result.stdout.strip()
            if commit_result is not None
            else "unknown"
        ),
        "git_dirty": (
            bool(status_result.stdout)
            if status_result is not None
            else None
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timer": "perf_counter_ns",
        "gc": "disabled during timed calls",
    }


def dump_run(document: dict[str, Any]) -> str:
    """Serialize a benchmark document with a single final newline."""

    return json.dumps(document, indent=2) + "\n"


_TOP_LEVEL_KEYS = {"schema_version", "suite", "repeats", "environment", "results"}
_RESULT_KEYS = {
    "solver",
    "modulus",
    "k",
    "bound",
    "mode",
    "times_ns",
    "min_ns",
    "median_ns",
    "triples_checked",
    "count_unit",
    "solutions_count",
    "reference",
}


def load_run(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a schema-version-1 result document."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load benchmark result: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("benchmark result must be a JSON object")
    missing = _TOP_LEVEL_KEYS.difference(document)
    if missing:
        raise ValueError(f"benchmark result is missing keys: {sorted(missing)}")
    if document["schema_version"] != "1":
        raise ValueError("unsupported benchmark schema_version")
    if not isinstance(document["results"], list):
        raise ValueError("benchmark results must be a list")
    for index, record in enumerate(document["results"]):
        if not isinstance(record, dict):
            raise ValueError(f"benchmark result {index} must be an object")
        missing = _RESULT_KEYS.difference(record)
        if missing:
            raise ValueError(
                f"benchmark result {index} is missing keys: {sorted(missing)}"
            )
    return document
