"""
Copyright Epic Games, Inc. All Rights Reserved.

Generate lorelib wrappers based on Jinja2 template.
"""

import os
import platform
import shutil
import sys
from pathlib import Path
import black
import isort

from common.generate import generate_templates
from registry import build_augmented
import common.visitor

SYSTEM = platform.system().lower()
MACHINE = platform.machine().lower().replace("x86_64", "amd64")

WINDOWS_LIB_NAME = "lorelib-amd64-unknown-windows.dll"
DARWIN_LIB_NAME = "lorelib-arm64-apple-darwin.dylib"
LINUX_ARM_LIB_NAME = "lorelib-arm64-graviton-linux.so"
LINUX_X64_LIB_NAME = "lorelib-amd64-unknown-linux.so"

SCRIPT_DIR = os.path.dirname(__file__)
LORE_HEADER_FILE = os.path.join(SCRIPT_DIR, "../lore/include/lore.h")
LORE_LIBRARY_PATH = os.path.join(SCRIPT_DIR, "../lore/lib")
TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
SDK_DIR = os.path.join(SCRIPT_DIR, "../lore")
SDK_TYPES_DIR = os.path.join(SDK_DIR, "types")

GENERATE_TARGETS = [
    ("enum_types.ji", SDK_TYPES_DIR, "enums.py"),
    ("args_types.ji", SDK_TYPES_DIR, "args.py"),
    ("events_types.ji", SDK_TYPES_DIR, "events.py"),
    ("types.ji", SDK_TYPES_DIR, "__init__.py"),
    ("functions.ji", SDK_DIR, "native.py"),
    ("fluent.ji", SDK_DIR, "fluent.py"),
]


def pretty_print_files(generate_targets):
    """Pretty prints the given Python file and updates it in place"""
    for _, directory, file_name in generate_targets:
        content_filename = os.path.join(directory, file_name)
        path = Path(content_filename)
        black.format_file_in_place(
            src=path, fast=True, mode=black.FileMode(), write_back=black.WriteBack.YES
        )
        isort.file(content_filename, profile="black")


generate_templates(
    LORE_HEADER_FILE,
    TEMPLATES_DIR,
    GENERATE_TARGETS,
    common.visitor.LoreVisitor,
    build_augmented,
)

print("Applying code formatting", end=" ")
pretty_print_files(GENERATE_TARGETS)
print("done.")
