#ifndef DIOPHANTINE_NATIVE_THREE_CUBES_H
#define DIOPHANTINE_NATIVE_THREE_CUBES_H

#include <stdint.h>

#ifdef __cplusplus
#define DS_EXTERN_C extern "C"
#else
#define DS_EXTERN_C
#endif

#ifdef _WIN32
#define DS_API DS_EXTERN_C __declspec(dllexport)
#else
#define DS_API DS_EXTERN_C __attribute__((visibility("default")))
#endif

DS_API int ds_abi_version(void);
DS_API int ds_cube_root_search(
    int64_t k,
    int64_t bound,
    int64_t modulus,
    int64_t threads,
    int64_t* out,
    int64_t capacity,
    int64_t* count,
    int64_t* checked
);
DS_API void ds_clear_cache(void);
DS_API int64_t ds_icbrt_floor(int64_t n);
DS_API int64_t ds_icbrt_ceil(int64_t n);

#endif
