import pytest

from lore import _loreffi
from lore.types import (
    LoreAddress,
    LoreFragment,
    LoreMetadata,
    LoreHash,
    LoreContext,
    LoreBranchId,
    LorePartition,
    LoreRepositoryId,
)
from lore.types.enums import LoreErrorCode, LoreLogLevel
from lore.types.events import (
    LoreBranchCreateEventDataFFI,
    LoreBranchLatestListEntryEventDataFFI,
    LoreErrorEventDataFFI,
    LoreFragmentWriteEventDataFFI,
    LoreLogEventDataFFI,
    LoreMetadataEventDataFFI,
    LoreNotificationResourceUnlockedEventDataFFI,
    LoreRevisionInfoEventDataFFI,
    LoreStorageCopyItemCompleteEventDataFFI,
    LoreStorageGetDataEventDataFFI,
    LoreStorageGetHeaderEventDataFFI,
    LoreStorageGetItemCompleteEventDataFFI,
    LoreStorageObliterateItemCompleteEventDataFFI,
    LoreStorageOpenedEventDataFFI,
    LoreStoragePutItemCompleteEventDataFFI,
    LoreStorageUploadItemCompleteEventDataFFI,
)


def test_lore_error_event_data():
    text = "Lore error".encode("utf-8")
    text_cdata = _loreffi.new("char[]", text)
    text_string_cdata = _loreffi.new("lore_string_t*")
    text_string_cdata.string = text_cdata
    text_string_cdata.length = len(text)

    error_event_type = _loreffi.new("lore_error_event_data_t*")
    error_event_type.error_type = 0
    error_event_type.error_inner = text_string_cdata[0]

    event = LoreErrorEventDataFFI.from_ffi(error_event_type, {"disposed": False})

    assert isinstance(event, LoreErrorEventDataFFI)
    assert event.error_type == 0
    assert isinstance(event.error_inner, str)
    assert event.error_inner == "Lore error"
    assert len(event.error_inner) == 10


def test_lore_metadata_event_data():
    key = "message".encode("utf-8")
    key_cdata = _loreffi.new("char[]", key)
    key_string_cdata = _loreffi.new("lore_string_t*")
    key_string_cdata.string = key_cdata
    key_string_cdata.length = len(key)

    tag = 6
    text = "commit message".encode("utf-8")
    text_cdata = _loreffi.new("char[]", text)
    text_string_cdata = _loreffi.new("lore_string_t*")
    text_string_cdata.string = text_cdata
    text_string_cdata.length = len(text)

    metadata_type = _loreffi.new("lore_metadata_t*")
    metadata_type.tag = tag
    metadata_type.string = text_string_cdata[0]

    metadata_event_type = _loreffi.new("lore_metadata_event_data_t*")
    metadata_event_type.key = key_string_cdata[0]
    metadata_event_type.value = metadata_type[0]

    event = LoreMetadataEventDataFFI.from_ffi(metadata_event_type, {"disposed": False})

    assert isinstance(event, LoreMetadataEventDataFFI)
    assert event.key == "message"
    assert isinstance(event.value, LoreMetadata)
    assert event.value.tag == 6
    assert isinstance(event.value.string, str)
    assert event.value.string == "commit message"


def test_lore_branch_create_event_data():
    name = "test-feature".encode("utf-8")
    name_cdata = _loreffi.new("char[]", name)
    name_string_cdata = _loreffi.new("lore_string_t*")
    name_string_cdata.string = name_cdata
    name_string_cdata.length = len(name)

    head = list(range(32))
    head_cdata = _loreffi.new("uint8_t[32]", head)
    head_hash_cdata = _loreffi.new("lore_hash_t*")
    head_hash_cdata.data = head_cdata

    branch_create_event_type = _loreffi.new("lore_branch_create_event_data_t*")
    branch_create_event_type.name = name_string_cdata[0]
    branch_create_event_type.latest = head_hash_cdata[0]

    event = LoreBranchCreateEventDataFFI.from_ffi(
        branch_create_event_type, {"disposed": False}
    )

    assert isinstance(event, LoreBranchCreateEventDataFFI)
    assert isinstance(event.name, str)
    assert event.name == "test-feature"
    assert len(event.name) == 12
    assert isinstance(event.latest, LoreHash)
    assert event.latest.data == bytes(range(32))
    assert (
        event.latest.data.hex()
        == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )

    # Clone and verify access after clone
    cloned = event.clone()
    assert cloned.name == "test-feature"
    assert isinstance(cloned.latest, bytes)
    assert len(cloned.latest) == 32
    assert (
        cloned.latest.hex()
        == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )


def test_lore_branch_head_list_entry_event_data():
    branch = list(range(16))
    branch_cdata = _loreffi.new("uint8_t[16]", branch)
    branch_context_cdata = _loreffi.new("lore_context_t*")
    branch_context_cdata.data = branch_cdata

    revision = list(range(32))
    revision_cdata = _loreffi.new("uint8_t[32]", revision)
    revision_hash_cdata = _loreffi.new("lore_hash_t*")
    revision_hash_cdata.data = revision_cdata

    branch_create_event_type = _loreffi.new(
        "lore_branch_latest_list_entry_event_data_t*"
    )
    branch_create_event_type.branch = branch_context_cdata[0]
    branch_create_event_type.revision = revision_hash_cdata[0]

    event = LoreBranchLatestListEntryEventDataFFI.from_ffi(
        branch_create_event_type, {"disposed": False}
    )

    assert isinstance(event, LoreBranchLatestListEntryEventDataFFI)
    assert isinstance(event.branch, LoreBranchId)
    assert event.branch.data == bytes(range(16))
    assert event.branch.data.hex() == "000102030405060708090a0b0c0d0e0f"
    assert isinstance(event.revision, LoreHash)
    assert event.revision.data == bytes(range(32))
    assert (
        event.revision.data.hex()
        == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )

    # Clone and verify Hash/Context accessible as bytes after clone
    cloned = event.clone()
    assert isinstance(cloned.branch, bytes)
    assert len(cloned.branch) == 16
    assert cloned.branch.hex() == "000102030405060708090a0b0c0d0e0f"
    assert isinstance(cloned.revision, bytes)
    assert len(cloned.revision) == 32
    assert (
        cloned.revision.hex()
        == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )


def test_lore_fragment_write_event_data():
    fragment_cdata = _loreffi.new("lore_fragment_t*")
    fragment_cdata.flags = 256
    fragment_cdata.size_payload = 1024
    fragment_cdata.size_content = 8

    fragment_write_event_type = _loreffi.new("lore_fragment_write_event_data_t*")
    fragment_write_event_type.fragment = fragment_cdata[0]
    fragment_write_event_type.deduplicated = True

    event = LoreFragmentWriteEventDataFFI.from_ffi(
        fragment_write_event_type, {"disposed": False}
    )

    assert isinstance(event, LoreFragmentWriteEventDataFFI)
    assert isinstance(event.fragment, LoreFragment)
    assert event.fragment.flags == 256
    assert event.fragment.size_payload == 1024
    assert event.fragment.size_content == 8
    assert event.deduplicated


def test_lore_notification_resource_unlocked_event_data():
    user_id = "root".encode("utf-8")
    user_id_cdata = _loreffi.new("char[]", user_id)
    user_id_string_cdata = _loreffi.new("lore_string_t*")
    user_id_string_cdata.string = user_id_cdata
    user_id_string_cdata.length = len(user_id)

    element1 = "element1".encode("utf-8")
    element1_cdata = _loreffi.new("char[]", element1)
    element1_string_cdata = _loreffi.new("lore_string_t*")
    element1_string_cdata.string = element1_cdata
    element1_string_cdata.length = len(element1)

    element2 = "element2".encode("utf-8")
    element2_cdata = _loreffi.new("char[]", element2)
    element2_string_cdata = _loreffi.new("lore_string_t*")
    element2_string_cdata.string = element2_cdata
    element2_string_cdata.length = len(element2)

    elements_array = [element1_string_cdata[0], element2_string_cdata[0]]
    elements_array_cdata = _loreffi.new("lore_string_t[]", elements_array)
    elements_string_array_cdata = _loreffi.new("lore_string_array_t*")
    elements_string_array_cdata.ptr = elements_array_cdata
    elements_string_array_cdata.count = len(elements_array)

    notification_event_type = _loreffi.new(
        "lore_notification_resource_unlocked_event_data_t*"
    )
    notification_event_type.user_id = user_id_string_cdata[0]
    notification_event_type.paths = elements_string_array_cdata[0]

    event = LoreNotificationResourceUnlockedEventDataFFI.from_ffi(
        notification_event_type, {"disposed": False}
    )

    assert isinstance(event, LoreNotificationResourceUnlockedEventDataFFI)
    assert isinstance(event.user_id, str)
    assert event.user_id == "root"
    assert len(event.user_id) == 4
    assert isinstance(event.paths, list)
    assert len(event.paths) == 2
    assert isinstance(event.paths[0], str)
    assert event.paths[0] == "element1"


def test_ffi_event_data_inaccessible_after_disposal():
    head = list(range(32))
    head_cdata = _loreffi.new("uint8_t[32]", head)
    head_hash_cdata = _loreffi.new("lore_hash_t*")
    head_hash_cdata.data = head_cdata

    name = "test".encode("utf-8")
    name_cdata = _loreffi.new("char[]", name)
    name_string_cdata = _loreffi.new("lore_string_t*")
    name_string_cdata.string = name_cdata
    name_string_cdata.length = len(name)

    cdata = _loreffi.new("lore_branch_create_event_data_t*")
    cdata.name = name_string_cdata[0]
    cdata.latest = head_hash_cdata[0]

    state = {"disposed": False}
    event = LoreBranchCreateEventDataFFI.from_ffi(cdata, state)

    # Accessible before disposal
    assert event.name == "test"
    cloned = event.clone()

    # Simulate disposal
    state["disposed"] = True

    # FFI access should raise
    with pytest.raises(ValueError):
        _ = event.name

    # Cloned data should still be accessible
    assert cloned.name == "test"
    assert len(cloned.latest) == 32


def test_lore_log_event_data():
    location = "test_module".encode("utf-8")
    location_cdata = _loreffi.new("char[]", location)
    location_string_cdata = _loreffi.new("lore_string_t*")
    location_string_cdata.string = location_cdata
    location_string_cdata.length = len(location)

    message = "something happened".encode("utf-8")
    message_cdata = _loreffi.new("char[]", message)
    message_string_cdata = _loreffi.new("lore_string_t*")
    message_string_cdata.string = message_cdata
    message_string_cdata.length = len(message)

    log_event_type = _loreffi.new("lore_log_event_data_t*")
    log_event_type.level = LoreLogLevel.INFO
    log_event_type.category = 42
    log_event_type.timestamp = 1234567890
    log_event_type.location = location_string_cdata[0]
    log_event_type.message = message_string_cdata[0]

    event = LoreLogEventDataFFI.from_ffi(log_event_type, {"disposed": False})

    assert isinstance(event, LoreLogEventDataFFI)
    assert event.level == LoreLogLevel.INFO
    assert event.category == 42
    assert event.timestamp == 1234567890
    assert event.location == "test_module"
    assert event.message == "something happened"

    cloned = event.clone()
    assert cloned.level == LoreLogLevel.INFO
    assert cloned.category == 42
    assert cloned.timestamp == 1234567890
    assert cloned.location == "test_module"
    assert cloned.message == "something happened"


def test_lore_revision_info_event_data():
    repo = list(range(16))
    repo_cdata = _loreffi.new("uint8_t[16]", repo)
    repo_context_cdata = _loreffi.new("lore_repository_id_t*")
    repo_context_cdata.data = repo_cdata

    revision = list(range(32))
    revision_cdata = _loreffi.new("uint8_t[32]", revision)
    revision_hash_cdata = _loreffi.new("lore_hash_t*")
    revision_hash_cdata.data = revision_cdata

    parent0 = list(range(32))
    parent1 = [0xFF] * 32

    revision_info_event_type = _loreffi.new("lore_revision_info_event_data_t*")
    revision_info_event_type.repository = repo_context_cdata[0]
    revision_info_event_type.revision = revision_hash_cdata[0]
    revision_info_event_type.revision_number = 5
    _loreffi.buffer(revision_info_event_type.parent[0].data)[:] = bytes(parent0)
    _loreffi.buffer(revision_info_event_type.parent[1].data)[:] = bytes(parent1)

    event = LoreRevisionInfoEventDataFFI.from_ffi(
        revision_info_event_type, {"disposed": False}
    )

    assert isinstance(event, LoreRevisionInfoEventDataFFI)
    assert isinstance(event.repository, LoreRepositoryId)
    assert event.repository.data == bytes(range(16))
    assert isinstance(event.revision, LoreHash)
    assert event.revision.data == bytes(range(32))
    assert event.revision_number == 5

    parent = event.parent
    assert len(parent) == 2
    assert isinstance(parent[0], LoreHash)
    assert parent[0].data == bytes(range(32))
    assert isinstance(parent[1], LoreHash)
    assert parent[1].data == bytes([0xFF] * 32)

    cloned = event.clone()
    assert cloned.repository == bytes(range(16))
    assert cloned.revision == bytes(range(32))
    assert cloned.revision_number == 5
    assert len(cloned.parent) == 2


def _new_address_cdata(hash_bytes: bytes, context_bytes: bytes):
    cdata = _loreffi.new("lore_address_t*")
    _loreffi.buffer(cdata.hash.data)[:] = hash_bytes
    _loreffi.buffer(cdata.context.data)[:] = context_bytes
    return cdata


def test_lore_storage_opened_event_data():
    cdata = _loreffi.new("lore_storage_opened_event_data_t*")
    cdata.handle_id = 12345

    event = LoreStorageOpenedEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert isinstance(event, LoreStorageOpenedEventDataFFI)
    assert event.handle_id == 12345

    cloned = event.clone()
    assert cloned.handle_id == 12345


def test_lore_storage_put_item_complete_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    cdata = _loreffi.new("lore_storage_put_item_complete_event_data_t*")
    cdata.id = 1
    cdata.address = address_cdata[0]
    cdata.error_code = LoreErrorCode.NONE

    event = LoreStoragePutItemCompleteEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert event.id == 1
    assert isinstance(event.address, LoreAddress)
    assert event.address.hash.data == bytes(range(32))
    assert event.address.context.data == bytes(range(16))
    assert event.error_code == LoreErrorCode.NONE

    cloned = event.clone()
    assert cloned.id == 1
    assert isinstance(cloned.address, LoreAddress)
    assert cloned.address.hash.data == bytes(range(32))
    assert cloned.error_code == LoreErrorCode.NONE


def test_lore_storage_get_header_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    cdata = _loreffi.new("lore_storage_get_header_event_data_t*")
    cdata.id = 3
    cdata.address = address_cdata[0]
    cdata.size_content = 4096

    event = LoreStorageGetHeaderEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert event.id == 3
    assert isinstance(event.address, LoreAddress)
    assert event.address.hash.data == bytes(range(32))
    assert event.size_content == 4096

    cloned = event.clone()
    assert cloned.id == 3
    assert cloned.size_content == 4096


def test_lore_storage_get_data_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    payload = bytes(range(64))
    payload_cdata = _loreffi.new("uint8_t[]", payload)
    bytes_cdata = _loreffi.new("lore_bytes_t*")
    bytes_cdata.ptr = payload_cdata
    bytes_cdata.len = len(payload)

    cdata = _loreffi.new("lore_storage_get_data_event_data_t*")
    cdata.id = 5
    cdata.address = address_cdata[0]
    cdata.offset = 128
    cdata.bytes = bytes_cdata[0]

    event = LoreStorageGetDataEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert event.id == 5
    assert isinstance(event.address, LoreAddress)
    assert event.offset == 128
    assert isinstance(event.bytes, bytes)
    assert event.bytes == payload
    assert len(event.bytes) == 64

    cloned = event.clone()
    assert cloned.id == 5
    assert cloned.offset == 128
    assert cloned.bytes == payload


def test_lore_storage_get_item_complete_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    cdata = _loreffi.new("lore_storage_get_item_complete_event_data_t*")
    cdata.id = 8
    cdata.address = address_cdata[0]
    cdata.error_code = LoreErrorCode.ADDRESS_NOT_FOUND

    event = LoreStorageGetItemCompleteEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert event.id == 8
    assert isinstance(event.address, LoreAddress)
    assert event.error_code == LoreErrorCode.ADDRESS_NOT_FOUND

    cloned = event.clone()
    assert cloned.id == 8
    assert cloned.error_code == LoreErrorCode.ADDRESS_NOT_FOUND


def test_lore_storage_copy_item_complete_event_data():
    source_partition = bytes(range(16))
    target_partition = bytes([0xFF] * 16)
    source_addr_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    source_partition_cdata = _loreffi.new("lore_partition_t*")
    _loreffi.buffer(source_partition_cdata.data)[:] = source_partition

    target_partition_cdata = _loreffi.new("lore_partition_t*")
    _loreffi.buffer(target_partition_cdata.data)[:] = target_partition

    cdata = _loreffi.new("lore_storage_copy_item_complete_event_data_t*")
    cdata.id = 13
    cdata.source_partition = source_partition_cdata[0]
    cdata.target_partition = target_partition_cdata[0]
    cdata.source_address = source_addr_cdata[0]
    cdata.error_code = LoreErrorCode.NONE

    event = LoreStorageCopyItemCompleteEventDataFFI.from_ffi(cdata, {"disposed": False})

    assert event.id == 13
    assert isinstance(event.source_partition, LorePartition)
    assert event.source_partition.data == source_partition
    assert isinstance(event.target_partition, LorePartition)
    assert event.target_partition.data == target_partition
    assert isinstance(event.source_address, LoreAddress)
    assert event.error_code == LoreErrorCode.NONE


def test_lore_storage_obliterate_item_complete_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    cdata = _loreffi.new("lore_storage_obliterate_item_complete_event_data_t*")
    cdata.id = 17
    cdata.address = address_cdata[0]
    cdata.local_success = 1
    cdata.remote_success = 0
    cdata.error_code = LoreErrorCode.INTERNAL

    event = LoreStorageObliterateItemCompleteEventDataFFI.from_ffi(
        cdata, {"disposed": False}
    )

    assert event.id == 17
    assert isinstance(event.address, LoreAddress)
    assert event.local_success
    assert not event.remote_success
    assert event.error_code == LoreErrorCode.INTERNAL


def test_lore_storage_upload_item_complete_event_data():
    address_cdata = _new_address_cdata(bytes(range(32)), bytes(range(16)))

    cdata = _loreffi.new("lore_storage_upload_item_complete_event_data_t*")
    cdata.id = 25
    cdata.address = address_cdata[0]
    cdata.already_durable = 1
    cdata.error_code = LoreErrorCode.NONE

    event = LoreStorageUploadItemCompleteEventDataFFI.from_ffi(
        cdata, {"disposed": False}
    )

    assert event.id == 25
    assert isinstance(event.address, LoreAddress)
    assert event.already_durable
    assert event.error_code == LoreErrorCode.NONE
