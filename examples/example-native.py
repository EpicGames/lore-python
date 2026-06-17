"""
Copyright Epic Games, Inc. All Rights Reserved.

Example showing how to execute basic workflow using lore
"""

import sys
import uuid

from lore.native import (
    lore_branch_push,
    lore_file_stage,
    lore_log_configure,
    lore_repository_clone,
    lore_repository_create,
    lore_revision_commit,
    lore_shutdown,
)
from lore.types import LoreEventCallbackConfig, LoreLogConfig
from lore.types.args import (
    LoreBranchPushArgs,
    LoreFileStageArgs,
    LoreGlobalArgs,
    LoreRepositoryCloneArgs,
    LoreRepositoryCreateArgs,
    LoreRevisionCommitArgs,
)
from lore.types.enums import LoreLogLevel
from lore.types.events import (
    LoreEventFFI,
    LoreLogEventDataFFI,
)


def event_handler(lore_event: LoreEventFFI, _user_context):
    """Handle callback events"""
    event = lore_event.get_data()
    if isinstance(event, LoreLogEventDataFFI):
        if event.level > LoreLogLevel.DEBUG:
            print(event.message)


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
REPOSITORY_URL = f"{REMOTE_URL}/{REPOSITORY_NAME}" if ONLINE else REPOSITORY_NAME
REPOSITORY_PATH = f"./LoreRepositories/{REPOSITORY_NAME}"
GLOBALS = LoreGlobalArgs(repository_path=REPOSITORY_PATH, offline=not ONLINE)
LOG_CONFIG = LoreLogConfig(file=True, file_path=LOG_FILE_PATH)
PATHS = [
    f"./LoreRepositories/{REPOSITORY_NAME}/file.txt",
    f"./LoreRepositories/{REPOSITORY_NAME}/log.txt",
]
CALLBACK_CONFIG = LoreEventCallbackConfig(func=event_handler)


# pylint: disable=missing-function-docstring, redefined-outer-name
def verify_result(operation_name: str, result: int):
    if result != 0:
        print(f"LORE {operation_name} failed.")
        exit(1)
    print(f"LORE {operation_name} success.")


# Initialize LORE
result = lore_log_configure(LOG_CONFIG)
verify_result("LogConfigure", result)

# Create repository
args = LoreRepositoryCreateArgs(
    repository_url=REPOSITORY_URL,
)
result = lore_repository_create(GLOBALS, args, CALLBACK_CONFIG)
verify_result("Repo Create", result)

# Create files to commit to the new repository
create_files()

# Stage file
args = LoreFileStageArgs(
    paths=PATHS,
)
result = lore_file_stage(GLOBALS, args, CALLBACK_CONFIG)
verify_result("File Stage", result)

# Revision commit
args = LoreRevisionCommitArgs(
    message="Initial commit",
)
result = lore_revision_commit(GLOBALS, args, CALLBACK_CONFIG)
verify_result("Revision Commit", result)

if ONLINE:
    # Branch push
    args = LoreBranchPushArgs()
    result = lore_branch_push(GLOBALS, args, CALLBACK_CONFIG)
    verify_result("Branch Push", result)

    # Clone repository
    globals_clone = LoreGlobalArgs(
        repository_path=REPOSITORY_PATH + "_clone",
    )
    args = LoreRepositoryCloneArgs(
        repository_url=REPOSITORY_URL,
    )
    result = lore_repository_clone(globals_clone, args, CALLBACK_CONFIG)
    verify_result("Repository Clone", result)

result = lore_shutdown()
verify_result("Shutdown", result)
