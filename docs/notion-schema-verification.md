# Read-only Notion schema verification

This utility checks that the three approved Notion data sources match the V2
configuration before an importer processes records. It verifies source identity,
parent database identity, required property IDs and types, and the two Exercise
Entries relation destinations. A successful run requires all three sources to pass.

It sends only HTTPS `GET /v1/data_sources/{data_source_id}` metadata requests to
`api.notion.com`, using Notion API version `2026-03-11`. It never follows redirects,
queries pages, reads workout records, writes responses to disk, or changes Notion.
It is a schema check, not an implemented workout pipeline or a pipeline acceptance
test. See the [field map](notion-field-map.md) and
[definition of done](definition-of-done.md) for the broader approved requirements.

## Setup

Use Python 3.11 or newer. From the V2 repository root, create a local virtual
environment if one does not exist, then install the pinned test dependency:

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
```

On Windows, `py -3` can replace the first `python` command. Use
`./.venv/Scripts/python.exe` in Git Bash or `& ./.venv/Scripts/python.exe` in
PowerShell. Activation is optional; using the environment's interpreter directly
avoids shell activation-policy differences. The verifier itself uses only the
Python standard library; pytest is needed only for automated tests.

## Configuration and credentials

[config/notion-schema.example.json](../config/notion-schema.example.json) contains
fictional UUIDs and property IDs for all 14 required fields. It illustrates this
shape; it cannot verify a real workspace:

```json
{
  "sources": {
    "exercise_entries": {
      "database_id": "11111111-1111-4111-8111-111111111101",
      "data_source_id": "11111111-1111-4111-8111-111111111102",
      "properties": {
        "workout_log": {"id": "fake_ee_workout_log", "type": "relation"}
      }
    }
  }
}
```

This shortened snippet is deliberately incomplete; use the linked full example
as the template. Prepare the real configuration locally at
`data/private/notion-schema.json`, an ignored location specified by the field map.
Keep it private. Do not put credentials in JSON. Each source needs both identity
UUIDs and its approved field mappings. Property IDs may be short opaque strings;
display names, emojis, and property ordering do not identify fields. Relation
destinations come from the configured Workout Log and Exercise data-source IDs.

The client reads only `NOTION_TOKEN` from the process environment. It does not
read `.env` files, accept a token argument, or fall back to other token variables.
Supply a token for an integration with read access to all three data sources.
Avoid typing the token into shell commands, source files, or screenshots.

## Run the verifier

When a trusted launcher has already supplied `NOTION_TOKEN`, run:

```text
.venv/Scripts/python.exe scripts/verify_notion_schema.py --config data/private/notion-schema.json
```

Alternatively, this command prompts without echoing the token and supplies it
only to the current Python process. It works in PowerShell and Git Bash without
putting the token in shell history:

```text
.venv/Scripts/python.exe -c "import getpass, os, runpy, sys; os.environ['NOTION_TOKEN'] = getpass.getpass('Notion token: '); sys.argv = ['verify_notion_schema.py', '--config', 'data/private/notion-schema.json']; runpy.run_path('scripts/verify_notion_schema.py', run_name='__main__')"
```

Configuration preflight runs before token lookup or API access. Output contains
only approved internal field labels and safe status messages. Success is printed
to standard output; validation and operational failures go to standard error.
Do not enable HTTP debugging or print exception details containing private data.

| Exit code | Meaning |
| --- | --- |
| `0` | Complete schema verification passed. `--help` also exits `0` without verification. |
| `1` | Configuration preflight or schema validation failed. |
| `2` | Usage, configuration loading, credentials, API transport/HTTP, response decoding, or size-limit failure. |

PowerShell exposes the result as `$LASTEXITCODE`; Git Bash uses `$?`.

## Run automated tests

```text
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests/test_verify_notion_schema.py -q
```

The tests use fictional fixtures and mocked credentials, files, and API responses.
They require no real token, private configuration, or Notion connectivity. Tests
cover the CLI flow and failure exits as well as the individual validators, bounded
reads, GET-only endpoints, redirect refusal, and output privacy. `-B` and
`-p no:cacheprovider` avoid bytecode and pytest cache files.

An optional syntax-only check compiles in memory without running the verifier:

```text
.venv/Scripts/python.exe -B -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/verify_notion_schema.py').read_text(encoding='utf-8')); print('Syntax OK')"
```

## Troubleshooting and limitations

- **Exit `1`:** use the approved internal field labels in the errors to check
  missing mappings, UUIDs, duplicate IDs, types, identities, and relation targets
  locally. A recreated property needs its new stable ID; renaming alone should
  not require a configuration change. Shared database IDs are allowed; shared
  data-source IDs across configured sources are rejected.
- **Exit `2`:** check the explicit configuration path, UTF-8/JSON syntax, token
  availability, integration access, connectivity, and API availability locally.
  Duplicate JSON keys and non-JSON constants such as `NaN` are rejected. Errors
  intentionally omit paths, identifiers, response bodies, and server messages.
- **Response limits:** each response is limited to 1 MiB. Declared oversized,
  malformed, or incomplete lengths are rejected; the body read is bounded even
  without a length header. Non-JSON and non-object responses fail closed.
- **Availability:** requests have a 30-second socket timeout. The client does not
  retry rate limits or transient failures; rerun after resolving the cause. It
  makes up to three sequential metadata requests and stops on retrieval failure.
- **Scope:** a pass describes the metadata received during that run. It does not
  prove future availability, extraction correctness, record-level relationships,
  history, database setup, recovery, dashboard behavior, or all workspace permissions.
  It does not mark any pipeline acceptance case as passed.

Offline automated results are separate from live verification. No live Notion
request is required to run the tests; an owner-run live check is still needed to
confirm access to a real workspace. Keep private configuration and its results local.