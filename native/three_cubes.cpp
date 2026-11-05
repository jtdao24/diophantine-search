#include "three_cubes.h"

#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <mutex>
#include <new>
#include <utility>
#include <vector>

namespace {

constexpr std::int64_t kMaxBound = 1'454'083;
constexpr std::int64_t kMaxModulus = 100'000;
constexpr std::int64_t kMaxTableEntries = 5'000'000;

struct Table {
    std::int64_t modulus;
    std::vector<std::int32_t> offsets;
    std::vector<std::int32_t> data;
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

int search_impl(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
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
    for (std::int64_t x = -bound; x <= x_upper; ++x) {
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
        const std::int32_t class_start = table->offsets[table_index];
        const std::int32_t class_end = table->offsets[table_index + 1U];
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
                    table->data[static_cast<std::size_t>(position)]
                );
                if (y < low) {
                    continue;
                }
                if (y > high) {
                    break;
                }

                ++(*checked);
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
                    if (*count < capacity) {
                        const std::size_t output_index =
                            static_cast<std::size_t>(*count) * 3U;
                        out[output_index] = x;
                        out[output_index + 1U] = y;
                        out[output_index + 2U] = z;
                    }
                    ++(*count);
                }
            }
        }
    }
    return *count > capacity ? 1 : 0;
}

}  // namespace

int ds_abi_version(void) {
    return 1;
}

int ds_cube_root_search(
    std::int64_t k,
    std::int64_t bound,
    std::int64_t modulus,
    std::int64_t* out,
    std::int64_t capacity,
    std::int64_t* count,
    std::int64_t* checked
) {
    try {
        return search_impl(k, bound, modulus, out, capacity, count, checked);
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
