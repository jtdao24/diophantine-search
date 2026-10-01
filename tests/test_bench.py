"""Tests for the reproducible benchmark framework."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from diophantine_search.bench import runner
from diophantine_search.bench.__main__ import main
from diophantine_search.bench.compare import compare_runs
from diophantine_search.bench.runner import (
    BenchmarkError,
    Case,
    SolverConfig,
    Suite,
    clear_solver_caches,
    dump_run,
    environment_metadata,
    load_run,
    reference_solutions,
    run_suite,
    time_case,
)
from diophantine_search.families.three_cubes import (
    SearchInstance,
    SearchResult,
)
from diophantine_search.families.three_cubes_cube_root import y_class_table
from diophantine_search.families.three_cubes_modular import cube_root_classes


RESULT_KEYS = [
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
]


@pytest.fixture(scope="module")
def smoke_document():
    return run_suite(runner.SUITES["smoke"], repeats=1)


def test_smoke_round_trip_and_results(smoke_document, tmp_path):
    path = tmp_path / "smoke.json"
    path.write_text(dump_run(smoke_document), encoding="utf-8", newline="\n")
    assert load_run(path) == smoke_document

    cases = {
        (case.solver.label, case.k, case.bound): case
        for case in runner.SUITES["smoke"].cases
    }
    for record in smoke_document["results"]:
        assert len(record["times_ns"]) == smoke_document["repeats"]
        assert all(
            isinstance(value, int) and value > 0
            for value in record["times_ns"]
        )
        assert record["min_ns"] <= record["median_ns"]
        case = cases[(record["solver"], record["k"], record["bound"])]
        direct = case.solver.run(SearchInstance(case.k, case.bound))
        assert record["triples_checked"] == direct.triples_checked
        assert (record["count_unit"] == "rows") == (
            case.solver.name == "cube-root"
        )
        assert record["reference"] == "brute-force"


def test_result_keys_order_and_modes(smoke_document):
    assert list(smoke_document) == [
        "schema_version",
        "suite",
        "repeats",
        "environment",
        "results",
    ]
    for record in smoke_document["results"]:
        assert list(record) == RESULT_KEYS
    for case in runner.SUITES["smoke"].cases:
        records = [
            record
            for record in smoke_document["results"]
            if (record["solver"], record["k"], record["bound"])
            == (case.solver.label, case.k, case.bound)
        ]
        assert [record["mode"] for record in records] == ["cold", "warm"]


def test_cold_and_warm_cache_misses(monkeypatch):
    case = Case(SolverConfig("cube-root", 63), 3, 10)
    original_clear = runner.clear_solver_caches
    misses_before_clear = []

    def observed_clear():
        misses_before_clear.append(y_class_table.cache_info().misses)
        original_clear()

    clear_solver_caches()
    monkeypatch.setattr(runner, "clear_solver_caches", observed_clear)
    time_case(case, "cold", 3)
    cold_misses = sum(misses_before_clear[1:]) + y_class_table.cache_info().misses
    assert cold_misses == 3

    misses_before_clear.clear()
    time_case(case, "warm", 3)
    warm_misses = sum(misses_before_clear[1:]) + y_class_table.cache_info().misses
    assert warm_misses == 1


def test_configs_are_cheap():
    clear_solver_caches()
    SolverConfig("cube-root", 15_561)
    SolverConfig("modular", 6_552)
    assert cube_root_classes.cache_info().currsize == 0
    assert y_class_table.cache_info().currsize == 0


@pytest.mark.parametrize("modulus", [1, 63, 819])
def test_cube_root_config_acceptance_matches_table(modulus):
    SolverConfig("cube-root", modulus)
    y_class_table(modulus)


@pytest.mark.parametrize("modulus", [43_010, 0, 100_001, 1.0, True])
def test_cube_root_config_rejection_matches_table(modulus):
    with pytest.raises(Exception) as config_error:
        SolverConfig("cube-root", modulus)
    with pytest.raises(Exception) as table_error:
        y_class_table(modulus)
    assert type(config_error.value) is type(table_error.value)


@pytest.mark.parametrize("modulus", [1, 819, 0, 100_001, 1.0, True])
def test_modular_config_validation_matches_classes(modulus):
    def outcome(call):
        try:
            call()
        except Exception as error:
            return type(error)
        return None

    assert outcome(lambda: SolverConfig("modular", modulus)) is outcome(
        lambda: cube_root_classes(modulus)
    )


def test_config_modulus_relationships():
    with pytest.raises(ValueError):
        SolverConfig("brute-force", 819)
    with pytest.raises(ValueError):
        SolverConfig("modular", None)


def test_verification_guard_and_cli_does_not_write(monkeypatch, tmp_path, capsys):
    original_run = SolverConfig.run

    def drop_solutions(self, instance):
        result = original_run(self, instance)
        return SearchResult(result.instance, (), result.triples_checked)

    monkeypatch.setattr(SolverConfig, "run", drop_solutions)
    suite = Suite(
        "broken",
        "deliberately broken",
        (Case(SolverConfig("brute-force", None), 3, 1),),
        1,
    )
    with pytest.raises(BenchmarkError, match="brute-force k=3 B=1"):
        run_suite(suite)

    monkeypatch.setitem(runner.SUITES, "broken", suite)
    output = tmp_path / "must-not-exist.json"
    assert main(
        ["run", "--suite", "broken", "--output", str(output)]
    ) == 1
    assert not output.exists()
    assert "benchmark error" in capsys.readouterr().err


def test_reference_threshold():
    assert reference_solutions(3, 200)[0] == "brute-force"
    assert reference_solutions(3, 201)[0] == "cube-root[m=9]"


def test_suite_names_and_case_counts():
    assert set(runner.SUITES) == {
        "smoke",
        "quick",
        "standard",
        "modulus-sweep",
    }
    assert {
        name: len(suite.cases) for name, suite in runner.SUITES.items()
    } == {"smoke": 12, "quick": 36, "standard": 64, "modulus-sweep": 69}


def _document(results, *, python_version="3.12", timestamp="one"):
    return {
        "environment": {
            "python_version": python_version,
            "timestamp_utc": timestamp,
        },
        "results": results,
    }


def test_compare_runs():
    old = _document(
        [
            {
                "solver": "a",
                "k": 3,
                "bound": 5,
                "mode": "cold",
                "median_ns": 20,
            },
            {
                "solver": "old",
                "k": 3,
                "bound": 5,
                "mode": "cold",
                "median_ns": 1,
            },
        ]
    )
    new = _document(
        [
            {
                "solver": "a",
                "k": 3,
                "bound": 5,
                "mode": "cold",
                "median_ns": 10,
            },
            {
                "solver": "new",
                "k": 3,
                "bound": 5,
                "mode": "cold",
                "median_ns": 1,
            },
        ],
        python_version="3.13",
        timestamp="two",
    )
    comparison = compare_runs(old, new)
    assert comparison["matches"][0]["speedup"] == 2.0
    assert comparison["only_in_old"] == [("old", 3, 5, "cold")]
    assert comparison["only_in_new"] == [("new", 3, 5, "cold")]
    assert comparison["environment_differences"] == ["python_version"]


def test_load_run_rejects_wrong_schema_and_missing_keys(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": "2"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_run(path)
    path.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_run(path)


def test_run_cli_output_force_and_unknown(tmp_path, capsys):
    output = tmp_path / "nested" / "smoke.json"
    arguments = [
        "run",
        "--suite",
        "smoke",
        "--repeats",
        "1",
        "--output",
        str(output),
    ]
    assert main(arguments) == 0
    assert load_run(output)["suite"] == "smoke"
    with pytest.raises(SystemExit) as exists_error:
        main(arguments)
    assert exists_error.value.code == 2
    assert main(arguments + ["--force"]) == 0
    with pytest.raises(SystemExit) as unknown_error:
        main(["run", "--suite", "nope"])
    assert unknown_error.value.code == 2
    capsys.readouterr()


def test_compare_and_profile_cli(smoke_document, tmp_path, capsys):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(dump_run(smoke_document), encoding="utf-8")
    new.write_text(dump_run(smoke_document), encoding="utf-8")
    assert main(["compare", str(old), str(new)]) == 0
    assert "speedup" in capsys.readouterr().out

    assert main(
        ["profile", "--solver", "cube-root", "--k", "33", "--bound", "50"]
    ) == 0
    profile_output = capsys.readouterr().out
    assert "cube_root" in profile_output
    assert "# k=33 bound=50 solutions=" in profile_output


def test_run_and_compare_output_has_no_trailing_whitespace(
    smoke_document, tmp_path, capsys
):
    assert main(["run", "--suite", "smoke", "--repeats", "1"]) == 0
    run_lines = capsys.readouterr().out.splitlines()
    assert all(line == line.rstrip() for line in run_lines)

    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(dump_run(smoke_document), encoding="utf-8")
    new.write_text(dump_run(smoke_document), encoding="utf-8")
    assert main(["compare", str(old), str(new)]) == 0
    compare_lines = capsys.readouterr().out.splitlines()
    assert all(line == line.rstrip() for line in compare_lines)


def test_git_metadata_ignores_untracked_files(monkeypatch):
    calls = []

    def fake_run(arguments, **kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    environment_metadata()
    assert calls == [
        ["git", "rev-parse", "HEAD"],
        ["git", "status", "--porcelain", "--untracked-files=no"],
    ]


@pytest.mark.parametrize("failure", ["raise", "nonzero"])
def test_git_metadata_failures(monkeypatch, failure):
    def fake_run(*args, **kwargs):
        if failure == "raise":
            raise FileNotFoundError
        return SimpleNamespace(returncode=1, stdout="ignored")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    metadata = environment_metadata()
    assert metadata["git_commit"] == "unknown"
    assert metadata["git_dirty"] is None


@pytest.mark.parametrize(("status", "dirty"), [("", False), (" M file\n", True)])
def test_git_metadata_success(monkeypatch, status, dirty):
    outputs = iter([" abc123\n", status])

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=next(outputs))

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    metadata = environment_metadata()
    assert metadata["git_commit"] == "abc123"
    assert metadata["git_dirty"] is dirty
