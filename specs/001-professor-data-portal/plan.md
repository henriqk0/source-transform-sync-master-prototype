# Implementation Plan: Professor Data Portal

**Branch**: `001-professor-data-portal` | **Date**: 2026-08-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-professor-data-portal/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Build a web application that displays, transforms, and synchronizes professor
research data. The frontend (Next.js + Tailwind, minimal dependencies, Fetch
API) calls a FastAPI backend that uses the canonical `research_domain` package
entities. Source data (parquet/JSON canonical files from
`ifesserra-lab/horizon_dashboard`) populates a SQLite database through an
admin-only seeding endpoint when the database is empty. Administrators
register professors; professors may only modify their own data. Each professor
gets a dedicated page with hierarchical data: name, current projects, article
counts by year, research locations, and article list.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript, Node 20+ (frontend)

**Primary Dependencies**:
- Backend: FastAPI, `research_domain` (pinned, from
  `github.com/The-Band-Solution/ResearchDomain`, via `pyproject.toml`),
  SQLAlchemy 2.x (SQLite strategy for `research_domain` repository contracts),
  PyArrow (parquet reads), PyJWT + bcrypt (auth)
- Frontend: Next.js (App Router), Tailwind CSS; no other runtime libraries

**Storage**: SQLite single-file database (`portal.db`), listed in
`.gitignore`; seeded from vendored horizon_dashboard source files under
`backend/data/`

**Testing**: pytest (unit/contract/integration against a real SQLite file
database), Playwright (UI + accessibility), ruff (lint/format); latency
regression tests in CI for the 2s p95 budget

**Target Platform**: Linux server; browser-based web app (desktop + mobile
viewport)

**Project Type**: Web application (frontend + backend)

**Performance Goals**: professor page fully rendered in < 2s p95 end-to-end;
article counts by year served from a pre-aggregated table

**Constraints**: hard 2s p95 budget (Constitution Art. IV); seeding and any
heavy operation run asynchronously or within budget; minimal frontend
libraries; LGPD masking enforced centrally

**Scale/Scope**: ~300 professors, ~5,000 articles, 200 projects (source data
scale); 3 backend modules (Auth, ResearchData, Ingestion) + frontend

**Personal Data / LGPD**: professor names and article metadata = internal;
emails, CPF/RG, full contact details, precise locations = sensitive. Masked
in logs, errors, analytics, and non-essential responses by default (central
masking layer)

**Domain Model Source**: `research_domain` v0.14.2 (pinned; git dependency
`The-Band-Solution/ResearchDomain`), entities per its `docs/entities.md`;
no local redefinition (Art. VII)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **TDD sequencing (Article II)**: PASS — task list will sequence unit,
  contract, integration, and UI tests before their implementation tasks;
  repository tests run against a real SQLite file database, never mocked SQL.
- **Architecture (Article I)**: PASS — backend is a modular monolith with
  three modules (Auth, ResearchData, Ingestion); each module owns its data;
  MVC + Repository & Service with one-way dependency
  (Controller → Service → Repository → Model).
- **Performance budget (Article IV)**: PASS — professor page reads are
  indexed + pre-aggregated (article counts by year); seeding is admin-only,
  runs in a background flow with status polling; latency tests in CI.
- **Data classification (Article V)**: PASS — classification recorded in
  Technical Context above; masking layer is central (logging middleware);
  denied-case tests planned for auth/registration/cross-professor edits.
- **HIG & accessibility (Articles I, VI)**: PASS — frontend uses
  platform-standard navigation/components, shared tokens (Tailwind theme),
  loading/empty/error states per screen, Dynamic Type/VoiceOver checks via
  Playwright.
- **Domain-first modeling (Article VII)**: PASS — canonical entities come
  from `research_domain` (pinned v0.14.2); portal adds only non-domain
  entities (user accounts, sync state) mapped to canonical entities at the
  boundary; `data-model.md` documents the mapping.

No gate violations. One user-request deviation (Vite) is justified in
Complexity Tracking below.

## Project Structure

### Documentation (this feature)

```text
specs/001-professor-data-portal/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   └── portal/
│       ├── main.py                 # FastAPI app assembly
│       ├── config.py               # env/config (DB path, JWT secret, admin bootstrap)
│       ├── auth/                   # Module: Auth (own data: user accounts)
│       │   ├── models.py           # UserAccount, Role (portal-owned)
│       │   ├── repositories.py     # SQLite repository (SQLAlchemy)
│       │   ├── services.py         # login, register-professor policy, token issue
│       │   └── controllers.py      # /api/auth/*, /api/admin/* gateways
│       ├── researchdata/           # Module: ResearchData (own data: research entities)
│       │   ├── models.py           # re-exports canonical research_domain entities
│       │   ├── repositories.py     # SQLite strategy implementing research_domain contracts
│       │   ├── services.py         # wraps research_domain controllers/services
│       │   └── controllers.py      # /api/professors/*
│       ├── ingestion/              # Module: Ingestion (own data: sync state)
│       │   ├── models.py           # SeedState/SyncRun, mapping projections
│       │   ├── repositories.py     # sync-state repository
│       │   ├── services.py         # parquet/json load, transform, atomic seed
│       │   └── controllers.py      # /api/admin/seed, /api/admin/sync-status
│       └── observability.py        # central LGPD masking + logging middleware
├── data/                           # vendored horizon_dashboard source files (parquet/json)
├── tests/
│   ├── unit/                       # models, services, repositories (real SQLite)
│   ├── contract/                   # controller endpoint shapes + status codes
│   ├── integration/                # cross-module flows (seed -> display -> edit)
│   └── ui/                         # Playwright journeys + a11y assertions
├── pyproject.toml                  # includes research_domain dependency
└── portal.db                       # SQLite (gitignored)

frontend/
├── src/
│   ├── app/                        # Next.js App Router pages
│   │   ├── page.tsx                # professor directory + search
│   │   ├── professors/[id]/        # professor profile page
│   │   ├── login/                  # admin/professor login
│   │   └── admin/                  # registration + seed/sync status
│   ├── components/                 # shared UI components (tokens via Tailwind)
│   └── lib/
│       ├── api.ts                  # fetch wrapper (only Fetch API)
│       └── auth.ts                 # token storage, session helpers
├── tests/                          # Playwright e2e + accessibility
└── package.json
```

**Structure Decision**: Two top-level projects per user requirement —
`backend/` (FastAPI modular monolith: Auth, ResearchData, Ingestion modules,
each owning its data) and `frontend/` (Next.js + Tailwind). Cross-module
backend access happens only through Service layers (Art. I). Source data is
vendored under `backend/data/`; the SQLite file `portal.db` is gitignored.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Vite excluded from frontend (user-requested toolchain change) | Next.js ships its own build pipeline/dev server (Turbopack); Vite is a competing bundler — running both duplicates the toolchain and violates the "minimal number of libraries" requirement | Vite-only React app rejected because the user explicitly required Next.js; Next.js+Vite together rejected because two bundlers conflict at build/dev time |
| Custom SQLite repository strategy for `research_domain` | `research_domain` v0.14.2 ships `memory` and `postgres` strategies only; user requires SQLite persistence | Postgres strategy rejected (user requires SQLite, no Postgres service); memory strategy rejected (no persistence across restarts) |

All constitution gates PASS — entries above document the user-request
deviation (Vite) and the persistence adaptation, both approved at planning.