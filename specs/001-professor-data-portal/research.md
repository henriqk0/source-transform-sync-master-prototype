# Research: Professor Data Portal

**Phase 0 output** — decisions for technical unknowns and dependencies,
recorded as Decision / Rationale / Alternatives.

## Decision 1: Frontend toolchain — Next.js + Tailwind, Vite excluded

- **Decision**: Use Next.js (App Router) + Tailwind CSS. Vite is **not**
  added. This is a deviation from the user's stated toolchain
  ("Next.js with Tailwind and Vite") and is approved at planning.
- **Rationale**: Next.js provides its own bundler and dev server (Turbopack/
  webpack); Vite is a competing build tool. Combining both creates two
  conflicting pipelines and contradicts the "minimal number of libraries"
  requirement. All UI libraries are kept minimal; backend calls use the
  browser Fetch API only.
- **Alternatives considered**:
  - Vite + React standalone: rejected — user explicitly required Next.js.
  - Next.js + Tailwind + Vite: rejected — duplicate toolchains conflict.
  - Next.js without Tailwind: rejected — user explicitly required Tailwind.

## Decision 2: Backend framework — FastAPI

- **Decision**: FastAPI (Python 3.11+) as the backend API framework, with
  Pydantic validation and auto-generated OpenAPI.
- **Rationale**: User-specified. FastAPI integrates cleanly with
  `research_domain` (a Python package) and supports async/background flows
  for seeding.
- **Alternatives considered**: Django (heavier, not requested), Flask
  (no built-in validation), Node/Express (different ecosystem from
  `research_domain`).

## Decision 3: Canonical domain model — `research_domain` package

- **Decision**: Add `research_domain` v0.14.2 as a `pyproject.toml`
  dependency (git dependency pinned to
  `github.com/The-Band-Solution/ResearchDomain`). Canonical entities
  (Researcher, Article, ResearchGroup, Campus, Organization, KnowledgeArea,
  Initiative, Advisorship, ResearchProduction, etc.) and their repository
  contracts are used directly; the portal never redefines them (Art. VII).
- **Rationale**: The constitution requires canonical domain entities from
  the `research-domain` external package; the package also provides
  controller/service layers for the research domain we can wrap.
- **Alternatives considered**: Defining entities locally — rejected
  (constitution Art. VII forbids it); vendoring the package source —
  rejected (dependency pinning is cleaner).

## Decision 4: Persistence — SQLite via a custom repository strategy

- **Decision**: SQLite single-file database (`backend/portal.db`, in
  `.gitignore`), accessed through repository classes that implement
  `research_domain`'s repository contracts (libbase `IRepository` and the
  entity-specific interfaces) using SQLAlchemy 2.x. This is the portal's
  "SQLite strategy" counterpart to the package's memory/postgres strategies.
- **Rationale**: `research_domain` v0.14.2 officially supports `memory` and
  `postgres` only; the user requires SQLite. Since its entities are
  SQLAlchemy-mapped (over eo_lib bases), a SQLite-backed implementation of
  its repository contracts is straightforward and keeps the package's
  services working unchanged.
- **Alternatives considered**: `postgres` strategy — rejected (user requires
  SQLite; no Postgres service in scope). `memory` strategy — rejected (data
  would not survive restarts).

## Decision 5: Source data — vendored horizon_dashboard files

- **Decision**: Vendor the relevant canonical files from
  `github.com/ifesserra-lab/horizon_dashboard` (`src/data/`) into
  `backend/data/`, pinned at a recorded commit:
  `researchers_canonical.parquet`, `articles_canonical.parquet`,
  `research_groups_canonical.parquet`, `campuses_canonical.parquet`,
  `organizations_canonical.parquet`, `knowledge_areas_canonical.parquet`,
  `initiatives_canonical.parquet`, `research_productions_canonical.parquet`,
  `production_authors_canonical.parquet`, `advisorships_canonical.parquet`,
  `fellowships_canonical.parquet`, `_meta.json`.
- **Rationale**: These are the real "various files" covering professors,
  articles, projects/initiatives, and locations. Parquet is read with
  PyArrow; JSON metadata with stdlib.
- **Alternatives considered**: Downloading at runtime — rejected (network
  dependency, non-deterministic); Lattes XML exports — rejected (not the
  actual data source provided).

## Decision 6: "Projects" concept — eo_lib Initiative

- **Decision**: "Current projects" (spec FR-002) maps to the canonical
  `Initiative` entity (status active) plus `Advisorship` (a specialized
  Initiative). "Research locations" maps to `Campus`/`Organization`.
- **Rationale**: `research_domain`'s domain (built on eo_lib) models
  initiatives with `status`, `start_date`, `end_date` — the closest canonical
  concept to projects. No new local entity is invented (Art. VII).
- **Alternatives considered**: Local `Project` entity — rejected (would
  redefine a canonical concept locally).

## Decision 7: Seeding — admin-only endpoint, empty-database guard

- **Decision**: `POST /api/admin/seed` (ADMIN role) loads the vendored files
  and populates SQLite **only if the database is empty** (no researchers and
  no user accounts). Runs as a background job with a
  `GET /api/admin/sync-status` polling endpoint; the whole load commits
  atomically in one transaction, so a failure leaves the database untouched.
- **Rationale**: Meets FR-019 and keeps the 2s p95 budget off the sync path
  (Art. IV). Atomic replace prevents partial states (Art. V).
- **Alternatives considered**: Synchronous seed — rejected (violates the
  2s budget for large files).

## Decision 8: Auth & roles — JWT with role claims

- **Decision**: Credential login (OAuth2 password flow) issuing short-lived
  JWTs (PyJWT) with `role` (ADMIN | PROFESSOR) and `researcher_id` claims;
  passwords hashed with bcrypt. First administrator bootstrapped via
  environment variables (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) or a CLI
  bootstrap command. Role checks live in Auth Service; professor-owns-data
  invariant (FR-018) enforced in the ResearchData Service.
- **Rationale**: Standard, minimal, testable; supports the denied-case tests
  required by Art. V. `research_domain` has no auth — this is portal-owned.
- **Alternatives considered**: Session cookies — fine but heavier for a
  Fetch-API SPA/SSR split; OAuth2 third-party — out of scope.

## Decision 9: LGPD masking — central layer

- **Decision**: A central logging/masking middleware in
  `backend/src/portal/observability.py` redacts sensitive fields (CPF, RG,
  emails, phones, precise location) in every request/response payload before
  logging or shipping; sensitive values are never included in non-essential
  API responses. Services expose masked serializers for audit events.
- **Rationale**: Art. V requires masking to be enforced centrally, not
  per-call.
- **Alternatives considered**: Per-module masking — rejected (constitution
  mandates a central layer).

## Decision 10: Testing & quality gates

- **Decision**: pytest for unit/contract/integration; repositories tested
  against a real SQLite file database (temp file per test), never mocked
  SQL; FastAPI TestClient for contract tests; Playwright for UI journeys
  with accessibility assertions (Dynamic Type, VoiceOver labels, contrast);
  ruff (lint + format) and coverage gates in CI; latency regression test
  asserting the 2s p95 budget for professor-page endpoints; N+1 query-count
  assertions in repository tests.
- **Rationale**: Satisfies Art. II (layered coverage), Art. III (CI
  linting), Art. IV (verified performance, query discipline).
- **Alternatives considered**: Mocking SQLAlchemy — rejected (Art. II);
  no UI tests — rejected (Art. II requires UI + accessibility).

## Decision 11: Frontend data access — Fetch API only

- **Decision**: The frontend calls backend endpoints exclusively through the
  browser Fetch API, wrapped in `frontend/src/lib/api.ts` (auth header,
  error normalization). No axios/react-query/SWR.
- **Rationale**: User requirement ("calls to the backend API via the Fetch
  API") plus minimal-libraries goal.
- **Alternatives considered**: axios — rejected (extra dependency); react-
  query — rejected (extra dependency, not needed at this scale).