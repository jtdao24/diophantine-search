"""Tests for the C++ cube-root row solver and its ctypes binding."""

from __future__ import annotations

import ctypes
from concurrent.futures import ThreadPoolExecutor
import os
import random

import pytest

from diophantine_search.families import three_cubes_native
from diophantine_search.__main__ import main
from diophantine_search.families.three_cubes import (
    SearchInstance,
    validate_result,
)
from diophantine_search.families.three_cubes_cube_root import cube_root_search
from diophantine_search.families.three_cubes_modular import MAX_MODULUS
from diophantine_search.families.three_cubes_native import (
    NATIVE_DEFAULT_MODULUS,
    NATIVE_MAX_BOUND,
    NativeLibraryError,
    _load_library,
    clear_native_cache,
    is_available,
    library_path,
    native_search,
)
from diophantine_search.intmath import icbrt_ceil, icbrt_floor

REQUIRES_NATIVE = pytest.mark.skipif(
    not is_available(), reason="native library not built"
)


def test_native_required():
    if os.environ.get("DIOPHANTINE_REQUIRE_NATIVE") == "1":
        assert is_available()


def test_missing_library_has_no_fallback(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "does-not-exist.dll"
    monkeypatch.setenv("DIOPHANTINE_NATIVE_LIB", str(missing))
    _load_library.cache_clear()
    try:
        assert library_path() is None
        assert not is_available()
        with pytest.raises(NativeLibraryError):
            native_search(SearchInstance(3, 5))
        with pytest.raises(SystemExit) as error:
            main(
                [
                    "three-cubes",
                    "--k",
                    "3",
                    "--bound",
                    "5",
                    "--solver",
                    "native",
                ]
            )
        assert error.value.code == 2
        assert "cmake -S native" in capsys.readouterr().err
    finally:
        _load_library.cache_clear()


@REQUIRES_NATIVE
def test_native_integer_cube_roots():
    library = _load_library()
    assert library.ds_abi_version() == 2
    for value in range(-20_000, 20_001):
        assert library.ds_icbrt_floor(value) == icbrt_floor(value)
        assert library.ds_icbrt_ceil(value) == icbrt_ceil(value)

    generator = random.Random(20261104)
    for _ in range(2000):
        root = generator.randint(-2_097_151, 2_097_151)
        cube = root**3
        for value in (cube - 1, cube, cube + 1):
            assert library.ds_icbrt_floor(value) == icbrt_floor(value)
            assert library.ds_icbrt_ceil(value) == icbrt_ceil(value)

    assert library.ds_icbrt_floor(2**63 - 1) == 2_097_151
    assert library.ds_icbrt_ceil(2**63 - 1) == 2_097_152
    assert library.ds_icbrt_floor(-(2**63)) == -2_097_152
    assert library.ds_icbrt_ceil(-(2**63)) == -2_097_152


@REQUIRES_NATIVE
def test_native_matches_python_matrix():
    for modulus in (1, 2, 4, 7, 8, 9, 13, 27, 63, 819):
        for bound in (0, 1, 2, 7, 30, 120):
            for k in range(-60, 61):
                instance = SearchInstance(k, bound)
                expected = cube_root_search(instance, modulus)
                actual = native_search(instance, modulus)
                assert actual.solutions == expected.solutions
                assert actual.triples_checked == expected.triples_checked


@REQUIRES_NATIVE
def test_native_bound_400_matches_python():
    for modulus in (9, 819):
        for k in (3, 29, 33, 42, 52, 74, 114):
            instance = SearchInstance(k, 400)
            expected = cube_root_search(instance, modulus)
            actual = native_search(instance, modulus)
            assert actual.solutions == expected.solutions
            assert actual.triples_checked == expected.triples_checked


@pytest.mark.slow
@REQUIRES_NATIVE
def test_native_bound_3000_matches_python():
    for modulus in (9, 819):
        for k in (3, 29, 33, 42, 52, 74, 114):
            instance = SearchInstance(k, 3000)
            expected = cube_root_search(instance, modulus)
            actual = native_search(instance, modulus)
            assert actual.solutions == expected.solutions
            assert actual.triples_checked == expected.triples_checked


@REQUIRES_NATIVE
@pytest.mark.parametrize(
    ("modulus", "expected"),
    [(1, 121_664), (9, 52_796), (63, 23_188), (819, 9_109)],
)
def test_native_pinned_checked_totals(modulus, expected):
    actual = sum(
        native_search(SearchInstance(k, 30), modulus).triples_checked
        for k in range(-100, 101)
    )
    assert actual == expected


@REQUIRES_NATIVE
@pytest.mark.parametrize("k", [-14, -13, -5, -4, 4, 5, 13, 14])
def test_native_mod_nine_exclusion(k):
    result = native_search(SearchInstance(k, 100), 819)
    assert result.solutions == ()
    assert result.triples_checked == 0


def _direct_search(k, bound, modulus, output, capacity, threads=1):
    count = ctypes.c_int64(-1)
    checked = ctypes.c_int64(-1)
    status = _load_library().ds_cube_root_search(
        k,
        bound,
        modulus,
        threads,
        output,
        capacity,
        ctypes.byref(count),
        ctypes.byref(checked),
    )
    return status, int(count.value), int(checked.value)


@REQUIRES_NATIVE
def test_native_buffer_retry_and_direct_capacity():
    instance = SearchInstance(8, 2000)
    expected = cube_root_search(instance, 819)
    actual = native_search(instance, 819)
    assert len(expected.solutions) > 1024
    assert actual == expected

    direct_expected = cube_root_search(SearchInstance(8, 10), 819)
    status, count, checked = _direct_search(8, 10, 819, None, 0)
    assert status == 1
    assert count == len(direct_expected.solutions)
    assert checked == direct_expected.triples_checked

    sentinel = -9_876_543_210
    output = (ctypes.c_int64 * 6)(*[sentinel] * 6)
    status, count, checked = _direct_search(8, 10, 819, output, 1)
    assert status == 1
    assert count == len(direct_expected.solutions)
    assert checked == direct_expected.triples_checked
    assert tuple(output[:3]) == direct_expected.solutions[0]
    assert tuple(output[3:]) == (sentinel, sentinel, sentinel)


@REQUIRES_NATIVE
def test_native_near_limit_arithmetic():
    bound = 1_154_107
    assert 6 * bound**3 <= 2**63 - 1
    assert 6 * (bound + 1) ** 3 > 2**63 - 1
    cube = bound**3
    cases = [
        (3 * cube, (bound, bound, bound)),
        (-3 * cube, (-bound, -bound, -bound)),
        (2 * cube + (bound - 1) ** 3, (bound - 1, bound, bound)),
        (
            cube + (bound - 1) ** 3 + (bound - 2) ** 3,
            (bound - 2, bound - 1, bound),
        ),
        (
            -(cube + (bound - 1) ** 3 + (bound - 2) ** 3),
            (-bound, -(bound - 1), -(bound - 2)),
        ),
    ]
    for k, solution in cases:
        result = native_search(SearchInstance(k, bound), 819)
        assert solution in result.solutions
        validate_result(result)


@pytest.mark.slow
@REQUIRES_NATIVE
def test_native_near_limit_matches_python():
    bound = 1_154_107
    k = bound**3 + (bound - 1) ** 3 + (bound - 2) ** 3
    instance = SearchInstance(k, bound)
    assert native_search(instance, 819) == cube_root_search(instance, 819)


@REQUIRES_NATIVE
def test_native_maximum_bound_and_k_range():
    bound = NATIVE_MAX_BOUND
    limit = 2**63 - 1 - 3 * bound**3
    assert limit == 18_710_051_606_446

    largest_excluded = limit - (limit - 4) % 9
    smallest_excluded = -limit + (4 - (-limit)) % 9
    for k in (4, largest_excluded, smallest_excluded):
        result = native_search(SearchInstance(k, bound))
        assert result.solutions == ()
        assert result.triples_checked == 0

    for k in (limit + 1, -limit - 1, 3 * bound**3):
        with pytest.raises(ValueError, match="native range"):
            native_search(SearchInstance(k, bound))


@REQUIRES_NATIVE
def test_native_python_range_validation_prevents_wraparound():
    for k in (2**64 + 3, 2**63):
        with pytest.raises(ValueError, match="native range"):
            native_search(SearchInstance(k, 5))
    with pytest.raises(ValueError, match="native range"):
        native_search(SearchInstance(3, NATIVE_MAX_BOUND + 1))

    bound = 10
    endpoint = 2**63 - 1 - 3000
    for k in (endpoint, -endpoint):
        result = native_search(SearchInstance(k, bound))
        assert result.solutions == ()
    for k in (endpoint + 1, -endpoint - 1):
        with pytest.raises(ValueError, match="native range"):
            native_search(SearchInstance(k, bound))


@REQUIRES_NATIVE
def test_native_c_api_range_endpoints():
    bound = 10
    endpoint = 2**63 - 1 - 3000
    for k in (endpoint, -endpoint):
        status, _, _ = _direct_search(k, bound, 819, None, 0)
        assert status == 0
    for k in (endpoint + 1, -endpoint - 1):
        status, _, _ = _direct_search(k, bound, 819, None, 0)
        assert status == 2


@REQUIRES_NATIVE
def test_native_c_api_validates_modulus_before_exclusion():
    status, _, _ = _direct_search(4, 10, 43_010, None, 0)
    assert status == 2


@REQUIRES_NATIVE
@pytest.mark.parametrize(
    ("k", "bound", "modulus"),
    [
        (0, -1, 819),
        (0, 1_454_084, 819),
        (0, 5, 0),
        (0, 5, 100_001),
        (0, 5, 43_010),
        (-(2**63), 0, 819),
        (2**63 - 1, 1, 819),
        (3 * 1_454_083**3, 1_454_083, 819),
    ],
)
def test_native_c_api_rejects_invalid_arguments(k, bound, modulus):
    status, _, _ = _direct_search(k, bound, modulus, None, 0)
    assert status == 2


@REQUIRES_NATIVE
@pytest.mark.parametrize("modulus", [0, -1, MAX_MODULUS + 1, 43_010])
def test_native_rejects_invalid_modulus(modulus):
    with pytest.raises(ValueError):
        native_search(SearchInstance(3, 5), modulus)


@REQUIRES_NATIVE
@pytest.mark.parametrize("modulus", [1.0, True])
def test_native_rejects_noninteger_modulus(modulus):
    with pytest.raises(TypeError):
        native_search(SearchInstance(3, 5), modulus)


@REQUIRES_NATIVE
def test_native_checks_instance_before_modulus():
    with pytest.raises(TypeError, match="SearchInstance"):
        native_search((3, 5), 0)


@REQUIRES_NATIVE
def test_native_python_modulus_validation_cache(monkeypatch):
    calls = 0
    original = three_cubes_native.cube_residues

    def counting_cube_residues(modulus):
        nonlocal calls
        calls += 1
        return original(modulus)

    monkeypatch.setattr(
        three_cubes_native, "cube_residues", counting_cube_residues
    )
    clear_native_cache()
    instance = SearchInstance(3, 5)
    native_search(instance, 819)
    native_search(instance, 819)
    assert calls == 1
    clear_native_cache()
    native_search(instance, 819)
    assert calls == 2


@REQUIRES_NATIVE
def test_native_modulus_cache_keeps_types_and_exceptions_distinct():
    instance = SearchInstance(3, 5)
    native_search(instance, 1)
    with pytest.raises(TypeError):
        native_search(instance, True)
    with pytest.raises(TypeError):
        native_search(instance, 1.0)
    for _ in range(2):
        with pytest.raises(ValueError):
            native_search(instance, 0)


@REQUIRES_NATIVE
def test_native_cache_and_threads():
    instance = SearchInstance(29, 100)
    expected = native_search(instance, 819)
    clear_native_cache()
    assert native_search(instance, 819) == expected
    native_search(instance, 63)
    assert native_search(instance, 819) == expected

    work = [
        (k, (63, 819, 1)[index % 3])
        for index, k in enumerate(range(-30, 31))
    ]
    baseline = {
        (k, modulus): native_search(SearchInstance(k, 30), modulus)
        for k, modulus in work
    }

    def run(item):
        k, modulus = item
        return item, native_search(SearchInstance(k, 30), modulus)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run, item) for item in work]
        clear_native_cache()
        threaded = dict(future.result() for future in futures)
    assert threaded == baseline


@REQUIRES_NATIVE
def test_native_default_modulus():
    assert NATIVE_DEFAULT_MODULUS == 15_561
    instance = SearchInstance(29, 100)
    assert native_search(instance) == native_search(instance, 15_561)


@REQUIRES_NATIVE
def test_native_default_solutions_match_python():
    for k in (3, 29, 33, 42):
        instance = SearchInstance(k, 400)
        assert native_search(instance, 15_561).solutions == cube_root_search(
            instance, 819
        ).solutions


@REQUIRES_NATIVE
def test_native_cli(capsys):
    expected_count = native_search(
        SearchInstance(3, 5), 15_561
    ).triples_checked
    assert main(
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "native",
        ]
    ) == 0
    assert capsys.readouterr().out.splitlines() == [
        "-5 4 4",
        "1 1 1",
        f"# k=3 bound=5 solutions=2 triples_checked={expected_count}",
    ]

    for arguments in (
        ["--k", "3", "--bound", "5", "--modulus", "43010"],
        ["--k", "3", "--bound", "5", "--modulus", "0"],
        ["--k", "18446744073709551619", "--bound", "5"],
    ):
        with pytest.raises(SystemExit) as error:
            main(["three-cubes", "--solver", "native", *arguments])
        assert error.value.code == 2
