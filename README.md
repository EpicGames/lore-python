# Lore Python SDK

## About
This repository contains tools to exend Lore with Python. 

Lore is an open source version control system that is designed for unprecedented scalability of both data and teams. It is optimized for projects that combine code with large binary assets, including games and entertainment, and caters for the needs of developers and artists alike. 

For full Lore documentation, architecture details, and contribution guidelines, visit the [main Lore repository](https://github.com/EpicGames/lore).

## Install

### Stable Release

```shell
python3 -m pip install lore-vcs
```

### Nightly Build

Nightly builds are published to PyPI with a `.devN` suffix. By default `pip` skips pre-releases, so you need to either opt in with `--pre` or pin an exact version. To install the latest nightly:

```shell
python3 -m pip install --pre lore-vcs
```

To install a specific nightly, browse the [release history](https://pypi.org/project/lore-vcs/#history) and pin the exact version:

```shell
python3 -m pip install "lore-vcs==0.1.2.dev345"
```

To upgrade an existing install to the latest nightly:


```shell
python3 -m pip install --pre --upgrade lore-vcs
```



## Minimal example

The top-level `lore` package exposes the high-level fluent API. A low-level, C-like wrapper around the underlying FFI is also available under `lore.native` for advanced use cases.

```python
from lore import Lore
from lore.types import LoreLogConfig
from lore.types.args import LoreGlobalArgs, LoreRepositoryStatusArgs
from lore.types.enums import LoreEventTag, LoreLogLevel
from lore.types.events import LoreEventFFI

Lore.log_configure(
    LoreLogConfig(file=True, file_path="/path/to/log/directory", level=LoreLogLevel.DEBUG)
)

global_args = LoreGlobalArgs(repository_path="/path/to/local/repository")
status_args = LoreRepositoryStatusArgs(staged=True, scan=True)


def on_event(lore_event: LoreEventFFI, _user_context: int):
    if lore_event.tag == LoreEventTag.REPOSITORY_STATUS_FILE:
        print(lore_event.get_data())


Lore.repository_status(global_args, status_args).callback(on_event).wait()
```

For comprehensive examples, see the [examples directory](examples/). Both [examples/example.py](examples/example.py) and [examples/example-native.py](examples/example-native.py) run offline by default; pass a remote URL (e.g. `lore://localhost`) as the first argument to exercise the online push/clone flow. See [examples/README.md](examples/README.md) for details, including how to run a local Lore server.

When running [examples/example.py](examples/example.py) or [examples/example-native.py](examples/example-native.py), set `ON_WINDOWS_LINUX_SUBSYSTEM=True` otherwise WSL fails to open the browser to complete user authentication.


## Contributing

### Set up your dev environment

1. Clone the Lore Python SDK repository:

```shell
git clone https://github.com/EpicGames/lore-python
```

2. Create a virtual environment and activate it:

```shell
uv venv .venv
source .venv/bin/activate
```

3. Install the dev tooling:

```shell
uv pip install --group dev
```

### Get the Lore library

The SDK binds against the Lore C library. Pick one of the two options below depending on whether you're also modifying the Lore core.

#### Option A — build the library from Lore source

Use this when you're changing the Lore C/Rust core alongside the Python SDK.

1. Clone [Lore's repository](https://github.com/EpicGames/lore) and build it:

```shell
cargo build --release
```

2. Set the environment variable `LORE_BUILD_PATH` to point to the release build path:

```shell
export LORE_BUILD_PATH="/<path-to>/lore/target/release"
```

#### Option B — fetch a pre-built Lore library

Use this when you only need to develop the Python SDK against an existing Lore version.

1. Download the header and binaries from [Lore's repository](https://github.com/EpicGames/lore) release page and place them under `/<path-to>/lore/`

2. Set the environment variable `LORE_BUILD_PATH` to point to the download path:

```shell
export LORE_BUILD_PATH="/<path-to>/lore/"
```

### Generate the Python bindings

1. Generate the `lore.types`, `lore.include` and `lore.lib` packages from lore build or fetched pre-built. Use `--no-project` so `uv` does not try to build the `lore-vcs` package which would fail because `lore/types`, `lore/include` and `lore/lib` don't exist yet.

```shell
uv run --no-project python find_lorelib.py
uv run --no-project python generator/generate.py
```

2. Install the package as 'editable'.

```shell
uv pip install -e .
```

3. Any edits you now make to `lore` will be immediately available in your current Python environment. If you change anything under `generator/templates/` or pull a new Lore pre-built binary, re-run step 1 to regenerate the bindings — no second editable install is needed.

#### Why the install is a multi-step process:

> [setup.py](setup.py) declares the packages `lore`, `lore.types`, `lore.include`, and `lore.lib`. Of these, only `lore` is checked into the repo — the other three are produced by `find_lorelib.py` and `generator/generate.py` from a local build.
>
> Setuptools refuses to perform an editable install (`uv pip install -e .`) until those directories exist on disk, so the generator must run _before_ the editable install.
>
> Running `uv pip install -e . --group dev` as a first step would fail with `error: package directory 'lore/types' does not exist`.


### Run the examples

With the dev environment set up, a Lore library available and the Python bindings generated, run an example as a module from the repository root:

```shell
uv run python examples/example.py
uv run python examples/example-native.py
```

### Run the test suite

```shell
uv run pytest
```

### Type-check

```shell
uv run mypy lore
```

`mypy` is configured in strict mode (see `[tool.mypy]` in [pyproject.toml](pyproject.toml)). Run it before opening a PR so type annotations on the public SDK surface stay correct for users.

## Releasing

Assumes the dev environment from [Contributing](#contributing) is set up, that is, the Lore library has been built or fetched and Python bindings regenerated against the version you're releasing.

### Build the wheel

The wheel version is computed from `LORE_VERSION` (and `LORE_REVISION` if set) — make sure they match what was used to generate the bindings.

```shell
uv build
```

The `.whl` lands in `dist/` with a platform-tagged filename (e.g. `lore_vcs-0.1.2.dev345-py3-none-macosx_11_0_arm64.whl`).

### Publish to PyPI

1. Get a PyPI API token from https://pypi.org/manage/account/token/ scoped to the `lore-vcs` project.

2. Publish:

```shell
uv publish --token <pypi-token>
```
