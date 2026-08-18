# Contract: Ingestion API

Base path: `/api` — database seeding and synchronization status (ADMIN
only).

## POST /api/admin/seed

Populate the SQLite database from the vendored source files
(`backend/data/`) — only when the database is empty (FR-019). Runs as a
background job; poll `GET /api/admin/sync-status`.

**Request**: no body.

**Responses**:

| Code | Body |
|------|------|
| 202 | `{ "status": "RUNNING", "started_at": "<iso>" }` |
| 400 | `{ "detail": "Seed already running" }` (concurrent run rejected) |
| 409 | `{ "detail": "Database already seeded" }` (not empty — no-op) |
| 401 | unauthenticated |
| 403 | authenticated but not ADMIN |

**Contract tests**: 202 starts job when DB empty; 409 when DB has data;
403 denied case for PROFESSOR/anon; 400 when a run is in progress.

## Re-synchronization semantics (FR-011/FR-019)

- Seeding populates the database only while it is empty (no researchers and
  no user accounts).
- While data exists, `POST /api/admin/seed` is refused with **409** — this
  protects professor edits (which live in the database only, FR-018/FR-021)
  from being overwritten by source files.
- Re-synchronization is possible only after the database is wiped (empty
  state). `GET /api/admin/sync-status` always reflects the last run.

## GET /api/admin/sync-status

Poll the last synchronization state (ADMIN only).

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "status": "IDLE"\|"RUNNING"\|"SUCCEEDED"\|"FAILED", "started_at": str\|null, "finished_at": str\|null, "counts": { "researchers": int, "articles": int, "initiatives": int, "research_groups": int, "campuses": int, "organizations": int, "knowledge_areas": int, "research_productions": int, "advisorships": int, "fellowships": int } \| null, "errors": [ { "file": str, "record": str\|null, "detail": str } ] \| null }` |
| 401 | unauthenticated |
| 403 | authenticated but not ADMIN |

Errors are masked (no sensitive values) per Art. V.

**Contract tests**: 200 RUNNING during a seed; 200 SUCCEEDED with counts
after completion; 200 FAILED with masked errors; 403 denied case.