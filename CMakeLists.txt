cmake_minimum_required(VERSION 3.15...4.3)
project(pyopl LANGUAGES C)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

python_add_library(
    _opl3
    MODULE
    src/pyopl/_opl3.c
    src/pyopl/scheduler.c
    vendor/nuked-opl3/opl3.c
    WITH_SOABI
)

target_include_directories(_opl3 PRIVATE
    src/pyopl
    vendor/nuked-opl3
)

if(MSVC)
    target_compile_options(_opl3 PRIVATE /O2)
else()
    target_compile_options(_opl3 PRIVATE -O2)
endif()

if(UNIX AND NOT APPLE)
    target_link_libraries(_opl3 PRIVATE atomic)
endif()

install(TARGETS _opl3 DESTINATION pyopl)
