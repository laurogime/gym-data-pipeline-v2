# ADR — Dashboard tool selection for Gym Data Pipeline V2

**Status — Accepted**

## Decision

Use **Power BI Desktop in Import mode** for the local V2 dashboard. Read the Gold reporting data from PostgreSQL with a read-only account. Refresh the report manually after a successful pipeline run. The dashboard uses the already-selected Gold weight–rep pair from each session as its input and does not recalculate set eligibility. The daily selection is a reporting rule, not a change to the session-level Gold datasets. Power BI Service and public publishing are out of scope. Use synthetic data in portfolio files and screenshots.

## Why Power BI over Streamlit

- **Less to build and maintain for this scope.** Power BI Desktop has a PostgreSQL connector and built-in report filters and line charts. Microsoft documents adding a secondary field to line-chart data labels, which gives us a native way to plot weight and display the paired reps. A Streamlit + Altair solution would require a Python app, chart code, and dependencies to maintain.
- **Fits the local Windows workflow.** Power BI Desktop is free to use locally. Import mode fits manual refresh after the pipeline runs and does not require a hosted dashboard or a live database query for each chart interaction.
- **Matches the learning goal.** Power BI gives the project a chance to practice BI modeling and report delivery alongside Python and PostgreSQL. Streamlit offers finer control over layout and labels, but visual flexibility alone does not justify adding a Python dashboard app to V2.

## Approved behavior

- Open on the current Monday–Sunday week in Philippine time and let the user select earlier weeks and an exercise.
- Use the linked Workout Log page’s creation timestamp converted to `Asia/Manila` to assign each session to its local calendar date and its Monday–Sunday week. This timestamp is not a measured start time.
- Plot one best point per qualifying day for the selected exercise. Compare the session-level Gold results for that day and select the highest weight, then the highest paired reps among results tied at that weight. Plot the winning weight and visibly label the reps from that same result. Keep the original session rows in Gold.
- Skip sessions without a qualifying weight–rep pair instead of plotting zero. Omit exercise entries without a linked Workout Log session and flag them for review. Show a clear empty state when the selected week has no qualifying points.

## Verification and when to revisit

Power BI may suppress labels when space is tight. Before accepting the dashboard, verify the native chart at normal desktop report size using two synthetic sessions on the same day, both at 60 kg, with 8 and 10 reps respectively. The chart must show exactly one point for that day at 60 kg, visibly labeled 10 reps without hovering, while Gold still contains both sessions. If the native chart has a problem, try a practical Power BI solution first. Keep the requirement for visible reps. Reconsider Streamlit only if a concrete, material problem remains and there is a clear reason that Streamlit would solve it well enough to justify the extra maintenance. A visual preference or a limitation of one chart configuration is not an automatic trigger to switch.

The dashboard tool is approved. The dashboard has not been built or tested. This decision does not authorize implementation.

## References

- [Power BI Desktop download and local use](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop)
- [Power Query PostgreSQL connector](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)
- [Power BI data label formatting](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualizations-format-visual)
- [Streamlit Altair support](https://docs.streamlit.io/develop/api-reference/charts/st.altair_chart)
