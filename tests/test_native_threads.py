"""Tests for deterministic multithreaded native row search."""

from __future__ import annotations

import ctypes
from concurrent.futures import ThreadPoolExecutor

import pytest

from diophantine_search.__main__ import main
from diophantine_search.families.three_cubes import (
    SearchInstance,
    validate_result,
)
from diophantine_search.families.three_cubes_cube_root import cube_root_search
from diophantine_search.families.three_cubes_native import (
    NATIVE_MAX_BOUND,
    _load_library,
    clear_native_cache,
    is_available,
    native_search,
)
from diophantine_search.intmath import icbrt_floor

pytestmark = pytest.mark.skipif(
    not is_available(), reason="native library not built"
)


def _direct_search(k, bound, modulus, threads, output, capacity):
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


def test_thread_counts_match_sequential_small_matrix():
    for modulus in (1, 63, 15_561):
        for bound in (0, 1, 7, 120):
            sequential = {
                k: native_search(SearchInstance(k, bound), modulus, 1)
                for k in range(-30, 31)
            }
            for threads in (2, 3, 4, 8, 20, 64, 256):
                for k in range(-30, 31):
                    assert (
                        native_search(
                            SearchInstance(k, bound), modulus, threads
                        )
                        == sequential[k]
                    )


def test_thread_counts_match_sequential_large_matrix():
    for modulus in (819, 15_561):
        for bound in (1000, 10_000):
            sequential = {
                k: native_search(SearchInstance(k, bound), modulus, 1)
                for k in (3, 29, 33, 42)
            }
            for threads in (2, 3, 4, 8, 20, 64):
                for k in (3, 29, 33, 42):
                    assert (
                        native_search(
                            SearchInstance(k, bound), modulus, threads
                        )
                        == sequential[k]
                    )


def test_eight_threads_match_python():
    modulus = 819
    for k in range(-60, 61):
        instance = SearchInstance(k, 120)
        assert native_search(instance, modulus, 8) == cube_root_search(
            instance, modulus
        )
    for k in (3, 29, 33, 42):
        instance = SearchInstance(k, 400)
        assert native_search(instance, modulus, 8) == cube_root_search(
            instance, modulus
        )


@pytest.mark.slow
def test_eight_threads_bound_3000_matches_python():
    for modulus in (9, 819):
        for k in (3, 29, 33, 42):
            instance = SearchInstance(k, 3000)
            assert native_search(instance, modulus, 8) == cube_root_search(
                instance, modulus
            )


def test_threaded_many_solutions_and_capacity():
    instance = SearchInstance(8, 2000)
    sequential = native_search(instance, 819, 1)
    threaded = native_search(instance, 819, 8)
    assert threaded == sequential
    assert all(
        left < right
        for left, right in zip(threaded.solutions, threaded.solutions[1:])
    )

    sentinel = -9_876_543_210
    output = (ctypes.c_int64 * 6)(*[sentinel] * 6)
    status, count, checked = _direct_search(8, 2000, 819, 8, output, 1)
    assert status == 1
    assert count == len(sequential.solutions)
    assert checked == sequential.triples_checked
    assert tuple(output[:3]) == sequential.solutions[0]
    assert tuple(output[3:]) == (sentinel, sentinel, sentinel)


def test_threaded_empty_work():
    k = -3003
    bound = 10
    assert k % 9 == 3
    x_upper = min(bound, icbrt_floor(k // 3))
    assert x_upper + bound + 1 == 0

    result = native_search(SearchInstance(k, bound), 819, 8)
    assert result.solutions == ()
    assert result.triples_checked == 0
    status, count, checked = _direct_search(k, bound, 819, 8, None, 0)
    assert status == 0
    assert count == 0
    assert checked == 0


def test_threaded_near_limit_arithmetic():
    bound = 1_154_107
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
        instance = SearchInstance(k, bound)
        sequential = native_search(instance, 819, 1)
        threaded = native_search(instance, 819, 8)
        assert threaded == sequential
        assert solution in threaded.solutions
        validate_result(threaded)


def test_threaded_maximum_bound_exclusion():
    result = native_search(SearchInstance(4, NATIVE_MAX_BOUND), 819, 8)
    assert result.solutions == ()
    assert result.triples_checked == 0


def test_threaded_repeatability():
    instance = SearchInstance(29, 3000)
    expected = native_search(instance, 819, 20)
    for _ in range(9):
        assert native_search(instance, 819, 20) == expected


def test_threaded_concurrent_callers_and_cache_clear():
    work = [
        (k, (63, 819)[index % 2])
        for index, k in enumerate(range(-30, 31))
    ]
    baseline = {
        item: native_search(SearchInstance(item[0], 300), item[1], 1)
        for item in work
    }

    def run(item):
        k, modulus = item
        return item, native_search(SearchInstance(k, 300), modulus, 4)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run, item) for item in work]
        clear_native_cache()
        threaded = dict(future.result() for future in futures)
    assert threaded == baseline


@pytest.mark.parametrize("threads", [0, -1, 257])
def test_thread_validation_range(threads):
    with pytest.raises(ValueError):
        native_search(SearchInstance(3, 5), threads=threads)


@pytest.mark.parametrize("threads", [1.0, True])
def test_thread_validation_type(threads):
    with pytest.raises(TypeError):
        native_search(SearchInstance(3, 5), threads=threads)


def test_thread_validation_checks_instance_first():
    with pytest.raises(TypeError, match="SearchInstance"):
        native_search((3, 5), threads=0)


@pytest.mark.parametrize("threads", [0, 257])
def test_c_api_thread_validation(threads):
    status, _, _ = _direct_search(3, 5, 819, threads, None, 0)
    assert status == 2


def test_thread_cli(capsys):
    arguments = [
        "three-cubes",
        "--k",
        "29",
        "--bound",
        "100",
        "--solver",
        "native",
    ]
    assert main(arguments) == 0
    sequential = capsys.readouterr().out.splitlines()
    assert main([*arguments, "--threads", "4"]) == 0
    assert capsys.readouterr().out.splitlines() == sequential

    for threads in ("0", "257"):
        with pytest.raises(SystemExit) as error:
            main([*arguments, "--threads", threads])
        assert error.value.code == 2

    for invalid in (
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--solver",
            "cube-root",
            "--threads",
            "2",
        ],
        [
            "three-cubes",
            "--k",
            "3",
            "--bound",
            "5",
            "--threads",
            "2",
        ],
    ):
        with pytest.raises(SystemExit) as error:
            main(invalid)
        assert error.value.code == 2
