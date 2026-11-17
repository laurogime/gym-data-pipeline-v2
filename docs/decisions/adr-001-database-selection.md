# ADR-001 — Database selection for Gym Data Pipeline V2

- **Status:** Accepted
- **Decision date:** 2026-11-16
- **Decision owner:** Project Lead Engineer
- **Applies to:** Version 2, Stage A. This is separate from V1 ADR-001.

## Context

V2 is a local-first Windows rebuild. It carries forward V1’s workout rules, not its SQL implementation. The database must support preserving measurement history, idempotent reruns, reproducible validation, and recovery. Expected workout data volume does not require a server database by itself.

## Decision

Use **PostgreSQL** as the Stage A database. Keep the working database and real workout data local. If hosted CI is approved later, run database integration tests against a disposable PostgreSQL instance with synthetic fixtures. The CI workflow should not depend on reaching the local database or using a Notion token.

## Alternatives considered

| Option | Windows and operations | Scheduling and CI | Learning and trade-off |
| --- | --- | --- | --- |
| **PostgreSQL — selected** | Native Windows installer and no database license fee. Adds a database service, role management, and backups to operate. | A local scheduler can invoke the pipeline if scheduling is later approved. GitHub documents a PostgreSQL service container for Linux-hosted CI. | Builds experience in client-server database operations beyond T-SQL. Also leaves open a dbt evaluation with the dbt Labs-maintained dbt Core v1 PostgreSQL adapter. |
| SQL Server Express | Already installed and familiar. Free edition with version-specific limits. | No SQL Server Agent. Local scheduling and isolated CI remain possible with separate setup. | Best for deepening T-SQL, but reusing V1 code is not a V2 objective. The dbt Core v1 SQL Server adapter is community-maintained. |
| DuckDB | Free, embedded, and lighter to run on Windows. No database service to maintain. | Simple isolated CI with a fresh file. The straightforward embedded-file setup requires coordinating access around a single writer process. | Good fit for a single-user analytics pipeline, but offers less practice operating a shared database. |

## Consequences and boundaries

- We accept the added work of operating a local database service and verifying recovery. Establish a least-privilege runtime role and verify that a backup can be restored into a clean test database.
- Review V1 ADRs 001, 002, and 006 and the associated tests before carrying forward any rules. Validate with synthetic examples that reruns create no duplicate measurements, checkbox-only changes create no measurement version, and real measurement edits preserve history.
- The PostgreSQL version, Python driver, dbt, Docker, GitHub Actions, scheduling approach, and dashboard are separate decisions. This ADR does not authorize implementation.
- This was a documentation-based evaluation. The V1 files were not inspected and no compatibility or recovery tests were run.

## References

- [PostgreSQL Windows installers](https://www.postgresql.org/download/windows/)
- [PostgreSQL license](https://www.postgresql.org/about/licence/)
- [PostgreSQL backup utility](https://www.postgresql.org/docs/current/app-pgdump.html)
- [GitHub Actions PostgreSQL service containers](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
- [GitHub-hosted runner private networking](https://docs.github.com/en/actions/concepts/runners/private-networking)
- [dbt Core v1 PostgreSQL adapter](https://docs.getdbt.com/docs/local/connect-data-platform/postgres-setup)
- [dbt Core v1 SQL Server adapter](https://docs.getdbt.com/docs/local/connect-data-platform/mssql-setup)
- [SQL Server Express scheduling](https://learn.microsoft.com/en-us/troubleshoot/sql/admin/schedule-automate-backup-database)
- [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency)