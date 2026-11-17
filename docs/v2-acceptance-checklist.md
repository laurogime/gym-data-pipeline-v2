# Gym Data Pipeline V2 — Acceptance checklist

**Checklist status — Approved by the Lead Engineer**  
**Execution status — Not run for every case below.** Confirmed expectations are not test results.

Use synthetic workouts in a separate PostgreSQL test database. Run the same V2 pipeline and Gold build that will process real workouts. Compare the saved results with the expected results recorded here. Use a synthetic Power BI report for the dashboard checks. These are the agreed Gold, source-handling, recovery, and chart scenarios. They do not by themselves cover all release requirements.

## 1. Exercise progression

Expect one row per qualifying session–exercise pair. For each case, the winner must keep the weight and reps from the same set. Sets 1 and 2 are eligible only when both values are present. V2 retains historical Set 3 values upstream without using them for progression.

| Case | Synthetic input | Expected Gold result |
| --- | --- | --- |
| E1 | Push Day 01, bench press. Sets 1–2: 60 kg × 10, 65 kg × 6. | 65 kg × 6. |
| E2 | Push Day 01, shoulder press. Sets 1–2: 30 kg × 8, 27.5 kg × 12. | 30 kg × 8. |
| E3 | Push Day 02, bench press. Sets 1–2: 62.5 kg × 8, 60 kg × 10. | 62.5 kg × 8. |
| E4 | Push Day 03, bench press. Sets 1–2: 65 kg × 10, 67.5 kg × 5. | 67.5 kg × 5. |
| E5 | Push Day 04, bench press. Sets 1–2: 65 kg × 6, 65 kg × 9. | 65 kg × 9. |
| E6 | Push Day 05, bench press. Sets 1–2: 67.5 kg × 8, 67.5 kg × 5. | 67.5 kg × 8. |
| E7 | Pull Day 01, row machine. Entry A: 40 kg × 8 and 37.5 kg × 12. Entry B: 40 kg × 10 and 35 kg × 15. | One row at 40 kg × 10 from Entry B, Set 1. |
| E8 | Bench press. Set 1 has 70 kg without reps. Set 2 has 65 kg × 8. | 65 kg × 8. |
| E9 | Bench press. Set 1 has 60 kg × 10. Set 2 has 12 reps without weight. | 60 kg × 10. |
| E10 | Bench press. Sets 1–3: 60 kg × 10, 65 kg × 6, 72.5 kg × 4. | 65 kg × 6. Set 3 remains upstream. |
| E11 | Bench press. Set 1 has 70 kg without reps. Set 2 has 8 reps without weight. Set 3 has 65 kg × 10. | No Gold row. Set 3 remains upstream. |

E8–E11 each use a separate workout. E1–E4 together verify that two exercises in the same session and the same exercise in separate sessions are not merged.

## 2. Workout duration

Use exercise-entry creation timestamps for the duration estimate, not the Workout Log page's creation time. Count timestamped entries before classifying the elapsed time. The V2 valid range is **5 minutes through 10 hours, inclusive**. The V1 minimum was 15 minutes.

| Case | Synthetic input | Expected status | Saved duration |
| --- | --- | --- | --- |
| D1 | Two distinct entries, both missing timestamps. | `INSUFFICIENT_DATA` | `NULL` |
| D2 | One entry at 09:00:00 and one without a timestamp. | `INSUFFICIENT_DATA` | `NULL` |
| D3 | Two distinct entries, both at 09:00:00. | `SUSPECT_TIMESTAMP` | `NULL` |
| D4 | 09:00:00 and 09:04:59. | `SUSPECT_TIMESTAMP` | `NULL` |
| D5 | 09:00:00 and 09:05:00. | `VALID` | 5 minutes |
| D6 | Monday 23:50:00 and Tuesday 00:20:00, linked to the same session. | `VALID` | 30 minutes |
| D7 | 08:00:00 and 18:00:00 on the same day. | `VALID` | 10 hours |
| D8 | 08:00:00 and 18:00:01 on the same day. | `INVALID` | `NULL` |

Use a different valid Workout Log link for each fixture and expect one output row per fixture session. Check thresholds against the actual elapsed time, before rounding for display.

## 3. Notion corrections and Workout Log links

For N1–N4, use a valid session link. A measurement version belongs to a stable Notion exercise-entry page ID. The dashboard shows current results, not edit history.

| Case | Synthetic input | Expected result |
| --- | --- | --- |
| N1 | An accepted measurement changes from 100 kg × 5 to 90 kg × 5 on the same entry. | 90 kg × 5 becomes current. Retain 100 kg × 5 in history and do not show it on the dashboard. |
| N2 | A new edit fails validation. The last accepted value was 90 kg × 5. | Flag the rejected edit. Gold still uses 90 kg × 5. |
| N3 | A new entry fails validation and has no accepted version. | Flag the entry. It contributes to neither Gold dataset. |
| N4 | Only the Completed checkbox changes. | No new measurement version and no change to Gold or the dashboard. |
| N5 | Complete weights and reps, but a blank Workout Log link. | Keep the raw entry in Bronze, flag it, and exclude it from both Gold datasets until the correct session is linked. Do not guess the session from the date. |
| N6 | The linked Workout Log page is not found in the loaded session data. The batch also contains valid entries. | Keep and flag the affected entry. It contributes to neither Gold dataset until the link is resolved. Other valid entries continue processing. |

## 4. Reruns and failure recovery

| Case | Synthetic input | Expected result |
| --- | --- | --- |
| R1 | A successful run saves 60 kg × 8 for one session and exercise. Run again without changing the source. | The same single progression row remains and no measurement-history version is added. The Gold output is unchanged. |
| R2 | The last successful Gold result is 60 kg × 8. An accepted correction is 62.5 kg × 8. Trigger a failure during the actual Gold publish. | Gold still shows 60 kg × 8 and the last successful outputs remain intact. Do not count a separate simulated transaction as evidence for this case. |
| R3 | After R2, retry the real pipeline successfully with the same accepted correction. | Gold has exactly one current row at 62.5 kg × 8 for the session and exercise. Keep 60 kg × 8 in history and do not add a duplicate version for 62.5 kg × 8. |

## 5. Power BI weekly progression chart

Use a Workout Log page's creation time converted to `Asia/Manila` to determine the local day and Monday–Sunday week. The chart shows the best qualifying result per day for one selected exercise. Compare session-level Gold results by weight first and paired reps second. The original Gold rows remain separate.

| Case | Synthetic input | Expected report |
| --- | --- | --- |
| P1 | Open the report on a Wednesday in Philippine time with no week selected. | Default to the current Monday–Sunday week and allow earlier weeks to be selected. |
| P2 | One Workout Log page was created Sunday at 11:59 PM and another Monday at 12:00 AM, both in Philippine time. | The sessions belong to different weeks. Use source times equivalent to those local times when verifying the conversion. |
| P3 | Two Friday bench-press sessions at 60 kg × 8 and 60 kg × 10. | One Friday point at 60 kg, labeled **10 reps** without hovering at normal desktop report size. Gold retains both sessions. |
| P4 | No session in the chosen week has a complete Set 1 or Set 2 for the selected exercise. | No point at zero. Show “No qualifying sessions for this exercise this week.” |
| P5 | Two bench-press sessions on the same local day at 62.5 kg × 5 and 60 kg × 10. | One point at 62.5 kg labeled **5 reps** without hovering. Gold retains both sessions. |

## Remaining release coverage

Before calling V2 ready, define separate checks for source extraction, historical reconciliation, and restoring a database backup. Keeping the last successful Gold results after a failed build does not verify backup restoration. These checks are not prerequisites for the repo skeleton.

## Approval and handoff

- [x] Lead Engineer approved the checklist baseline, including R3 and P5.
- [ ] Open or approve a separate **Initialize the V2 repository** issue. This checklist review does not create the repo, write code, or run tests.
