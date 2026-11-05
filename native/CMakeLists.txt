cmake_minimum_required(VERSION 3.20)

project(diophantine_native LANGUAGES CXX)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_library(diophantine_native SHARED three_cubes.cpp)
target_compile_features(diophantine_native PRIVATE cxx_std_20)
set_target_properties(
    diophantine_native
    PROPERTIES
        CXX_EXTENSIONS OFF
        PREFIX ""
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

if(MSVC)
    target_compile_options(diophantine_native PRIVATE /W4)
else()
    target_compile_options(
        diophantine_native
        PRIVATE -Wall -Wextra -Wconversion -Wsign-conversion
    )
endif()

if(MINGW)
    target_link_options(diophantine_native PRIVATE -static)
endif()
