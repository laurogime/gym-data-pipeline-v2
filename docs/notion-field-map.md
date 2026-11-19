# Notion source field map

This document records the confirmed Notion fields for Version 2 of the Gym Data Pipeline. It describes what the manual pipeline will read and how each field will be used once the pipeline is implemented.

## Exercise Entries

One row represents one logged exercise entry within a workout. Use the Notion page ID to identify the entry and track corrections to it.

| Notion property | Type | How the pipeline will use it |
| --- | --- | --- |
| `Workout Log` | Relation to Workout Log | Link the entry to one workout session. Many exercise entries can link to the same workout. If one entry links to multiple workouts, flag it for review and exclude it from dashboard calculations. |
| `Exercise` | Relation to Exercise | Use the linked exercise page ID to group the same exercise across workouts. |
| `1st set` | Number | First-set weight in kilograms. |
| `# of reps (1st set)` | Number | First-set repetitions. Pair with `1st set`. |
| `2nd set` | Number | Second-set weight in kilograms. |
| `# of reps (2nd set)` | Number | Second-set repetitions. Pair with `2nd set`. |
| `3rd set` | Number | Third-set weight in kilograms. Preserve for history. |
| `# of reps (3rd set)` | Number | Third-set repetitions. Pair with `3rd set` and preserve for history. |
| `Today` | Created time | Estimate workout duration from the span between the earliest and latest exercise-entry creation times in the same session. |
| `Completed` | Checkbox | Organize the Notion view only. Do not use it to filter what the pipeline reads. Toggling it alone does not create a new measurement version or change dashboard results. |
| `treadmill (km)` | Number | Not used by the exercise progression or workout duration report. |

All weights are in kilograms, including historical entries. Only complete weight-and-repetition pairs from Sets 1 and 2 qualify for exercise progression. Set 3 is preserved for history but does not qualify for progression.

## Workout Log

One row represents one workout session. Use the Notion page ID to identify the session.

| Notion property | Type | How the pipeline will use it |
| --- | --- | --- |
| `Session Name` | Title | Identify the session by its human-readable name. The page ID remains the stable identifier. |
| `Created time` | Created time | Assign the session to its local calendar day and Monday–Sunday reporting week in Philippine time. Do not use it to estimate workout duration. |

## Exercise

One row represents one exercise definition. Use the Notion page ID to identify the exercise.

| Notion property | Type | How the pipeline will use it |
| --- | --- | --- |
| `Exercise Name` | Title | Use the name as the dashboard label. The page ID remains the stable identifier for grouping. |


See the [definition of done](definition-of-done.md) for the pipeline acceptance cases and their execution status.