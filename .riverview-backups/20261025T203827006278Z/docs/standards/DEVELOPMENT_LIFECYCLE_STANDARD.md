# Riverview~ Development Lifecycle Standard

**Document Revision:** 1.0.0  
**Status:** Proposed — pending Steward acceptance  
**Date:** 2026-10-09  
**Purpose:** Govern intake, design, creation, verification, deployment, maintenance, revisioning and recovery for all Riverview engineering work.  
**Related standards:** `docs/standards/COMPONENT_DEFINITION_OF_DONE.md` Rev 1.3; `docs/standards/ENGINEERING_RECORDS_STANDARD.md` Rev 1.0.

## Non-negotiable controlled-file rule

Every controlled repository file, including source, tests, scripts, configuration, documentation, diagrams and procedures, carries a **file-specific revision**. Every change to file content increments its revision, including changes to its own header. Every replacement preserves a retrievable copy of the immediately preceding revision **before** the new version is applied. Git commit history is necessary but not a substitute for file revision metadata or independently identifiable backups.

Use semantic numeric revisions `MAJOR.MINOR.PATCH` consistently for new files; increments must be monotonic and unique per file. A new file starts at `1.0.0` (or `0.1.0` if explicitly experimental). Changing a file without incrementing its revision is a failed checkout. Renames and deletions require manifest records and preservation of prior content. Generated/binary files that cannot safely embed a header use a versioned sidecar manifest entry and checksum; do not corrupt their formats to force a text header.

**Backups:** Before a controlled update, capture the previous file bytes and their SHA-256 hash in a revision-keyed backup artifact or immutable Git object referenced by a backup manifest. The manifest records path, prior revision, new revision, previous content hash, source commit/object ID, timestamp, task ID, and restoration instructions. The pre-change backup must be verified retrievable before applying a destructive change. Retain backups through a documented retention policy; never silently delete the sole restorable predecessor. Backup/restoration must work independently of an agent's conversation state. Git object retention must be protected (e.g., immutable backup refs or exported archives), since ordinary branch history can be rewritten/pruned. A second recoverable copy outside the working tree is required for critical deployed artifacts. Restore tests are mandatory for critical components.

## Standard code documentation header

Every human-authored source code file begins with a language-appropriate comment header containing, at minimum:

- Riverview~ identifier and relative file path
- Component ID and file revision
- Purpose and operational responsibility
- Execution model (event-driven, scheduled, request-driven, interactive, hybrid, or N/A)
- External visibility/observability interface (or parent component reference / N/A justification)
- Dependencies and important inputs/outputs
- Authority and operational constraints relevant to the file
- Last change summary, date UTC and task ID
- Links to the owning specification, tests and complete revision history

Header format can vary by language or file type, but field meanings must remain consistent. The full history belongs in Git/manifest/journal; keep headers concise. For Python, a comment header may precede a module docstring; preserve language-required directives (shebang, encoding, strict parser constraints). For formats that prohibit comments (JSON, binaries, lockfiles, generated assets), use a versioned manifest sidecar rather than invalid syntax. Do not put secrets in headers.

### Illustrative Python header

```python
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/postgres_ledger.py
# Component: POSTGRES-LEDGER
# Revision: 1.0.0
# Purpose: Durable assignment and event persistence
# Execution Model: Request-driven library
# Observability: Steward snapshot via owning adapter
# Dependencies: PostgreSQL 16; Psycopg 3
# Authority: Persistence only; caller authorization enforced by service contract
# Changed: 2026-10-09 UTC | TASK-ID | Baseline controlled revision
# Contracts: docs/components/POSTGRES_LEDGER.md
# Tests: tests/test_postgres_ledger.py
# History: Git + revision/backup manifest
# =============================================================================
```

## Work classification and proportional documentation

Classify every engineering assignment as design, new component, enhancement, defect repair, investigation, or operational change. Assign durable task ID, owner, component, affected files, relevant standard revisions, scope and acceptance criteria. L1 internal utilities use parent component docs and tests; L2 operational modules require contract, recovery/observability and tests; L3 institutional components require full Component Definition of Done evidence. **All levels obey file revision, header/sidecar, and backup requirements.**

## Lifecycle

1. **Intake / Definition of Ready:** identify intended result, component, task ID, execution model, authority, observable outputs, risks, dependencies, affected files, test/acceptance plan and documentation depth.
2. **Design:** define interfaces, event/state behavior, persistent operation, failure/recovery paths, visibility hooks, data handling, change impact and architecture diagrams appropriate to level. Record material decisions in the development journal.
3. **Pre-change preservation:** read current file revision, preserve and verify the exact predecessor, register hashes and backup location, then increment file revision and update code header or sidecar.
4. **Implementation:** implement source, tests, docs, diagrams, cookbooks and telemetry together; no unjustified one-shot limitations or turn-based execution dependencies for persistent institutional functions.
5. **Automated checkout:** validate header/sidecar presence, per-file revision increment, backup retrievability and hash, source/tests, repeat execution, recovery, external observability, and affected contracts. Persist both PASS and FAIL evidence with host, commit, command, exit code and timestamps.
6. **Deployment / acceptance:** identify deployed revisions, preserve deployed predecessor, verify restart and rollback paths, run environment-specific checks, evaluate applicable DoD gates and record Steward acceptance where required. Routine already-authorized operations must not be held for repeated manual approval.
7. **Operations / maintenance:** monitor events, health, regressions and incidents; changes re-enter the lifecycle at appropriate scope. Corrections to earlier records are appended and linked, not silently overwritten.

## Enforcement and migration

Implement a repository pre-commit/CI validator and controlled-file update tooling. Validator rejects changed controlled files with unchanged/missing revisions, missing required header fields or sidecars, or absent predecessor backup references. Detect untracked rename/delete changes and unsupported file formats. A task can still execute continuously at runtime; development governance must not become a runtime approval bottleneck.

**Bootstrap existing repository:** inventory all files; preserve baseline copies/hashes; add revision headers/sidecars; commit baseline as a dedicated migration with a checkout report. Do not falsely claim legacy revisions or retroactively fabricate backups. Existing Git history remains available as supplementary evidence. Until migration and enforcement exist, mark file-revision compliance **NOT YET VERIFIED**, not PASS.

## Required record links

Engineering journal = why; Git/CHANGELOG = what changed; checkout evidence = what was verified; operational event ledger = what ran. Cross-link using task ID, component ID, source commit, deployment ID and correlation ID as applicable. Avoid duplicate manual logs.

## Revision history

- **1.0.0 — 2026-10-09:** Initial lifecycle standard, mandatory file-level revision and pre-change backups, standard code headers, checkout enforcement, and legacy migration plan.
