"""Synthetic, offline tests of configured fields, independent of EXPECTED_FIELDS."""

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


# Loading by file path keeps these tests independent of package installation.
# The script's main guard prevents CLI execution when the module is imported.
SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_notion_schema.py"
SPEC = importlib.util.spec_from_file_location("verify_notion_schema_under_test", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

# Specify the expected input independently; do not import EXPECTED_FIELDS or
# load configuration files. All identifiers below are deliberately fictional.
SYNTHETIC_CONFIG = {
    "database_id": "fake_database",
    "data_source_id": "fake_data_source",
    "properties": {
        "workout_log": {"id": "fake_workout_log", "type": "relation"},
        "exercise": {"id": "fake_exercise", "type": "relation"},
        "set_1_weight": {"id": "fake_set_1_weight", "type": "number"},
        "set_1_reps": {"id": "fake_set_1_reps", "type": "number"},
        "set_2_weight": {"id": "fake_set_2_weight", "type": "number"},
        "set_2_reps": {"id": "fake_set_2_reps", "type": "number"},
        "set_3_weight": {"id": "fake_set_3_weight", "type": "number"},
        "set_3_reps": {"id": "fake_set_3_reps", "type": "number"},
        "created_time": {"id": "fake_created_time", "type": "created_time"},
        "completed": {"id": "fake_completed", "type": "checkbox"},
        "treadmill_km": {"id": "fake_treadmill_km", "type": "number"},
    },
}


@pytest.fixture(autouse=True)
def preserve_synthetic_baseline():
    """Detect accidental changes to the shared original in every test case."""
    # autouse applies this guard to every case; after yield, pytest checks the baseline.
    snapshot = deepcopy(SYNTHETIC_CONFIG)
    yield
    assert SYNTHETIC_CONFIG == snapshot


@pytest.fixture
def config():
    """Give each case its own independent nested mappings."""
    # A shallow copy would still share nested field mappings across tests.
    return deepcopy(SYNTHETIC_CONFIG)


def check_without_mutation(config):
    """Return errors for the supplied Exercise Entries config; fail on mutation or ID disclosure."""
    before = deepcopy(config)
    errors = MODULE.check_configured_fields("exercise_entries", config)
    assert config == before
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    # No fictional property IDs may appear in diagnostics either.
    assert "fake_" not in " ".join(errors)
    return errors


def test_valid_exercise_entries(config):
    """Require the complete synthetic Exercise Entries fixture to pass field checks."""
    assert check_without_mutation(config) == []


def test_missing_required_field(config):
    """Require one relevant error when a required field is removed from the fixture."""
    del config["properties"]["set_1_weight"]
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "set_1_weight" in errors[0]
    assert "missing" in errors[0].lower()


def test_unexpected_field_is_not_disclosed(config):
    """Reject an added field without echoing its fictional sensitive name or type."""
    unknown_name = "fictional_sensitive_extra_field"
    unknown_type = "fictional_sensitive_type"
    config["properties"][unknown_name] = {"id": "fake_extra", "type": unknown_type}
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "unexpected" in errors[0].lower()
    assert unknown_name not in " ".join(errors)
    assert unknown_type not in " ".join(errors)


def test_incorrect_property_type(config):
    """Reject an incorrect configured type without exposing the supplied value."""
    config["properties"]["set_1_weight"]["type"] = "fictional_wrong_type"
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "set_1_weight" in errors[0]
    assert "type" in errors[0].lower()
    assert "fictional_wrong_type" not in errors[0]


# pytest runs a separate case per value so blank and non-string failures stay distinct.
@pytest.mark.parametrize("invalid_id", ["", " \t\n", 42, None, False, []])
def test_invalid_property_id(config, invalid_id):
    """Reject each blank or non-string ID while keeping the remaining fixture valid."""
    config["properties"]["set_1_weight"]["id"] = invalid_id
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "set_1_weight" in errors[0]
    assert "id" in errors[0].lower()


@pytest.mark.parametrize("mapping", [None, [], "fictional_bad_mapping", 42])
def test_malformed_property_mapping(config, mapping):
    """Reject non-dictionary field mappings without exposing their supplied contents."""
    config["properties"]["set_1_weight"] = mapping
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "set_1_weight" in errors[0]
    assert "mapping" in errors[0].lower()
    assert "fictional_bad_mapping" not in " ".join(errors)


def test_empty_id_and_incorrect_type_collect_two_errors(config):
    """Require both independent defects in one field to be reported in a single call."""
    config["properties"]["set_1_weight"] = {"id": "", "type": "checkbox"}
    errors = check_without_mutation(config)
    assert len(errors) == 2
    assert all("set_1_weight" in error for error in errors)
    assert any("id" in error.lower() for error in errors)
    assert any("type" in error.lower() for error in errors)


def test_missing_properties(config):
    """Require a useful error when the supplied source has no properties mapping."""
    del config["properties"]
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "properties" in errors[0].lower()


@pytest.mark.parametrize("properties", [None, [], "fictional_bad_properties", 42])
def test_malformed_properties(config, properties):
    """Reject invalid properties containers instead of attempting field-level checks."""
    config["properties"] = properties
    errors = check_without_mutation(config)
    assert len(errors) == 1
    assert "properties" in errors[0].lower()
    assert "fictional_bad_properties" not in " ".join(errors)


def test_synthetic_copies_are_independent(config):
    """Prove nested edits to one fixture copy cannot contaminate the original or another copy."""
    other = deepcopy(SYNTHETIC_CONFIG)
    config["properties"]["set_1_weight"]["id"] = "fake_changed_copy"
    del config["properties"]["exercise"]
    assert other == SYNTHETIC_CONFIG
    assert other["properties"]["set_1_weight"]["id"] == "fake_set_1_weight"
    assert "exercise" in other["properties"]
    assert check_without_mutation(other) == []

@pytest.fixture
def small_source_configs():
    """Fresh, independently specified mappings for the other two sources."""
    return {
        "workout_log": {
            "database_id": "fake_workout_database",
            "data_source_id": "fake_workout_source",
            "properties": {
                "session_name": {"id": "fake_session_title", "type": "title"},
                "created_time": {"id": "fake_session_created", "type": "created_time"},
            },
        },
        "exercise": {
            "database_id": "fake_exercise_database",
            "data_source_id": "fake_exercise_source",
            "properties": {
                "exercise_name": {"id": "fake_exercise_title", "type": "title"},
            },
        },
    }


def check_source_without_mutation(source_name, source_config):
    """Return errors for the supplied source/config; fail on mutation or synthetic value disclosure."""
    snapshot = deepcopy(source_config)
    errors = MODULE.check_configured_fields(source_name, source_config)
    assert source_config == snapshot
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    # Synthetic markers let us detect accidental disclosure without using private data.
    assert "fake_" not in messages
    assert "fictional_sensitive" not in messages
    return errors


@pytest.mark.parametrize("source_name", ["workout_log", "exercise"])
def test_other_sources_valid(source_name, small_source_configs):
    """Require each independently defined source fixture to pass without errors."""
    assert check_source_without_mutation(source_name, small_source_configs[source_name]) == []


@pytest.mark.parametrize(
    "source_name, missing_field",
    [("workout_log", "session_name"), ("exercise", "exercise_name")],
)
def test_other_sources_missing_required_field(source_name, missing_field, small_source_configs):
    """Require one missing-field error for the selected source and required field."""
    source_config = small_source_configs[source_name]
    del source_config["properties"][missing_field]
    errors = check_source_without_mutation(source_name, source_config)
    assert len(errors) == 1
    assert missing_field in errors[0]
    assert "missing" in errors[0].lower()


@pytest.mark.parametrize(
    "source_name, field_name",
    [("workout_log", "created_time"), ("exercise", "exercise_name")],
)
def test_other_sources_incorrect_type(source_name, field_name, small_source_configs):
    """Require a type error for the selected source field without disclosing its bad value."""
    source_config = small_source_configs[source_name]
    source_config["properties"][field_name]["type"] = "fictional_sensitive_wrong_type"
    errors = check_source_without_mutation(source_name, source_config)
    assert len(errors) == 1
    assert field_name in errors[0]
    assert "type" in errors[0].lower()


@pytest.mark.parametrize("source_name", ["workout_log", "exercise"])
def test_other_sources_unexpected_values_are_not_disclosed(source_name, small_source_configs):
    """Reject extra fields in either source without leaking synthetic names, IDs, or types."""
    source_config = small_source_configs[source_name]
    source_config["properties"]["fictional_sensitive_extra_field"] = {
        "id": "fake_private_extra_id",
        "type": "fictional_sensitive_extra_type",
    }
    errors = check_source_without_mutation(source_name, source_config)
    assert len(errors) == 1
    assert "unexpected" in errors[0].lower()


def test_unknown_source_is_rejected_without_disclosure(small_source_configs):
    """Reject an unknown source without reflecting its supplied name in diagnostics."""
    errors = check_source_without_mutation(
        "fictional_sensitive_unknown_source", small_source_configs["workout_log"]
    )
    assert len(errors) == 1
    assert "source" in errors[0].lower()
    assert "unknown" in errors[0].lower()


# Stacked decorators exercise every source with every malformed input, not just pairs.
@pytest.mark.parametrize("source_name", ["exercise_entries", "workout_log", "exercise"])
@pytest.mark.parametrize("source_config", [None, [], "fictional_sensitive_config", 42])
def test_malformed_source_is_rejected(source_name, source_config):
    """Require a safe structural error for each malformed source input and approved source."""
    errors = check_source_without_mutation(source_name, source_config)
    assert len(errors) == 1
    assert "source configuration" in errors[0].lower()


def test_other_source_fixtures_are_independent(small_source_configs):
    """Prove nested copy edits leave both original source fixtures intact and valid."""
    snapshot = deepcopy(small_source_configs)
    changed = deepcopy(small_source_configs)
    changed["workout_log"]["properties"]["session_name"]["id"] = "fake_changed_id"
    del changed["exercise"]["properties"]["exercise_name"]
    assert small_source_configs == snapshot
    for source_name, source_config in small_source_configs.items():
        assert check_source_without_mutation(source_name, source_config) == []

@pytest.fixture
def identity_pair():
    """Return fresh, independently specified configuration and metadata dictionaries.

    The repeated UUID literals are fictional; spelling out both sides prevents
    expected metadata from being generated from the configuration under test.
    """
    return (
        {
            "data_source_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee01",
            "database_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02",
        },
        {
            "object": "data_source",
            "id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee01",
            "parent": {
                "type": "database_id",
                "database_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02",
            },
            "fictional_sensitive_extra": "fictional_sensitive_raw_metadata",
        },
    )


def check_identity_without_disclosure(source_name, config, metadata):
    """Return identity errors; assert input preservation and safe diagnostics.

    Snapshot both inputs, including nested parents, so every scenario checks
    immutability even when the function rejects malformed containers.
    """
    config_before = deepcopy(config)
    metadata_before = deepcopy(metadata)
    errors = MODULE.check_source_identity(source_name, config, metadata)
    assert config == config_before
    assert metadata == metadata_before
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    assert "fictional_sensitive" not in messages
    # Check normalized UUID text too: changing case or removing hyphens must
    # not allow identifiers to slip through the diagnostic privacy assertions.
    compact_messages = messages.lower().replace("-", "")
    for secret in (
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee01",
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee02",
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee03",
        "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee04",
    ):
        assert secret.replace("-", "") not in compact_messages
    return errors


@pytest.mark.parametrize("source_name", ["exercise_entries", "workout_log", "exercise"])
def test_identity_valid(source_name, identity_pair):
    """Require matching identities and database parent to pass for every source."""
    config, metadata = identity_pair
    assert check_identity_without_disclosure(source_name, config, metadata) == []


@pytest.mark.parametrize(
    "field, expected_label",
    [("id", "data-source ID"), ("parent", "parent database ID")],
)
def test_identity_single_mismatch(field, expected_label, identity_pair):
    """Require one relevant error when exactly one well-formed live ID differs."""
    config, metadata = identity_pair
    if field == "id":
        metadata["id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee03"
    else:
        metadata["parent"]["database_id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee04"
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert expected_label in errors[0]
    assert "match" in errors[0].lower()


def test_identity_two_independent_mismatches(identity_pair):
    """Require both ID mismatches in one call rather than stopping at the first."""
    config, metadata = identity_pair
    metadata["id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee03"
    metadata["parent"]["database_id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee04"
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 2
    assert any("data-source ID" in error for error in errors)
    assert any("parent database ID" in error for error in errors)
    assert all("match" in error.lower() for error in errors)


@pytest.mark.parametrize("object_type", ["page", None, 42, {}])
def test_identity_wrong_response_object(object_type, identity_pair):
    """Reject non-data-source responses even when their identity fields match."""
    config, metadata = identity_pair
    metadata["object"] = object_type
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "object" in errors[0].lower()


def test_identity_missing_response_object(identity_pair):
    """Reject metadata without its response object discriminator."""
    config, metadata = identity_pair
    del metadata["object"]
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "object" in errors[0].lower()


def test_identity_missing_parent(identity_pair):
    """Reject absent parent metadata without assuming a database relationship."""
    config, metadata = identity_pair
    del metadata["parent"]
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert errors
    assert any("parent" in error.lower() for error in errors)


@pytest.mark.parametrize("parent", [None, [], 42, "fictional_sensitive_parent", {}])
def test_identity_malformed_parent(parent, identity_pair):
    """Reject non-object or incomplete parents without exposing supplied values."""
    config, metadata = identity_pair
    metadata["parent"] = parent
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert errors
    assert any("parent" in error.lower() for error in errors)


@pytest.mark.parametrize("parent_type", ["page_id", None, "fictional_sensitive_parent_type"])
def test_identity_wrong_parent_type(parent_type, identity_pair):
    """Require a database parent discriminator even with a matching database ID."""
    config, metadata = identity_pair
    metadata["parent"]["type"] = parent_type
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "parent type" in errors[0].lower()


# Cover all four ID positions independently; a valid counterpart must not hide
# missing, blank, non-string, or unparseable identity information.
@pytest.mark.parametrize(
    "location, key",
    [("config", "data_source_id"), ("config", "database_id"),
     ("metadata", "id"), ("parent", "database_id")],
)
@pytest.mark.parametrize("invalid_id", [None, "", " \t\n", 42, [], "fictional_sensitive_bad_uuid"])
def test_identity_invalid_uuid(location, key, invalid_id, identity_pair):
    """Require one safe identity error for each invalid value and ID position."""
    config, metadata = identity_pair
    containers = {"config": config, "metadata": metadata, "parent": metadata["parent"]}
    containers[location][key] = invalid_id
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "ID" in errors[0]
    assert "malformed" in errors[0].lower() or "missing" in errors[0].lower()


@pytest.mark.parametrize(
    "location, key",
    [("config", "data_source_id"), ("config", "database_id"),
     ("metadata", "id"), ("parent", "database_id")],
)
def test_identity_missing_uuid(location, key, identity_pair):
    """Distinguish omitted keys from explicitly supplied invalid ID values."""
    config, metadata = identity_pair
    containers = {"config": config, "metadata": metadata, "parent": metadata["parent"]}
    del containers[location][key]
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "ID" in errors[0]


def test_identity_unknown_source_is_not_disclosed(identity_pair):
    """Reject an unrecognized source without repeating its potentially private name."""
    config, metadata = identity_pair
    errors = check_identity_without_disclosure("fictional_sensitive_unknown_source", config, metadata)
    assert len(errors) == 1
    assert "unknown" in errors[0].lower()


@pytest.mark.parametrize("side", ["config", "metadata"])
@pytest.mark.parametrize("malformed", [None, [], 42, "fictional_sensitive_container"])
def test_identity_malformed_container(side, malformed, identity_pair):
    """Reject each malformed outer container while leaving its valid peer untouched."""
    config, metadata = identity_pair
    if side == "config":
        config = malformed
    else:
        metadata = malformed
    errors = check_identity_without_disclosure("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "object" in errors[0].lower()


def test_identity_both_containers_malformed():
    """Require independent errors when neither outer input is an object."""
    errors = check_identity_without_disclosure("exercise_entries", None, [])
    assert len(errors) == 2


@pytest.mark.parametrize("side", ["config", "metadata"])
@pytest.mark.parametrize("format_name", ["uppercase", "compact", "braced"])
def test_identity_equivalent_uuid_formats(side, format_name, identity_pair):
    """Accept equivalent UUID spellings on either side of both ID comparisons."""
    config, metadata = identity_pair
    if side == "config":
        targets = [(config, "data_source_id"), (config, "database_id")]
    else:
        targets = [(metadata, "id"), (metadata["parent"], "database_id")]
    for container, key in targets:
        value = container[key]
        if format_name == "uppercase":
            container[key] = value.upper()
        elif format_name == "compact":
            container[key] = value.replace("-", "")
        else:
            container[key] = "{" + value + "}"
    assert check_identity_without_disclosure("exercise_entries", config, metadata) == []


def test_identity_fixture_copies_are_isolated(identity_pair):
    """Prove nested edits to copies cannot contaminate the original valid pair."""
    snapshot = deepcopy(identity_pair)
    copied_config, copied_metadata = deepcopy(identity_pair)
    copied_config["data_source_id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee03"
    copied_metadata["parent"]["database_id"] = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeee04"
    assert identity_pair == snapshot
    config, metadata = identity_pair
    assert check_identity_without_disclosure("exercise_entries", config, metadata) == []

@pytest.fixture(params=["exercise_entries", "workout_log", "exercise"])
def property_pair(request):
    """Return fresh config/metadata for each source, independent of implementation constants.

    Live fields are written separately from configuration so an incorrect ID or
    type on one side is not automatically copied into the expected counterpart.
    Short fictional IDs deliberately demonstrate that UUID parsing is inappropriate.
    """
    configs = {
        "exercise_entries": {"properties": {
            "workout_log": {"id": "fake_p01", "type": "relation"},
            "exercise": {"id": "fake_p02", "type": "relation"},
            "set_1_weight": {"id": "fake_p03", "type": "number"},
            "set_1_reps": {"id": "fake_p04", "type": "number"},
            "set_2_weight": {"id": "fake_p05", "type": "number"},
            "set_2_reps": {"id": "fake_p06", "type": "number"},
            "set_3_weight": {"id": "fake_p07", "type": "number"},
            "set_3_reps": {"id": "fake_p08", "type": "number"},
            "created_time": {"id": "fake_p09", "type": "created_time"},
            "completed": {"id": "fake_p10", "type": "checkbox"},
            "treadmill_km": {"id": "fake_p11", "type": "number"},
        }},
        "workout_log": {"properties": {
            "session_name": {"id": "fake_w01", "type": "title"},
            "created_time": {"id": "fake_w02", "type": "created_time"},
        }},
        "exercise": {"properties": {
            "exercise_name": {"id": "fake_e01", "type": "title"},
        }},
    }
    live = {
        "exercise_entries": {"properties": {
            "fictional_sensitive_log": {"id": "fake_p01", "type": "relation"},
            "fictional_sensitive_exercise": {"id": "fake_p02", "type": "relation"},
            "fictional_sensitive_w1": {"id": "fake_p03", "type": "number"},
            "fictional_sensitive_r1": {"id": "fake_p04", "type": "number"},
            "fictional_sensitive_w2": {"id": "fake_p05", "type": "number"},
            "fictional_sensitive_r2": {"id": "fake_p06", "type": "number"},
            "fictional_sensitive_w3": {"id": "fake_p07", "type": "number"},
            "fictional_sensitive_r3": {"id": "fake_p08", "type": "number"},
            "fictional_sensitive_created": {"id": "fake_p09", "type": "created_time"},
            "fictional_sensitive_done": {"id": "fake_p10", "type": "checkbox"},
            "fictional_sensitive_distance": {"id": "fake_p11", "type": "number"},
        }},
        "workout_log": {"properties": {
            "fictional_sensitive_session": {"id": "fake_w01", "type": "title"},
            "fictional_sensitive_date": {"id": "fake_w02", "type": "created_time"},
        }},
        "exercise": {"properties": {
            "fictional_sensitive_name": {"id": "fake_e01", "type": "title"},
        }},
    }
    source_name = request.param
    return source_name, configs[source_name], live[source_name]


def check_properties_safely(source_name, config, metadata):
    """Return property errors; fail if either input changes or markers leak.

    Every new scenario uses this helper, including error paths, to check the
    immutability and diagnostic-privacy contracts alongside its specific result.
    """
    before_config = deepcopy(config)
    before_metadata = deepcopy(metadata)
    errors = MODULE.check_property_ids(source_name, config, metadata)
    assert config == before_config
    assert metadata == before_metadata
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    assert "fake_" not in messages
    assert "fictional_sensitive" not in messages
    return errors


def test_property_ids_match_with_short_ids(property_pair):
    """Accept all required IDs/types for every source using non-UUID identifiers."""
    source, config, metadata = property_pair
    assert check_properties_safely(source, config, metadata) == []


def test_property_ids_ignore_display_name_changes(property_pair):
    """Accept renamed display keys, including emojis and whitespace, by matching IDs."""
    source, config, metadata = property_pair
    metadata["properties"] = {
        f"  fictional_sensitive_renamed 🏋️ {index}\t ": mapping
        for index, mapping in enumerate(metadata["properties"].values())
    }
    assert check_properties_safely(source, config, metadata) == []


def test_property_ids_allow_unrelated_live_fields(property_pair):
    """Allow valid extra Notion fields without expanding the required configuration."""
    source, config, metadata = property_pair
    metadata["properties"]["fictional_sensitive_extra"] = {"id": "fake_extra", "type": "rich_text"}
    assert check_properties_safely(source, config, metadata) == []


def test_property_ids_reject_extra_configured_fields(property_pair):
    """Reject unapproved configured fields without disclosing their names or IDs."""
    source, config, metadata = property_pair
    config["properties"]["fictional_sensitive_extra"] = {"id": "fake_extra", "type": "number"}
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert "unexpected" in errors[0].lower()


def test_property_ids_missing_live_id(property_pair):
    """Report the approved field label when its ID is not present in Notion metadata."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    del metadata["properties"][next(iter(metadata["properties"]))]
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert field in errors[0]
    assert "absent" in errors[0].lower()


def test_property_ids_wrong_live_type(property_pair):
    """Reject an ID match when its type differs from the independently approved type."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    next(iter(metadata["properties"].values()))["type"] = "fictional_sensitive_wrong_type"
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert field in errors[0]
    assert "live property type" in errors[0].lower()


def test_property_ids_duplicate_configuration_same_type(property_pair):
    """Detect a configured ID collision even when the duplicate has an identical type."""
    source, config, metadata = property_pair
    # An extra alias works even for Exercise's single required field. Its separate
    # unexpected-field error must not suppress the duplicate-ID error.
    config["properties"]["fictional_sensitive_alias"] = deepcopy(next(iter(config["properties"].values())))
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 2
    assert any("duplicate configured property ID" in error for error in errors)
    assert any("unexpected" in error.lower() for error in errors)


def test_property_ids_duplicate_required_configuration(config):
    """Detect collisions between two approved fields of the same type without an extra alias."""
    config["properties"]["set_1_reps"]["id"] = config["properties"]["set_1_weight"]["id"]
    # These fields are both numbers, so matching types cannot excuse the collision.
    metadata = {"properties": {
        f"fictional_sensitive_{index}": deepcopy(mapping)
        for index, mapping in enumerate(SYNTHETIC_CONFIG["properties"].values())
    }}
    errors = check_properties_safely("exercise_entries", config, metadata)
    assert len(errors) == 1
    assert "duplicate configured property ID" in errors[0]


@pytest.mark.parametrize("conflicting_type", [False, True])
def test_property_ids_duplicate_live_ids(property_pair, conflicting_type):
    """Reject ambiguous live IDs whether their types agree or conflict."""
    source, config, metadata = property_pair
    duplicate = deepcopy(next(iter(metadata["properties"].values())))
    if conflicting_type:
        duplicate["type"] = "fictional_sensitive_conflicting_type"
    metadata["properties"]["fictional_sensitive_duplicate"] = duplicate
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert "duplicate live property ID" in errors[0]


@pytest.mark.parametrize("invalid_id", [None, "", " \t\n", 42, [], {}])
def test_property_ids_invalid_configured_id(property_pair, invalid_id):
    """Reject blank or non-string configured IDs without requiring UUID formatting."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    config["properties"][field]["id"] = invalid_id
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert field in errors[0]
    assert "property ID" in errors[0]


def test_property_ids_missing_configured_id(property_pair):
    """Reject an omitted ID key instead of treating it as an optional mapping attribute."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    del config["properties"][field]["id"]
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert field in errors[0]
    assert "property ID" in errors[0]


@pytest.mark.parametrize("mapping", [None, [], "fictional_sensitive_mapping", 42])
def test_property_ids_malformed_configured_mapping(property_pair, mapping):
    """Reject non-object required mappings without attempting ID lookup on them."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    config["properties"][field] = mapping
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert field in errors[0]
    assert "mapping" in errors[0].lower()


@pytest.mark.parametrize(
    "mapping, relevant_error",
    [
        (None, "live property mapping"),
        ([], "live property mapping"),
        ("fictional_sensitive_mapping", "live property mapping"),
        ({"type": "number"}, "live property ID"),
        ({"id": "", "type": "number"}, "live property ID"),
        ({"id": " \t ", "type": "number"}, "live property ID"),
        ({"id": 42, "type": "number"}, "live property ID"),
        ({"id": [], "type": "number"}, "live property ID"),
        ({"id": "fake_extra"}, "live property type"),
        ({"id": "fake_extra", "type": ""}, "live property type"),
        ({"id": "fake_extra", "type": " \t "}, "live property type"),
        ({"id": "fake_extra", "type": None}, "live property type"),
        ({"id": "fake_extra", "type": 42}, "live property type"),
        ({"id": "fake_extra", "type": []}, "live property type"),
    ],
)
def test_property_ids_malformed_live_properties(property_pair, mapping, relevant_error):
    """Reject malformed extra live fields too, without unrelated missing-required errors."""
    source, config, metadata = property_pair
    metadata["properties"]["fictional_sensitive_malformed"] = deepcopy(mapping)
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert relevant_error in errors[0]


@pytest.mark.parametrize("side", ["config", "metadata"])
@pytest.mark.parametrize("properties", [None, [], 42, "fictional_sensitive_properties"])
def test_property_ids_malformed_properties_container(property_pair, side, properties):
    """Reject wrong properties-container types on either side of the comparison."""
    source, config, metadata = property_pair
    target = config if side == "config" else metadata
    target["properties"] = properties
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert "properties" in errors[0].lower()
    assert "object" in errors[0].lower()


@pytest.mark.parametrize("side", ["config", "metadata"])
def test_property_ids_missing_properties_container(property_pair, side):
    """Reject missing containers instead of interpreting missing metadata as success."""
    source, config, metadata = property_pair
    del (config if side == "config" else metadata)["properties"]
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert "properties" in errors[0].lower()
    assert "object" in errors[0].lower()


@pytest.mark.parametrize("side", ["config", "metadata"])
def test_property_ids_empty_properties_container(property_pair, side):
    """Require a relevant missing-field/ID error for every approved field in an empty side."""
    source, config, metadata = property_pair
    fields = list(config["properties"])
    target = config if side == "config" else metadata
    target["properties"] = {}
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == len(fields)
    for field in fields:
        assert any(field in error and ("missing" in error or "absent" in error) for error in errors)


@pytest.mark.parametrize("side", ["config", "metadata"])
@pytest.mark.parametrize("container", [None, [], 42, "fictional_sensitive_container"])
def test_property_ids_malformed_outer_container(property_pair, side, container):
    """Reject malformed source or metadata inputs before reading their properties."""
    source, config, metadata = property_pair
    if side == "config":
        config = container
    else:
        metadata = container
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 1
    assert "object" in errors[0].lower()


def test_property_ids_collect_independent_errors(property_pair):
    """Require a missing required ID and a malformed extra mapping in the same result."""
    source, config, metadata = property_pair
    field = next(iter(config["properties"]))
    del metadata["properties"][next(iter(metadata["properties"]))]
    metadata["properties"]["fictional_sensitive_malformed"] = None
    errors = check_properties_safely(source, config, metadata)
    assert len(errors) == 2
    assert any(field in error and "absent" in error for error in errors)
    assert any("live property mapping" in error for error in errors)


def test_property_ids_unknown_source_is_safe(property_pair):
    """Reject unknown source names without reflecting arbitrary input into diagnostics."""
    _, config, metadata = property_pair
    errors = check_properties_safely("fictional_sensitive_unknown_source", config, metadata)
    assert len(errors) == 1
    assert "unknown" in errors[0].lower()


def test_property_ids_fixture_isolation(property_pair):
    """Prove nested edits to copies leave the original source and metadata pair valid."""
    snapshot = deepcopy(property_pair)
    source, config, metadata = deepcopy(property_pair)
    next(iter(config["properties"].values()))["id"] = "fake_changed"
    next(iter(metadata["properties"].values()))["type"] = "fictional_sensitive_changed"
    assert property_pair == snapshot
    original_source, original_config, original_metadata = property_pair
    assert check_properties_safely(original_source, original_config, original_metadata) == []


def test_property_ids_ignore_live_property_order(property_pair):
    """Accept reversed live properties for each source without changing either input."""
    source, config, metadata = property_pair
    original_items = list(metadata["properties"].items())
    # Rebuild only the container order; retain every display name, ID, and type.
    metadata["properties"] = dict(reversed(original_items))
    assert list(metadata["properties"].items()) == list(reversed(original_items))
    # The helper snapshots both inputs immediately before calling validation.
    assert check_properties_safely(source, config, metadata) == []


@pytest.fixture
def relation_pair():
    """Return isolated, independently written relation configuration and metadata.

    Only the two relation fields are needed here; destination IDs live in their
    source configurations, rather than being duplicated in relation mappings.
    """
    return (
        {"sources": {
            "exercise_entries": {"properties": {
                "workout_log": {"id": "fake_rel_log", "type": "relation"},
                "exercise": {"id": "fake_rel_ex", "type": "relation"},
            }},
            "workout_log": {"data_source_id": "bbbbbbbb-cccc-4ddd-8eee-fffffffffff1"},
            "exercise": {"data_source_id": "bbbbbbbb-cccc-4ddd-8eee-fffffffffff2"},
        }},
        {"properties": {
            "fictional_sensitive_log": {
                "id": "fake_rel_log", "type": "relation",
                "relation": {"data_source_id": "bbbbbbbb-cccc-4ddd-8eee-fffffffffff1"},
            },
            "fictional_sensitive_ex": {
                "id": "fake_rel_ex", "type": "relation",
                "relation": {"data_source_id": "bbbbbbbb-cccc-4ddd-8eee-fffffffffff2"},
            },
        }},
    )


@pytest.fixture(params=[
    ("workout_log", "fictional_sensitive_log"),
    ("exercise", "fictional_sensitive_ex"),
])
def relation_field(request):
    """Run field-specific failures independently for both approved relations."""
    return request.param


def check_relations_safely(config, metadata):
    """Return relation errors; fail on input mutation or synthetic secret disclosure."""
    before_config = deepcopy(config)
    before_metadata = deepcopy(metadata)
    errors = MODULE.check_relation_targets(config, metadata)
    assert config == before_config
    assert metadata == before_metadata
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    # Markers catch arbitrary values as well as display names and short IDs.
    assert "fake_" not in messages
    assert "fictional_sensitive" not in messages
    compact = messages.lower().replace("-", "")
    for secret in (
        "bbbbbbbb-cccc-4ddd-8eee-fffffffffff1",
        "bbbbbbbb-cccc-4ddd-8eee-fffffffffff2",
        "bbbbbbbb-cccc-4ddd-8eee-fffffffffff3",
    ):
        assert secret.replace("-", "") not in compact
    return errors


def test_relation_targets_correct(relation_pair):
    """Accept both matching relation destinations without changing the input pair."""
    assert check_relations_safely(*relation_pair) == []


def test_relation_targets_swapped(relation_pair):
    """Require two distinct field-specific errors when destinations are swapped."""
    config, metadata = relation_pair
    metadata["properties"]["fictional_sensitive_log"]["relation"]["data_source_id"] = "bbbbbbbb-cccc-4ddd-8eee-fffffffffff2"
    metadata["properties"]["fictional_sensitive_ex"]["relation"]["data_source_id"] = "bbbbbbbb-cccc-4ddd-8eee-fffffffffff1"
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 2
    assert len(set(errors)) == 2
    for field in ("workout_log", "exercise"):
        assert any(f"exercise_entries.{field}:" in error and "does not match" in error for error in errors)


def test_relation_target_one_mismatch(relation_pair, relation_field):
    """Reject one incorrect target while preserving the other valid relation."""
    config, metadata = relation_pair
    field, display = relation_field
    metadata["properties"][display]["relation"]["data_source_id"] = "bbbbbbbb-cccc-4ddd-8eee-fffffffffff3"
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "does not match" in errors[0]


def test_relation_targets_ignore_display_names_and_order(relation_pair):
    """Find relations by ID after renaming, adding emojis, and reversing their order."""
    config, metadata = relation_pair
    metadata["properties"] = {
        f" 🏋️ fictional_sensitive_renamed_{index}\t": mapping
        for index, mapping in enumerate(reversed(list(metadata["properties"].values())))
    }
    assert check_relations_safely(config, metadata) == []


@pytest.mark.parametrize("side", ["config", "live"])
@pytest.mark.parametrize("format_name", ["uppercase", "compact", "braced"])
def test_relation_targets_uuid_normalization(relation_pair, relation_field, side, format_name):
    """Accept equivalent UUID spellings on either side of either target comparison."""
    config, metadata = relation_pair
    field, display = relation_field
    target = config["sources"][field] if side == "config" else metadata["properties"][display]["relation"]
    value = target["data_source_id"]
    if format_name == "uppercase":
        target["data_source_id"] = value.upper()
    elif format_name == "compact":
        target["data_source_id"] = value.replace("-", "")
    else:
        target["data_source_id"] = "{" + value + "}"
    assert check_relations_safely(config, metadata) == []


def test_relation_target_missing_destination_source(relation_pair, relation_field):
    """Reject missing destination configuration instead of guessing its identity."""
    config, metadata = relation_pair
    field, _ = relation_field
    del config["sources"][field]
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "destination configuration" in errors[0]


# Apply each invalid value separately to configured and live destination IDs.
@pytest.mark.parametrize("side", ["config", "live"])
@pytest.mark.parametrize("invalid_id", [None, "", " \t\n", 42, [], {}, "fictional_sensitive_bad_uuid"])
def test_relation_target_invalid_destination_uuid(relation_pair, relation_field, side, invalid_id):
    """Reject malformed destination UUIDs without leaking values or parser exceptions."""
    config, metadata = relation_pair
    field, display = relation_field
    target = config["sources"][field] if side == "config" else metadata["properties"][display]["relation"]
    target["data_source_id"] = invalid_id
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "destination ID" in errors[0]
    assert "malformed" in errors[0]


@pytest.mark.parametrize("side", ["config", "live"])
def test_relation_target_missing_destination_uuid(relation_pair, relation_field, side):
    """Reject omitted destination keys independently from explicit invalid values."""
    config, metadata = relation_pair
    field, display = relation_field
    target = config["sources"][field] if side == "config" else metadata["properties"][display]["relation"]
    del target["data_source_id"]
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "destination ID" in errors[0]
    assert "missing" in errors[0]


@pytest.mark.parametrize("relation", [None, [], 42, "fictional_sensitive_relation"])
def test_relation_target_malformed_relation_object(relation_pair, relation_field, relation):
    """Reject non-object relation metadata rather than reading arbitrary values."""
    config, metadata = relation_pair
    field, display = relation_field
    metadata["properties"][display]["relation"] = relation
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "live relation mapping" in errors[0]


def test_relation_target_missing_relation_object(relation_pair, relation_field):
    """Require the relation object even when the property ID and type match."""
    config, metadata = relation_pair
    field, display = relation_field
    del metadata["properties"][display]["relation"]
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "live relation mapping" in errors[0]


@pytest.mark.parametrize("side", ["config", "live"])
@pytest.mark.parametrize("wrong_type", [None, "number", "fictional_sensitive_type"])
def test_relation_target_incorrect_property_type(relation_pair, relation_field, side, wrong_type):
    """Require relation types on both sides even when target UUIDs are correct."""
    config, metadata = relation_pair
    field, display = relation_field
    mapping = config["sources"]["exercise_entries"]["properties"][field] if side == "config" else metadata["properties"][display]
    mapping["type"] = wrong_type
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "property type must be relation" in errors[0]


@pytest.mark.parametrize("side", ["config", "live"])
def test_relation_target_missing_property_id(relation_pair, relation_field, side):
    """Reject omitted IDs rather than locating a relation by name or position."""
    config, metadata = relation_pair
    _, display = relation_field
    field, _ = relation_field
    mapping = config["sources"]["exercise_entries"]["properties"][field] if side == "config" else metadata["properties"][display]
    del mapping["id"]
    errors = check_relations_safely(config, metadata)
    assert any("property ID is missing or malformed" in error for error in errors)


def test_relation_target_missing_live_property(relation_pair, relation_field):
    """Reject an absent relation property even when the other relation is valid."""
    config, metadata = relation_pair
    field, display = relation_field
    del metadata["properties"][display]
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "property ID is absent" in errors[0]


def test_relation_targets_duplicate_configured_ids(relation_pair):
    """Reject same-type configured ID collisions before choosing either relation."""
    config, metadata = relation_pair
    props = config["sources"]["exercise_entries"]["properties"]
    props["exercise"]["id"] = "fake_rel_log"
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert "configuration: duplicate property ID" in errors[0]


@pytest.mark.parametrize("prepend", [False, True])
def test_relation_targets_duplicate_live_ids(relation_pair, relation_field, prepend):
    """Reject same-type duplicates regardless of order, including conflicting targets."""
    config, metadata = relation_pair
    _, display = relation_field
    duplicate = deepcopy(metadata["properties"][display])
    duplicate["relation"]["data_source_id"] = "bbbbbbbb-cccc-4ddd-8eee-fffffffffff3"
    if prepend:
        metadata["properties"] = {"fictional_sensitive_duplicate": duplicate, **metadata["properties"]}
    else:
        metadata["properties"]["fictional_sensitive_duplicate"] = duplicate
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 1
    assert "metadata: duplicate property ID" in errors[0]


@pytest.mark.parametrize("location, category", [
    ("config", "Relation configuration must be an object"),
    ("sources", "sources must be an object"),
    ("entries", "source configuration must be an object"),
    ("configured_properties", "configuration: properties must be an object"),
    ("metadata", "live metadata must be an object"),
    ("live_properties", "metadata: properties must be an object"),
    ("destination", "destination configuration must be an object"),
])
@pytest.mark.parametrize("invalid", [None, [], 42, "fictional_sensitive_container"])
def test_relation_targets_malformed_containers(relation_pair, location, category, invalid):
    """Reject malformed containers at each boundary with a relevant safe category."""
    config, metadata = relation_pair
    if location == "config":
        config = invalid
    elif location == "sources":
        config["sources"] = invalid
    elif location == "entries":
        config["sources"]["exercise_entries"] = invalid
    elif location == "configured_properties":
        config["sources"]["exercise_entries"]["properties"] = invalid
    elif location == "metadata":
        metadata = invalid
    elif location == "live_properties":
        metadata["properties"] = invalid
    else:
        config["sources"]["workout_log"] = invalid
    errors = check_relations_safely(config, metadata)
    assert any(category in error for error in errors)


def test_relation_targets_extra_live_property_allowed(relation_pair):
    """Allow unrelated well-formed live fields without inventing extra required links."""
    config, metadata = relation_pair
    metadata["properties"]["fictional_sensitive_extra"] = {"id": "fake_extra", "type": "number"}
    assert check_relations_safely(config, metadata) == []


def test_relation_targets_collect_independent_errors(relation_pair):
    """Collect a configured UUID failure and a separate malformed live relation together."""
    config, metadata = relation_pair
    config["sources"]["workout_log"]["data_source_id"] = "fictional_sensitive_bad_uuid"
    metadata["properties"]["fictional_sensitive_ex"]["relation"] = None
    errors = check_relations_safely(config, metadata)
    assert len(errors) == 2
    assert any("exercise_entries.workout_log:" in error and "configured destination ID" in error for error in errors)
    assert any("exercise_entries.exercise:" in error and "live relation mapping" in error for error in errors)


def test_relation_pair_copies_are_isolated(relation_pair):
    """Prove nested mutations to copied inputs leave the original pair valid."""
    snapshot = deepcopy(relation_pair)
    config, metadata = deepcopy(relation_pair)
    config["sources"]["workout_log"]["data_source_id"] = "fictional_sensitive_changed"
    metadata["properties"]["fictional_sensitive_log"]["relation"] = None
    assert relation_pair == snapshot
    assert check_relations_safely(*relation_pair) == []


@pytest.fixture
def preflight_config(config, small_source_configs):
    """Build a fresh full config from independent synthetic field fixtures and UUIDs.

    No schema file or implementation constants supply expectations. Each source
    gets distinct UUIDs so individual failures can be introduced independently.
    """
    sources = {"exercise_entries": config, **deepcopy(small_source_configs)}
    identities = {
        "exercise_entries": ("cccccccc-dddd-4eee-8fff-aaaaaaaaaaa1", "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa2"),
        "workout_log": ("cccccccc-dddd-4eee-8fff-aaaaaaaaaaa3", "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa4"),
        "exercise": ("cccccccc-dddd-4eee-8fff-aaaaaaaaaaa5", "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa6"),
    }
    for source, (database_id, data_source_id) in identities.items():
        sources[source]["database_id"] = database_id
        sources[source]["data_source_id"] = data_source_id
    return {"sources": sources}


@pytest.fixture(params=["exercise_entries", "workout_log", "exercise"])
def preflight_source(request):
    """Exercise source-specific failures for every independently approved source."""
    return request.param


def check_preflight_safely(configuration):
    """Return preflight errors; assert input preservation and diagnostic privacy."""
    snapshot = deepcopy(configuration)
    errors = MODULE.check_configuration(configuration)
    assert configuration == snapshot
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    assert "fake_" not in messages
    assert "fictional_sensitive" not in messages
    # Catch UUID disclosure even if diagnostics normalize case or hyphenation.
    compact_messages = messages.lower().replace("-", "")
    for suffix in range(1, 7):
        secret = f"cccccccc-dddd-4eee-8fff-aaaaaaaaaaa{suffix}"
        assert secret.replace("-", "") not in compact_messages
    return errors


def test_preflight_valid_configuration(preflight_config):
    """Require the complete synthetic configuration to pass without mutation."""
    assert check_preflight_safely(preflight_config) == []


def test_preflight_missing_source(preflight_config, preflight_source):
    """Require each approved source rather than silently accepting a partial config."""
    del preflight_config["sources"][preflight_source]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert "required source is missing" in errors[0]


def test_preflight_all_sources_missing():
    """Collect all three source omissions when the sources object is empty."""
    errors = check_preflight_safely({"sources": {}})
    assert len(errors) == 3
    for source in ("exercise_entries", "workout_log", "exercise"):
        assert any(source in error and "required source is missing" in error for error in errors)


def test_preflight_unexpected_source_is_not_disclosed(preflight_config):
    """Reject arbitrary source entries without echoing names or synthetic credentials."""
    preflight_config["sources"]["fictional_sensitive_source_name"] = {
        "credential": "fictional_sensitive_credential_value", "id": "fake_private_id"
    }
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert "unexpected source" in errors[0].lower()


@pytest.mark.parametrize("configuration", [None, [], 42, "fictional_sensitive_config"])
def test_preflight_malformed_configuration(configuration):
    """Reject non-object input safely, including a missing configuration represented by None."""
    errors = check_preflight_safely(configuration)
    assert len(errors) == 1
    assert "configuration must be an object" in errors[0].lower()


def test_preflight_missing_sources_container():
    """Reject a missing sources key before inspecting individual sources."""
    errors = check_preflight_safely({})
    assert len(errors) == 1
    assert "sources must be an object" in errors[0].lower()


@pytest.mark.parametrize("sources", [None, [], 42, "fictional_sensitive_sources"])
def test_preflight_malformed_sources_container(sources):
    """Reject wrong sources-container types without reflecting their contents."""
    errors = check_preflight_safely({"sources": sources})
    assert len(errors) == 1
    assert "sources must be an object" in errors[0].lower()


@pytest.mark.parametrize("source_config", [None, [], 42, "fictional_sensitive_source"])
def test_preflight_malformed_source(preflight_config, preflight_source, source_config):
    """Reject a malformed approved source while retaining independent checks elsewhere."""
    preflight_config["sources"][preflight_source] = source_config
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert "source configuration must be an object" in errors[0]


@pytest.mark.parametrize("id_field", ["database_id", "data_source_id"])
@pytest.mark.parametrize("invalid_id", [None, "", " \t\n", 42, [], {}, "fictional_sensitive_bad_uuid"])
def test_preflight_invalid_uuid(preflight_config, preflight_source, id_field, invalid_id):
    """Reject each invalid UUID value independently at all six identity positions."""
    preflight_config["sources"][preflight_source][id_field] = invalid_id
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert id_field in errors[0]
    assert "malformed" in errors[0]


@pytest.mark.parametrize("id_field", ["database_id", "data_source_id"])
def test_preflight_missing_uuid(preflight_config, preflight_source, id_field):
    """Distinguish an omitted identity key from an explicitly invalid UUID value."""
    del preflight_config["sources"][preflight_source][id_field]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert id_field in errors[0]
    assert "missing" in errors[0]


@pytest.mark.parametrize("format_name", ["uppercase", "compact", "braced"])
def test_preflight_equivalent_uuid_formats(preflight_config, format_name):
    """Accept equivalent UUID spellings for both identity fields in all sources."""
    for source in preflight_config["sources"].values():
        for id_field in ("database_id", "data_source_id"):
            value = source[id_field]
            if format_name == "uppercase":
                source[id_field] = value.upper()
            elif format_name == "compact":
                source[id_field] = value.replace("-", "")
            else:
                source[id_field] = "{" + value + "}"
    assert check_preflight_safely(preflight_config) == []


@pytest.mark.parametrize("first, second", [
    ("exercise_entries", "workout_log"),
    ("exercise_entries", "exercise"),
    ("workout_log", "exercise"),
])
@pytest.mark.parametrize("format_name", ["same", "uppercase", "compact", "braced"])
def test_preflight_reused_data_source_uuid(preflight_config, first, second, format_name):
    """Reject semantic data-source reuse across every pair, including different spellings."""
    value = preflight_config["sources"][first]["data_source_id"]
    if format_name == "uppercase":
        value = value.upper()
    elif format_name == "compact":
        value = value.replace("-", "")
    elif format_name == "braced":
        value = "{" + value + "}"
    preflight_config["sources"][second]["data_source_id"] = value
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert "data_source_id" in errors[0]
    assert "reused" in errors[0]


def test_preflight_shared_database_uuid_allowed(preflight_config):
    """Allow sources to share a database while keeping their data-source IDs distinct."""
    for source in preflight_config["sources"].values():
        source["database_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa1"
    assert check_preflight_safely(preflight_config) == []


def test_preflight_duplicate_required_property_id(preflight_config):
    """Reject an ID collision between approved fields even when both types are numbers."""
    properties = preflight_config["sources"]["exercise_entries"]["properties"]
    properties["set_1_reps"]["id"] = properties["set_1_weight"]["id"]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert "exercise_entries" in errors[0]
    assert "duplicate configured property ID" in errors[0]


def test_preflight_property_ids_can_repeat_across_sources(preflight_config):
    """Scope property-ID uniqueness to each source rather than the entire configuration."""
    for source in preflight_config["sources"].values():
        next(iter(source["properties"].values()))["id"] = "fake_shared_property_id"
    assert check_preflight_safely(preflight_config) == []


def test_preflight_unexpected_mapping_duplicate_id(preflight_config, preflight_source):
    """Require both unexpected-field and duplicate-ID errors for an extra alias."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    properties["fictional_sensitive_extra_field"] = deepcopy(next(iter(properties.values())))
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 2
    assert any("unexpected configured field" in error for error in errors)
    assert any("duplicate configured property ID" in error for error in errors)


def test_preflight_missing_properties(preflight_config, preflight_source):
    """Require the properties container even when source UUIDs are valid."""
    del preflight_config["sources"][preflight_source]["properties"]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert "properties must be an object" in errors[0]


@pytest.mark.parametrize("properties", [None, [], 42, "fictional_sensitive_properties"])
def test_preflight_malformed_properties(preflight_config, preflight_source, properties):
    """Reject wrong properties-container types before reading field mappings."""
    preflight_config["sources"][preflight_source]["properties"] = properties
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert preflight_source in errors[0]
    assert "properties must be an object" in errors[0]


def test_preflight_missing_required_field(preflight_config, preflight_source):
    """Ensure preflight includes required-field validation rather than checking IDs alone."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    field = next(iter(properties))
    del properties[field]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert f"{preflight_source}.{field}:" in errors[0]
    assert "required field is missing" in errors[0]


@pytest.mark.parametrize("mapping", [None, [], 42, "fictional_sensitive_mapping"])
def test_preflight_malformed_property_mapping(preflight_config, preflight_source, mapping):
    """Reject non-object required mappings without disclosing arbitrary input values."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    field = next(iter(properties))
    properties[field] = mapping
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert f"{preflight_source}.{field}:" in errors[0]
    assert "property mapping must be an object" in errors[0]


@pytest.mark.parametrize("invalid_id", [None, "", " \t\n", 42, []])
def test_preflight_invalid_property_id(preflight_config, preflight_source, invalid_id):
    """Reject missing, blank, and non-string property IDs independently of UUID checks."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    field = next(iter(properties))
    properties[field]["id"] = invalid_id
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert field in errors[0]
    assert "property ID must be a non-empty string" in errors[0]


def test_preflight_missing_property_id(preflight_config, preflight_source):
    """Reject omitted property IDs as well as explicit invalid ID values."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    field = next(iter(properties))
    del properties[field]["id"]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert field in errors[0]
    assert "property ID must be a non-empty string" in errors[0]


@pytest.mark.parametrize("wrong_type", [None, 42, "fictional_sensitive_wrong_type"])
def test_preflight_incorrect_property_type(preflight_config, preflight_source, wrong_type):
    """Require approved types rather than trusting the configured type value."""
    properties = preflight_config["sources"][preflight_source]["properties"]
    field = next(iter(properties))
    properties[field]["type"] = wrong_type
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 1
    assert field in errors[0]
    assert "configured property type is incorrect" in errors[0]


def test_preflight_collects_independent_errors(preflight_config):
    """Collect identity, field-type, and omission errors across all three sources."""
    sources = preflight_config["sources"]
    sources["exercise_entries"]["database_id"] = "fictional_sensitive_bad_uuid"
    sources["workout_log"]["properties"]["session_name"]["type"] = "number"
    del sources["exercise"]["properties"]["exercise_name"]
    errors = check_preflight_safely(preflight_config)
    assert len(errors) == 3
    assert any("exercise_entries" in error and "database_id" in error for error in errors)
    assert any("workout_log.session_name:" in error and "type is incorrect" in error for error in errors)
    assert any("exercise.exercise_name:" in error and "missing" in error for error in errors)


def test_preflight_fixture_copies_are_isolated(preflight_config):
    """Prove nested edits to a deep copy cannot contaminate the original valid fixture."""
    snapshot = deepcopy(preflight_config)
    altered = deepcopy(preflight_config)
    altered["sources"]["exercise"]["properties"]["exercise_name"]["id"] = "fake_changed_id"
    del altered["sources"]["workout_log"]
    assert preflight_config == snapshot
    assert check_preflight_safely(preflight_config) == []


@pytest.fixture
def schema_pair(preflight_config):
    """Return valid full configuration and independently specified metadata.

    Reuse the independently defined configuration fixture, but spell out live
    IDs, types, identities, and relation destinations rather than copying them
    from configuration or implementation constants.
    """
    metadata = {
        "exercise_entries": {
            "object": "data_source",
            "id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa2",
            "parent": {"type": "database_id", "database_id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa1"},
            "properties": {
                "fictional_sensitive_log": {"id": "fake_workout_log", "type": "relation", "relation": {"data_source_id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa4"}},
                "fictional_sensitive_ex": {"id": "fake_exercise", "type": "relation", "relation": {"data_source_id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa6"}},
                "fictional_sensitive_w1": {"id": "fake_set_1_weight", "type": "number"},
                "fictional_sensitive_r1": {"id": "fake_set_1_reps", "type": "number"},
                "fictional_sensitive_w2": {"id": "fake_set_2_weight", "type": "number"},
                "fictional_sensitive_r2": {"id": "fake_set_2_reps", "type": "number"},
                "fictional_sensitive_w3": {"id": "fake_set_3_weight", "type": "number"},
                "fictional_sensitive_r3": {"id": "fake_set_3_reps", "type": "number"},
                "fictional_sensitive_created": {"id": "fake_created_time", "type": "created_time"},
                "fictional_sensitive_done": {"id": "fake_completed", "type": "checkbox"},
                "fictional_sensitive_distance": {"id": "fake_treadmill_km", "type": "number"},
            },
        },
        "workout_log": {
            "object": "data_source",
            "id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa4",
            "parent": {"type": "database_id", "database_id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa3"},
            "properties": {
                "fictional_sensitive_title": {"id": "fake_session_title", "type": "title"},
                "fictional_sensitive_date": {"id": "fake_session_created", "type": "created_time"},
            },
        },
        "exercise": {
            "object": "data_source",
            "id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa6",
            "parent": {"type": "database_id", "database_id": "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa5"},
            "properties": {
                "fictional_sensitive_name": {"id": "fake_exercise_title", "type": "title"},
            },
        },
    }
    return preflight_config, metadata


def check_schema_safely(config, metadata):
    """Return orchestration errors; fail on input mutation or sensitive diagnostics."""
    config_snapshot = deepcopy(config)
    metadata_snapshot = deepcopy(metadata)
    errors = MODULE.validate_schema(config, metadata)
    assert config == config_snapshot
    assert metadata == metadata_snapshot
    assert isinstance(errors, list)
    assert all(isinstance(error, str) for error in errors)
    messages = " ".join(errors)
    assert "fake_" not in messages
    assert "fictional_sensitive" not in messages
    compact = messages.lower().replace("-", "")
    for suffix in range(1, 8):
        secret = f"cccccccc-dddd-4eee-8fff-aaaaaaaaaaa{suffix}"
        assert secret.replace("-", "") not in compact
    return errors


def test_schema_complete_valid(schema_pair):
    """Accept only the complete matching identities, properties, and relation links."""
    assert check_schema_safely(*schema_pair) == []


def test_schema_preflight_stops_metadata_validation(schema_pair, monkeypatch):
    """Return the specific preflight error without calling any live-metadata validator."""
    config, metadata = schema_pair
    del config["sources"]["workout_log"]

    def forbidden_validator(*args, **kwargs):
        """Fail immediately if orchestration proceeds past failed preflight."""
        pytest.fail("Live-metadata validation must not run after preflight failure.")

    for name in ("check_source_identity", "check_property_ids", "check_relation_targets"):
        monkeypatch.setattr(MODULE, name, forbidden_validator)
    # None would itself fail metadata checks; only preflight's error may return.
    assert check_schema_safely(config, None) == ["workout_log: required source is missing."]


@pytest.mark.parametrize("metadata", [None, [], 42, "fictional_sensitive_metadata"])
def test_schema_malformed_metadata_root(schema_pair, metadata):
    """Reject missing or malformed metadata roots with a safe structural error."""
    config, _ = schema_pair
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert "schema metadata must be an object" in errors[0].lower()


@pytest.mark.parametrize("source", ["exercise_entries", "workout_log", "exercise"])
def test_schema_missing_source_metadata(schema_pair, source):
    """Require every source even when all remaining identities and relations are valid."""
    config, metadata = schema_pair
    del metadata[source]
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"{source}:" in errors[0]
    assert "required source metadata is missing" in errors[0]


def test_schema_empty_metadata(schema_pair):
    """Collect one missing-source error for each source when metadata is empty."""
    config, _ = schema_pair
    errors = check_schema_safely(config, {})
    assert len(errors) == 3
    for source in ("exercise_entries", "workout_log", "exercise"):
        assert any(f"{source}:" in error and "metadata is missing" in error for error in errors)


@pytest.mark.parametrize("source", ["exercise_entries", "workout_log", "exercise"])
@pytest.mark.parametrize("bad_metadata", [None, [], 42, "fictional_sensitive_source_metadata"])
def test_schema_malformed_source_metadata(schema_pair, source, bad_metadata):
    """Reject malformed source-level entries while continuing other source checks."""
    config, metadata = schema_pair
    metadata[source] = bad_metadata
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"{source}:" in errors[0]
    assert "source metadata must be an object" in errors[0]


def test_schema_unexpected_source_metadata_is_safe(schema_pair):
    """Reject arbitrary source keys without disclosing their names or payload values."""
    config, metadata = schema_pair
    metadata["fictional_sensitive_unknown_source"] = {"payload": "fictional_sensitive_raw_response"}
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert "unexpected source" in errors[0]


@pytest.mark.parametrize("source", ["exercise_entries", "workout_log", "exercise"])
@pytest.mark.parametrize("identity", ["data_source", "database"])
def test_schema_identity_mismatch(schema_pair, source, identity):
    """Check each source's own identity, including both relation destinations."""
    config, metadata = schema_pair
    if identity == "data_source":
        metadata[source]["id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
        category = "data-source ID"
    else:
        metadata[source]["parent"]["database_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
        category = "parent database ID"
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"{source}:" in errors[0]
    assert category in errors[0]
    assert "does not match" in errors[0]


@pytest.mark.parametrize("source, display, field", [
    ("exercise_entries", "fictional_sensitive_w1", "set_1_weight"),
    ("workout_log", "fictional_sensitive_title", "session_name"),
    ("exercise", "fictional_sensitive_name", "exercise_name"),
])
def test_schema_missing_required_live_id(schema_pair, source, display, field):
    """Require each source's property schema, even when its relation target is valid."""
    config, metadata = schema_pair
    del metadata[source]["properties"][display]
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"{source}.{field}:" in errors[0]
    assert "property ID is absent" in errors[0]


@pytest.mark.parametrize("source, display, field", [
    ("exercise_entries", "fictional_sensitive_w1", "set_1_weight"),
    ("workout_log", "fictional_sensitive_title", "session_name"),
    ("exercise", "fictional_sensitive_name", "exercise_name"),
])
def test_schema_incorrect_live_type(schema_pair, source, display, field):
    """Reject wrong property types in every source without trusting valid relation links."""
    config, metadata = schema_pair
    metadata[source]["properties"][display]["type"] = "fictional_sensitive_wrong_type"
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"{source}.{field}:" in errors[0]
    assert "live property type" in errors[0]


@pytest.mark.parametrize("display, field", [
    ("fictional_sensitive_log", "workout_log"),
    ("fictional_sensitive_ex", "exercise"),
])
def test_schema_incorrect_relation_destination(schema_pair, display, field):
    """Reject an incorrect relation target despite otherwise valid source schemas."""
    config, metadata = schema_pair
    metadata["exercise_entries"]["properties"][display]["relation"]["data_source_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 1
    assert f"exercise_entries.{field}:" in errors[0]
    assert "relation destination does not match" in errors[0]


def test_schema_swapped_relation_destinations(schema_pair):
    """Collect distinct errors for both swapped links without accepting source identity alone."""
    config, metadata = schema_pair
    props = metadata["exercise_entries"]["properties"]
    props["fictional_sensitive_log"]["relation"]["data_source_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa6"
    props["fictional_sensitive_ex"]["relation"]["data_source_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa4"
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 2
    for field in ("workout_log", "exercise"):
        assert any(f"exercise_entries.{field}:" in error and "relation destination" in error for error in errors)


def test_schema_collects_independent_source_errors(schema_pair):
    """Collect an identity error, a missing property, and a type error across three sources."""
    config, metadata = schema_pair
    metadata["exercise_entries"]["id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
    del metadata["workout_log"]["properties"]["fictional_sensitive_title"]
    metadata["exercise"]["properties"]["fictional_sensitive_name"]["type"] = "number"
    errors = check_schema_safely(config, metadata)
    assert len(errors) == 3
    assert any("exercise_entries:" in error and "data-source ID" in error for error in errors)
    assert any("workout_log.session_name:" in error and "absent" in error for error in errors)
    assert any("exercise.exercise_name:" in error and "live property type" in error for error in errors)


def test_schema_accepts_renamed_reordered_properties(schema_pair):
    """Accept renamed, emoji-prefixed, reversed live properties in all three sources."""
    config, metadata = schema_pair
    for source_metadata in metadata.values():
        source_metadata["properties"] = {
            f" 🏋️ fictional_sensitive_renamed_{index}\t": mapping
            for index, mapping in enumerate(reversed(list(source_metadata["properties"].values())))
        }
    assert check_schema_safely(config, metadata) == []


@pytest.mark.parametrize("scenario", ["valid", "invalid_config", "invalid_metadata"])
def test_schema_validation_performs_no_io(schema_pair, monkeypatch, scenario):
    """Guard common file/network entry points on both success and failure paths."""
    import builtins
    import io
    import os
    import socket

    config, metadata = schema_pair
    if scenario == "invalid_config":
        del config["sources"]["exercise"]
    elif scenario == "invalid_metadata":
        metadata = None

    def forbidden_io(*args, **kwargs):
        """Fail before any attempted file access, retrieval, or network connection."""
        pytest.fail("Schema validation must perform no file or network I/O.")

    # Limit patches to the validation call so pytest can still read source files
    # for its own reporting after a failure. No real I/O is attempted by this test.
    with monkeypatch.context() as guard:
        for owner, name in (
            (builtins, "open"), (io, "open"), (os, "open"), (Path, "open"),
            (socket, "socket"), (socket, "create_connection"),
            (MODULE.http.client, "HTTPSConnection"), (MODULE.http.client, "HTTPConnection"),
            (MODULE, "load_configuration"), (MODULE, "retrieve_metadata"),
        ):
            guard.setattr(owner, name, forbidden_io)
        errors = check_schema_safely(config, metadata)
    if scenario == "valid":
        assert errors == []
    elif scenario == "invalid_config":
        assert errors == ["exercise: required source is missing."]
    else:
        assert len(errors) == 1
        assert "Schema metadata must be an object" in errors[0]


def test_schema_fixture_copies_are_isolated(schema_pair):
    """Prove nested edits to copied inputs cannot contaminate the complete valid pair."""
    snapshot = deepcopy(schema_pair)
    config, metadata = deepcopy(schema_pair)
    config["sources"]["exercise"]["properties"]["exercise_name"]["id"] = "fake_changed"
    metadata["workout_log"]["properties"]["fictional_sensitive_title"]["type"] = "number"
    assert schema_pair == snapshot
    assert check_schema_safely(*schema_pair) == []


@pytest.fixture
def cli_harness(schema_pair, monkeypatch):
    """Run real CLI stages against in-memory files, credentials, and HTTPS doubles.

    No host environment values or files are read. Any unmocked file/network
    entry point fails before doing I/O. Tests may alter state to inject faults.
    """
    import builtins
    import io
    import json
    import socket
    from unittest.mock import Mock

    config, metadata = schema_pair
    state = {
        "config": config, "metadata": metadata, "config_text": None,
        "bodies": {}, "statuses": {}, "lengths": {}, "connections": [],
        "responses": [], "requests": [], "opens": 0,
        "connect_error": None, "read_error": None,
        "path": Path("fictional_sensitive_config.json"),
    }
    source_order = ("exercise_entries", "workout_log", "exercise")
    endpoints = (
        "/v1/data_sources/cccccccc-dddd-4eee-8fff-aaaaaaaaaaa2",
        "/v1/data_sources/cccccccc-dddd-4eee-8fff-aaaaaaaaaaa4",
        "/v1/data_sources/cccccccc-dddd-4eee-8fff-aaaaaaaaaaa6",
    )

    def forbidden_io(*args, **kwargs):
        """Fail before touching disk, cleartext HTTP, or a real network socket."""
        pytest.fail("Unexpected file or network access in the mocked CLI.")

    def open_config(path, *args, **kwargs):
        """Return synthetic JSON only for the explicit read-only configuration path."""
        assert path == state["path"]
        assert not args
        assert kwargs == {"encoding": "utf-8"}
        state["opens"] += 1
        text = state["config_text"]
        return io.StringIO(json.dumps(state["config"]) if text is None else text)

    def connect(host, timeout):
        """Provide a bounded mock response for one approved GET metadata request."""
        assert host == "api.notion.com"
        assert timeout == 30
        if state["connect_error"] is not None:
            raise state["connect_error"]
        index = len(state["connections"])
        assert index < 3
        source = source_order[index]
        body = state["bodies"].get(index)
        if body is None:
            body = json.dumps(state["metadata"][source]).encode("utf-8")
        response = Mock(status=state["statuses"].get(index, 200))
        response.getheader.side_effect = lambda name: state["lengths"].get(index) if name == "Content-Length" else None

        def read(amount):
            """Emulate a bounded read; an unbounded call cannot satisfy this signature."""
            assert amount == 1024 * 1024 + 1
            if state["read_error"] is not None:
                raise state["read_error"]
            return body[:amount]

        response.read.side_effect = read
        connection = Mock()

        def request(method, url, headers):
            """Reject record queries, writes, redirects, or leaked endpoint control."""
            assert method == "GET"
            assert url == endpoints[index]
            assert headers == {
                "Authorization": "Bearer fictional_sensitive_test_token",
                "Notion-Version": "2026-03-11",
                "Accept": "application/json",
            }
            state["requests"].append((method, url))

        connection.request.side_effect = request
        connection.getresponse.return_value = response
        state["connections"].append(connection)
        state["responses"].append(response)
        return connection

    # Replace the entire environment so tests never inspect real credentials.
    monkeypatch.setattr(MODULE.os, "environ", {"NOTION_TOKEN": "fictional_sensitive_test_token"})
    monkeypatch.setattr(Path, "open", open_config)
    for owner, name in (
        (builtins, "open"), (io, "open"), (MODULE.os, "open"),
        (socket, "socket"), (socket, "create_connection"),
        (MODULE.http.client, "HTTPConnection"),
    ):
        monkeypatch.setattr(owner, name, forbidden_io)
    monkeypatch.setattr(MODULE.http.client, "HTTPSConnection", connect)
    return state


def run_mock_cli(state, capsys):
    """Return CLI status/output after asserting no synthetic secrets reach either stream."""
    status = MODULE.main(["--config", str(state["path"])])
    captured = capsys.readouterr()
    assert_cli_output_safe(captured)
    if status != 0:
        assert captured.out == ""
        assert "passed" not in captured.err.lower()
    return status, captured


def assert_cli_output_safe(captured):
    """Reject credential, path, property-name, UUID, and raw-response markers in output."""
    text = captured.out + captured.err
    assert "fictional_sensitive" not in text
    assert "fake_" not in text
    assert "/v1/" not in text
    compact = text.lower().replace("-", "")
    for suffix in range(1, 8):
        assert f"ccccccccdddd4eee8fffaaaaaaaaaaa{suffix}" not in compact


def test_cli_valid_full_flow(cli_harness, capsys):
    """Exercise load, preflight, all three GETs, validation, and success reporting."""
    snapshot = deepcopy((cli_harness["config"], cli_harness["metadata"]))
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 0
    assert "passed for all three sources" in output.out
    assert output.err == ""
    assert cli_harness["opens"] == 1
    assert len(cli_harness["requests"]) == 3
    for connection, response in zip(cli_harness["connections"], cli_harness["responses"]):
        connection.close.assert_called_once_with()
        response.read.assert_called_once_with(1024 * 1024 + 1)
    assert (cli_harness["config"], cli_harness["metadata"]) == snapshot


def test_cli_invalid_config_never_reads_credentials_or_calls_api(cli_harness, monkeypatch, capsys):
    """Stop after preflight, before token lookup, endpoint construction, or network access."""
    del cli_harness["config"]["sources"]["exercise"]

    class ForbiddenEnvironment(dict):
        """Fail if validation tries to obtain credentials before preflight passes."""
        def get(self, key, default=None):
            """Reject token lookup; allow argparse's locale lookup in this empty fake env."""
            if key == "NOTION_TOKEN":
                pytest.fail("Credential lookup before successful preflight.")
            return super().get(key, default)

    # Restore the fake environment before pytest needs it for teardown/reporting.
    with monkeypatch.context() as guard:
        guard.setattr(MODULE.os, "environ", ForbiddenEnvironment())
        status, output = run_mock_cli(cli_harness, capsys)
    assert status == 1
    assert "exercise: required source is missing" in output.err
    assert cli_harness["requests"] == []
    assert cli_harness["connections"] == []


@pytest.mark.parametrize("problem, category", [
    ("identity", "data-source ID does not match"),
    ("parent", "parent database ID does not match"),
    ("property_type", "live property type does not match"),
    ("relation", "relation destination does not match"),
    ("missing_property", "property ID is absent"),
    ("missing_properties", "live properties must be an object"),
])
def test_cli_schema_failure_exits_one(cli_harness, capsys, problem, category):
    """Do not report success for valid JSON carrying incorrect or incomplete schemas."""
    metadata = cli_harness["metadata"]
    if problem == "identity":
        metadata["exercise"]["id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
    elif problem == "parent":
        metadata["workout_log"]["parent"]["database_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
    elif problem == "property_type":
        metadata["exercise"]["properties"]["fictional_sensitive_name"]["type"] = "fictional_sensitive_wrong_type"
    elif problem == "relation":
        metadata["exercise_entries"]["properties"]["fictional_sensitive_log"]["relation"]["data_source_id"] = "cccccccc-dddd-4eee-8fff-aaaaaaaaaaa7"
    elif problem == "missing_property":
        del metadata["exercise"]["properties"]["fictional_sensitive_name"]
    else:
        del metadata["exercise"]["properties"]
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 1
    assert category in output.err
    assert len(cli_harness["requests"]) == 3


@pytest.mark.parametrize("incomplete", [None, {}, {"exercise_entries": None}])
def test_cli_incomplete_retrieval_result_cannot_succeed(cli_harness, monkeypatch, capsys, incomplete):
    """Defend against incomplete aggregate metadata even if a retrieval adapter returns it."""
    monkeypatch.setattr(MODULE, "retrieve_metadata", lambda configuration: incomplete)
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 1
    assert "metadata" in output.err.lower()


@pytest.mark.parametrize("token", [None, "", " \t "])
def test_cli_missing_token_operational_failure(cli_harness, capsys, token):
    """Require only NOTION_TOKEN; never substitute another credential variable."""
    MODULE.os.environ.clear()
    MODULE.os.environ["NOTION_API_KEY"] = "fictional_sensitive_wrong_variable"
    if token is not None:
        MODULE.os.environ["NOTION_TOKEN"] = token
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert "could not complete" in output.err
    assert cli_harness["connections"] == []


@pytest.mark.parametrize("status_code", [301, 302, 307, 308, 400, 401, 403, 404, 429, 500])
def test_cli_http_failure_and_redirects_are_not_followed(cli_harness, capsys, status_code):
    """Reject non-200 responses without reading their bodies or following redirects."""
    cli_harness["statuses"][0] = status_code
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert "could not complete" in output.err
    assert len(cli_harness["connections"]) == 1
    cli_harness["responses"][0].read.assert_not_called()
    cli_harness["connections"][0].close.assert_called_once_with()


@pytest.mark.parametrize("last_source", [1, 2])
def test_cli_later_source_failure_prevents_partial_success(cli_harness, capsys, last_source):
    """Fail the complete run when a later source fails after earlier successful GETs."""
    cli_harness["statuses"][last_source] = 403
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert len(cli_harness["requests"]) == last_source + 1
    for connection in cli_harness["connections"]:
        connection.close.assert_called_once_with()


@pytest.mark.parametrize("stage", ["connect_error", "read_error"])
def test_cli_transport_exceptions_are_sanitized(cli_harness, capsys, stage):
    """Suppress sensitive exception details on connection and response-reading failures."""
    cli_harness[stage] = OSError("fictional_sensitive_exception fake_secret /v1/data_sources/private")
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert "could not complete" in output.err
    for connection in cli_harness["connections"]:
        connection.close.assert_called_once_with()


@pytest.mark.parametrize("body", [
    b'{"fictional_sensitive_raw":', b'[]', b'null', b'42',
    b'"fictional_sensitive_scalar"', b'\xff', b'{"value": NaN}',
    b'{"value": Infinity}', b'{"object":"data_source","object":"fictional_sensitive_duplicate"}',
])
def test_cli_invalid_response_json_is_operational_failure(cli_harness, capsys, body):
    """Reject invalid encoding, syntax, non-object JSON, constants, and duplicate keys."""
    cli_harness["bodies"][0] = body
    status, output = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert "could not complete" in output.err
    assert len(cli_harness["requests"]) == 1


def test_cli_response_size_limit_without_header(cli_harness, capsys):
    """Bound bytes read even if the server provides no Content-Length."""
    cli_harness["bodies"][0] = b" " * (1024 * 1024 + 1)
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    cli_harness["responses"][0].read.assert_called_once_with(1024 * 1024 + 1)
    cli_harness["connections"][0].close.assert_called_once_with()


def test_cli_response_size_limit_with_oversized_header(cli_harness, capsys):
    """Reject an oversized declared length before buffering its body."""
    cli_harness["lengths"][0] = str(1024 * 1024 + 1)
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    cli_harness["responses"][0].read.assert_not_called()


def test_cli_response_size_limit_with_false_header(cli_harness, capsys):
    """Do not trust a small declared length to override the actual response cap."""
    cli_harness["lengths"][0] = "1"
    cli_harness["bodies"][0] = b" " * (1024 * 1024 + 1)
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    cli_harness["responses"][0].read.assert_called_once_with(1024 * 1024 + 1)


@pytest.mark.parametrize("length", ["-1", "fictional_sensitive_length", "1.5", "١", "999999"])
def test_cli_invalid_or_incomplete_response_length(cli_harness, capsys, length):
    """Reject malformed length headers and truncated bodies without disclosing them."""
    cli_harness["lengths"][0] = length
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2


def test_cli_exact_size_limit_is_allowed(cli_harness, capsys):
    """Accept a valid object padded to exactly the documented 1 MiB boundary."""
    import json

    body = json.dumps(cli_harness["metadata"]["exercise_entries"]).encode("utf-8")
    cli_harness["bodies"][0] = body + b" " * (1024 * 1024 - len(body))
    cli_harness["lengths"][0] = str(1024 * 1024)
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 0


@pytest.mark.parametrize("text", [
    '{"fictional_sensitive_raw":', '{"sources":{},"sources":{}}', '{"value":NaN}',
])
def test_cli_invalid_config_json_is_operational_failure(cli_harness, capsys, text):
    """Reject undecodable configuration before credentials or API access."""
    cli_harness["config_text"] = text
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert cli_harness["connections"] == []


def test_cli_config_loading_error_is_safe(cli_harness, monkeypatch, capsys):
    """Map file failures to exit 2 while hiding private paths and exception messages."""
    def inaccessible_config(*args, **kwargs):
        """Emulate a config file that cannot be opened without touching disk."""
        raise OSError("fictional_sensitive_config_path fake_private_id")

    monkeypatch.setattr(Path, "open", inaccessible_config)
    status, _ = run_mock_cli(cli_harness, capsys)
    assert status == 2
    assert cli_harness["connections"] == []


def test_client_direct_call_requires_preflight(cli_harness, capsys):
    """Prevent direct callers from placing unvalidated IDs into request paths."""
    cli_harness["config"]["sources"]["exercise"]["data_source_id"] = "fictional_sensitive_path/../../query"
    with pytest.raises(RuntimeError, match="Configuration preflight failed"):
        MODULE.retrieve_metadata(cli_harness["config"])
    assert cli_harness["connections"] == []
    output = capsys.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("args", [
    [], ["--config"], ["--fictional_sensitive_token", "fictional_sensitive_value"],
    ["--config", "fictional_sensitive_config.json", "--fictional_sensitive_unknown"],
])
def test_cli_argument_errors_are_safe(cli_harness, capsys, args):
    """Exit 2 for usage errors without echoing arbitrary arguments or paths."""
    with pytest.raises(SystemExit) as result:
        MODULE.main(args)
    assert result.value.code == 2
    output = capsys.readouterr()
    assert_cli_output_safe(output)
    assert "Usage error" in output.err
    assert cli_harness["opens"] == 0
    assert cli_harness["connections"] == []


def test_cli_help_is_offline(cli_harness, capsys):
    """Provide help with exit 0 before configuration, credentials, or network access."""
    with pytest.raises(SystemExit) as result:
        MODULE.main(["--help"])
    assert result.value.code == 0
    output = capsys.readouterr()
    assert "--config" in output.out
    assert output.err == ""
    assert cli_harness["opens"] == 0
    assert cli_harness["connections"] == []