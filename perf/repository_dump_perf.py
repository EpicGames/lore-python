#!/usr/bin/env python3
"""
Copyright Epic Games, Inc. All Rights Reserved.

Performance test for native vs. fluent API event handling in the Python SDK.

Mirrors:
  - urc-js-sdk/src/perf/repository-dump.perf.ts
  - urc-go-sdk/lore_go/cmd/perf-repository-dump/main.go
so the SDKs can be compared head-to-head on per-event FFI overhead.

Run with:

    uv run python perf/repository_dump_perf.py

For stabler numbers on macOS / Linux:

    taskpolicy -c utility uv run python perf/repository_dump_perf.py   # macOS
    nice -n -19           uv run python perf/repository_dump_perf.py   # Linux

Measures the cost of consuming LORE_EVENT_REPOSITORY_STATE_DUMP_NODE events
across four SDK access patterns:
  1. raw native callback (lore.native.lore_repository_dump)
  2. fluent .callback(cb).wait()
  3. fluent .async_iter() (asyncio)
  4. fluent .collect()

Two variants per mode:
  A. accumulate event.size only
  B. accumulate len(name), len(type_data), and every numeric field. Variant B
     forces the LoreString -> Python str decode on the FFI paths (modes 1, 2),
     mirroring the JS variant B's koffi struct decode. Collect / async_iter
     paths (modes 3, 4) pay that decode cost up-front during the SDK's clone
     step, so their variant B is just len() on already-decoded strings.

Each (mode, variant) pair runs in its OWN child Python process so peak RSS
can be attributed cleanly per access pattern. Within one child: warmup +
N_RUNS measured rounds. The parent orchestrates 4 modes × 2 variants = 8
children sequentially. The shared setup (create repo + stage 100k files +
commit) is done once in the parent; children re-open the existing repo via
the --child-repo flag.

Trade-off: we lose per-round cross-mode interleaving (a system blip during
one child only affects that mode's numbers). In exchange the per-mode peak
RSS is no longer polluted by previous modes' allocations.

To eliminate disk-cache variance, point the repo at a ramdisk by setting
LORE_PERF_REPO_PARENT. Defaults to tempfile.gettempdir() otherwise.

    # Linux — /dev/shm is already tmpfs, no setup needed:
    LORE_PERF_REPO_PARENT=/dev/shm uv run python perf/repository_dump_perf.py

    # macOS — create a 4 GB ramdisk once, reuse across runs, then eject:
    diskutil erasevolume APFS perfdisk $(hdiutil attach -nomount ram://8388608)
    LORE_PERF_REPO_PARENT=/Volumes/perfdisk uv run python perf/repository_dump_perf.py
    diskutil eject /Volumes/perfdisk
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

# Allow `python perf/repository_dump_perf.py` from anywhere by putting the
# project root on sys.path. This makes `import lore` resolve to the local
# package (or the editable install pointing at it) rather than a namespace
# collision from some other cwd.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lore import Lore  # noqa: E402
from lore.native import (  # noqa: E402
    lore_repository_dump,
)
from lore.types import LoreEventCallbackConfig  # noqa: E402
from lore.types.args import (  # noqa: E402
    LoreFileStageArgs,
    LoreGlobalArgs,
    LoreRepositoryCreateArgs,
    LoreRepositoryDumpArgs,
    LoreRepositoryFlushArgs,
    LoreRevisionCommitArgs,
)
from lore.types.enums import LoreEventTag  # noqa: E402
from lore.types.events import LoreEventFFI  # noqa: E402

FILE_COUNT = 100_000
FILES_PER_LEAF_DIR = 100
TOP_DIRS = 10
SUB_DIRS = 100
N_RUNS = 10
COOLDOWN_S = 0.5

NODE_TAG = LoreEventTag.REPOSITORY_STATE_DUMP_NODE

MODES = ["native", "fluent-callback", "fluent-async_iter", "fluent-collect"]
VARIANTS = ["A", "B"]

# cffi prints "Input length smaller than expected. Padding with default." to
# stdout during the `from lore import Lore` import. The child uses this
# marker to delimit its JSON output so the parent can find it regardless of
# how much pre-JSON noise the cffi import dumped to stdout.
CHILD_JSON_MARKER = "===PERF_JSON==="


@dataclass
class Pass:
    events: int = 0
    accumulated_size: int = 0
    ms: float = 0.0
    rss_bytes: int = 0
    name_len_total: int = 0
    type_data_len_total: int = 0
    numeric_total: int = 0


def _current_rss_bytes() -> int:
    """macOS-only: shell out to `ps -o rss=` for current RSS in KB -> bytes."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            text=True,
        )
        return int(out.strip()) * 1024
    except (subprocess.CalledProcessError, ValueError):
        return 0


def _process_peak_rss_bytes() -> int:
    """macOS-only: ru_maxrss is in bytes (Linux returns KB, but we're macOS)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _fmt_mb(bytes_: float) -> str:
    return f"{bytes_ / 1024.0 / 1024.0:6.1f} MB"


def make_consumer(p: Pass, variant: str) -> Callable[[object], None]:
    """Return a function that accumulates the right fields for the variant.

    Works on both FFI-backed and cloned event data because both expose the
    same attribute names (.name, .type_data, .id, ...). The FFI dataclass
    decodes properties lazily — accessing .name inside this consumer triggers
    the LoreString -> str decode. The cloned dataclass already has the strings
    materialized.
    """
    if variant == "A":

        def consume_a(data: object) -> None:
            p.events += 1
            p.accumulated_size += data.size  # type: ignore[attr-defined]

        return consume_a

    def consume_b(data: object) -> None:
        p.events += 1
        p.accumulated_size += data.size  # type: ignore[attr-defined]
        p.name_len_total += len(data.name)  # type: ignore[attr-defined]
        p.type_data_len_total += len(data.type_data)  # type: ignore[attr-defined]
        p.numeric_total += (
            data.id  # type: ignore[attr-defined]
            + data.parent  # type: ignore[attr-defined]
            + data.sibling  # type: ignore[attr-defined]
            + data.mode  # type: ignore[attr-defined]
            + data.size  # type: ignore[attr-defined]
            + data.flags  # type: ignore[attr-defined]
        )

    return consume_b


# ---------------------------------------------------------------------------
# Setup (parent-only)
# ---------------------------------------------------------------------------


def _parent_dir() -> tuple[str, str]:
    parent = os.environ.get("LORE_PERF_REPO_PARENT")
    if parent:
        return parent, "(parent from LORE_PERF_REPO_PARENT)"
    return tempfile.gettempdir(), "(parent from tempfile.gettempdir())"


def _pad6(n: int) -> str:
    return f"{n:06d}"


def _pad2(n: int) -> str:
    return f"{n:02d}"


def _create_files(repo_path: str) -> None:
    for top in range(TOP_DIRS):
        for sub in range(SUB_DIRS):
            os.makedirs(os.path.join(repo_path, _pad2(top), _pad2(sub)), exist_ok=True)
    for n in range(FILE_COUNT):
        top = n // 10_000
        sub = (n // FILES_PER_LEAF_DIR) % SUB_DIRS
        name = _pad6(n)
        path = os.path.join(repo_path, _pad2(top), _pad2(sub), f"{name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(name)


def setup_repo() -> tuple[LoreGlobalArgs, str]:
    parent, parent_label = _parent_dir()
    repo_path = tempfile.mkdtemp(prefix="lore-py-sdk-perf-", dir=parent)
    global_args = LoreGlobalArgs(
        repository_path=repo_path,
        correlation_id="perf-repository-dump",
        offline=True,
    )

    log_parent(f"setup: repo at {repo_path} {parent_label}")

    t = time.perf_counter()
    create_args = LoreRepositoryCreateArgs(repository_url=str(uuid.uuid4()))
    rc = Lore.repository_create(global_args, create_args).wait()
    _check_rc("repository_create", rc)
    log_parent(f"setup: repository_create done ({_fmt_since(t)})")

    t = time.perf_counter()
    _create_files(repo_path)
    log_parent(
        f"setup: created {FILE_COUNT} files in {TOP_DIRS * SUB_DIRS} leaf dirs "
        f"({_fmt_since(t)})"
    )

    t = time.perf_counter()
    stage_args = LoreFileStageArgs(paths=[repo_path])
    rc = Lore.file_stage(global_args, stage_args).wait()
    _check_rc("file_stage", rc)
    log_parent(f"setup: file_stage done ({_fmt_since(t)})")

    t = time.perf_counter()
    commit_args = LoreRevisionCommitArgs(message="perf setup")
    rc = Lore.revision_commit(global_args, commit_args).wait()
    _check_rc("revision_commit", rc)
    log_parent(f"setup: revision_commit done ({_fmt_since(t)})")

    t = time.perf_counter()
    flush_args = LoreRepositoryFlushArgs()
    rc = Lore.repository_flush(global_args, flush_args).wait()
    _check_rc("repository_flush", rc)
    log_parent(f"setup: repository_flush done ({_fmt_since(t)})")

    return global_args, repo_path


def teardown(global_args: LoreGlobalArgs, repo_path: str) -> None:
    try:
        Lore.repository_flush(global_args, LoreRepositoryFlushArgs()).wait()
    except Exception as e:  # noqa: BLE001
        print(f"teardown: repository_flush failed: {e}", file=sys.stderr)
    shutil.rmtree(repo_path, ignore_errors=True)


def _check_rc(op: str, rc: int) -> None:
    if rc != 0:
        raise RuntimeError(f"{op} returned non-zero rc={rc}")


# ---------------------------------------------------------------------------
# Runners (one per mode, used by child)
# ---------------------------------------------------------------------------


def run_native(global_args: LoreGlobalArgs, variant: str) -> Pass:
    p = Pass()
    consume = make_consumer(p, variant)

    def on_event(event: LoreEventFFI, _user_context: int) -> None:
        if event.tag != NODE_TAG:
            return
        consume(event.get_data())

    args = LoreRepositoryDumpArgs()
    callback = LoreEventCallbackConfig(func=on_event)
    t0 = time.perf_counter()
    rc = lore_repository_dump(global_args, args, callback)
    p.ms = _ms_since(t0)
    p.rss_bytes = _current_rss_bytes()
    if rc != 0:
        raise RuntimeError(f"native lore_repository_dump rc={rc}")
    return p


def run_fluent_callback(global_args: LoreGlobalArgs, variant: str) -> Pass:
    p = Pass()
    consume = make_consumer(p, variant)

    def on_event(event: LoreEventFFI, _user_context: int) -> None:
        if event.tag != NODE_TAG:
            return
        consume(event.get_data())

    args = LoreRepositoryDumpArgs()
    t0 = time.perf_counter()
    Lore.repository_dump(global_args, args).filter_by_type([NODE_TAG]).callback(
        on_event
    ).wait()
    p.ms = _ms_since(t0)
    p.rss_bytes = _current_rss_bytes()
    return p


def run_fluent_async_iter(global_args: LoreGlobalArgs, variant: str) -> Pass:
    return asyncio.run(_run_fluent_async_iter_impl(global_args, variant))


async def _run_fluent_async_iter_impl(
    global_args: LoreGlobalArgs, variant: str
) -> Pass:
    p = Pass()
    consume = make_consumer(p, variant)
    args = LoreRepositoryDumpArgs()
    t0 = time.perf_counter()
    async for event in (
        Lore.repository_dump(global_args, args).filter_by_type([NODE_TAG]).async_iter()
    ):
        consume(event)
    p.ms = _ms_since(t0)
    p.rss_bytes = _current_rss_bytes()
    return p


def run_fluent_collect(global_args: LoreGlobalArgs, variant: str) -> Pass:
    p = Pass()
    consume = make_consumer(p, variant)
    args = LoreRepositoryDumpArgs()
    t0 = time.perf_counter()
    events = (
        Lore.repository_dump(global_args, args).filter_by_type([NODE_TAG]).collect()
    )
    for event in events:
        consume(event)
    p.ms = _ms_since(t0)
    p.rss_bytes = _current_rss_bytes()
    return p


def run_mode(mode: str, variant: str, global_args: LoreGlobalArgs) -> Pass:
    if mode == "native":
        return run_native(global_args, variant)
    if mode == "fluent-callback":
        return run_fluent_callback(global_args, variant)
    if mode == "fluent-async_iter":
        return run_fluent_async_iter(global_args, variant)
    if mode == "fluent-collect":
        return run_fluent_collect(global_args, variant)
    raise ValueError(f"unknown mode {mode!r}")


# ---------------------------------------------------------------------------
# Child path
# ---------------------------------------------------------------------------


def run_child(mode: str, variant: str, repo_path: str) -> int:
    if mode not in MODES:
        raise ValueError(f"unknown --child-mode {mode!r}")
    if variant not in VARIANTS:
        raise ValueError(f"unknown --child-variant {variant!r}")

    global_args = LoreGlobalArgs(
        repository_path=repo_path,
        correlation_id=f"perf-child-{mode}-{variant}",
        offline=True,
    )

    tag = f"[mode={mode:<22} variant={variant}]"

    # Warmup (untimed in terms of mean stats, but logged to stderr).
    time.sleep(COOLDOWN_S)
    warm = run_mode(mode, variant, global_args)
    log_child(
        f"{tag} warmup    time={_fmt_ms(warm.ms)}  events={warm.events}  "
        f"rss={_fmt_mb(warm.rss_bytes)}"
    )
    # Force a full cycle-collecting GC between rounds so each round's transient
    # garbage doesn't leak into the next round's peakRSS. CPython's refcounting
    # already frees most allocations immediately when their refcount drops to
    # 0; gc.collect() additionally handles reference cycles. Note that pymalloc
    # may not return freed memory to the OS, so peakRSS effects in Python are
    # smaller than in Go (where debug.FreeOSMemory aggressively unmaps).
    gc.collect()

    passes: list[Pass] = []
    for round_idx in range(1, N_RUNS + 1):
        time.sleep(COOLDOWN_S)
        p = run_mode(mode, variant, global_args)
        passes.append(p)
        log_child(
            f"{tag} round={round_idx:2d} time={_fmt_ms(p.ms)}  events={p.events}  "
            f"rss={_fmt_mb(p.rss_bytes)}"
        )
        gc.collect()

    result = {
        "mode": mode,
        "variant": variant,
        "passes": [asdict(p) for p in passes],
        "peakRssBytes": _process_peak_rss_bytes(),
    }
    sys.stdout.write("\n" + CHILD_JSON_MARKER + "\n")
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()
    return 0


# ---------------------------------------------------------------------------
# Parent path
# ---------------------------------------------------------------------------


@dataclass
class ChildResult:
    mode: str
    variant: str
    passes: list[Pass] = field(default_factory=list)
    peak_rss_bytes: int = 0


@dataclass
class VariantResult:
    variant: str
    per_mode: dict[str, ChildResult] = field(default_factory=dict)


def spawn_child(mode: str, variant: str, repo_path: str) -> ChildResult:
    proc = subprocess.run(
        [
            sys.executable,
            __file__,
            "--child-mode",
            mode,
            "--child-variant",
            variant,
            "--child-repo",
            repo_path,
        ],
        stdout=subprocess.PIPE,
        # stderr is inherited from the parent so per-round progress streams live.
        check=True,
    )
    out = proc.stdout.decode("utf-8")
    idx = out.rfind(CHILD_JSON_MARKER)
    if idx < 0:
        preview = out[-500:] if len(out) > 500 else out
        raise RuntimeError(
            f"child stdout missing {CHILD_JSON_MARKER!r}; tail={preview!r}"
        )
    json_text = out[idx + len(CHILD_JSON_MARKER) :].strip()
    data: dict[str, Any] = json.loads(json_text)
    passes = [Pass(**p) for p in data["passes"]]
    return ChildResult(
        mode=data["mode"],
        variant=data["variant"],
        passes=passes,
        peak_rss_bytes=int(data["peakRssBytes"]),
    )


def run_parent() -> int:
    global_args, repo_path = setup_repo()
    try:
        results: list[VariantResult] = []
        for variant in VARIANTS:
            label = (
                "(event.size only)"
                if variant == "A"
                else "(len(name) + len(type_data) + numeric fields)"
            )
            log_parent(
                f"\n--- Variant {variant} {label}: running each mode in its own "
                f"child process ---"
            )
            per_mode: dict[str, ChildResult] = {}
            for mode in MODES:
                time.sleep(COOLDOWN_S)
                per_mode[mode] = spawn_child(mode, variant, repo_path)
            results.append(VariantResult(variant=variant, per_mode=per_mode))

        for r in results:
            check_consistency(r)
        for r in results:
            print_summary(r)
    finally:
        teardown(global_args, repo_path)
    return 0


def check_consistency(result: VariantResult) -> None:
    samples: list[tuple[str, int, Pass]] = []
    for mode in MODES:
        child = result.per_mode.get(mode)
        if not child:
            continue
        for i, p in enumerate(child.passes):
            samples.append((mode, i + 1, p))
    if not samples:
        return
    ref = samples[0][2]
    for mode, round_idx, p in samples:
        if p.events != ref.events:
            log_parent(
                f"  WARN variant {result.variant} {mode} round{round_idx}: "
                f"events={p.events} differs from reference {ref.events}"
            )
        if p.accumulated_size != ref.accumulated_size:
            log_parent(
                f"  WARN variant {result.variant} {mode} round{round_idx}: "
                f"accumulated_size={p.accumulated_size} differs from reference "
                f"{ref.accumulated_size}"
            )
        if result.variant == "B":
            if (
                p.name_len_total != ref.name_len_total
                or p.type_data_len_total != ref.type_data_len_total
                or p.numeric_total != ref.numeric_total
            ):
                log_parent(
                    f"  WARN variant B {mode} round{round_idx}: heavy-field "
                    f"accumulators differ from reference "
                    f"(nameLen={p.name_len_total}/{ref.name_len_total} "
                    f"typeDataLen={p.type_data_len_total}/{ref.type_data_len_total} "
                    f"numeric={p.numeric_total}/{ref.numeric_total})"
                )


def print_summary(result: VariantResult) -> None:
    label = (
        "(event.size only)"
        if result.variant == "A"
        else "(len(name) + len(type_data) + numeric fields)"
    )
    log_parent(
        f"\n=== Variant {result.variant} {label} — "
        f"summary over {N_RUNS} runs per mode (each mode in its own child process) ==="
    )

    # (mode, time_min, time_mean, time_max, eps, peak_rss)
    rows: list[tuple[str, float, float, float, int, int, int]] = []
    for mode in MODES:
        child = result.per_mode.get(mode)
        if not child or not child.passes:
            continue
        times = [p.ms for p in child.passes]
        total_events = sum(p.events for p in child.passes)
        total_ms = sum(times)
        eps = int(total_events * 1000 / total_ms) if total_ms > 0 else 0
        rows.append(
            (
                mode,
                min(times),
                sum(times) / len(times),
                max(times),
                eps,
                child.peak_rss_bytes,
                child.passes[0].events,
            )
        )

    fastest_mean = min(r[2] for r in rows) if rows else 1.0
    for mode, mn, mean, mx, eps, peak_rss, events in rows:
        ratio = mean / fastest_mean if fastest_mean > 0 else 1.0
        log_parent(
            f"mode={mode:<24} events={events}  "
            f"min={_fmt_ms(mn)}  mean={_fmt_ms(mean)}  max={_fmt_ms(mx)}  "
            f"ev/s={eps:>9,}  peakRSS={_fmt_mb(peak_rss)}  (mean {ratio:.2f}x)"
        )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def log_parent(msg: str) -> None:
    print(msg, flush=True)


def log_child(msg: str) -> None:
    """Child writes progress to stderr so stdout stays clean for JSON output."""
    print(msg, file=sys.stderr, flush=True)


def _ms_since(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


def _fmt_ms(ms: float) -> str:
    return f"{ms:7.1f}ms"


def _fmt_since(t0: float) -> str:
    return _fmt_ms(_ms_since(t0))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child-mode", default="")
    parser.add_argument("--child-variant", default="")
    parser.add_argument("--child-repo", default="")
    args = parser.parse_args()

    if args.child_mode:
        return run_child(args.child_mode, args.child_variant, args.child_repo)
    return run_parent()


if __name__ == "__main__":
    sys.exit(main())
