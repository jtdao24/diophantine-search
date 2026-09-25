"""Integrity tests for independently generated golden data."""

import json
from pathlib import Path

import pytest

from diophantine_search.families.three_cubes import (
    in_domain,
    is_canonical,
    is_solution,
    is_trivial,
)
from diophantine_search.testing.three_cubes_golden import (
    GOLDEN_SPECS,
    build_golden_sets,
    independent_solution_table,
    load_golden,
    render_golden,
)

DATA = Path(__file__).parent / "data" / "three_cubes_golden.json"


def test_golden_metadata(golden_sets):
    assert tuple(
        (golden.name, golden.bound, golden.k_min, golden.k_max)
        for golden in golden_sets
    ) == GOLDEN_SPECS


def test_stored_solutions_are_valid(golden_sets):
    for golden in golden_sets:
        for k, solutions in golden.results.items():
            assert all(
                left < right
                for left, right in zip(solutions, solutions[1:])
            )
            for triple in solutions:
                assert is_canonical(triple)
                assert in_domain(triple, golden.bound)
                assert is_solution(k, triple)


def test_mod_nine_entries_are_empty(golden_sets):
    for golden in golden_sets:
        for k in range(golden.k_min, golden.k_max + 1):
            if k % 9 in {4, 5}:
                assert golden.results[k] == ()


def test_zero_entries(golden_sets):
    for golden in golden_sets:
        if golden.k_min <= 0 <= golden.k_max:
            assert golden.results[0] == tuple(
                (-t, 0, t) for t in range(golden.bound, -1, -1)
            )


def test_trivial_counts(golden_sets):
    for golden in golden_sets:
        cubes = {n**3 for n in range(-golden.bound, golden.bound + 1)}
        for k, solutions in golden.results.items():
            expected = golden.bound + 1 if k in cubes else 0
            assert sum(is_trivial(triple) for triple in solutions) == expected


def test_fast_set_is_independently_reproducible(golden_sets):
    fast = next(golden for golden in golden_sets if golden.name == "fast")
    assert fast.results == independent_solution_table(30, -100, 100)


@pytest.mark.slow
def test_entire_file_is_reproducible():
    expected = render_golden(build_golden_sets()).encode("utf-8")
    assert DATA.read_bytes() == expected


def _small_document():
    return {
        "family": "three_cubes",
        "format_version": "1",
        "method": "ordered enumeration of D(B), canonicalize, deduplicate",
        "sets": [
            {
                "name": "small",
                "bound": "0",
                "k_min": "0",
                "k_max": "1",
                "results": [
                    {"k": "0", "solutions": [["0", "0", "0"]]},
                    {"k": "1", "solutions": []},
                ],
            }
        ],
    }


def _write_document(path, document):
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")


def test_load_rejects_wrong_family(tmp_path):
    document = _small_document()
    document["family"] = "other"
    path = tmp_path / "wrong-family.json"
    _write_document(path, document)
    with pytest.raises(ValueError):
        load_golden(path)


def test_load_rejects_missing_k(tmp_path):
    document = _small_document()
    document["sets"][0]["results"].pop()
    path = tmp_path / "missing-k.json"
    _write_document(path, document)
    with pytest.raises(ValueError):
        load_golden(path)


def test_load_rejects_duplicated_k(tmp_path):
    document = _small_document()
    document["sets"][0]["results"][1]["k"] = "0"
    path = tmp_path / "duplicated-k.json"
    _write_document(path, document)
    with pytest.raises(ValueError):
        load_golden(path)
