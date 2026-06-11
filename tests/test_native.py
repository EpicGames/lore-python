import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from lore.native import (
    lore_branch_archive,
    lore_branch_create,
    lore_branch_diff,
    lore_branch_info,
    lore_branch_list,
    lore_branch_merge_resolve_mine,
    lore_branch_merge_start,
    lore_branch_switch,
    lore_file_history,
    lore_file_info,
    lore_file_metadata_list,
    lore_file_metadata_set,
    lore_file_stage,
    lore_file_unstage,
    lore_file_write,
    lore_repository_create,
    lore_repository_create_async,
    lore_repository_instance_list,
    lore_repository_status,
    lore_revision_amend,
    lore_revision_commit,
    lore_revision_diff,
    lore_revision_find,
    lore_revision_history,
    lore_revision_info,
    lore_revision_metadata_list,
    lore_revision_metadata_set,
    lore_shutdown,
    lore_storage_close,
    lore_storage_close_async,
    lore_storage_get,
    lore_storage_get_async,
    lore_storage_open,
    lore_storage_open_async,
    lore_storage_put,
    lore_storage_put_async,
    lore_version,
)
from lore.types import (
    LoreEventCallbackConfig,
    LoreStorageGetItem,
    LoreStoragePutItem,
    LoreStore,
)
from lore.types.args import (
    LoreBranchArchiveArgs,
    LoreBranchCreateArgs,
    LoreBranchDiffArgs,
    LoreBranchInfoArgs,
    LoreBranchListArgs,
    LoreBranchMergeResolveMineArgs,
    LoreBranchMergeStartArgs,
    LoreBranchSwitchArgs,
    LoreFileHistoryArgs,
    LoreFileInfoArgs,
    LoreFileMetadataListArgs,
    LoreFileMetadataSetArgs,
    LoreFileStageArgs,
    LoreFileUnstageArgs,
    LoreFileWriteArgs,
    LoreGlobalArgs,
    LoreRepositoryCreateArgs,
    LoreRepositoryInstanceListArgs,
    LoreRepositoryStatusArgs,
    LoreRevisionAmendArgs,
    LoreRevisionCommitArgs,
    LoreRevisionDiffArgs,
    LoreRevisionFindArgs,
    LoreRevisionHistoryArgs,
    LoreRevisionInfoArgs,
    LoreRevisionMetadataListArgs,
    LoreRevisionMetadataSetArgs,
    LoreStorageCloseArgs,
    LoreStorageGetArgs,
    LoreStorageOpenArgs,
    LoreStoragePutArgs,
)
from lore.types.enums import LoreErrorCode, LoreMetadataType
from lore.types.events import (
    LoreBranchArchiveEventDataFFI,
    LoreBranchCreateEventDataFFI,
    LoreBranchDiffChangeEventDataFFI,
    LoreBranchInfoEventDataFFI,
    LoreBranchListEndEventDataFFI,
    LoreBranchListEntryEventDataFFI,
    LoreBranchMergeConflictFileEventDataFFI,
    LoreEventFFI,
    LoreFileAction,
    LoreFileHistoryEventDataFFI,
    LoreFileInfoEventDataFFI,
    LoreFileStageEndEventDataFFI,
    LoreFileStageFileEventDataFFI,
    LoreFileUnstageEndEventDataFFI,
    LoreLogEventData,
    LoreLogEventDataFFI,
    LoreMetadataEventDataFFI,
    LoreRepositoryInstanceEventDataFFI,
    LoreRepositoryStatusFileEventDataFFI,
    LoreRepositoryStatusRevisionEventDataFFI,
    LoreRevisionCommitEndEventDataFFI,
    LoreRevisionCommitRevisionEventDataFFI,
    LoreRevisionDiffFileEventDataFFI,
    LoreRevisionFindEventDataFFI,
    LoreRevisionHistoryEntryEventDataFFI,
    LoreRevisionInfoEventDataFFI,
    LoreStorageGetDataEventDataFFI,
    LoreStorageGetHeaderEventDataFFI,
    LoreStorageGetItemCompleteEventDataFFI,
    LoreStorageOpenedEventDataFFI,
    LoreStoragePutItemCompleteEventDataFFI,
)


class LoreBase:

    @staticmethod
    def no_op_handler(_event: LoreEventFFI, _user_context: int):
        pass

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.global_args = LoreGlobalArgs()
        self.global_args.offline = True
        self.global_args.repository_path = self.tmp_dir

        self.create_repository()

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        lore_shutdown()

    def create_repository(self):
        args = LoreRepositoryCreateArgs()
        args.repository_url = str(uuid.uuid4())
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        return lore_repository_create(self.global_args, args, callback)

    def create_random_file(self):
        tmp_file = self.tmp_dir + f"/file{str(uuid.uuid4())}.txt"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et"
            )
        return tmp_file

    def file_stage(self, tmp_file, callback_handler):
        args = LoreFileStageArgs()
        args.paths = [tmp_file]
        callback = LoreEventCallbackConfig(func=callback_handler)
        return lore_file_stage(self.global_args, args, callback)

    def file_unstage(self, tmp_file, callback_handler):
        args = LoreFileUnstageArgs()
        args.paths = [tmp_file]
        callback = LoreEventCallbackConfig(func=callback_handler)
        return lore_file_unstage(self.global_args, args, callback)

    def revision_commit(self, callback_handler):
        args = LoreRevisionCommitArgs()
        args.message = "Initial commit"
        callback = LoreEventCallbackConfig(func=callback_handler)
        return lore_revision_commit(self.global_args, args, callback)


class TestLoreVersionCommand:

    def test_lore_version(self):
        version = lore_version()
        assert version != ""


class TestLoreRepositoryStatusCommand(LoreBase):

    _revision_event_received = False
    _file_events: dict[str, object] = {}

    @staticmethod
    def _status_handler(lore_event: LoreEventFFI, _user_context: int):
        event = lore_event.get_data()
        match event:
            case LoreRepositoryStatusRevisionEventDataFFI():
                TestLoreRepositoryStatusCommand._revision_event_received = True
                assert event.branch_name == "main"
            case LoreRepositoryStatusFileEventDataFFI():
                TestLoreRepositoryStatusCommand._file_events[event.path] = {
                    "flag_staged": event.flag_staged,
                    "action": event.action,
                }

    def test_repository_status_works(self):
        TestLoreRepositoryStatusCommand._revision_event_received = False
        TestLoreRepositoryStatusCommand._file_events = {}

        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        args = LoreRepositoryStatusArgs(staged=True, scan=True, sync_point=True)
        callback = LoreEventCallbackConfig(
            func=TestLoreRepositoryStatusCommand._status_handler
        )
        result = lore_repository_status(self.global_args, args, callback)

        assert result == 0
        assert TestLoreRepositoryStatusCommand._revision_event_received

        staged_filename = os.path.basename(tmp_file)
        assert staged_filename in TestLoreRepositoryStatusCommand._file_events
        assert TestLoreRepositoryStatusCommand._file_events[staged_filename][
            "flag_staged"
        ]
        assert (
            TestLoreRepositoryStatusCommand._file_events[staged_filename]["action"]
            == LoreFileAction.ADD
        )


class TestLoreRepositoryCommand:
    _events_ffi: list[LoreEventFFI] = []
    _log_events_ffi: list[LoreLogEventDataFFI] = []
    _log_events: list[LoreLogEventData] = []

    def setup_method(self):
        self.global_args = LoreGlobalArgs()
        self.global_args.offline = True

    def teardown_method(self):
        lore_shutdown()

    def test_create_repository(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        args = LoreRepositoryCreateArgs()
        args.repository_url = str(uuid.uuid4())
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_repository_create(self.global_args, args, callback)

        assert result == 0

    @pytest.mark.asyncio
    async def test_create_repository_async(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        args = LoreRepositoryCreateArgs()
        args.repository_url = str(uuid.uuid4())
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = await lore_repository_create_async(self.global_args, args, callback)

        assert result == 0

    @staticmethod
    def _use_loreeventffi_after_callback_handler(
        lore_event: LoreEventFFI, _user_context: int
    ):
        TestLoreRepositoryCommand._events_ffi.append(lore_event)

    def test_use_loreeventffi_after_callback_throws(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        args = LoreRepositoryCreateArgs(repository_url=str(uuid.uuid4()))
        callback = LoreEventCallbackConfig(
            func=TestLoreRepositoryCommand._use_loreeventffi_after_callback_handler
        )
        result = lore_repository_create(self.global_args, args, callback)

        assert result == 0

        with pytest.raises(ValueError):
            for e in TestLoreRepositoryCommand._events_ffi:
                event = e.get_data()
                if isinstance(event, LoreLogEventDataFFI):
                    print(f"e.tag = {event.message}")

    @staticmethod
    def _use_loreeventdataffi_after_callback_handler(
        lore_event: LoreEventFFI, _user_context: int
    ):
        log_event = lore_event.get_data()
        if isinstance(log_event, LoreLogEventDataFFI):
            TestLoreRepositoryCommand._log_events_ffi.append(log_event)

    def test_use_loreeventdataffi_after_callback_throws(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        args = LoreRepositoryCreateArgs(repository_url=str(uuid.uuid4()))
        callback = LoreEventCallbackConfig(
            func=TestLoreRepositoryCommand._use_loreeventdataffi_after_callback_handler
        )
        result = lore_repository_create(
            self.global_args,
            args,
            callback,
        )

        assert result == 0

        with pytest.raises(ValueError):
            for e in TestLoreRepositoryCommand._log_events_ffi:
                print(f"e.tag = {e.message}")

    @staticmethod
    def _use_loreeventdata_after_callback_handler(
        lore_event: LoreEventFFI, _user_context: int
    ):
        log_event = lore_event.get_data()
        if isinstance(log_event, LoreLogEventDataFFI):
            TestLoreRepositoryCommand._log_events.append(log_event.clone())

    def test_use_loreeventdata_after_callback_throws(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        args = LoreRepositoryCreateArgs(repository_url=str(uuid.uuid4()))
        callback = LoreEventCallbackConfig(
            func=TestLoreRepositoryCommand._use_loreeventdata_after_callback_handler
        )
        result = lore_repository_create(
            self.global_args,
            args,
            callback,
        )

        assert result == 0

        last_log_event = TestLoreRepositoryCommand._log_events[-1]
        assert "Finished command: lore::repository::create" in last_log_event.message


class TestLoreFileCommand(LoreBase):
    _expected_file_describe_filename = ""

    @staticmethod
    def _file_handler(lore_event: LoreEventFFI, _user_context: int):
        event = lore_event.get_data()
        match event:
            case LoreFileStageEndEventDataFFI():
                assert 1 == event.count.file_add_count
                return
            case LoreFileUnstageEndEventDataFFI():
                assert 1 == event.count.file_unstaged_count
                return
            case LoreFileHistoryEventDataFFI():
                assert (
                    os.path.basename(
                        TestLoreFileCommand._expected_file_history_filename
                    )
                    == event.path
                )
                return

    def test_file_stage_works(self):
        tmp_file = self.create_random_file()
        result = self.file_stage(tmp_file, TestLoreFileCommand._file_handler)

        assert result == 0

    def test_file_unstage_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        result = self.file_unstage(tmp_file, TestLoreFileCommand._file_handler)
        assert result == 0

    def test_file_history_works(self):
        TestLoreFileCommand._expected_file_history_filename = self.create_random_file()
        self.file_stage(
            TestLoreFileCommand._expected_file_history_filename, LoreBase.no_op_handler
        )
        self.revision_commit(LoreBase.no_op_handler)

        self.global_args.repository_path = self.tmp_dir

        args = LoreFileHistoryArgs()
        args.path = TestLoreFileCommand._expected_file_history_filename
        callback = LoreEventCallbackConfig(func=TestLoreFileCommand._file_handler)
        result = lore_file_history(self.global_args, args, callback)
        assert result == 0

    def test_file_info_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        file_info_events = []

        def handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreFileInfoEventDataFFI):
                file_info_events.append(event.clone())

        args = LoreFileInfoArgs(paths=[tmp_file])
        callback = LoreEventCallbackConfig(func=handler)
        result = lore_file_info(self.global_args, args, callback)

        assert result == 0
        assert len(file_info_events) == 1
        assert file_info_events[0].is_file
        assert not file_info_events[0].is_dir

    def test_file_write_works(self):
        tmp_file = self.create_random_file()
        version1_content = "Version 1 content"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(version1_content)

        self.file_stage(tmp_file, LoreBase.no_op_handler)

        first_revision_hash = []

        def commit_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionCommitRevisionEventDataFFI):
                first_revision_hash.append(event.revision.data.hex())

        self.revision_commit(commit_handler)
        assert len(first_revision_hash) == 1

        version2_content = "Version 2 content - updated"
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(version2_content)

        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        output_path = tmp_file + ".old"
        args = LoreFileWriteArgs(
            path=tmp_file,
            revision=first_revision_hash[0],
            output=output_path,
        )
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_file_write(self.global_args, args, callback)

        assert result == 0
        with open(output_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        assert old_content == version1_content

    def test_file_metadata_set_and_list_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        set_args = LoreFileMetadataSetArgs(
            paths=[tmp_file],
            keys=["test-key"],
            values=["test-value"],
            formats=[LoreMetadataType.STRING],
            entries=[1],
        )
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_file_metadata_set(self.global_args, set_args, callback)
        assert result == 0

        metadata_events = []

        def list_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreMetadataEventDataFFI):
                metadata_events.append(event.clone())

        list_args = LoreFileMetadataListArgs(path=tmp_file)
        callback = LoreEventCallbackConfig(func=list_handler)
        result = lore_file_metadata_list(self.global_args, list_args, callback)

        assert result == 0
        assert any(
            e.key == "test-key" and e.value.string == "test-value"
            for e in metadata_events
        )


class TestLoreRevisionCommand(LoreBase):
    _expected_test_file_name = ""

    @staticmethod
    def revision_handler(lore_event: LoreEventFFI, _user_context: int):
        event = lore_event.get_data()
        match event:
            case LoreRevisionCommitEndEventDataFFI():
                assert 1 == event.count.file_count
                return
            case LoreRevisionHistoryEntryEventDataFFI():
                assert 1 == event.revision_number
                return

    def test_revision_commit_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        result = self.revision_commit(TestLoreRevisionCommand.revision_handler)
        assert result == 0

    def test_revision_list_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        self.global_args.repository_path = self.tmp_dir

        args = LoreRevisionHistoryArgs()
        callback = LoreEventCallbackConfig(
            func=TestLoreRevisionCommand.revision_handler
        )
        result = lore_revision_history(self.global_args, args, callback)
        assert result == 0

    def test_revision_amend_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        amended_message = "amended commit message"
        args = LoreRevisionAmendArgs(message=amended_message)
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_revision_amend(self.global_args, args, callback)
        assert result == 0

        commit_messages = []

        def history_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreMetadataEventDataFFI):
                if event.key == "message":
                    commit_messages.append(event.value.string)

        args = LoreRevisionHistoryArgs()
        callback = LoreEventCallbackConfig(func=history_handler)
        result = lore_revision_history(self.global_args, args, callback)
        assert result == 0
        assert amended_message in commit_messages

    def test_revision_diff_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        original_revision_hash = []

        def info_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionInfoEventDataFFI):
                original_revision_hash.append(event.revision.data.hex())

        info_args = LoreRevisionInfoArgs()
        callback = LoreEventCallbackConfig(func=info_handler)
        result = lore_revision_info(self.global_args, info_args, callback)
        assert result == 0
        assert len(original_revision_hash) == 1

        new_file = self.create_random_file()
        self.file_stage(new_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        diff_files = []

        def diff_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionDiffFileEventDataFFI):
                diff_files.append(event.clone())

        diff_args = LoreRevisionDiffArgs(revision_source=original_revision_hash[0])
        callback = LoreEventCallbackConfig(func=diff_handler)
        result = lore_revision_diff(self.global_args, diff_args, callback)
        assert result == 0
        assert any(
            os.path.basename(new_file) == f.path and f.action == LoreFileAction.ADD
            for f in diff_files
        )

    def test_revision_info_with_hash_array_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        revision_info = []

        def info_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionInfoEventDataFFI):
                revision_info.append(event.clone())

        args = LoreRevisionInfoArgs()
        callback = LoreEventCallbackConfig(func=info_handler)
        result = lore_revision_info(self.global_args, args, callback)

        assert result == 0
        assert len(revision_info) == 1
        assert revision_info[0].revision_number == 1
        assert len(revision_info[0].revision) == 32
        assert isinstance(revision_info[0].parent, list)

    def test_revision_metadata_set_and_list_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        set_args = LoreRevisionMetadataSetArgs(
            keys=["custom-key"],
            values=["custom-value"],
            formats=[LoreMetadataType.STRING],
        )
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_revision_metadata_set(self.global_args, set_args, callback)
        assert result == 0

        self.revision_commit(LoreBase.no_op_handler)

        metadata_entries = []

        def list_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreMetadataEventDataFFI):
                metadata_entries.append(event.clone())

        list_args = LoreRevisionMetadataListArgs()
        callback = LoreEventCallbackConfig(func=list_handler)
        result = lore_revision_metadata_list(self.global_args, list_args, callback)

        assert result == 0
        assert any(
            e.key == "custom-key" and e.value.string == "custom-value"
            for e in metadata_entries
        )

    def test_revision_find_by_metadata_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)

        set_args = LoreRevisionMetadataSetArgs(
            keys=["search-key"],
            values=["search-value"],
            formats=[LoreMetadataType.STRING],
        )
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_revision_metadata_set(self.global_args, set_args, callback)
        assert result == 0

        self.revision_commit(LoreBase.no_op_handler)

        find_results = []

        def find_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionFindEventDataFFI):
                find_results.append(event.clone())

        find_args = LoreRevisionFindArgs(key="search-key", value="search-value")
        callback = LoreEventCallbackConfig(func=find_handler)
        result = lore_revision_find(self.global_args, find_args, callback)

        assert result == 0
        assert len(find_results) == 1
        assert len(find_results[0].signature) == 32

    def test_revision_find_by_number_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        find_results = []

        def find_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreRevisionFindEventDataFFI):
                find_results.append(event.clone())

        find_args = LoreRevisionFindArgs(number=1)
        callback = LoreEventCallbackConfig(func=find_handler)
        result = lore_revision_find(self.global_args, find_args, callback)

        assert result == 0
        assert len(find_results) == 1
        assert len(find_results[0].signature) == 32


class TestLoreBranchCommand(LoreBase):
    _expected_branch_name = "test-branch"
    _expected_test_file_name = ""

    @staticmethod
    def branch_handler(lore_event: LoreEventFFI, _user_context: int):
        event = lore_event.get_data()
        match event:
            case LoreBranchCreateEventDataFFI():
                assert TestLoreBranchCommand._expected_branch_name == event.name
                return
            case ():
                print(f"---> {event.branch.name}")
                assert "main" == event.branch.name
                return
            case LoreBranchListEntryEventDataFFI():
                if event.name == "main":
                    assert not event.stack
                else:
                    assert 1 == len(event.stack)
                    assert 16 == len(event.stack[0].branch.data)
                    assert 32 == len(event.stack[0].revision.data)
                return
            case LoreBranchListEndEventDataFFI():
                assert 2 == event.count
                return
            case LoreBranchDiffChangeEventDataFFI():
                assert (
                    TestLoreBranchCommand._expected_test_file_name == event.change.path
                )
                assert LoreFileAction.ADD, event.change.action
                return
            case LoreBranchArchiveEventDataFFI():
                assert TestLoreBranchCommand._expected_branch_name == event.name
                return

    def branch_create(self, callback_handler):
        self.global_args.repository_path = self.tmp_dir

        args = LoreBranchCreateArgs(
            branch=TestLoreBranchCommand._expected_branch_name,
        )
        callback = LoreEventCallbackConfig(func=callback_handler)
        return lore_branch_create(self.global_args, args, callback)

    def branch_switch(self, callback_handler):
        self.global_args.repository_path = self.tmp_dir

        args = LoreBranchSwitchArgs(branch="main")
        callback = LoreEventCallbackConfig(func=callback_handler)
        return lore_branch_switch(self.global_args, args, callback)

    def test_branch_create_works(self):
        TestLoreBranchCommand._expected_test_file_name = self.create_random_file()
        self.file_stage(
            TestLoreBranchCommand._expected_test_file_name, LoreBase.no_op_handler
        )
        self.revision_commit(LoreBase.no_op_handler)

        result = self.branch_create(TestLoreBranchCommand.branch_handler)
        assert result == 0

    def test_branch_diff_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)
        self.branch_create(LoreBase.no_op_handler)

        self.global_args.repository_path = self.tmp_dir

        args = LoreBranchDiffArgs(target="main")
        callback = LoreEventCallbackConfig(func=TestLoreBranchCommand.branch_handler)
        result = lore_branch_diff(self.global_args, args, callback)

        assert result == 0

    def test_branch_switch_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        self.branch_create(LoreBase.no_op_handler)
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)
        result = self.branch_switch(TestLoreBranchCommand.branch_handler)

        assert result == 0
        assert not Path(tmp_file).exists()

    def test_branch_list_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)
        self.branch_create(LoreBase.no_op_handler)

        self.global_args.repository_path = self.tmp_dir
        args = LoreBranchListArgs()
        callback = LoreEventCallbackConfig(func=TestLoreBranchCommand.branch_handler)
        result = lore_branch_list(self.global_args, args, callback)

        assert result == 0

    def test_branch_archive_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, lambda lore_event, user_context: None)
        self.revision_commit(lambda lore_event, user_context: None)
        self.branch_create(lambda lore_event, user_context: None)
        self.branch_switch(lambda lore_event, user_context: None)

        self.global_args.repository_path = self.tmp_dir
        args = LoreBranchArchiveArgs()
        args.branch = TestLoreBranchCommand._expected_branch_name
        callback = LoreEventCallbackConfig(func=TestLoreBranchCommand.branch_handler)
        result = lore_branch_archive(self.global_args, args, callback)

        assert result == 0

    def test_branch_merge_with_conflict_resolution_works(self):
        feature_branch = "feature-branch"

        # Create and commit a file on main
        conflict_file = self.tmp_dir + "/conflict-file.txt"
        with open(conflict_file, "w", encoding="utf-8") as f:
            f.write("Main branch content")
        self.file_stage(conflict_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        # Create feature branch and commit conflicting content
        args = LoreBranchCreateArgs(branch=feature_branch)
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        lore_branch_create(self.global_args, args, callback)

        with open(conflict_file, "w", encoding="utf-8") as f:
            f.write("Feature branch content")
        self.file_stage(conflict_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        # Switch back to main and commit conflicting content
        args = LoreBranchSwitchArgs(branch="main")
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        lore_branch_switch(self.global_args, args, callback)

        with open(conflict_file, "w", encoding="utf-8") as f:
            f.write("Main branch conflicting content")
        self.file_stage(conflict_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        # Start merge
        conflict_paths = []

        def merge_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreBranchMergeConflictFileEventDataFFI):
                conflict_paths.append(event.path)

        merge_args = LoreBranchMergeStartArgs(
            branch=feature_branch,
            message="merge feature branch",
        )
        callback = LoreEventCallbackConfig(func=merge_handler)
        result = lore_branch_merge_start(self.global_args, merge_args, callback)
        assert result == 0
        assert len(conflict_paths) > 0

        # Resolve conflict using "mine"
        stage_file_events = []

        def resolve_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreFileStageFileEventDataFFI):
                stage_file_events.append(event.path)

        resolve_args = LoreBranchMergeResolveMineArgs(paths=[conflict_file])
        callback = LoreEventCallbackConfig(func=resolve_handler)
        result = lore_branch_merge_resolve_mine(
            self.global_args, resolve_args, callback
        )
        assert result == 0
        assert len(stage_file_events) > 0

    def test_branch_unicode_names_works(self):
        unicode_branch = "feature/\U0001f680-rocket"

        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        args = LoreBranchCreateArgs(branch=unicode_branch)
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_branch_create(self.global_args, args, callback)
        assert result == 0

        branch_names = []

        def list_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreBranchListEntryEventDataFFI):
                branch_names.append(event.name)

        args = LoreBranchListArgs()
        callback = LoreEventCallbackConfig(func=list_handler)
        result = lore_branch_list(self.global_args, args, callback)
        assert result == 0
        assert unicode_branch in branch_names

    def test_branch_info_works(self):
        tmp_file = self.create_random_file()
        self.file_stage(tmp_file, LoreBase.no_op_handler)
        self.revision_commit(LoreBase.no_op_handler)

        branch_info_events = []

        def info_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreBranchInfoEventDataFFI):
                branch_info_events.append(event.clone())

        args = LoreBranchInfoArgs()
        callback = LoreEventCallbackConfig(func=info_handler)
        result = lore_branch_info(self.global_args, args, callback)

        assert result == 0
        assert len(branch_info_events) == 1
        assert branch_info_events[0].name == "main"


class TestLoreUnicodeSupport(LoreBase):

    def test_unicode_in_filenames_content_and_commit_messages(self):
        unicode_filename = "öäÄÅ的ЛЛЛ-こんにちは-\U0001f680.txt"
        unicode_content = "Hello 世界! Привет мир! \U0001f389 日本語, Русский, العربية"
        unicode_commit_message = "add unicode file with öäÄÅ的ЛЛЛ \U0001f680"

        unicode_file = self.tmp_dir + "/" + unicode_filename
        with open(unicode_file, "w", encoding="utf-8") as f:
            f.write(unicode_content)

        # Stage and verify unicode filename in event
        staged_paths = []

        def stage_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreFileStageFileEventDataFFI):
                staged_paths.append(event.path)

        self.file_stage(unicode_file, stage_handler)
        assert unicode_filename in staged_paths

        # Commit with unicode message
        args = LoreRevisionCommitArgs()
        args.message = unicode_commit_message
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_revision_commit(self.global_args, args, callback)
        assert result == 0

        # Verify unicode commit message in history
        commit_messages = []

        def history_handler(lore_event: LoreEventFFI, _user_context: int):
            event = lore_event.get_data()
            if isinstance(event, LoreMetadataEventDataFFI):
                if event.key == "message":
                    commit_messages.append(event.value.string)

        history_args = LoreRevisionHistoryArgs()
        callback = LoreEventCallbackConfig(func=history_handler)
        result = lore_revision_history(self.global_args, history_args, callback)
        assert result == 0
        assert unicode_commit_message in commit_messages

        # Verify unicode content survives round-trip via file write
        output_path = self.tmp_dir + "/unicode_output.txt"
        write_args = LoreFileWriteArgs(path=unicode_file, output=output_path)
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        result = lore_file_write(self.global_args, write_args, callback)
        assert result == 0
        with open(output_path, "r", encoding="utf-8") as f:
            assert f.read() == unicode_content


class TestLoreRepositoryInstanceCommand(LoreBase):
    _instance_events: list = []

    @staticmethod
    def _instance_handler(lore_event: LoreEventFFI, _user_context: int):
        event = lore_event.get_data()
        match event:
            case LoreRepositoryInstanceEventDataFFI():
                TestLoreRepositoryInstanceCommand._instance_events.append(event.clone())

    def test_repository_instance_list(self):
        TestLoreRepositoryInstanceCommand._instance_events = []
        args = LoreRepositoryInstanceListArgs()
        callback = LoreEventCallbackConfig(
            func=TestLoreRepositoryInstanceCommand._instance_handler
        )
        result = lore_repository_instance_list(self.global_args, args, callback)
        assert result == 0
        assert len(TestLoreRepositoryInstanceCommand._instance_events) >= 1
        event = TestLoreRepositoryInstanceCommand._instance_events[0]
        assert event.path != ""


class TestLoreStorageCommand:
    """Storage API tests using in-memory mode (no on-disk repo required)."""

    _PARTITION = bytes(range(16))
    _CONTEXT = bytes(range(16))

    def setup_method(self):
        self.global_args = LoreGlobalArgs()
        self.global_args.offline = True

    def teardown_method(self):
        lore_shutdown()

    def _open_in_memory(self) -> int:
        opened_handles: list[int] = []

        def handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStorageOpenedEventDataFFI):
                opened_handles.append(event.handle_id)

        args = LoreStorageOpenArgs(repository_path="", in_memory=True)
        callback = LoreEventCallbackConfig(func=handler)
        result = lore_storage_open(self.global_args, args, callback)
        assert result == 0
        assert len(opened_handles) == 1
        assert opened_handles[0] != 0
        return opened_handles[0]

    def _close(self, handle: int) -> int:
        args = LoreStorageCloseArgs(handle=handle)
        callback = LoreEventCallbackConfig(func=LoreBase.no_op_handler)
        return lore_storage_close(self.global_args, args, callback)

    def test_storage_open_in_memory_works(self):
        handle = self._open_in_memory()
        assert self._close(handle) == 0

    def test_storage_close_works(self):
        handle = self._open_in_memory()
        result = self._close(handle)
        assert result == 0

    def test_storage_put_works(self):
        handle = self._open_in_memory()
        try:
            put_completes: list = []

            def handler(lore_event: LoreEventFFI, _ctx: int):
                event = lore_event.get_data()
                if isinstance(event, LoreStoragePutItemCompleteEventDataFFI):
                    put_completes.append(event.clone())

            put_item = LoreStoragePutItem(
                id=1,
                partition=self._PARTITION,
                context=self._CONTEXT,
                data=b"hello storage",
                remote_write=False,
            )
            args = LoreStoragePutArgs(handle=handle, items=[put_item])
            callback = LoreEventCallbackConfig(func=handler)
            result = lore_storage_put(self.global_args, args, callback)

            assert result == 0
            assert len(put_completes) == 1
            assert put_completes[0].id == 1
            assert put_completes[0].error_code == LoreErrorCode.NONE
        finally:
            self._close(handle)

    def test_storage_put_get_roundtrip(self):
        handle = self._open_in_memory()
        try:
            payload = b"roundtrip payload bytes"
            put_completes: list = []

            def put_handler(lore_event: LoreEventFFI, _ctx: int):
                event = lore_event.get_data()
                if isinstance(event, LoreStoragePutItemCompleteEventDataFFI):
                    put_completes.append(event.clone())

            put_item = LoreStoragePutItem(
                id=1,
                partition=self._PARTITION,
                context=self._CONTEXT,
                data=payload,
                remote_write=False,
            )
            put_args = LoreStoragePutArgs(handle=handle, items=[put_item])
            assert (
                lore_storage_put(
                    self.global_args,
                    put_args,
                    LoreEventCallbackConfig(func=put_handler),
                )
                == 0
            )
            assert len(put_completes) == 1
            assert put_completes[0].error_code == LoreErrorCode.NONE
            stored_address = put_completes[0].address

            get_headers: list = []
            get_data_chunks: list[bytes] = []
            get_completes: list = []

            def get_handler(lore_event: LoreEventFFI, _ctx: int):
                event = lore_event.get_data()
                if isinstance(event, LoreStorageGetHeaderEventDataFFI):
                    get_headers.append(event.clone())
                elif isinstance(event, LoreStorageGetDataEventDataFFI):
                    get_data_chunks.append(event.bytes)
                elif isinstance(event, LoreStorageGetItemCompleteEventDataFFI):
                    get_completes.append(event.clone())

            get_item = LoreStorageGetItem(
                id=2,
                partition=self._PARTITION,
                address=stored_address,
                streaming=False,
            )
            get_args = LoreStorageGetArgs(handle=handle, items=[get_item])
            assert (
                lore_storage_get(
                    self.global_args,
                    get_args,
                    LoreEventCallbackConfig(func=get_handler),
                )
                == 0
            )

            assert len(get_completes) == 1
            assert get_completes[0].error_code == LoreErrorCode.NONE
            assert len(get_headers) == 1
            assert get_headers[0].size_content == len(payload)
            assert b"".join(get_data_chunks) == payload
        finally:
            self._close(handle)

    def test_storage_get_address_not_found(self):
        handle = self._open_in_memory()
        try:
            from lore.types import LoreAddress

            missing_address = LoreAddress(bytes([0xAA] * 32), bytes([0xBB] * 16))

            get_completes: list = []

            def handler(lore_event: LoreEventFFI, _ctx: int):
                event = lore_event.get_data()
                if isinstance(event, LoreStorageGetItemCompleteEventDataFFI):
                    get_completes.append(event.clone())

            get_item = LoreStorageGetItem(
                id=99,
                partition=self._PARTITION,
                address=missing_address,
                streaming=False,
            )
            get_args = LoreStorageGetArgs(handle=handle, items=[get_item])
            lore_storage_get(
                self.global_args,
                get_args,
                LoreEventCallbackConfig(func=handler),
            )

            assert len(get_completes) == 1
            assert get_completes[0].error_code == LoreErrorCode.ADDRESS_NOT_FOUND
        finally:
            self._close(handle)

    @pytest.mark.asyncio
    async def test_storage_open_async_works(self):
        opened_handles: list[int] = []

        def handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStorageOpenedEventDataFFI):
                opened_handles.append(event.handle_id)

        args = LoreStorageOpenArgs(repository_path="", in_memory=True)
        callback = LoreEventCallbackConfig(func=handler)
        result = await lore_storage_open_async(self.global_args, args, callback)

        assert result == 0
        assert len(opened_handles) == 1
        handle = opened_handles[0]

        close_args = LoreStorageCloseArgs(handle=handle)
        await lore_storage_close_async(
            self.global_args,
            close_args,
            LoreEventCallbackConfig(func=LoreBase.no_op_handler),
        )

    @pytest.mark.asyncio
    async def test_storage_put_get_close_async_roundtrip(self):
        opened_handles: list[int] = []

        def open_handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStorageOpenedEventDataFFI):
                opened_handles.append(event.handle_id)

        await lore_storage_open_async(
            self.global_args,
            LoreStorageOpenArgs(repository_path="", in_memory=True),
            LoreEventCallbackConfig(func=open_handler),
        )
        handle = opened_handles[0]

        put_completes: list = []

        def put_handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStoragePutItemCompleteEventDataFFI):
                put_completes.append(event.clone())

        payload = b"async roundtrip"
        put_item = LoreStoragePutItem(
            id=1,
            partition=self._PARTITION,
            context=self._CONTEXT,
            data=payload,
            remote_write=False,
        )
        await lore_storage_put_async(
            self.global_args,
            LoreStoragePutArgs(handle=handle, items=[put_item]),
            LoreEventCallbackConfig(func=put_handler),
        )
        assert len(put_completes) == 1
        stored_address = put_completes[0].address

        chunks: list[bytes] = []

        def get_handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStorageGetDataEventDataFFI):
                chunks.append(event.bytes)

        get_item = LoreStorageGetItem(
            id=2,
            partition=self._PARTITION,
            address=stored_address,
            streaming=False,
        )
        await lore_storage_get_async(
            self.global_args,
            LoreStorageGetArgs(handle=handle, items=[get_item]),
            LoreEventCallbackConfig(func=get_handler),
        )
        assert b"".join(chunks) == payload

        await lore_storage_close_async(
            self.global_args,
            LoreStorageCloseArgs(handle=handle),
            LoreEventCallbackConfig(func=LoreBase.no_op_handler),
        )

    def test_storage_close_invalid_returns_error(self):
        args = LoreStorageCloseArgs(handle=LoreStore.INVALID.handle_id)
        result = lore_storage_close(
            self.global_args,
            args,
            LoreEventCallbackConfig(func=LoreBase.no_op_handler),
        )
        assert result != 0

    def test_storage_put_invalid_returns_error(self):
        put_completes: list = []

        def handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStoragePutItemCompleteEventDataFFI):
                put_completes.append(event.clone())

        put_item = LoreStoragePutItem(
            id=1,
            partition=self._PARTITION,
            context=self._CONTEXT,
            data=b"never stored",
            remote_write=False,
        )
        args = LoreStoragePutArgs(handle=LoreStore.INVALID.handle_id, items=[put_item])
        result = lore_storage_put(
            self.global_args, args, LoreEventCallbackConfig(func=handler)
        )

        assert result != 0 or all(
            e.error_code != LoreErrorCode.NONE for e in put_completes
        )

    def test_storage_get_invalid_returns_error(self):
        from lore.types import LoreAddress

        get_completes: list = []

        def handler(lore_event: LoreEventFFI, _ctx: int):
            event = lore_event.get_data()
            if isinstance(event, LoreStorageGetItemCompleteEventDataFFI):
                get_completes.append(event.clone())

        get_item = LoreStorageGetItem(
            id=1,
            partition=self._PARTITION,
            address=LoreAddress(bytes(32), bytes(16)),
            streaming=False,
        )
        args = LoreStorageGetArgs(handle=LoreStore.INVALID.handle_id, items=[get_item])
        result = lore_storage_get(
            self.global_args, args, LoreEventCallbackConfig(func=handler)
        )

        assert result != 0 or all(
            e.error_code != LoreErrorCode.NONE for e in get_completes
        )
