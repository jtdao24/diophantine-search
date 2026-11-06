#include "three_cubes.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <new>
#include <system_error>
#include <thread>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kMaxBound = 1'454'083;
constexpr std::int64_t kMaxModulus = 100'000;
constexpr std::int64_t kMaxTableEntries = 5'000'000;
constexpr std::int64_t kMaxThreads = 256;
constexpr std::int64_t kChunk = 64;

struct Table {
    std::int64_t modulus;
    std::vector<std::int32_t> offsets;
    std::vector<std::int32_t> data;
};

struct alignas(64) WorkerState {
    std::vector<std::array<std::int64_t, 3>> solutions;
    std::int64_t checked = 0;
};

std::mutex table_mutex;
std::shared_ptr<const Table> cached_table;

std::int64_t cube(std::int64_t value) noexcept {
    return value * value * value;
}

std::uint64_t unsigned_cube(std::uint64_t value) noexcept {
    return value * value * value;
}

std::int64_t floor_div(std::int64_t value, std::int64_t divisor) noexcept {
    std::int64_t quotient = value / divisor;
    if (value % divisor < 0) {
        --quotient;
    }
    return quotient;
}

std::int64_t nonnegative_mod(
    std::int64_t value, std::int64_t modulus
) noexcept {
    const std::int64_t remainder = value % modulus;
    return remainder < 0 ? remainder + modulus : remainder;
}

std::uint64_t unsigned_icbrt_floor(std::uint64_t value) noexcept {
    if (value < 2U) {
        return value;
    }

    const auto width = std::bit_width(value);
    const auto shift = static_cast<unsigned int>((width + 2) / 3);
    std::uint64_t root = std::uint64_t{1} << shift;
    while (true) {
        const std::uint64_t next =
            (2U * root + value / (root * root)) / 3U;
        if (next >= root) {
            break;
        }
        root = next;
    }

    while (unsigned_cube(root + 1U) <= value) {
        ++root;
    }
    while (unsigned_cube(root) > value) {
        --root;
    }
    return root;
}

std::int64_t icbrt_floor_impl(std::int64_t value) noexcept {
    if (value == std::numeric_limits<std::int64_t>::min()) {
        return -2'097'152;
    }
    if (value >= 0) {
        return static_cast<std::int64_t>(
            unsigned_icbrt_floor(static_cast<std::uint64_t>(value))
        );
    }

    const std::uint64_t magnitude = static_cast<std::uint64_t>(-value);
    const std::uint64_t lower = unsigned_icbrt_floor(magnitude);
    const std::uint64_t ceiling =
        unsigned_cube(lower) == magnitude ? lower : lower + 1U;
    return -static_cast<std::int64_t>(ceiling);
}

std::int64_t icbrt_ceil_impl(std::int64_t value) noexcept {
    if (value == std::numeric_limits<std::int64_t>::min()) {
        return -2'097'152;
    }
    if (value >= 0) {
        const std::uint64_t magnitude = static_cast<std::uint64_t>(value);
        const std::uint64_t lower = unsigned_icbrt_floor(magnitude);
        const std::uint64_t ceiling =
            unsigned_cube(lower) == magnitude ? lower : lower + 1U;
        return static_cast<std::int64_t>(ceiling);
    }
    return -static_cast<std::int64_t>(
        unsigned_icbrt_floor(static_cast<std::uint64_t>(-value))
    );
}

std::vector<std::int32_t> cube_residues(std::int64_t modulus) {
    const std::size_t size = static_cast<std::size_t>(modulus);
    std::vector<std::uint8_t> seen(size, std::uint8_t{0});
    for (std::int64_t candidate = 0; candidate < modulus; ++candidate) {
        const std::int64_t residue = cube(candidate) % modulus;
        seen[static_cast<std::size_t>(residue)] = std::uint8_t{1};
    }

    std::vector<std::int32_t> residues;
    residues.reserve(size);
    for (std::int64_t residue = 0; residue < modulus; ++residue) {
        if (seen[static_cast<std::size_t>(residue)] != 0U) {
            residues.push_back(static_cast<std::int32_t>(residue));
        }
    }
    return residues;
}

std::shared_ptr<const Table> build_table(
    std::int64_t modulus, const std::vector<std::int32_t>& residues
) {
    const std::size_t size = static_cast<std::size_t>(modulus);
    std::vector<std::int32_t> counts(size, 0);
    for (std::int64_t candidate = 0; candidate < modulus; ++candidate) {
        const std::int64_t candidate_cube = cube(candidate);
        for (const std::int32_t residue : residues) {
            const std::int64_t index = nonnegative_mod(
                candidate_cube + static_cast<std::int64_t>(residue), modulus
            );
            ++counts[static_cast<std::size_t>(index)];
        }
    }

    auto table = std::make_shared<Table>();
    table->modulus = modulus;
    table->offsets.resize(size + 1U, 0);
    for (std::size_t index = 0; index < size; ++index) {
        table->offsets[index + 1U] = table->offsets[index] + counts[index];
    }
    table->data.resize(
        static_cast<std::size_t>(table->offsets.back()), 0
    );
    std::vector<std::int32_t> positions(
        table->offsets.begin(), table->offsets.end() - 1
    );

    // candidate is the stored y class. Visiting it in ascending order means
    // every table entry is already sorted without a separate sorting pass.
    for (std::int64_t candidate = 0; candidate < modulus; ++candidate) {
        const std::int64_t candidate_cube = cube(candidate);
        for (const std::int32_t residue : residues) {
            const std::int64_t index = nonnegative_mod(
                candidate_cube + static_cast<std::int64_t>(residue), modulus
            );
            std::int32_t& position = positions[static_cast<std::size_t>(index)];
            table->data[static_cast<std::size_t>(position)] =
                static_cast<std::int32_t>(candidate);
            ++position;
        }
    }
    return table;
}

std::shared_ptr<const Table> get_table(
    std::int64_t modulus, const std::vector<std::int32_t>& residues
) {
    {
        const std::lock_guard<std::mutex> lock(table_mutex);
        if (cached_table && cached_table->modulus == modulus) {
            return cached_table;
        }
    }

    std::shared_ptr<const Table> built = build_table(modulus, residues);
    const std::lock_guard<std::mutex> lock(table_mutex);
    if (cached_table && cached_table->modulus == modulus) {
        return cached_table;
    }
    cached_table = std::move(built);
    return cached_table;
}

std::size_t cube_index(std::int64_t value, std::int64_t bound) noexcept {
    return static_cast<std::size_t>(value + bound);
}

void process_rows(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
    std::int64_t bound_cube,
    std::int64_t x_begin,
    std::int64_t x_end,
    const std::int64_t* cubes,
    const std::int32_t* offsets,
    const std::int32_t* data,
    WorkerState* state
) {
    std::int64_t local_checked = 0;
    for (std::int64_t x = x_begin; x < x_end; ++x) {
        const std::int64_t rest = k - cubes[cube_index(x, bound)];
        const std::int64_t low = std::max(
            x, icbrt_ceil_impl(rest - bound_cube)
        );
        const std::int64_t high = std::min(
            bound, icbrt_floor_impl(floor_div(rest, 2))
        );
        if (low > high) {
            continue;
        }

        const std::size_t table_index = static_cast<std::size_t>(
            nonnegative_mod(rest, modulus)
        );
        const std::int32_t class_start = offsets[table_index];
        const std::int32_t class_end = offsets[table_index + 1U];
        if (class_start == class_end) {
            continue;
        }

        std::int64_t z = bound;
        const std::int64_t first_base = low - nonnegative_mod(low, modulus);
        for (
            std::int64_t base = first_base;
            base <= high;
            base += modulus
        ) {
            for (
                std::int32_t position = class_start;
                position < class_end;
                ++position
            ) {
                const std::int64_t y = base + static_cast<std::int64_t>(
                    data[static_cast<std::size_t>(position)]
                );
                if (y < low) {
                    continue;
                }
                if (y > high) {
                    break;
                }

                ++local_checked;
                const std::int64_t target =
                    rest - cubes[cube_index(y, bound)];

                // y rises, so target = rest - y^3 strictly falls and z never
                // needs to rise. The lower bound gives target <= B^3, making
                // z = B a valid start. The upper bound gives y^3 <= target,
                // so the pointer stops at z >= y and never leaves the array.
                while (
                    z > -bound && cubes[cube_index(z, bound)] > target
                ) {
                    --z;
                }
                if (cubes[cube_index(z, bound)] == target) {
                    state->solutions.push_back({x, y, z});
                }
            }
        }
    }
    state->checked += local_checked;
}

void run_worker(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
    std::int64_t bound_cube,
    std::int64_t x_upper,
    const std::int64_t* cubes,
    const std::int32_t* offsets,
    const std::int32_t* data,
    std::atomic<std::int64_t>* next,
    std::atomic<bool>* failed,
    WorkerState* state
) noexcept {
    try {
        while (!failed->load(std::memory_order_relaxed)) {
            const std::int64_t start = next->fetch_add(
                kChunk, std::memory_order_relaxed
            );
            if (start > x_upper) {
                break;
            }
            const std::int64_t end = std::min(
                start + kChunk, x_upper + 1
            );
            process_rows(
                k,
                bound,
                modulus,
                bound_cube,
                start,
                end,
                cubes,
                offsets,
                data,
                state
            );
        }
    } catch (const std::bad_alloc&) {
        failed->store(true, std::memory_order_relaxed);
    } catch (...) {
        failed->store(true, std::memory_order_relaxed);
    }
}

int search_impl(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
    std::int64_t requested_threads,
    std::int64_t* out,
    std::int64_t capacity,
    std::int64_t* count,
    std::int64_t* checked
) {
    if (count == nullptr || checked == nullptr) {
        return 2;
    }
    *count = 0;
    *checked = 0;
    if (capacity < 0 || (out == nullptr && capacity > 0)) {
        return 2;
    }
    if (bound < 0 || bound > kMaxBound) {
        return 2;
    }
    if (modulus < 1 || modulus > kMaxModulus) {
        return 2;
    }
    if (requested_threads < 1 || requested_threads > kMaxThreads) {
        return 2;
    }
    if (k == std::numeric_limits<std::int64_t>::min()) {
        return 2;
    }

    const std::int64_t bound_cube = cube(bound);
    const std::int64_t range_margin = 3 * bound_cube;
    const std::int64_t magnitude = k < 0 ? -k : k;
    if (magnitude > std::numeric_limits<std::int64_t>::max() - range_margin) {
        return 2;
    }

    std::shared_ptr<const Table> table;
    {
        const std::lock_guard<std::mutex> lock(table_mutex);
        if (cached_table && cached_table->modulus == modulus) {
            table = cached_table;
        }
    }

    std::vector<std::int32_t> residues;
    if (!table) {
        residues = cube_residues(modulus);
        const std::int64_t table_entries =
            modulus * static_cast<std::int64_t>(residues.size());
        if (table_entries > kMaxTableEntries) {
            return 2;
        }
    }

    const std::int64_t modulo_nine = nonnegative_mod(k, 9);
    if (modulo_nine == 4 || modulo_nine == 5) {
        return 0;
    }

    if (!table) {
        table = get_table(modulus, residues);
    }
    const std::int64_t cube_count = 2 * bound + 1;
    std::vector<std::int64_t> cubes(
        static_cast<std::size_t>(cube_count), 0
    );
    for (std::int64_t value = -bound; value <= bound; ++value) {
        cubes[cube_index(value, bound)] = cube(value);
    }

    const std::int64_t x_upper = std::min(
        bound, icbrt_floor_impl(floor_div(k, 3))
    );
    const std::int64_t x_count = x_upper + bound + 1;
    if (x_count <= 0) {
        return 0;
    }
    const std::int64_t chunk_count = (x_count + kChunk - 1) / kChunk;
    const std::int64_t worker_count = std::max(
        std::int64_t{1}, std::min(requested_threads, chunk_count)
    );

    std::vector<WorkerState> workers(
        static_cast<std::size_t>(worker_count)
    );
    alignas(64) std::atomic<std::int64_t> next{-bound};
    std::atomic<bool> failed{false};
    std::vector<std::thread> worker_threads;
    try {
        worker_threads.reserve(
            static_cast<std::size_t>(worker_count - 1)
        );
    } catch (...) {
    }

    for (std::int64_t index = 1; index < worker_count; ++index) {
        try {
            worker_threads.emplace_back(
                run_worker,
                k,
                bound,
                modulus,
                bound_cube,
                x_upper,
                cubes.data(),
                table->offsets.data(),
                table->data.data(),
                &next,
                &failed,
                &workers[static_cast<std::size_t>(index)]
            );
        } catch (const std::system_error&) {
            break;
        } catch (...) {
            break;
        }
    }

    run_worker(
        k,
        bound,
        modulus,
        bound_cube,
        x_upper,
        cubes.data(),
        table->offsets.data(),
        table->data.data(),
        &next,
        &failed,
        &workers[0]
    );
    for (std::thread& worker : worker_threads) {
        worker.join();
    }
    if (failed.load(std::memory_order_relaxed)) {
        *count = 0;
        *checked = 0;
        return 3;
    }

    std::int64_t total_checked = 0;
    std::size_t solution_count = 0;
    for (const WorkerState& worker : workers) {
        total_checked += worker.checked;
        solution_count += worker.solutions.size();
    }
    std::vector<std::array<std::int64_t, 3>> solutions;
    solutions.reserve(solution_count);
    for (WorkerState& worker : workers) {
        solutions.insert(
            solutions.end(),
            worker.solutions.begin(),
            worker.solutions.end()
        );
    }

    // Every x belongs to exactly one chunk and every chunk to one worker.
    // Solutions and checked rows are determined independently for each x;
    // sorting the concatenated worker output restores lexicographic order.
    std::sort(solutions.begin(), solutions.end());
    *checked = total_checked;
    *count = static_cast<std::int64_t>(solutions.size());
    const std::int64_t copy_count = std::min(*count, capacity);
    for (std::int64_t index = 0; index < copy_count; ++index) {
        const std::size_t solution_index = static_cast<std::size_t>(index);
        const std::size_t output_index = solution_index * 3U;
        out[output_index] = solutions[solution_index][0];
        out[output_index + 1U] = solutions[solution_index][1];
        out[output_index + 2U] = solutions[solution_index][2];
    }
    return *count > capacity ? 1 : 0;
}

}  // namespace

int ds_abi_version(void) {
    return 2;
}

int ds_cube_root_search(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
    std::int64_t threads,
    std::int64_t* out,
    std::int64_t capacity,
    std::int64_t* count,
    std::int64_t* checked
) {
    try {
        return search_impl(
            k, bound, modulus, threads, out, capacity, count, checked
        );
    } catch (const std::bad_alloc&) {
        return 3;
    } catch (...) {
        return 2;
    }
}

void ds_clear_cache(void) {
    try {
        const std::lock_guard<std::mutex> lock(table_mutex);
        cached_table.reset();
    } catch (...) {
    }
}

std::int64_t ds_icbrt_floor(std::int64_t n) {
    return icbrt_floor_impl(n);
}

std::int64_t ds_icbrt_ceil(std::int64_t n) {
    return icbrt_ceil_impl(n);
}
