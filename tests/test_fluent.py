import pytest
import asyncio
import uuid

from lore import Lore
from lore.types.args import (
    LoreGlobalArgs,
    LoreRepositoryCreateArgs,
    LoreRepositoryStatusArgs,
)
from lore.types.events import LoreCompleteEventData, LoreEndEventData
from lore.types.enums import LoreEventTag


class TestFluentAPI:
    def setup_method(self):
        self.global_args = LoreGlobalArgs()
        self.global_args.offline = True

        self.args = LoreRepositoryCreateArgs()
        self.args.repository_url = str(uuid.uuid4())

    def teardown_method(self):
        Lore.shutdown()

    def test_wait_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        result = Lore.repository_create(self.global_args, self.args).wait()
        assert result == 0

    @pytest.mark.asyncio
    async def test_wait_async_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        task = Lore.repository_create(self.global_args, self.args).wait_async()
        assert task is not None
        result = await task
        assert result == 0

    @pytest.mark.asyncio
    async def test_same_user_context_multiple_wait_async_works(self, tmp_path):
        def check_user_context(lore_event, user_context):
            assert user_context == 123

        tasks = []
        numTasks = 5
        for i in range(numTasks):
            repo_id = str(uuid.uuid4())
            self.global_args.repository_path = str(tmp_path) + repo_id
            self.args.repository_url = repo_id
            task = (
                Lore.repository_create(self.global_args, self.args)
                .callback(check_user_context)
                .user_context(123)
                .wait_async()
            )
            tasks.append(task)

        for i in range(numTasks):
            assert tasks[i] is not None
            result = await tasks[i]
            assert result == 0

    def test_collect_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = Lore.repository_create(self.global_args, self.args).collect()
        assert len(events) > 0

        complete_event = [ce for ce in events if isinstance(ce, LoreCompleteEventData)]
        assert len(complete_event) == 1

    @pytest.mark.asyncio
    async def test_collect_async_throws(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = await Lore.repository_create(
            self.global_args, self.args
        ).collect_async()
        assert len(events) > 0

        complete_event = [ce for ce in events if isinstance(ce, LoreCompleteEventData)]
        assert len(complete_event) == 1

    @pytest.mark.asyncio
    async def test_async_iter_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        event_iterator = Lore.repository_create(
            self.global_args, self.args
        ).async_iter()
        async for event in event_iterator:
            if isinstance(event, LoreCompleteEventData):
                assert event.status == 0

    @pytest.mark.asyncio
    async def test_async_iter_with_filter_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        event_iterator = (
            Lore.repository_create(self.global_args, self.args)
            .filter_by_type([LoreEventTag.COMPLETE])
            .async_iter()
        )
        async for event in event_iterator:
            if isinstance(event, LoreCompleteEventData):
                assert event.status == 0
            else:
                pytest.fail("Got events other than LoreCompleteEventData")

    def test_filter_by_type_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = (
            Lore.repository_create(self.global_args, self.args)
            .filter_by_type([LoreEventTag.COMPLETE, LoreEventTag.END])
            .collect()
        )
        assert len(events) == 2

        complete_event = [ce for ce in events if isinstance(ce, LoreCompleteEventData)]
        assert len(complete_event) == 1
        assert complete_event[0].status == 0

        end_event = [ee for ee in events if isinstance(ee, LoreEndEventData)]
        assert len(end_event) == 1

    def test_user_context_works(self, tmp_path):
        def check_user_context(lore_event, user_context):
            assert user_context == 1234

        self.global_args.repository_path = str(tmp_path)
        result = (
            Lore.repository_create(self.global_args, self.args)
            .user_context(1234)
            .callback(check_user_context)
            .wait()
        )
        assert result == 0

    def test_global_callback_works(self, tmp_path):
        log_events = []

        def logger(lore_event, _user_context):
            assert lore_event.tag == LoreEventTag.LOG
            log_events.append(lore_event.get_data().message)

        unsubscribe = Lore.global_callback(LoreEventTag.LOG, logger)

        self.global_args.repository_path = str(tmp_path)
        Lore.repository_create(self.global_args, self.args).wait()

        log_events_after_first_call = len(log_events)
        assert log_events_after_first_call > 0

        Lore.repository_status(self.global_args, LoreRepositoryStatusArgs()).wait()

        log_events_after_second_call = len(log_events)
        assert log_events_after_second_call > log_events_after_first_call

        # after unsubscribe the global log gatherer should be disabled
        unsubscribe()

        Lore.repository_status(self.global_args, LoreRepositoryStatusArgs()).wait()

        log_events_after_third_call = len(log_events)
        assert log_events_after_third_call == log_events_after_second_call

    def test_wait_nonzero_return_code(self):
        invalid_args = LoreGlobalArgs()
        invalid_args.offline = True
        invalid_args.repository_path = "/tmp/nonexistent-repo-path"
        result = Lore.repository_status(invalid_args, LoreRepositoryStatusArgs()).wait()
        assert result != 0

    def test_collect_nonzero_return_code(self):
        invalid_args = LoreGlobalArgs()
        invalid_args.offline = True
        invalid_args.repository_path = "/tmp/nonexistent-repo-path"
        events = Lore.repository_status(
            invalid_args, LoreRepositoryStatusArgs()
        ).collect()
        complete_events = [e for e in events if isinstance(e, LoreCompleteEventData)]
        assert len(complete_events) == 1
        assert complete_events[0].status != 0

    @pytest.mark.asyncio
    async def test_async_iter_nonzero_return_code(self):
        invalid_args = LoreGlobalArgs()
        invalid_args.offline = True
        invalid_args.repository_path = "/tmp/nonexistent-repo-path"
        events = []
        async for event in Lore.repository_status(
            invalid_args, LoreRepositoryStatusArgs()
        ).async_iter():
            events.append(event)
        complete_events = [e for e in events if isinstance(e, LoreCompleteEventData)]
        assert len(complete_events) == 1
        assert complete_events[0].status != 0

    @pytest.mark.asyncio
    async def test_global_callback_async_works(self, tmp_path):
        log_events = []

        def logger(lore_event, _user_context):
            assert lore_event.tag == LoreEventTag.LOG
            log_events.append(lore_event.get_data().message)

        unsubscribe = Lore.global_callback(LoreEventTag.LOG, logger)

        self.global_args.repository_path = str(tmp_path)
        await Lore.repository_create(self.global_args, self.args).wait_async()

        log_events_after_first_call = len(log_events)
        assert log_events_after_first_call > 0

        await Lore.repository_status(
            self.global_args, LoreRepositoryStatusArgs()
        ).wait_async()

        log_events_after_second_call = len(log_events)
        assert log_events_after_second_call > log_events_after_first_call

        # after unsubscribe the global log gatherer should be disabled
        unsubscribe()

        await Lore.repository_status(
            self.global_args, LoreRepositoryStatusArgs()
        ).wait_async()

        log_events_after_third_call = len(log_events)
        assert log_events_after_third_call == log_events_after_second_call

    def test_cold_handle_no_execution_until_wait(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        callback_called = []

        def handler(lore_event, user_context):
            callback_called.append(True)

        executor = Lore.repository_create(self.global_args, self.args).callback(handler)
        assert len(callback_called) == 0

        executor.wait()
        assert len(callback_called) > 0

    def test_method_chaining_works(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        callback_called = []

        def handler(lore_event, user_context):
            callback_called.append(user_context)

        result = (
            Lore.repository_create(self.global_args, self.args)
            .callback(handler)
            .filter_by_type([LoreEventTag.COMPLETE, LoreEventTag.END])
            .user_context(42)
            .wait()
        )
        assert result == 0
        assert all(ctx == 42 for ctx in callback_called)

    def test_double_wait_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        executor.wait()

        with pytest.raises(RuntimeError, match="Already started"):
            executor.wait()

    def test_double_collect_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        executor.collect()

        with pytest.raises(RuntimeError, match="Already started"):
            executor.collect()

    def test_wait_then_collect_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        executor.wait()

        with pytest.raises(RuntimeError, match="Already started"):
            executor.collect()

    @pytest.mark.asyncio
    async def test_double_async_iter_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        async for _ in executor.async_iter():
            pass

        with pytest.raises(RuntimeError, match="Already started"):
            executor.async_iter()

    @pytest.mark.asyncio
    async def test_wait_then_async_iter_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        executor.wait()

        with pytest.raises(RuntimeError, match="Already started"):
            executor.async_iter()

    @pytest.mark.asyncio
    async def test_async_iter_then_wait_raises(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        executor = Lore.repository_create(self.global_args, self.args)
        async for _ in executor.async_iter():
            pass

        with pytest.raises(RuntimeError, match="Already started"):
            executor.wait()

    def test_collect_with_filter(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = (
            Lore.repository_create(self.global_args, self.args)
            .filter_by_type([LoreEventTag.COMPLETE, LoreEventTag.END])
            .collect()
        )
        assert len(events) == 2
        assert any(isinstance(e, LoreCompleteEventData) for e in events)
        assert any(isinstance(e, LoreEndEventData) for e in events)

    def test_collect_event_data_accessible_outside_callback(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = Lore.repository_create(self.global_args, self.args).collect()

        complete_events = [e for e in events if isinstance(e, LoreCompleteEventData)]
        assert len(complete_events) == 1
        assert complete_events[0].status == 0

        end_events = [e for e in events if isinstance(e, LoreEndEventData)]
        assert len(end_events) == 1

    @pytest.mark.asyncio
    async def test_async_iter_event_data_accessible_outside(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        events = []
        async for event in Lore.repository_create(
            self.global_args, self.args
        ).async_iter():
            events.append(event)

        complete_events = [e for e in events if isinstance(e, LoreCompleteEventData)]
        assert len(complete_events) == 1
        assert complete_events[0].status == 0

        end_events = [e for e in events if isinstance(e, LoreEndEventData)]
        assert len(end_events) == 1

    @pytest.mark.asyncio
    async def test_async_iter_break_early(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        first_event = None
        async for event in Lore.repository_create(
            self.global_args, self.args
        ).async_iter():
            first_event = event
            break

        assert first_event is not None

    def test_multiple_global_callbacks_same_type(self, tmp_path):
        log_events_a = []
        log_events_b = []

        def logger_a(lore_event, _user_context):
            log_events_a.append(True)

        def logger_b(lore_event, _user_context):
            log_events_b.append(True)

        unsub_a = Lore.global_callback(LoreEventTag.LOG, logger_a)
        unsub_b = Lore.global_callback(LoreEventTag.LOG, logger_b)

        self.global_args.repository_path = str(tmp_path)
        Lore.repository_create(self.global_args, self.args).wait()

        assert len(log_events_a) > 0
        assert len(log_events_b) > 0
        assert len(log_events_a) == len(log_events_b)

        unsub_a()
        unsub_b()

    def test_global_callback_ignores_per_call_filter(self, tmp_path):
        log_events = []

        def logger(lore_event, _user_context):
            log_events.append(True)

        unsub = Lore.global_callback(LoreEventTag.LOG, logger)

        self.global_args.repository_path = str(tmp_path)
        Lore.repository_create(self.global_args, self.args).filter_by_type(
            [LoreEventTag.COMPLETE]
        ).wait()

        assert len(log_events) > 0

        unsub()

    def test_wait_without_callback_succeeds(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)
        result = Lore.repository_create(self.global_args, self.args).wait()
        assert result == 0

    def test_complete_and_end_events_emitted_for_all_methods(self, tmp_path):
        self.global_args.repository_path = str(tmp_path)

        # wait + callback
        wait_events = []

        def wait_handler(lore_event, _user_context):
            wait_events.append(lore_event.get_data().clone())

        self.args.repository_url = str(uuid.uuid4())
        Lore.repository_create(self.global_args, self.args).callback(
            wait_handler
        ).wait()
        assert any(isinstance(e, LoreCompleteEventData) for e in wait_events)
        assert any(isinstance(e, LoreEndEventData) for e in wait_events)

        # collect
        self.args.repository_url = str(uuid.uuid4())
        collect_events = Lore.repository_create(self.global_args, self.args).collect()
        assert any(isinstance(e, LoreCompleteEventData) for e in collect_events)
        assert any(isinstance(e, LoreEndEventData) for e in collect_events)

    @pytest.mark.asyncio
    async def test_multiple_parallel_calls(self, tmp_path):
        num_calls = 50
        tasks = []
        for i in range(num_calls):
            repo_id = str(uuid.uuid4())
            global_args = LoreGlobalArgs()
            global_args.offline = True
            global_args.repository_path = str(tmp_path) + f"/repo-{i}"
            args = LoreRepositoryCreateArgs()
            args.repository_url = repo_id
            task = Lore.repository_create(global_args, args).wait_async()
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        assert len(results) == num_calls
        assert all(r == 0 for r in results)
