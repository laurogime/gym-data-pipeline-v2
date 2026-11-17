# Repository rules for coding agents

## Scope and authorization

- Work on one approved issue at a time. Follow its requirements and stay within its scope.
- Use this V2 repository only. Do not access V1 or search for another repository unless the owner explicitly authorizes it.
- Before editing, verify the V2 workspace root, expected branch, and origin. Use `git -C "<verified V2 root>"` for Git commands and resolve file paths only within that root. If you cannot verify the root, stop and ask the owner. Do not search outside the workspace.
- Approved technology decisions are not authorization to install tools or implement a pipeline, database, dashboard, or CI. Obtain scope through a separately approved issue.

## Data and secrets

- Protect credentials, tokens, connection strings, local secrets, and private workout data. Never expose them in repository files, logs, screenshots, or reports.
- Keep real workout data local. Use synthetic data for shared fixtures, tests, portfolio files, and screenshots.
- Keep Markdown documentation and future synthetic fixtures visible to version control. Do not use broad ignore rules to conceal data or documentation.

## Approved expectations and verification

- Treat the approved decision documents and acceptance checklist as the baseline. Preserve approved test expectations; do not weaken, remove, or rewrite them to make an implementation pass.
- Do not change case execution status without authorized execution and supporting evidence. Approved expectations are not test results.
- Run only checks appropriate to the approved issue. Repository initialization does not authorize pipeline acceptance tests.
- Report files changed, commands run, check results, blockers, and what was and was not verified. Distinguish static checks from executed pipeline, database, or dashboard tests.

## Owner handoff

The owner handles Git staging, commits, pushes, pull requests, and merges. Agents must not perform Git write operations. Leave changes unstaged for the owner to review.