# Tasks: Professor Data Portal

**Input**: Design documents from `/specs/001-professor-data-portal/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks are MANDATORY (Constitution Article II — TDD). Tests MUST
be written before their implementation tasks, confirmed failing (Red), then
made to pass (Green). Test coverage is layered: unit tests (Models, Services,
Repositories against a real SQLite file database), contract tests for every
Controller endpoint, integration tests for cross-module flows, and UI tests
with accessibility assertions.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `backend/src/portal/{auth,researchdata,ingestion}/`, tests in `backend/tests/{unit,contract,integration}/`
- Frontend: `frontend/src/app/`, UI tests in `frontend/tests/`
- Source data vendored in `backend/data/` (read-only inputs, FR-021)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure: `backend/src/portal/{auth,researchdata,ingestion}/`, `backend/tests/{unit,contract,integration}/`, `frontend/src/app/`, `frontend/tests/`
- [X] T002 [P] Initialize backend project: `backend/pyproject.toml` with FastAPI, `research_domain` git dependency (pinned v0.14.2), SQLAlchemy 2.x, PyArrow, PyJWT, bcrypt, pytest, ruff
- [X] T003 [P] Initialize frontend project: Next.js App Router + Tailwind CSS scaffold in `frontend/package.json`, `frontend/src/app/layout.tsx` (minimal dependencies)
- [X] T004 [P] Configure ruff lint/format and pytest settings in `backend/pyproject.toml` (tool.ruff, tool.pytest sections)
- [X] T005 Vendor horizon_dashboard source files into `backend/data/` (pinned commit per plan; `backend/data/README.md` records source URL + commit)
- [X] T006 [P] Add `.gitignore` entries: `backend/portal.db`, `.venv/`, `node_modules/`, `frontend/.next/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (MANDATORY - write FIRST, confirm RED before implementation)

- [X] T007 [P] Unit test LGPD masking middleware (sensitive fields redacted in logs and payloads) in `backend/tests/unit/test_observability.py`
- [X] T008 [P] Unit test `research_domain` SQLite repository strategy against a real SQLite file DB (CRUD per repository contract) in `backend/tests/unit/test_researchdata_repositories.py`
- [X] T009 [P] Unit test Auth repository + UserAccount model (unique username, bcrypt hashing, role validation) in `backend/tests/unit/test_auth_repository.py`
- [X] T010 [P] Unit test ArticleCountByYear + SyncState models/repositories in `backend/tests/unit/test_ingestion_repositories.py`

### Implementation for Foundational

- [X] T011 Implement `backend/src/portal/config.py` (DB path, JWT secret, ADMIN bootstrap env vars, settings loading)
- [X] T012 Implement central LGPD masking + logging middleware in `backend/src/portal/observability.py`
- [X] T013 Implement Auth models (UserAccount, Role enum) in `backend/src/portal/auth/models.py`
- [X] T014 Implement Auth repository (SQLAlchemy + real SQLite) in `backend/src/portal/auth/repositories.py`
- [X] T015 Implement `research_domain` SQLite repository strategy (implements package repository contracts) in `backend/src/portal/researchdata/repositories.py`
- [X] T016 Implement SyncState model/repository in `backend/src/portal/ingestion/models.py` and ArticleCountByYear model/repository in `backend/src/portal/researchdata/models.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Professor Profile Pages (Priority: P1) 🎯 MVP

**Goal**: Hierarchical professor pages: name, current projects, article counts by year, locations, article list

**Independent Test**: With a curated sample data set loaded, a professor page renders all expected sections in order and data matches the sample exactly.

### Tests for User Story 1 (MANDATORY - write FIRST, confirm RED before implementation) ⚠️

- [X] T017 [P] [US1] Unit test ResearchData services: profile assembly + article counts by year (ordering, empty sections) in `backend/tests/unit/test_researchdata_services.py`
- [X] T018 [P] [US1] Contract test GET /api/professors/{id} (hierarchy order, response shape, 404) in `backend/tests/contract/test_professor_profile.py`
- [X] T019 [P] [US1] Contract test GET /api/professors (pagination shape, page_size bounds, 422; `q` search filtering — fragment match + pagination combined) in `backend/tests/contract/test_professors_list.py`
- [X] T020 [P] [US1] Query-count (N+1) regression test for profile assembly in `backend/tests/unit/test_professor_queries.py`
- [X] T021 [P] [US1] UI test professor page: section order, empty states, loading state, accessibility assertions (Dynamic Type, VoiceOver labels, contrast) in `frontend/tests/profile.spec.ts`

### Implementation for User Story 1

- [X] T022 [US1] Implement ResearchData services (profile assembly wrapping `research_domain` controllers, counts from ArticleCountByYear) in `backend/src/portal/researchdata/services.py`
- [X] T023 [P] [US1] Implement ResearchData controllers (GET /api/professors with pagination + `q` name search, GET /api/professors/{id}) in `backend/src/portal/researchdata/controllers.py`
- [X] T024 [US1] Implement Fetch API wrapper (auth header, error normalization) in `frontend/src/lib/api.ts`
- [X] T025 [US1] Implement professor profile page (hierarchical sections, loading/empty/error states, paginated articles) in `frontend/src/app/professors/[id]/page.tsx`
- [X] T026 [US1] Implement professor directory page with search box (`q` → filtered results) in `frontend/src/app/page.tsx`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (MVP)

---

## Phase 4: User Story 2 - Synchronize and Transform Data Files (Priority: P2)

**Goal**: Admin triggers seed from vendored parquet/JSON files when DB is empty; atomic, async, with status polling; source files are read-only (FR-021)

**Independent Test**: An administrator triggers synchronization of the vendored source files; after it completes the portal reports a successful sync, and every record in the files is queryable and correct.

### Tests for User Story 2 (MANDATORY - write FIRST, confirm RED before implementation) ⚠️

- [X] T027 [P] [US2] Unit test parquet/json → canonical entity mapping (fixture files per data-model.md section 6; dangling project/location references produce record-level validation errors while the professor is still published) in `backend/tests/unit/test_ingestion_mapping.py`
- [X] T028 [P] [US2] Unit test seed atomicity + deduplication (failure leaves DB untouched, 0 duplicates; source files are never written — FR-021) in `backend/tests/unit/test_ingestion_atomicity.py`
- [X] T029 [P] [US2] Contract test POST /api/admin/seed (202 start, 409 already-seeded, 400 concurrent, 401/403 denied) in `backend/tests/contract/test_seed.py`
- [X] T030 [P] [US2] Contract test GET /api/admin/sync-status (RUNNING/SUCCEEDED/FAILED shapes, masked errors) in `backend/tests/contract/test_sync_status.py`
- [X] T031 [US2] Integration test seed → professor page shows synced data (Ingestion → ResearchData cross-module) in `backend/tests/integration/test_seed_to_profile.py`

### Implementation for User Story 2

- [X] T032 [US2] Implement ingestion mapping + loader (PyArrow parquet reads, column mapping per data-model.md) in `backend/src/portal/ingestion/services.py`
- [X] T033 [US2] Implement background seed job (empty-DB guard, atomic transaction, SyncState transitions) in `backend/src/portal/ingestion/jobs.py`
- [X] T034 [US2] Implement ingestion controllers (POST /api/admin/seed, GET /api/admin/sync-status) in `backend/src/portal/ingestion/controllers.py`
- [X] T035 [US2] Implement seed trigger + status polling UI (admin page, progress feedback per HIG; re-sync refusal surfaced as 409 message) in `frontend/src/app/admin/page.tsx`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 4 - Admin Registration and Professor Self-Management (Priority: P2)

**Goal**: Login, admin-only professor registration, professors edit only their own data

**Independent Test**: An administrator registers a professor; the professor logs in, edits their own data successfully, and is denied when attempting to edit another professor's data.

### Tests for User Story 4 (MANDATORY - write FIRST, confirm RED before implementation) ⚠️

- [X] T036 [P] [US4] Unit test Auth services: bcrypt hashing, JWT issuance, role/researcher_id claims in `backend/tests/unit/test_auth_services.py`
- [X] T037 [P] [US4] Contract test POST /api/auth/login (200, 401 wrong password, 401 unknown user) + GET /api/auth/me (200, 401) in `backend/tests/contract/test_auth.py`
- [X] T038 [P] [US4] Contract test POST /api/admin/professors (201, 400 duplicate, 403 non-admin denied case) in `backend/tests/contract/test_admin_professors.py`
- [X] T039 [P] [US4] Contract test PATCH /api/professors/{id} (owner 200 incl. emails, ADMIN 200, cross-professor 403 denied, anon 401) in `backend/tests/contract/test_professor_edit.py`
- [X] T040 [P] [US4] Integration test authz denied cases end-to-end (non-admin registration rejected, no data change) in `backend/tests/integration/test_authz_denied.py`
- [X] T041 [P] [US4] UI test login, register, self-edit (email + other fields), denied edit flows in `frontend/tests/auth.spec.ts`

### Implementation for User Story 4

- [X] T042 [US4] Implement Auth services (login, token issuance, admin bootstrap via env) in `backend/src/portal/auth/services.py`
- [X] T043 [US4] Implement Auth controllers (POST /api/auth/login, GET /api/auth/me) in `backend/src/portal/auth/controllers.py`
- [X] T044 [US4] Implement professor registration flow (Auth Service → ResearchData Service) + edit-own-data invariant (owner or ADMIN; edits apply to DB only, never source files) in `backend/src/portal/researchdata/services.py`
- [X] T045 [US4] Implement login page in `frontend/src/app/login/page.tsx`
- [X] T046 [US4] Implement admin registration UI (form, denied-case feedback) in `frontend/src/app/admin/page.tsx`

**Checkpoint**: At this point, User Stories 1, 2 AND 4 should all work independently

---

## Phase 6: LGPD Data Protection Operations (FR-013, Art. V)

**Goal**: First-class LGPD access/erasure Service operations. Sensitive fields (CPF, RG, precise location, financial details) are NEVER visible or editable in the UI; email and other non-sensitive fields are editable by the owner via PATCH (Phase 5)

**Independent Test**: The owning professor retrieves their personal data via the access endpoint; the same professor requests erasure and sensitive data + account are anonymized; a cross-professor request is denied.

### Tests for LGPD Operations (MANDATORY - write FIRST, confirm RED before implementation) ⚠️

- [X] T047 [P] [US4] Contract test GET /api/professors/{id}/personal-data (owner 200, ADMIN 200, cross-professor 403 denied, anon 401, 404) in `backend/tests/contract/test_lgpd_access.py`
- [X] T048 [P] [US4] Contract test DELETE /api/professors/{id}/personal-data (owner 200, ADMIN 200, denied cases, erasure + account anonymization, audit log has no sensitive values) in `backend/tests/contract/test_lgpd_erasure.py`
- [X] T049 [P] [US4] Unit test LGPD service operations (access export, erasure anonymization, audit trail, no sensitive data in logs) in `backend/tests/unit/test_lgpd_services.py`

### Implementation for LGPD Operations

- [X] T050 [US4] Implement LGPD service operations (access + erasure with audit trail) in `backend/src/portal/researchdata/services.py`
- [X] T051 [US4] Implement LGPD controllers (GET/DELETE /api/professors/{id}/personal-data) in `backend/src/portal/researchdata/controllers.py`

**Checkpoint**: LGPD operations complete; UI never exposes sensitive fields (verified by audit + contract tests)

---

## Phase 7: User Story 3 - Find Professors and Track Data Freshness (Priority: P3)

**Goal**: Search-by-name journey (backend `q` filter lives in US1; US3 adds the UI journey) + admin freshness banner; re-sync refused while data exists (409)

**Independent Test**: A user searches a professor by name fragment and reaches the correct profile; an administrator sees the last-sync timestamp and is refused a re-synchronization while data exists.

### Tests for User Story 3 (MANDATORY - write FIRST, confirm RED before implementation) ⚠️

- [X] T052 [P] [US3] UI test freshness banner (last-sync timestamp + record counts on admin page; re-sync trigger surfaces the 409 refusal message when data exists) in `frontend/tests/freshness.spec.ts`
- [X] T053 [P] [US3] UI test search journey (query → results → profile page) in `frontend/tests/search.spec.ts`
- [X] T054 [US3] Integration test freshness: sync-status reflects last seed (timestamps, counts); re-sync attempt returns 409 with no data change in `backend/tests/integration/test_sync_freshness.py`

### Implementation for User Story 3

- [X] T055 [US3] Implement search journey UX on directory page (debounced `q` wiring, loading/empty states, keyboard navigation per HIG) in `frontend/src/app/page.tsx`
- [X] T056 [US3] Implement sync-status display + re-sync trigger UI (refusal surfaced as 409 message when data exists) in `frontend/src/app/admin/page.tsx`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T057 [P] Latency regression test for professor page + search endpoints (2s p95 budget for pages, Art. IV; search < 5s per SC-006) in `backend/tests/contract/test_latency.py`
- [X] T058 Accessibility audit (Dynamic Type, contrast, VoiceOver) across all screens in `frontend/tests/accessibility.spec.ts`
- [X] T059 [P] CI workflow: ruff lint/format, pytest, Playwright, latency gate in `.github/workflows/ci.yml`
- [X] T060 [P] Documentation updates in `specs/001-professor-data-portal/quickstart.md` (validation results)
- [X] T061 Run quickstart.md validation end-to-end (fresh DB → seed → professor pages → authz denied cases → LGPD access/erasure), asserting record counts meet SC-004 scale (≥5,000 articles, ≥300 professors — or the actual vendored-source totals if lower, documented in quickstart results)
- [X] T062 Final ruff format/check + coverage pass on touched files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2/US4 → LGPD → US3)
- **LGPD (Phase 6)**: Depends on Phase 5 (auth + owner invariants) and Phase 4 (SyncState/masking)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - no dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - depends on US1 profile display for the integration test (seed → profile)
- **User Story 4 (P2)**: Can start after Foundational - depends on US1 (edits professor data via ResearchData services) and Auth foundation
- **LGPD (FR-013)**: Depends on US4 (owner invariants, accounts) and US2 (masking/audit infra)
- **User Story 3 (P3)**: Can start after Foundational - extends US1 (search on directory) and US2 (freshness status); should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Art. II)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- US2 (ingestion) and US4 (auth) can be developed in parallel after US1
- LGPD tests (T047-T049) can run in parallel once US4 contracts exist
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (MANDATORY - written first):
Task: "Unit test ResearchData services in backend/tests/unit/test_researchdata_services.py"
Task: "Contract test GET /api/professors/{id} in backend/tests/contract/test_professor_profile.py"
Task: "Contract test GET /api/professors in backend/tests/contract/test_professors_list.py"
Task: "UI test professor page in frontend/tests/profile.spec.ts"

# Then implement (after tests RED):
Task: "ResearchData services in backend/src/portal/researchdata/services.py"
Task: "ResearchData controllers in backend/src/portal/researchdata/controllers.py"
Task: "Professor profile page in frontend/src/app/professors/[id]/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (with a curated/small sample data set)
4. **STOP and VALIDATE**: Test User Story 1 independently (profile renders, counts match)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 (seed pipeline) → Test independently → Deploy/Demo
4. Add User Story 4 (authz) → Test independently → Deploy/Demo
5. Add LGPD operations (access/erasure) → Test independently → Deploy/Demo
6. Add User Story 3 (search + freshness) → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (profile pages)
   - Developer B: User Story 2 (seed pipeline) [after US1 services exist for integration test]
   - Developer C: User Story 4 (auth)
3. Developer D: LGPD operations after US4 contracts stabilize
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Red-Green-Refactor, Art. II)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution gates: repository tests use a real SQLite file DB (never mocked SQL); denied-case tests mandated (Art. V); latency gate (Art. IV); lint/format gate (Art. III)
- LGPD fields are never visible or editable in the UI; email and other non-sensitive fields are editable by the owner only; source data files are read-only (FR-021)
---

## Phase 9: Convergence

**Purpose**: Findings from the convergence assessment (2026-08-18) — closing
latent atomicity and concurrency-response gaps. All other intent is satisfied.

- [ ] T063 Make the `article_counts_by_year` rebuild participate in the seed's injected transaction (give `ArticleCountRepository` the same session-injection pattern as `SQLiteRepository` in `backend/src/portal/researchdata/repositories.py`) so no mid-seed commit can publish data before the seed transaction completes, per FR-006/SC-005 and Art. V (partial)
- [ ] T064 Return HTTP 400 "Seed already running" instead of an unhandled 500 when two concurrent seed requests race past the running-state check in `backend/src/portal/ingestion/controllers.py` (catch the `RuntimeError` from `sync_states.begin()`), per FR-008 (partial)
