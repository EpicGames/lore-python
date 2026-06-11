"""
Copyright Epic Games, Inc. All Rights Reserved.

Builds lore_py package
"""

import os
import platform
import sys

from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel

LORE_VERSION = os.environ.get("LORE_VERSION")
LORE_REVISION = os.environ.get("LORE_REVISION")
SIBLING_REVISION = os.environ.get("SIBLING_REVISION")
LORE_NAME = os.environ.get("LORE_NAME")
LORE_PACKAGE_NAME = os.environ.get("LORE_PACKAGE_NAME", "lore-vcs")

SYSTEM = platform.system().lower()
MACHINE = platform.machine().lower().replace("x86_64", "amd64")

WINDOWS_LIB_NAME = "lorelib-amd64-unknown-windows.dll"
DARWIN_LIB_NAME = "lorelib-arm64-apple-darwin.dylib"
LINUX_ARM_LIB_NAME = "lorelib-arm64-graviton-linux.so"
LINUX_X64_LIB_NAME = "lorelib-amd64-unknown-linux.so"


def _wheel_lib_name():
    if SYSTEM == "windows":
        return WINDOWS_LIB_NAME
    elif SYSTEM == "linux":
        if MACHINE in ("arm64", "aarch64"):
            return LINUX_ARM_LIB_NAME
        return LINUX_X64_LIB_NAME
    elif SYSTEM == "darwin":
        return DARWIN_LIB_NAME
    else:
        sys.exit(f"unsupported platform found: {SYSTEM}")


class LoreDistribution(Distribution):
    """Lore Distribution"""

    def has_ext_modules(self):
        """Forces platform specific build"""
        return True


class LoreBdist(bdist_wheel):
    """Lore Bdist Tagging"""

    def get_tag(self):
        """Makes the wheel compatible with Python 3.x"""
        _wheel_py, _wheel_py_abi, wheel_platform = super().get_tag()
        return ("py3", "none", wheel_platform)


def _py_version():
    if not LORE_VERSION:
        return "0.1"
    if not LORE_REVISION:
        return f"{LORE_VERSION}+{LORE_NAME}" if LORE_NAME else f"{LORE_VERSION}"

    # Nightly build. Composite builds (Epic/Urc primary + Epic/Lore overlay)
    # carry two revisions: the sibling (Epic/Lore) revision goes in the PEP 440
    # dev segment and the primary (URC) revision in the local (+) segment, so a
    # change in either yields a distinct version and never overwrites a previous
    # release. Open-source builds (Epic/Lore only) have no sibling and keep the
    # single-revision form.
    if SIBLING_REVISION:
        dev = SIBLING_REVISION
        local_parts = [LORE_REVISION]
    else:
        dev = LORE_REVISION
        local_parts = []
    if LORE_NAME:
        local_parts.append(LORE_NAME)

    version = f"{LORE_VERSION}.dev{dev}"
    if local_parts:
        version += "+" + ".".join(local_parts)
    return version


def _py_package():
    return [
        "include/*.h",
        f"lib/{_wheel_lib_name()}",
        "lib/*.txt",  # Lore license/notice files, when present
    ]


setup(
    name=LORE_PACKAGE_NAME,
    version=_py_version(),
    license="MIT",
    author="Epic Games, Inc.",
    classifiers=["Private :: Do Not Upload"],
    python_requires=">=3.10",
    install_requires=["cffi>=2.0.0"],
    packages=["lore", "lore.types", "lore.include", "lore.lib"],
    package_data={"lore": _py_package()},
    include_package_data=True,
    cmdclass={"bdist_wheel": LoreBdist},
    distclass=LoreDistribution,
)
