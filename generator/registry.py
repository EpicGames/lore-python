"""
Copyright Epic Games, Inc. All Rights Reserved.

Type registries used by the Jinja templates. The seed maps below are the
hand-curated mappings for primitive, scalar, and event-data-array types.
`build_augmented` extends them with auto-detected entries for every
`*_array_t` typedef found in `lore.h`, so that adding a new array type to the
header requires zero edits here or in `utils.ji`.
"""

from common import util

# Defaults for Python primitive type annotations. Everything else (enums,
# class wrappers, list[...] forms) is auto-registered by the corresponding
# loop in `build_augmented` using `setdefault`, so manual entries here are
# only needed for types no loop covers (primitives, nested-event wrappers).
SEED_INIT_MAP = {
    "int": "0",
    "str": "''",
    "bool": "False",
    "bytes": "bytes()",
    "LoreRevisionSyncProgressEventData": "LoreRevisionSyncProgressEventData()",
}


# Dataclass-field defaults. Same auto-registration story as `SEED_INIT_MAP` —
# only primitives and types no loop covers need manual entries.
SEED_DATACLASS_INIT_MAP = {
    "int": "0",
    "str": "''",
    "bool": "False",
    "bytes": "bytes()",
    "LoreRevisionSyncProgressEventData": "field(default_factory=LoreRevisionSyncProgressEventData)",
}


# C-type → Python-type mappings the auto-loops in `build_augmented` can't
# derive. Everything that *can* be derived is registered later via
# `setdefault`, so adding an entry here is only required for:
#   - C primitives                            (uint8_t, int32_t, void*, ...)
#   - Hand-written scalar wrappers             (lore_string_t, lore_hash_t, ...)
#   - Pointer-to-element / C-array forms       (lore_string_t*, lore_hash_t[])
#   - Nested-event wrappers (Scenario 3)       (lore_*_event_data_t referenced
#                                              as a field by another event)
SEED_PY_MAP = {
    "void*": "bytes",
    "uint8_t": "bool",
    "uint16_t": "int",
    "int": "int",
    "int32_t": "int",
    "uint32_t": "int",
    "int64_t": "int",
    "uint64_t": "int",
    "uintptr_t": "int",
    "uint32_t*": "list[int]",
    "lore_metadata_type_t*": "list[LoreMetadataType]",
    "lore_string_t": "str",
    "lore_string_t*": "list[str]",
    "lore_instance_id_t": "bytes",
    "lore_hash_t": "bytes",
    "lore_hash_t[]": "list[bytes]",
    "lore_hash_array_t": "list[bytes]",
    "lore_context_t": "bytes",
    "lore_partition_t": "bytes",
    "lore_branch_id_t": "bytes",
    "lore_repository_id_t": "bytes",
    "lore_branch_point_t*": "list[LoreBranchPoint]",
    "lore_revision_sync_progress_event_data_t": "LoreRevisionSyncProgressEventData",
    "lore_bytes_t": "bytes",
    "lore_store_t": "int",
    "lore_node_id_t": "int",
}


SEED_BLIT_TYPES = [
    "lore_hash_t",
    "lore_binary_t",
    "lore_string_t",
    "lore_address_t",
    "lore_context_t",
    "lore_partition_t",
    "lore_branch_id_t",
    "lore_repository_id_t",
    "lore_fragment_t",
    "lore_metadata_t",
    "lore_hash_array_t",
    "lore_log_config_t",
    "lore_branch_point_t",
    "lore_instance_id_t",
    "lore_bytes_t",
    "lore_store_t",
]


# Hand-written scalar wrappers with a `from_ffi` classmethod AND a `.data`
# byte-array attribute. The events/types templates return these as wrapper
# instances (not their native Python representation) and clone via `.data`.
# Small fixed set — add a line only when a new hand-written scalar wrapper
# with this shape is introduced in `lore_py/types/__init__.py`.
SEED_FROM_FFI_SCALAR_TYPES = [
    "lore_hash_t",
    "lore_context_t",
    "lore_partition_t",
    "lore_branch_id_t",
    "lore_repository_id_t",
    "lore_instance_id_t",
]


# Hand-written struct-like wrappers (multi-field, `.clone()` method,
# `.as_value()` setter) that live in `SEED_HARDCODED_BLIT_TYPES` and so
# wouldn't be picked up by `detect_from_ffi_struct_types`. Auto-generated
# entity types from `types.ji` are detected automatically and don't belong
# here.
SEED_FROM_FFI_STRUCT_TYPES = [
    "lore_metadata_t",
]


# C types whose Python wrapper is hand-written in `lore_py/types/__init__.py`
# (or `events_types.ji` for `lore_event_t`). Listing them here tells
# `types.ji` / `events_types.ji` to skip auto-emitting a class so the
# generated and hand-written definitions don't collide. `*_array_t` typedefs
# discovered by the visitor are appended at runtime by the array loops in
# `build_augmented`, so they don't need to be seeded.
SEED_HARDCODED_BLIT_TYPES = [
    "lore_hash_t",
    "lore_event_t",
    "lore_binary_t",
    "lore_string_t",
    "lore_context_t",
    "lore_partition_t",
    "lore_branch_id_t",
    "lore_repository_id_t",
    "lore_metadata_t",
    "lore_event_callback_config_t",
    "lore_instance_id_t",
    "lore_bytes_t",
    "lore_store_t",
]


UNCOMMON_FUNCTIONS = [
    "lore_event_type",
    "lore_log_configure",
    "lore_shutdown",
    "lore_set_allocator",
    "lore_version",
    "lore_user_directory",
    "lore_set_thread_limit",
]


# Element-c-type → (wrapper_class, native_py_type) for the "native_wrapper"
# array category. The wrapper class accepts the native Python type in its
# constructor and exposes `as_value()`. Add a line here when a new pointer-
# backed scalar type with a native Python equivalent is introduced.
NATIVE_WRAPPER_ELEMENTS = {
    "lore_string_t": ("LoreString", "str"),
    "lore_instance_id_t": ("LoreInstanceId", "bytes"),
}


PRIMITIVE_INT_ELEMENTS = {"uint16_t", "uint32_t", "uint64_t", "int32_t", "uintptr_t"}


def _annotation_for_element(element_c_type, enums):
    """Compute (category, py_annotation, element_class) for an array element."""
    if element_c_type == "uint8_t":
        return ("primitive_bool", "list[bool]", None)
    if element_c_type in PRIMITIVE_INT_ELEMENTS:
        return ("primitive_int", "list[int]", None)
    if element_c_type in enums:
        enum_class = util.pascal_case(element_c_type.removesuffix("_t"))
        return ("enum", f"list[{enum_class}]", enum_class)
    if element_c_type in NATIVE_WRAPPER_ELEMENTS:
        wrapper_class, native_type = NATIVE_WRAPPER_ELEMENTS[element_c_type]
        return ("native_wrapper", f"list[{native_type}]", wrapper_class)
    element_class = util.pascal_case(element_c_type.removesuffix("_t"))
    return ("struct", f"list[{element_class}]", element_class)


def detect_array_types(types_dict, enums_dict):
    """Find every `*_array_t` in `types_dict` and return a list of dicts.

    Each result dict carries everything the templates need:
      - array_c_type, array_class
      - element_c_type, element_class (None for primitives/bool)
      - ptr_field, count_field
      - py_annotation, category
    """
    detected = []
    for struct_name, fields in types_dict.items():
        if not struct_name.endswith("_array_t"):
            continue
        if len(fields) != 2:
            continue
        ptr_field_type, ptr_field_name, _, _ = fields[0]
        _, count_field_name, _, _ = fields[1]
        if not ptr_field_type.endswith("*"):
            continue
        element_c_type = ptr_field_type[:-1]  # strip the trailing '*'
        category, py_annotation, element_class = _annotation_for_element(
            element_c_type, enums_dict
        )
        detected.append(
            {
                "array_c_type": struct_name,
                "array_class": util.pascal_case(struct_name.removesuffix("_t")),
                "element_c_type": element_c_type,
                "element_class": element_class,
                "ptr_field": ptr_field_name,
                "count_field": count_field_name,
                "py_annotation": py_annotation,
                "category": category,
            }
        )
    return detected


def detect_used_struct_types(fields_dict, from_ffi_struct_types, array_types):
    """Subset of `from_ffi_struct_types` actually referenced (directly or as
    the element of an array field) in `fields_dict`. The array element type
    needs to be importable because the type annotation `list[Element]` names
    it directly. Used to scope each template's import block so we don't pull
    in dozens of unreferenced wrapper imports just because the wider
    auto-detection set is bigger.
    """
    array_to_element = {
        arr["array_c_type"]: arr["element_c_type"] for arr in array_types
    }
    used = set()
    for fields in fields_dict.values():
        for field in fields:
            field_type = field[0]
            if field_type in from_ffi_struct_types:
                used.add(field_type)
            elem = array_to_element.get(field_type)
            if elem and elem in from_ffi_struct_types:
                used.add(elem)
    return sorted(used)


def detect_from_ffi_struct_types(types_dict, hardcoded_blit_types):
    """Auto-generated entity wrapper types (have `from_ffi` from `types.ji`).

    Anything in `visitor.types` that isn't an array and isn't hand-written
    (i.e., not in `hardcoded_blit_types`) is generated by `types.ji` and so
    always has a `from_ffi` classmethod, an `.as_value()` method, and a
    `.clone()` method. Returning the full set means every template branch
    keyed on `from_ffi_struct_types` works for new types added to `lore.h`
    without any registry edit. Hand-written struct-like wrappers (e.g.
    `lore_metadata_t`) live in `SEED_FROM_FFI_STRUCT_TYPES` and are unioned
    in by the caller.
    """
    detected = set()
    for struct_name in types_dict:
        if struct_name.endswith("_array_t"):
            continue
        if struct_name in hardcoded_blit_types:
            continue
        detected.add(struct_name)
    return sorted(detected)


def build_augmented(visitor):
    """Return augmented copies of the seed registries plus the array_types list.

    The seed maps stay untouched. We layer on auto-detected entries for every
    enum and `*_array_t` discovered by the visitor so Jinja lookups succeed
    for both pre-existing and newly-introduced typedefs.
    """
    array_types = detect_array_types(visitor.types, visitor.enums)
    # Event-data-array typedefs (ending in `event_data_array_t`) live in
    # `visitor.events` rather than `visitor.types`. We don't auto-generate
    # wrapper classes for them — those are FFI-only and either hand-written
    # or unused — but we DO need to register them in the maps so any field
    # whose type references one resolves cleanly.
    event_array_types = detect_array_types(visitor.events, visitor.enums)

    py_map = dict(SEED_PY_MAP)
    init_map = dict(SEED_INIT_MAP)
    dataclass_init_map = dict(SEED_DATACLASS_INIT_MAP)
    blit_types = list(SEED_BLIT_TYPES)
    hardcoded_blit_types = list(SEED_HARDCODED_BLIT_TYPES)

    for enum_c_type, values in visitor.enums.items():
        enum_class = util.pascal_case(enum_c_type.removesuffix("_t"))
        py_map.setdefault(enum_c_type, enum_class)
        if values:
            default = f"{enum_class}.{values[0]}"
            init_map.setdefault(enum_class, default)
            dataclass_init_map.setdefault(enum_class, default)

    for arr in array_types:
        py_map[arr["array_c_type"]] = arr["py_annotation"]
        init_map.setdefault(arr["py_annotation"], "list()")
        dataclass_init_map.setdefault(
            arr["py_annotation"], "field(default_factory=list)"
        )
        if arr["array_c_type"] not in blit_types:
            blit_types.append(arr["array_c_type"])
        if arr["array_c_type"] not in hardcoded_blit_types:
            hardcoded_blit_types.append(arr["array_c_type"])

    # Register event-data-array types in py_map and skip them from
    # auto-generation in events_types.ji (added to hardcoded_blit_types).
    # No wrapper class is emitted — these are referenced via the existing
    # hand-written FFI classes or are simply unused.
    for arr in event_array_types:
        py_map.setdefault(arr["array_c_type"], arr["py_annotation"])
        dataclass_init_map.setdefault(
            arr["py_annotation"], "field(default_factory=list)"
        )
        if arr["array_c_type"] not in hardcoded_blit_types:
            hardcoded_blit_types.append(arr["array_c_type"])

    # Auto-detect every from_ffi-capable struct type. The seed list folds in
    # hand-written struct-like wrappers that live in `hardcoded_blit_types`
    # (e.g. `lore_metadata_t`). Each detected type needs registry entries so
    # the field's type annotation and default render correctly.
    from_ffi_struct_types = sorted(
        set(SEED_FROM_FFI_STRUCT_TYPES)
        | set(detect_from_ffi_struct_types(visitor.types, hardcoded_blit_types))
    )
    from_ffi_scalar_types = list(SEED_FROM_FFI_SCALAR_TYPES)

    for sw in from_ffi_struct_types:
        wrapper_class = util.pascal_case(sw.removesuffix("_t"))
        py_map.setdefault(sw, wrapper_class)
        init_map.setdefault(wrapper_class, f"{wrapper_class}()")
        dataclass_init_map.setdefault(
            wrapper_class, f"field(default_factory={wrapper_class})"
        )

    return {
        "py_map": py_map,
        "init_map": init_map,
        "dataclass_init_map": dataclass_init_map,
        "blit_types": blit_types,
        "hardcoded_blit_types": hardcoded_blit_types,
        "from_ffi_struct_types": from_ffi_struct_types,
        "from_ffi_scalar_types": from_ffi_scalar_types,
        "args_used_struct_types": detect_used_struct_types(
            visitor.args, from_ffi_struct_types, array_types
        ),
        "events_used_struct_types": detect_used_struct_types(
            visitor.events, from_ffi_struct_types, array_types
        ),
        "uncommon_functions": UNCOMMON_FUNCTIONS,
        "array_types": array_types,
        "event_array_types": event_array_types,
    }
