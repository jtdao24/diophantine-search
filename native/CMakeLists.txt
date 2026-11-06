cmake_minimum_required(VERSION 3.20)

project(diophantine_native LANGUAGES CXX)

find_package(Threads REQUIRED)
option(DS_BUILD_STRESS "Build the thread stress program" OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_library(diophantine_native SHARED three_cubes.cpp)
target_link_libraries(diophantine_native PRIVATE Threads::Threads)
set_target_properties(
    diophantine_native
    PROPERTIES
        CXX_EXTENSIONS OFF
        PREFIX ""
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

function(ds_configure_target target)
    target_compile_features(${target} PRIVATE cxx_std_20)
    set_target_properties(${target} PROPERTIES CXX_EXTENSIONS OFF)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4)
    else()
        target_compile_options(
            ${target}
            PRIVATE -Wall -Wextra -Wconversion -Wsign-conversion
        )
    endif()
    if(MINGW)
        target_link_options(${target} PRIVATE -static)
    endif()
endfunction()

ds_configure_target(diophantine_native)

if(DS_BUILD_STRESS)
    add_executable(
        stress_three_cubes
        stress_three_cubes.cpp
        three_cubes.cpp
    )
    target_link_libraries(stress_three_cubes PRIVATE Threads::Threads)
    set_target_properties(
        stress_three_cubes
        PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
    )
    ds_configure_target(stress_three_cubes)
endif()
