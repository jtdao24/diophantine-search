#include "three_cubes.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <thread>
#include <utility>
#include <vector>

namespace {

struct Case {
    std::int64_t k;
    std::int64_t bound;
    std::int64_t modulus;
};

struct Result {
    int status;
    std::int64_t count;
    std::int64_t checked;
    std::vector<std::int64_t> triples;
};

constexpr std::array<Case, 6> kCases{{
    {3, 2000, 819},
    {29, 3000, 15561},
    {33, 3000, 63},
    {8, 2000, 819},
    {0, 1000, 9},
    {1, 2000, 1},
}};

Result search(const Case& test_case, std::int64_t threads) {
    std::int64_t count = 0;
    std::int64_t checked = 0;
    int status = ds_cube_root_search(
        test_case.k,
        test_case.bound,
        test_case.modulus,
        threads,
        nullptr,
        0,
        &count,
        &checked
    );
    if (status != 0 && status != 1) {
        return {status, count, checked, {}};
    }

    std::vector<std::int64_t> triples(
        static_cast<std::size_t>(count) * 3U, 0
    );
    status = ds_cube_root_search(
        test_case.k,
        test_case.bound,
        test_case.modulus,
        threads,
        triples.empty() ? nullptr : triples.data(),
        count,
        &count,
        &checked
    );
    return {status, count, checked, std::move(triples)};
}

bool equal(const Result& left, const Result& right) {
    return left.status == right.status && left.count == right.count
        && left.checked == right.checked && left.triples == right.triples;
}

}  // namespace

int main() {
    constexpr std::array<std::int64_t, 5> thread_counts{{2, 4, 8, 20, 64}};
    for (const Case& test_case : kCases) {
        const Result sequential = search(test_case, 1);
        for (int round = 0; round < 3; ++round) {
            for (const std::int64_t threads : thread_counts) {
                if (!equal(sequential, search(test_case, threads))) {
                    std::cerr << "mismatch in direct stress round " << round
                              << '\n';
                    return 1;
                }
            }
        }
    }

    std::array<std::array<Result, kCases.size()>, 4> expected;
    for (std::size_t caller = 0; caller < expected.size(); ++caller) {
        for (std::size_t index = 0; index < kCases.size(); ++index) {
            Case test_case = kCases[index];
            test_case.modulus = (caller + index) % 2U == 0U ? 819 : 63;
            expected[caller][index] = search(test_case, 1);
        }
    }

    std::atomic<bool> stop_clearer{false};
    std::atomic<bool> failed{false};
    std::thread clearer([&stop_clearer]() {
        while (!stop_clearer.load(std::memory_order_relaxed)) {
            ds_clear_cache();
            std::this_thread::yield();
        }
    });
    std::array<std::thread, 4> callers;
    for (std::size_t caller = 0; caller < callers.size(); ++caller) {
        callers[caller] = std::thread([caller, &expected, &failed]() {
            try {
                for (std::size_t index = 0; index < kCases.size(); ++index) {
                    Case test_case = kCases[index];
                    test_case.modulus =
                        (caller + index) % 2U == 0U ? 819 : 63;
                    if (!equal(expected[caller][index], search(test_case, 4))) {
                        failed.store(true, std::memory_order_relaxed);
                        return;
                    }
                }
            } catch (...) {
                failed.store(true, std::memory_order_relaxed);
            }
        });
    }
    for (std::thread& caller : callers) {
        caller.join();
    }
    stop_clearer.store(true, std::memory_order_relaxed);
    clearer.join();
    if (failed.load(std::memory_order_relaxed)) {
        std::cerr << "mismatch in concurrent stress\n";
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
