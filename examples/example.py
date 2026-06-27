"""
Copyright Epic Games, Inc. All Rights Reserved.

Example showing how to execute basic workflow using Fluent API
"""

import sys
import uuid

from lore.types import LoreLogConfig
from lore.types.args import (
    LoreBranchPushArgs,
    LoreFileStageArgs,
    LoreGlobalArgs,
    LoreRepositoryCloneArgs,
    LoreRepositoryCreateArgs,
    LoreRevisionCommitArgs,
)
from lore.types.enums import LoreLogLevel, LoreEventTag
from lore.types.events import LoreEventFFI
from lore import Lore, LoreError


def logger(lore_event: LoreEventFFI, _user_context):
    """Global log event handler"""
    event = lore_event.get_data()
    if event.level > LoreLogLevel.DEBUG:
        print(event.message)


def event_handler(lore_event: LoreEventFFI, _user_context):
    """Handle callback events"""
    # No-op: kept for symmetry with the native example. Auth events are not
    # produced because this example does not perform authentication.
    _ = lore_event


def create_files():
    """Generate random files to commit to repository"""
    for file in PATHS:
        with open(file, "w", encoding="utf8") as f:
            f.write(
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et"
            )


# If a remote URL is provided as the first CLI arg, run in online mode (push
# the revision and clone the repository back). Otherwise run a fully offline
# example that only creates a local repository and commits a file.
# Authentication is not handled by this example; if the remote requires it,
# run `lore auth` before invoking this script.
REMOTE_URL = sys.argv[1] if len(sys.argv) > 1 else None
ONLINE = REMOTE_URL is not None

if ONLINE:
    print(f"Running in online mode against: {REMOTE_URL}")
else:
    print(
        "Running in offline mode (pass a remote URL as the first arg to enable push/clone)"
    )

# Set up general configuration
LOG_FILE_PATH = "./LoreRepositories"
REPOSITORY_NAME = "EpicRepo" + str(uuid.uuid4())
REPOSITORY_URL = (
    f"{REMOTE_URL}/{REPOSITORY_NAME}" if ONLINE else REPOSITORY_NAME
)
REPOSITORY_PATH = f"./LoreRepositories/{REPOSITORY_NAME}"
GLOBALS = LoreGlobalArgs(repository_path=REPOSITORY_PATH, offline=not ONLINE)
LOG_CONFIG = LoreLogConfig(file=True, file_path=LOG_FILE_PATH)
PATHS = [
    f"./LoreRepositories/{REPOSITORY_NAME}/file.txt",
    f"./LoreRepositories/{REPOSITORY_NAME}/log.txt",
]


# Lore operations raise a LoreError when they finish with a non-zero return
# code; the exception message carries the underlying error detail. A single
# try/except around the workflow is all that is needed to handle failures.
try:
    # Initialize Lore
    Lore.log_configure(LOG_CONFIG)

    # Configure global log handler
    Lore.global_callback(LoreEventTag.LOG, logger)

    # Create repository
    Lore.repository_create(
        GLOBALS, LoreRepositoryCreateArgs(repository_url=REPOSITORY_URL)
    ).callback(event_handler).wait()
    print("Repository created.")

    # Create files to commit to the new repository
    create_files()

    # Stage files
    Lore.file_stage(GLOBALS, LoreFileStageArgs(paths=PATHS)).callback(
        event_handler
    ).wait()
    print("Files staged.")

    # Revision commit
    Lore.revision_commit(
        GLOBALS, LoreRevisionCommitArgs(message="Initial commit")
    ).callback(event_handler).wait()
    print("Revision committed.")

    if ONLINE:
        # Branch push
        Lore.branch_push(GLOBALS, LoreBranchPushArgs()).callback(event_handler).wait()
        print("Branch pushed.")

        # Clone repository back
        globals_clone = LoreGlobalArgs(repository_path=REPOSITORY_PATH + "_clone")
        Lore.repository_clone(
            globals_clone, LoreRepositoryCloneArgs(repository_url=REPOSITORY_URL)
        ).callback(event_handler).wait()
        print("Repository cloned.")

    Lore.shutdown()
    print("Done.")
except LoreError as error:
    print(f"Lore operation failed: {error}")
    exit(1)
