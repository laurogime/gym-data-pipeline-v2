# Notion source field map

This document records the confirmed Notion fields for Version 2 of the Gym Data Pipeline. It describes what the manual pipeline will read and how each field will be used once the pipeline is implemented.

## Field identification strategy

Version 2 identifies Notion properties using their stable property IDs,
scoped to the correct data source. Display names are for human reference
and must not be used as runtime identifiers.

Each required property maps to:
- A consistent internal field name.
- Its Notion property ID.
- Its expected Notion property type.
- Its owning data source.

The importer must validate the following before processing records:

1. The expected data source exists and is accessible.
2. Each required property ID exists and has the expected type.
3. Relation properties point to the approved target data sources.
4. Missing, deleted, recreated, or incompatible properties are reported
   as schema errors rather than silently accepted.
5. Display-name matching is never used as a fallback.

Property names may contain emojis, trailing spaces, or be renamed
without breaking the mapping, provided their IDs and types remain valid.

Private database IDs, data source IDs, and property IDs are stored locally
in `data/private/notion-schema.json`, which is excluded from Git.
API credentials must be stored separately and never committed.

Notion page IDs identify individual workout records. Property IDs identify
fields within a data source. These serve different purposes.

This document describes the approved design; the importer has not yet
been implemented.

## Exercise Entries

One row represents one logged exercise entry within a workout. Use the Notion page ID to identify the entry and track corrections to it.

| Notion property (reference label) | Internal field | API type | How the pipeline will use it |
| --- | --- | --- | --- |
| `Workout Log` | `workout_log` | `relation` | Link the entry to one workout session. Many exercise entries can link to the same workout. If one entry links to multiple workouts, flag it for review and exclude it from dashboard calculations. |
| `Exercise` | `exercise` | `relation` | Use the linked exercise page ID to group the same exercise across workouts. |
| `1st set` | `set_1_weight` | `number` | First-set weight in kilograms. |
| `# of reps (1st set)` | `set_1_reps` | `number` | First-set repetitions. Pair with `1st set`. |
| `2nd set` | `set_2_weight` | `number` | Second-set weight in kilograms. |
| `# of reps (2nd set)` | `set_2_reps` | `number` | Second-set repetitions. Pair with `2nd set`. |
| `3rd set` | `set_3_weight` | `number` | Third-set weight in kilograms. Preserve for history. |
| `# of reps (3rd set)` | `set_3_reps` | `number` | Third-set repetitions. Pair with `3rd set` and preserve for history. |
| `Today` | `created_time` | `created_time` | Estimate workout duration from the span between the earliest and latest exercise-entry creation times in the same session. |
| `Completed` | `completed` | `checkbox` | Organize the Notion view only. Do not use it to filter what the pipeline reads. Toggling it alone does not create a new measurement version or change dashboard results. |
| `treadmill (km)` | `treadmill_km` | `number` | Not used by the exercise progression or workout duration report. |

All weights are in kilograms, including historical entries. Only complete weight-and-repetition pairs from Sets 1 and 2 qualify for exercise progression. Set 3 is preserved for history but does not qualify for progression.

### Unused Title property

Notion includes an unnamed Title property (`title`) in Exercise Entries.
This property is intentionally left empty because exercise entries do not
require a text label.

The property is not part of the 11 mapped workout fields and is not
required for reporting or measurement tracking. The pipeline must not
require a nonempty Title value or use it to identify exercise entries.
Each entry is identified by its stable Notion page ID.

The Title property remains unchanged in Notion.

## Workout Log

One row represents one workout session. Use the Notion page ID to identify the session.

| Notion property (reference label) | Internal field | API type | How the pipeline will use it |
| --- | --- | --- | --- |
| `Session Name` | `session_name` | `title` | Identify the session by its human-readable name. The page ID remains the stable identifier. |
| `Created time` | `created_time` | `created_time` | Assign the session to its local calendar day and Monday–Sunday reporting week in Philippine time. Do not use it to estimate workout duration. |

## Exercise

One row represents one exercise definition. Use the Notion page ID to identify the exercise.

| Notion property (reference label) | Internal field | API type | How the pipeline will use it |
| --- | --- | --- | --- |
| `Exercise Name` | `exercise_name` | `title` | Use the name as the dashboard label. The page ID remains the stable identifier for grouping. |


See the [definition of done](definition-of-done.md) for the pipeline acceptance cases and their execution status.