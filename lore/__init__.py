"""
Copyright Epic Games, Inc. All Rights Reserved.

Lore Python Bindings

Loads the Lore dll and parses it's header to provide acccess to Lore functionality
from pythons scripts
"""

import platform
from pathlib import Path

from cffi import FFI


SYSTEM = platform.system().lower()
MACHINE = platform.machine().lower().replace("x86_64", "amd64")

WINDOWS_LIB_NAME = "lorelib-amd64-unknown-windows.dll"
DARWIN_LIB_NAME = "lorelib-arm64-apple-darwin.dylib"
LINUX_ARM_LIB_NAME = "lorelib-arm64-graviton-linux.so"
LINUX_X64_LIB_NAME = "lorelib-amd64-unknown-linux.so"


def _current_lib_name():
    if SYSTEM == "linux":
        if MACHINE in ("arm64", "aarch64"):
            return LINUX_ARM_LIB_NAME
        else:
            return LINUX_X64_LIB_NAME
    elif SYSTEM == "darwin":
        return DARWIN_LIB_NAME
    else:
        return WINDOWS_LIB_NAME


def initialise():
    """Loads lorelib shared library and initialises it for use"""
    package_root = Path(__file__).resolve().parent

    lib_name = _current_lib_name()
    lib_file = package_root.joinpath("lib", lib_name)

    inc_dir = package_root.joinpath("include")
    inc_file = inc_dir.joinpath("lore.h")

    with open(inc_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    contents = "".join(line for line in lines if not line.lstrip().startswith("#"))

    loreffi = FFI()
    loreffi.cdef(contents)
    lore = loreffi.dlopen(str(lib_file))

    return lore, loreffi


_lore, _loreffi = initialise()

# Re-export the fluent API entry points so users can do `from lore_py import Lore`.
# The low-level FFI wrappers remain accessible via `from lore_py.native import ...`.
from .fluent import Lore, LoreError, LoreExecutor  # noqa: E402
