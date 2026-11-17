# Gym Data Pipeline V2

Gym Data Pipeline V2 is a local-first Windows rebuild for processing workout records from Notion into reporting datasets and a local dashboard. It aims to preserve measurement history, support repeatable reruns and recovery, and report exercise progression and estimated workout duration.

## Current status

The pipeline is not implemented yet. This repository currently records approved decisions and acceptance expectations. Repository initialization does not install components or demonstrate working pipeline behavior.

- **PostgreSQL** is the approved Stage A database choice. This approval does not establish that PostgreSQL is installed or configured.
- **Power BI Desktop in Import mode** is the approved local dashboard choice, with manual refresh after a successful pipeline run. This approval does not establish that Power BI is installed or that a report exists.

Real workout data and credentials must stay local and private. Use synthetic data for shared fixtures, portfolio artifacts, and screenshots.

## Approved planning documents

- [Database selection (ADR-001)](docs/decisions/adr-001-database-selection.md)
- [Dashboard tool selection](docs/decisions/dashboard-tool-selection.md)
- [V2 acceptance checklist](docs/v2-acceptance-checklist.md)

The checklist defines 33 approved cases. Its existing execution status is **Not run for every case below**; approved expectations are not passing test results. Implementation, database setup, report creation, and CI require separately approved work.