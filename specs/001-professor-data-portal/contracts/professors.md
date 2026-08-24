# Contract: Professors API

Base path: `/api` — public professor profiles + admin registration +
professor self-management.

## GET /api/professors

Search/list professors (public).

**Query params**:

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `q` | string | — | name fragment filter |
| `page` | int | 1 | ≥ 1 |
| `page_size` | int | 20 | 1..100 |

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "items": [ { "id": int, "name": str, "affiliation": str\|null } ], "total": int, "page": int, "page_size": int }` |
| 422 | validation error |

## GET /api/professors/{id}

Full professor profile (public), hierarchical order per FR-002.

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "id": int, "name": str, "affiliation": str\|null, "resume": str\|null, "current_projects": [ { "id": int, "name": str, "status": str } ], "article_counts_by_year": [ { "year": int, "count": int } ], "locations": [ { "id": int, "name": str, "type": "campus"\|"organization" } ], "articles": [ { "id": int, "title": str, "year": int, "type": str, "doi": str\|null } ] }` |
| 404 | `{ "detail": "Professor not found" }` |

`article_counts_by_year` ordered most-recent year first; `articles` paginated
server-side (default 50, `?page=` for more) — the 2s p95 budget (Art. IV) is
enforced here.

## POST /api/admin/professors

Register a professor (ADMIN only).

**Request** (JSON):

| Field | Type | Required |
|-------|------|----------|
| `name` | string | yes |
| `emails` | string[] | no |
| `resume` | string | no |
| `username` | string | yes |
| `password` | string | yes (min 8) |
| `cnpq_id` | string | no |

**CNPq id linkage**: when `cnpq_id` matches a professor already saved in the
database — including professors loaded by seeding, whose lattes ids are
extracted from their `cnpq_url` at seed time — no new professor row is
created: the new login links to that existing `Researcher` (`researcher_id`
of the response is the saved professor's id). A first-time `cnpq_id` creates
the professor and records the mapping. Researchers without a `cnpq_url` in
the source data cannot be matched by lattes id.

**Responses**:

| Code | Body |
|------|------|
| 201 | `{ "id": int, "username": str, "role": "PROFESSOR", "researcher_id": int }` |
| 400 | duplicate username / invalid input |
| 401 | unauthenticated |
| 403 | authenticated but not ADMIN |
| 422 | validation error |

**Contract tests**: 201 happy path; 403 for PROFESSOR/anon (denied case);
400 duplicate username; created account can log in; `cnpq_id` linkage reuses
the saved professor (no duplicate row) and the linked login authenticates with
that `researcher_id`.

## PATCH /api/professors/{id}

Modify professor data (owner PROFESSOR or ADMIN only).

**Request** (JSON, partial):

| Field | Type |
|-------|------|
| `name` | string? |
| `emails` | string[]? |
| `resume` | string? |

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "id": int, "name": str, "emails": [str], "resume": str\|null }` |
| 401 | unauthenticated |
| 403 | authenticated but not owner and not ADMIN (denied case) |
| 404 | professor not found |
| 422 | validation error |

**Contract tests**: 200 for owner; 200 for ADMIN on any professor; 403 for a
professor editing another professor (denied case, FR-018); 401 anon.