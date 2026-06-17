import pytest

from lore import _loreffi
from lore.types import (
    LoreAddress,
    LoreBinary,
    LoreBranchDiffNodeData,
    LoreBranchId,
    LoreBranchPoint,
    LoreBranchSwitchData,
    LoreBytes,
    LoreContext,
    LoreFragment,
    LoreHash,
    LoreHashArray,
    LoreInstanceIdArray,
    LoreMetadata,
    LorePartition,
    LoreStorageGetItem,
    LoreStorageGetItemArray,
    LoreStoragePutItem,
    LoreStoragePutItemArray,
    LoreStore,
    LoreString,
)
from lore.types.enums import (
    LoreBranchLocation,
    LoreFileAction,
    LoreMetadataTag,
    LoreMetadataType,
)

mymetadatatypearray = [
    LoreMetadataType.BINARY,
    LoreMetadataType.NUMERIC,
    LoreMetadataType.STRING,
]
mycontext = bytes(range(16))
myhash = bytes(range(32))
myintarray = list(range(24))
myaddress = LoreAddress(myhash, mycontext)
mybinary = bytes(range(10))
mybranchpoint = LoreBranchPoint(mycontext, myhash)
mybranchpointarray = [mybranchpoint, mybranchpoint]


def test_lore_metadata_type_array():
    expected_count = 3

    assert len(mymetadatatypearray) == expected_count

    expected_values = [
        LoreMetadataType.BINARY,
        LoreMetadataType.NUMERIC,
        LoreMetadataType.STRING,
    ]

    for idx, elem in enumerate(mymetadatatypearray):
        assert elem == expected_values[idx]


def test_lore_hash():
    expected_value = 0
    for elem in myhash:
        assert elem == expected_value
        expected_value += 1


def test_lore_int_array():
    expected_count = 24
    assert len(myintarray) == expected_count

    expected_value = 0
    for elem in myintarray:
        assert elem == expected_value
        expected_value += 1


def test_lore_address():
    assert isinstance(myaddress.hash, LoreHash)
    assert isinstance(myaddress.context, LoreContext)


def test_lore_address_none_constructor():
    myaddress_wrong = LoreAddress()

    assert (
        myaddress_wrong.hash.data
        == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    assert (
        myaddress_wrong.context.data
        == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )


def test_lore_binary():
    expected_length = 10
    assert len(mybinary) == expected_length

    expected_value = 0
    for elem in mybinary:
        assert elem == expected_value
        expected_value += 1


def test_lore_metadata_address():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.ADDRESS
    cdata.address = myaddress.as_value()
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.ADDRESS
    assert isinstance(mymetadata.address, LoreAddress)
    assert isinstance(mymetadata.address.hash, LoreHash)
    assert isinstance(mymetadata.address.context, LoreContext)


def test_lore_metadata_binary():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.BINARY
    binary = LoreBinary(mybinary)
    cdata.binary = binary.as_value()
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.BINARY
    assert isinstance(mymetadata.binary, bytes)
    assert len(mymetadata.binary) == 10


def test_lore_metadata_boolean():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.BOOLEAN
    cdata.boolean = True
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.BOOLEAN
    assert isinstance(mymetadata.boolean, bool)
    assert mymetadata.boolean


def test_lore_metadata_context():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.CONTEXT
    context = LoreContext(mycontext)
    cdata.context = context.as_value()
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.CONTEXT
    assert isinstance(mymetadata.context, LoreContext)
    assert len(mymetadata.context.data) == 16


def test_lore_metadata_hash():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.HASH
    hash = LoreHash(myhash)
    cdata.hash = hash.as_value()
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.HASH
    assert isinstance(mymetadata.hash, LoreHash)
    assert len(mymetadata.hash.data) == 32


def test_lore_metadata_numeric():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.NUMERIC
    cdata.numeric = 1234
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.NUMERIC
    assert mymetadata.numeric == 1234


def test_lore_metadata_string():
    cdata = _loreffi.new("lore_metadata_t*")
    cdata.tag = LoreMetadataTag.STRING
    string = LoreString("mystring")
    cdata.string = string.as_value()
    mymetadata = LoreMetadata.from_ffi(cdata)

    assert mymetadata.tag == LoreMetadataTag.STRING
    assert isinstance(mymetadata.string, str)
    assert mymetadata.string == "mystring"


def test_lore_fragment():
    myfragment = LoreFragment(1)
    assert myfragment.flags == 1

    myfragment = LoreFragment(1, 2)
    assert myfragment.flags == 1
    assert myfragment.size_payload == 2

    myfragment = LoreFragment(1, 2, 3)
    assert myfragment.flags == 1
    assert myfragment.size_payload == 2
    assert myfragment.size_content == 3


def test_lore_fragment_accessing_unset_properties():
    myfragment = LoreFragment(1)
    assert myfragment.size_payload == 0
    assert myfragment.size_content == 0


def test_lore_fragment_none_constructor():
    myfragment = LoreFragment()
    assert myfragment.flags == 0
    assert myfragment.size_payload == 0
    assert myfragment.size_content == 0


def test_branch_point():
    assert isinstance(mybranchpoint.branch, LoreBranchId)
    assert isinstance(mybranchpoint.revision, LoreHash)


def test_branch_point_none_constructor():
    mybranchpoint_wrong = LoreBranchPoint()

    assert (
        mybranchpoint_wrong.branch.data
        == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    assert (
        mybranchpoint_wrong.revision.data
        == b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    )


def test_lore_hash_hex_encoding():
    hash_bytes = bytes(range(32))
    h = LoreHash(hash_bytes)
    hex_str = h.data.hex()

    expected = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    assert hex_str == expected
    assert len(hex_str) == 64

    all_zeros = LoreHash(bytes(32))
    assert all_zeros.data.hex() == "0" * 64

    all_ff = LoreHash(bytes([0xFF] * 32))
    assert all_ff.data.hex() == "ff" * 32


def test_lore_context_hex_encoding():
    context_bytes = bytes(range(16))
    c = LoreContext(context_bytes)
    hex_str = c.data.hex()

    expected = "000102030405060708090a0b0c0d0e0f"
    assert hex_str == expected
    assert len(hex_str) == 32

    all_zeros = LoreContext(bytes(16))
    assert all_zeros.data.hex() == "0" * 32

    all_ff = LoreContext(bytes([0xFF] * 16))
    assert all_ff.data.hex() == "ff" * 16


def test_lore_branch_diff_node_data():
    node = LoreBranchDiffNodeData(action=LoreFileAction.ADD, path="src/main.py")

    assert node.action == LoreFileAction.ADD
    assert node.path == "src/main.py"

    cloned = node.clone()
    assert cloned.action == LoreFileAction.ADD
    assert cloned.path == "src/main.py"


def test_lore_branch_diff_node_data_from_ffi():
    cdata = _loreffi.new("lore_branch_diff_node_data_t*")
    cdata.action = LoreFileAction.DELETE

    path_str = LoreString("deleted/file.txt")
    cdata.path = path_str.as_value()

    node = LoreBranchDiffNodeData.from_ffi(cdata)
    assert node.action == LoreFileAction.DELETE
    assert node.path == "deleted/file.txt"


def test_lore_branch_switch_data():
    branch_id = bytes(range(16))
    local_hash = bytes(range(32))
    remote_hash = bytes([0xFF] * 32)
    rev_hash = bytes([0xAA] * 32)

    data = LoreBranchSwitchData(
        id=branch_id,
        name="feature-branch",
        latest_local=local_hash,
        latest_remote=remote_hash,
        revision=rev_hash,
        location=LoreBranchLocation.REMOTE,
    )

    assert isinstance(data.id, LoreBranchId)
    assert data.id.data == branch_id
    assert data.name == "feature-branch"
    assert isinstance(data.latest_local, LoreHash)
    assert data.latest_local.data == local_hash
    assert isinstance(data.latest_remote, LoreHash)
    assert data.latest_remote.data == remote_hash
    assert isinstance(data.revision, LoreHash)
    assert data.revision.data == rev_hash
    assert data.location == LoreBranchLocation.REMOTE

    cloned = data.clone()
    assert cloned.name == "feature-branch"
    assert cloned.id.data == branch_id
    assert cloned.latest_local.data == local_hash
    assert cloned.latest_remote.data == remote_hash
    assert cloned.revision.data == rev_hash
    assert cloned.location == LoreBranchLocation.REMOTE


def test_lore_hash_array():
    hash1 = bytes(range(32))
    hash2 = bytes([0xFF] * 32)

    arr = LoreHashArray([hash1, hash2])
    assert len(arr.hashes) == 2

    native = LoreHashArray.to_native(arr.as_ptr())
    assert len(native) == 2
    assert isinstance(native[0], LoreHash)
    assert native[0].data == hash1
    assert isinstance(native[1], LoreHash)
    assert native[1].data == hash2


def test_lore_instance_id_array():
    id1_bytes = bytes(range(16))
    id2_bytes = bytes([0xFF] * 16)

    arr = LoreInstanceIdArray([id1_bytes, id2_bytes])
    assert arr.cdata.count == 2

    native = LoreInstanceIdArray.to_native(arr.as_ptr())
    assert native == [id1_bytes, id2_bytes]


def test_lore_bytes():
    payload = bytes(range(20))
    b = LoreBytes(payload)

    assert b.cdata.len == 20
    assert LoreBytes.to_native(b.as_ptr()) == payload


def test_lore_bytes_empty():
    b = LoreBytes()
    assert b.cdata.len == 0
    assert LoreBytes.to_native(b.as_ptr()) == b""


def test_lore_store():
    store = LoreStore(handle_id=42)

    assert store.handle_id == 42
    assert LoreStore.to_native(store.as_ptr()) == 42


def test_lore_store_default_constructor():
    store = LoreStore()
    assert store.handle_id == 0


def test_lore_store_from_ffi():
    cdata = _loreffi.new("lore_store_t*")
    cdata.handle_id = 99

    store = LoreStore.from_ffi(cdata)
    assert store.handle_id == 99


def test_lore_store_invalid_constant():
    assert isinstance(LoreStore.INVALID, LoreStore)
    assert LoreStore.INVALID.handle_id == 0


def test_lore_storage_put_item():
    partition = bytes(range(16))
    context = bytes(range(16))
    payload = b"hello world"

    item = LoreStoragePutItem(
        id=7,
        partition=partition,
        context=context,
        data=payload,
        remote_write=True,
    )

    assert item.id == 7
    assert isinstance(item.partition, LorePartition)
    assert item.partition.data == partition
    assert isinstance(item.context, LoreContext)
    assert item.context.data == context
    assert item.data == payload
    assert item.remote_write

    cloned = item.clone()
    assert cloned.id == 7
    assert cloned.partition.data == partition
    assert cloned.context.data == context
    assert cloned.data == payload
    assert cloned.remote_write


def test_lore_storage_get_item():
    partition = bytes(range(16))
    address = LoreAddress(myhash, mycontext)

    item = LoreStorageGetItem(
        id=11,
        partition=partition,
        address=address,
        streaming=False,
    )

    assert item.id == 11
    assert isinstance(item.partition, LorePartition)
    assert item.partition.data == partition
    assert isinstance(item.address, LoreAddress)
    assert item.address.hash.data == myhash
    assert item.address.context.data == mycontext
    assert not item.streaming

    cloned = item.clone()
    assert cloned.id == 11
    assert cloned.partition.data == partition
    assert isinstance(cloned.address, LoreAddress)
    assert cloned.address.hash.data == myhash
    assert cloned.address.context.data == mycontext
    assert not cloned.streaming


def test_lore_storage_put_item_array():
    item1 = LoreStoragePutItem(
        id=1,
        partition=bytes(range(16)),
        context=bytes(range(16)),
        data=b"item-one",
        remote_write=False,
    )
    item2 = LoreStoragePutItem(
        id=2,
        partition=bytes([0xFF] * 16),
        context=bytes([0xAA] * 16),
        data=b"item-two-data",
        remote_write=True,
    )

    arr = LoreStoragePutItemArray([item1, item2])
    assert arr.cdata.count == 2

    native = LoreStoragePutItemArray.to_native(arr.as_ptr())
    assert len(native) == 2
    assert isinstance(native[0], LoreStoragePutItem)
    assert native[0].id == 1
    assert native[1].id == 2


def test_lore_storage_put_item_array_empty():
    arr = LoreStoragePutItemArray()
    assert arr.cdata.count == 0
    assert LoreStoragePutItemArray.to_native(arr.as_ptr()) == []


def test_lore_storage_get_item_array():
    addr = LoreAddress(myhash, mycontext)

    item1 = LoreStorageGetItem(
        id=10,
        partition=bytes(range(16)),
        address=addr,
        streaming=False,
    )
    item2 = LoreStorageGetItem(
        id=20,
        partition=bytes([0xFF] * 16),
        address=addr,
        streaming=True,
    )

    arr = LoreStorageGetItemArray([item1, item2])
    assert arr.cdata.count == 2

    native = LoreStorageGetItemArray.to_native(arr.as_ptr())
    assert len(native) == 2
    assert isinstance(native[0], LoreStorageGetItem)
    assert native[0].id == 10
    assert native[1].id == 20


def test_lore_storage_get_item_array_empty():
    arr = LoreStorageGetItemArray()
    assert arr.cdata.count == 0
    assert LoreStorageGetItemArray.to_native(arr.as_ptr()) == []
