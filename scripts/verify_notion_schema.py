"""Verify configured Notion schema using read-only data-source metadata only.

No page queries, workout-record retrieval, or response files are supported.
"""

import argparse
import http.client
import json
import os
from pathlib import Path
import sys
from uuid import UUID


NOTION_API_VERSION = "2026-03-11"
TOKEN_ENV_VAR = "NOTION_TOKEN"
# Schemas are small; cap each response at 1 MiB, independently of server headers.
MAX_RESPONSE_BYTES = 1024 * 1024

# Independent expectations: never derive these from user configuration or metadata.
EXPECTED_FIELDS = {
    "exercise_entries": {
        "workout_log": "relation",
        "exercise": "relation",
        "set_1_weight": "number",
        "set_1_reps": "number",
        "set_2_weight": "number",
        "set_2_reps": "number",
        "set_3_weight": "number",
        "set_3_reps": "number",
        "created_time": "created_time",
        "completed": "checkbox",
        "treadmill_km": "number",
    },
    "workout_log": {
        "session_name": "title",
        "created_time": "created_time",
    },
    "exercise": {
        "exercise_name": "title",
    },
}


def decode_json(document: str | bytes) -> object:
    """Decode JSON; reject duplicate keys and non-JSON numeric constants.

    Raise ValueError on ambiguous or invalid JSON without including input values.
    Callers must also check the decoded structure before using it.
    """
    def unique_object(pairs):
        """Build an object from key/value pairs; reject duplicate keys to avoid ambiguity."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON object key.")
            result[key] = value
        return result

    def reject_constant(value):
        """Reject NaN and infinity, which Python accepts but the JSON standard does not."""
        raise ValueError("Invalid JSON constant.")

    return json.loads(document, object_pairs_hook=unique_object, parse_constant=reject_constant)


def load_configuration(path: Path) -> dict:
    """Load the explicit path's UTF-8 JSON configuration; sanitize loading failures.

    Property mappings contain id and type. Loading is not schema verification.
    Return decoded JSON for preflight, which rejects non-object configurations.
    Raise RuntimeError on file/encoding/JSON errors. Never infer a private path
    or load dotenv files.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            return decode_json(handle.read())
    except (OSError, ValueError):
        raise RuntimeError("Configuration could not be loaded.") from None


def retrieve_metadata(configuration: dict) -> dict:
    """Retrieve only data-source metadata with GET; never follow redirects.

    Credentials come exclusively from NOTION_TOKEN. Responses remain in memory;
    identifiers, URLs, credentials, and response bodies must never be reported.
    Require valid preflight even for direct callers; raise a sanitized RuntimeError
    for invalid configuration, credentials, HTTP, JSON, size, or transport failures.
    Return one in-memory response object per approved source, capped at 1 MiB each.
    """
    if check_configuration(configuration):
        raise RuntimeError("Configuration preflight failed.")
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token or not token.strip():
        raise RuntimeError("Required token environment variable is not set.")

    metadata = {}
    try:
        for source_name in EXPECTED_FIELDS:
            data_source_id = str(
                UUID(configuration["sources"][source_name]["data_source_id"])
            )
            connection = http.client.HTTPSConnection("api.notion.com", timeout=30)
            try:
                connection.request(
                    "GET",
                    "/v1/data_sources/" + data_source_id,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Notion-Version": NOTION_API_VERSION,
                        "Accept": "application/json",
                    },
                )
                response = connection.getresponse()
                if response.status != 200:
                    raise RuntimeError("Metadata retrieval failed.")
                # Treat headers as untrusted. The bounded read also protects us
                # when Content-Length is absent, false, or chunked.
                length_header = response.getheader("Content-Length")
                expected_length = None
                if length_header is not None:
                    if not length_header.isascii() or not length_header.isdigit():
                        raise RuntimeError("Invalid response length.")
                    expected_length = int(length_header)
                    if expected_length > MAX_RESPONSE_BYTES:
                        raise RuntimeError("Metadata response exceeds size limit.")
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise RuntimeError("Metadata response exceeds size limit.")
                if expected_length is not None and len(body) != expected_length:
                    raise RuntimeError("Metadata response is incomplete.")
                payload = decode_json(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("Metadata response must be an object.")
                metadata[source_name] = payload
            finally:
                connection.close()
    except Exception:
        # Never expose exception details that could contain private information.
        raise RuntimeError("Metadata retrieval failed.") from None
    return metadata


def check_configured_fields(source_name: str, source_config: dict) -> list[str]:
    """Check one source's configured properties against EXPECTED_FIELDS.

    source_name selects an approved source; source_config is its dictionary,
    with a properties dictionary mapping field names to id/type dictionaries.
    Return a list of safe error messages, or [] when the field checks pass.
    Unknown sources or malformed outer structures return one error immediately;
    otherwise collect all detectable field errors so callers can fix them together.

    The input is not modified, and no files or API metadata are accessed.
    Messages name only approved source/field labels, never configured values or
    unknown labels. Passing does not verify IDs against Notion, ID uniqueness,
    data-source identity, or relation targets.
    """
    # Reject unknown names before using source labels in diagnostics.
    if not isinstance(source_name, str) or source_name not in EXPECTED_FIELDS:
        return ["Unknown source; cannot check configured fields."]
    if not isinstance(source_config, dict):
        return [f"{source_name}: source configuration must be an object."]

    # Field checks require a mapping; malformed containers cannot be inspected safely.
    properties = source_config.get("properties")
    if not isinstance(properties, dict):
        return [f"{source_name}: properties must be an object."]

    expected = EXPECTED_FIELDS[source_name]
    errors = []
    for field_name, expected_type in expected.items():
        label = f"{source_name}.{field_name}"
        if field_name not in properties:
            errors.append(f"{label}: required field is missing.")
            continue

        mapping = properties[field_name]
        if not isinstance(mapping, dict):
            errors.append(f"{label}: property mapping must be an object.")
            continue

        # Check ID and type independently so both problems can be reported.
        # Stripping only for this check also rejects whitespace-only IDs.
        property_id = mapping.get("id")
        if not isinstance(property_id, str) or not property_id.strip():
            errors.append(f"{label}: property ID must be a non-empty string.")
        if mapping.get("type") != expected_type:
            errors.append(f"{label}: configured property type is incorrect.")

    for field_name in properties:
        if field_name not in expected:
            # The unexpected label itself could contain private information.
            errors.append(f"{source_name}: unexpected configured field.")

    return errors


def check_source_identity(
    source_name: str, source_config: dict, live_metadata: dict
) -> list[str]:
    """Compare configured source/database IDs with supplied data-source metadata.

    source_name selects an approved source. source_config contains database_id
    and data_source_id; live_metadata is the already-retrieved response object.
    Return safe error strings, or [] when object type, IDs, and parent match.
    Malformed containers are rejected without inspecting their children, while
    independent checks continue. Missing, blank, non-string, and invalid UUID
    values are errors; valid UUID spellings are normalized before comparison.
    Inputs are not modified. No files, credentials, or network are accessed.
    """
    # Only approved labels may enter messages; arbitrary names could be private.
    if not isinstance(source_name, str) or source_name not in EXPECTED_FIELDS:
        return ["Unknown source; cannot check source identity."]

    errors = []
    identity_values = {}
    if isinstance(source_config, dict):
        identity_values["configured data-source ID"] = source_config.get("data_source_id")
        identity_values["configured database ID"] = source_config.get("database_id")
    else:
        errors.append(f"{source_name}: source configuration must be an object.")

    if isinstance(live_metadata, dict):
        if live_metadata.get("object") != "data_source":
            errors.append(f"{source_name}: metadata object must be a data source.")
        identity_values["response data-source ID"] = live_metadata.get("id")
        parent = live_metadata.get("parent")
        if isinstance(parent, dict):
            # Parent type and ID are separate checks so one cannot hide the other.
            if parent.get("type") != "database_id":
                errors.append(f"{source_name}: parent type must be database_id.")
            identity_values["parent database ID"] = parent.get("database_id")
        else:
            errors.append(f"{source_name}: metadata parent must be an object.")
    else:
        errors.append(f"{source_name}: live metadata must be an object.")

    normalized_ids = {}
    for label, value in identity_values.items():
        # Never interpolate values or UUID exception details into diagnostics.
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{source_name}: {label} is missing or malformed.")
            continue
        try:
            normalized_ids[label] = UUID(value)
        except ValueError:
            errors.append(f"{source_name}: {label} is missing or malformed.")

    # Compare only valid UUIDs, avoiding misleading mismatch errors for absent IDs.
    comparisons = (
        ("configured data-source ID", "response data-source ID", "data-source ID"),
        ("configured database ID", "parent database ID", "parent database ID"),
    )
    for configured_label, live_label, description in comparisons:
        if configured_label in normalized_ids and live_label in normalized_ids:
            if normalized_ids[configured_label] != normalized_ids[live_label]:
                errors.append(f"{source_name}: {description} does not match configuration.")

    return errors

def check_property_ids(
    source_name: str, source_config: dict, live_metadata: dict
) -> list[str]:
    """Check required configured IDs against already-retrieved property metadata.

    source_name selects EXPECTED_FIELDS. source_config contains field-to-id/type
    mappings under properties; live_metadata contains display-name-to-property
    mappings under properties. Return safe errors, or [] when checks pass.
    Malformed containers, mappings, IDs, types, and duplicate IDs are rejected.
    IDs are opaque non-blank strings, compared exactly without UUID parsing.
    Extra well-formed live properties are allowed. No inputs are modified, and
    no I/O, data-source identity checks, or relation-target checks are performed.
    """
    # Validate the label before it can enter diagnostics; never echo unknown names.
    if not isinstance(source_name, str) or source_name not in EXPECTED_FIELDS:
        return ["Unknown source; cannot check property IDs."]

    # Reuse configuration checks so missing fields and wrong configured types
    # cannot silently pass merely because a matching live ID exists.
    errors = check_configured_fields(source_name, source_config)
    expected = EXPECTED_FIELDS[source_name]
    configured_ids = {}
    seen_configured_ids = set()
    duplicate_configured_ids = set()
    properties = source_config.get("properties") if isinstance(source_config, dict) else None
    if isinstance(properties, dict):
        for field_name, mapping in properties.items():
            # Required-field mapping errors are already reported above. Extra
            # mappings still need inspection to detect collisions within the source.
            if not isinstance(mapping, dict):
                if field_name not in expected:
                    errors.append(f"{source_name}: extra configured mapping is malformed.")
                continue
            property_id = mapping.get("id")
            if not isinstance(property_id, str) or not property_id.strip():
                if field_name not in expected:
                    errors.append(f"{source_name}: extra configured property ID is malformed.")
                continue
            if property_id in seen_configured_ids:
                if property_id not in duplicate_configured_ids:
                    errors.append(f"{source_name}: duplicate configured property ID.")
                duplicate_configured_ids.add(property_id)
            seen_configured_ids.add(property_id)
            if field_name in expected:
                configured_ids[field_name] = property_id

    if not isinstance(live_metadata, dict):
        errors.append(f"{source_name}: live metadata must be an object.")
        return errors
    live_properties = live_metadata.get("properties")
    if not isinstance(live_properties, dict):
        errors.append(f"{source_name}: live properties must be an object.")
        return errors

    live_by_id = {}
    seen_live_ids = set()
    duplicate_live_ids = set()
    # Display names are deliberately ignored: names can change and may be private.
    for mapping in live_properties.values():
        if not isinstance(mapping, dict):
            errors.append(f"{source_name}: live property mapping is malformed.")
            continue
        property_id = mapping.get("id")
        if not isinstance(property_id, str) or not property_id.strip():
            errors.append(f"{source_name}: live property ID is malformed.")
            continue
        if property_id in seen_live_ids:
            if property_id not in duplicate_live_ids:
                errors.append(f"{source_name}: duplicate live property ID.")
            duplicate_live_ids.add(property_id)
        seen_live_ids.add(property_id)
        live_type = mapping.get("type")
        if not isinstance(live_type, str) or not live_type.strip():
            errors.append(f"{source_name}: live property type is malformed.")
        # Keep the first entry; duplicate IDs will be excluded before lookup use.
        if property_id not in live_by_id:
            live_by_id[property_id] = mapping

    for field_name, expected_type in expected.items():
        property_id = configured_ids.get(field_name)
        if property_id is None:
            continue
        # Ambiguous IDs must never be accepted by choosing one duplicate's type.
        if property_id in duplicate_configured_ids or property_id in duplicate_live_ids:
            continue
        label = f"{source_name}.{field_name}"
        if property_id not in live_by_id:
            errors.append(f"{label}: configured property ID is absent from live metadata.")
            continue
        if live_by_id[property_id].get("type") != expected_type:
            errors.append(f"{label}: live property type does not match the approved type.")

    return errors

def check_relation_targets(
    configuration: dict, exercise_entries_metadata: dict
) -> list[str]:
    """Check Exercise Entries relations against destinations in configuration.sources.

    configuration is the full schema configuration; exercise_entries_metadata
    is the already-retrieved Exercise Entries data-source response. Return safe
    errors, or [] when both required relations point to the configured sources.
    Reject malformed structures, ambiguous property IDs, and invalid target UUIDs
    without modifying inputs or performing I/O. Property IDs remain opaque strings.
    This checks links only: later orchestration must also validate each destination
    data source's own identity and schema before declaring verification successful.
    """
    if not isinstance(configuration, dict):
        return ["Relation configuration must be an object."]
    sources = configuration.get("sources")
    if not isinstance(sources, dict):
        return ["Relation configuration sources must be an object."]

    errors = []

    def index_properties(properties, description):
        """Return an ID lookup and duplicate-ID set; append safe structural errors.

        description is an internal label. Ignore display names and never include
        mapping contents in errors. Inspect all IDs before any relation lookup.
        """
        lookup = {}
        duplicates = set()
        if not isinstance(properties, dict):
            errors.append(f"{description}: properties must be an object.")
            return lookup, duplicates
        for mapping in properties.values():
            if not isinstance(mapping, dict):
                errors.append(f"{description}: property mapping is malformed.")
                continue
            property_id = mapping.get("id")
            if not isinstance(property_id, str) or not property_id.strip():
                errors.append(f"{description}: property ID is missing or malformed.")
                continue
            if property_id in lookup:
                if property_id not in duplicates:
                    errors.append(f"{description}: duplicate property ID.")
                duplicates.add(property_id)
            else:
                lookup[property_id] = mapping
        return lookup, duplicates

    entries = sources.get("exercise_entries")
    if not isinstance(entries, dict):
        errors.append("exercise_entries: source configuration must be an object.")
        configured_properties = None
    else:
        configured_properties = entries.get("properties")
    _, configured_duplicates = index_properties(
        configured_properties, "exercise_entries configuration"
    )

    if not isinstance(exercise_entries_metadata, dict):
        errors.append("exercise_entries: live metadata must be an object.")
        live_properties = None
    else:
        live_properties = exercise_entries_metadata.get("properties")
    live_by_id, live_duplicates = index_properties(
        live_properties, "exercise_entries metadata"
    )

    # Only these approved labels enter diagnostics; IDs and display names never do.
    # Each field name also selects its existing destination source configuration.
    for field_name in ("workout_log", "exercise"):
        label = f"exercise_entries.{field_name}"
        destination = sources.get(field_name)
        expected_target = None
        if not isinstance(destination, dict):
            errors.append(f"{label}: destination configuration must be an object.")
        else:
            destination_id = destination.get("data_source_id")
            if not isinstance(destination_id, str) or not destination_id.strip():
                errors.append(f"{label}: configured destination ID is missing or malformed.")
            else:
                try:
                    expected_target = UUID(destination_id)
                except ValueError:
                    errors.append(f"{label}: configured destination ID is missing or malformed.")

        # Destination checks above remain independent of property lookup failures.
        if not isinstance(configured_properties, dict):
            continue
        configured_mapping = configured_properties.get(field_name)
        if not isinstance(configured_mapping, dict):
            errors.append(f"{label}: configured relation mapping is missing or malformed.")
            continue
        property_id = configured_mapping.get("id")
        if configured_mapping.get("type") != "relation":
            errors.append(f"{label}: configured property type must be relation.")
        if not isinstance(property_id, str) or not property_id.strip():
            # The indexing pass already reported this invalid ID.
            continue
        if property_id in configured_duplicates or property_id in live_duplicates:
            # Never choose an arbitrary mapping for an ambiguous ID.
            continue
        if not isinstance(live_properties, dict):
            continue
        live_mapping = live_by_id.get(property_id)
        if live_mapping is None:
            errors.append(f"{label}: relation property ID is absent from live metadata.")
            continue
        if live_mapping.get("type") != "relation":
            errors.append(f"{label}: live property type must be relation.")
        relation = live_mapping.get("relation")
        if not isinstance(relation, dict):
            errors.append(f"{label}: live relation mapping is missing or malformed.")
            continue
        target_id = relation.get("data_source_id")
        if not isinstance(target_id, str) or not target_id.strip():
            errors.append(f"{label}: live destination ID is missing or malformed.")
            continue
        try:
            live_target = UUID(target_id)
        except ValueError:
            # UUID exception details can contain IDs; return only a fixed message.
            errors.append(f"{label}: live destination ID is missing or malformed.")
            continue
        if expected_target is not None and live_target != expected_target:
            errors.append(f"{label}: relation destination does not match configuration.")

    return errors

def check_configuration(configuration: dict) -> list[str]:
    """Validate a complete schema configuration without I/O or input mutation.

    configuration must contain sources for all three approved source names.
    Return safe error messages, or [] when UUIDs, configured fields, and ID
    uniqueness checks pass. Reject malformed outer containers immediately;
    otherwise collect independent errors across sources. UUIDs are normalized
    for data-source uniqueness; property IDs remain opaque strings and need
    only be unique within their source. Database IDs may be shared.
    Passing preflight does not establish live identity, schema, or relation targets.
    """
    if not isinstance(configuration, dict):
        return ["Configuration must be an object."]
    sources = configuration.get("sources")
    if not isinstance(sources, dict):
        return ["Configuration sources must be an object."]

    errors = []
    # Arbitrary source keys may contain private information; never echo them.
    for source_name in sources:
        if source_name not in EXPECTED_FIELDS:
            errors.append("Configuration contains an unexpected source entry.")

    seen_data_source_ids = {}
    for source_name in EXPECTED_FIELDS:
        if source_name not in sources:
            errors.append(f"{source_name}: required source is missing.")
            continue
        source_config = sources[source_name]
        if not isinstance(source_config, dict):
            errors.append(f"{source_name}: source configuration must be an object.")
            continue

        # Validate the IDs independently so one malformed ID cannot hide another.
        for id_field in ("database_id", "data_source_id"):
            value = source_config.get(id_field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{source_name}: {id_field} is missing or malformed.")
                continue
            try:
                normalized_id = UUID(value)
            except ValueError:
                # UUID parser exceptions may contain the private input value.
                errors.append(f"{source_name}: {id_field} is missing or malformed.")
                continue
            if id_field == "data_source_id":
                if normalized_id in seen_data_source_ids:
                    other_source = seen_data_source_ids[normalized_id]
                    errors.append(
                        f"{source_name}: data_source_id is reused from {other_source}."
                    )
                else:
                    seen_data_source_ids[normalized_id] = source_name

        errors.extend(check_configured_fields(source_name, source_config))
        properties = source_config.get("properties")
        if not isinstance(properties, dict):
            # The field validator already reported this container error.
            continue

        seen_property_ids = set()
        duplicate_property_ids = set()
        for field_name, mapping in properties.items():
            # Include unexpected mappings: aliases must not hide ID collisions.
            # Required-field shape/ID errors have already been reported above.
            if not isinstance(mapping, dict):
                if field_name not in EXPECTED_FIELDS[source_name]:
                    errors.append(f"{source_name}: extra configured mapping is malformed.")
                continue
            property_id = mapping.get("id")
            if not isinstance(property_id, str) or not property_id.strip():
                if field_name not in EXPECTED_FIELDS[source_name]:
                    errors.append(f"{source_name}: extra configured property ID is malformed.")
                continue
            if property_id in seen_property_ids:
                # Report each colliding ID once without revealing its value or names.
                if property_id not in duplicate_property_ids:
                    errors.append(f"{source_name}: duplicate configured property ID.")
                duplicate_property_ids.add(property_id)
            seen_property_ids.add(property_id)

    return errors

def validate_schema(configuration: dict, metadata: dict) -> list[str]:
    """Coordinate complete schema checks on supplied configuration and metadata.

    configuration is the full sources configuration; metadata maps each approved
    source name to its already-retrieved data-source response. Return safe errors,
    or [] only when preflight, all source identities/properties, and both relation
    targets pass. Preflight failures stop metadata inspection; malformed metadata
    containers are rejected, while independent source errors are collected.
    This function performs no I/O and does not modify either input. It verifies
    schema metadata only, not workout records, permissions, or pipeline behavior.
    """
    # Stop before inspecting metadata if the expected configuration is untrusted.
    errors = check_configuration(configuration)
    if errors:
        return errors
    if not isinstance(metadata, dict):
        return ["Schema metadata must be an object."]

    # Arbitrary metadata keys may contain private names; never echo their values.
    for source_name in metadata:
        if source_name not in EXPECTED_FIELDS:
            errors.append("Schema metadata contains an unexpected source entry.")

    for source_name in EXPECTED_FIELDS:
        if source_name not in metadata:
            errors.append(f"{source_name}: required source metadata is missing.")
            continue
        source_metadata = metadata[source_name]
        if not isinstance(source_metadata, dict):
            errors.append(f"{source_name}: source metadata must be an object.")
            continue
        source_config = configuration["sources"][source_name]
        # Check every source even after failures. A correct relation target does
        # not establish that its destination has a valid identity or schema.
        errors.extend(check_source_identity(source_name, source_config, source_metadata))
        errors.extend(check_property_ids(source_name, source_config, source_metadata))

    entries_metadata = metadata.get("exercise_entries")
    if isinstance(entries_metadata, dict):
        # Relation checks remain independent of source identity/property errors.
        # Missing or malformed entries metadata has already been rejected above.
        errors.extend(check_relation_targets(configuration, entries_metadata))

    return errors


def report_result(errors: list[str] | None = None, *, operational_failure: bool = False) -> int:
    """Print trusted validator errors or a fixed operational message; return 0/1/2.

    errors must come from the safe validators, never raw API/exception text.
    Operational failure takes precedence; only an empty error list indicates success.
    """
    if operational_failure or errors is None:
        print(
            "Verification could not complete: configuration loading or metadata retrieval failed. "
            "Check the config file, NOTION_TOKEN, access, network, and response limits locally.",
            file=sys.stderr,
        )
        return 2
    if errors:
        print("Schema verification failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Schema verification passed for all three sources.")
    return 0


class SafeArgumentParser(argparse.ArgumentParser):
    """Parse CLI options without reflecting arbitrary argument values into errors."""

    def error(self, message):
        """Exit 2 with fixed guidance instead of argparse's potentially sensitive message."""
        self.exit(2, "Usage error: provide --config PATH; use --help for details.\n")


def main(argv: list[str] | None = None) -> int:
    """Run load, preflight, retrieval, validation, and reporting; return 0/1/2.

    argv optionally supplies arguments for offline tests; None uses process args.
    Parse errors exit 2 and help exits 0. Other operational exceptions are reported
    without details. Read only the requested config and metadata; write no files.
    """
    parser = SafeArgumentParser(prog="verify_notion_schema.py", description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--config", type=Path, required=True,
        help="Path to the local JSON schema configuration.",
    )
    args = parser.parse_args(argv)
    try:
        configuration = load_configuration(args.config)
        errors = check_configuration(configuration)
        if errors:
            # No credential lookup or network access happens before preflight passes.
            return report_result(errors)
        metadata = retrieve_metadata(configuration)
        return report_result(validate_schema(configuration, metadata))
    except Exception:
        # Do not print exceptions: paths, response text, URLs, or headers can leak.
        return report_result(operational_failure=True)


if __name__ == "__main__":
    sys.exit(main())