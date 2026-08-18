# Feature Specification: Professor Data Portal

**Feature Branch**: `001-professor-data-portal`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Help me build a web application to display, transform, and synchronize a data source. The data comes from various files covering everything from projects and Lattes CV articles to the locations where professors conduct their research. Each professor should have a dedicated page displaying all related data in a hierarchical format, starting with the most relevant information (name, current projects, article counts by year, etc.)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Professor Profile Pages (Priority: P1)

A user opens the portal and navigates to a professor's dedicated page. The
page presents the professor's data in a clear hierarchy, starting with the
most relevant information: name and affiliation, current projects, article
counts by year, research locations, and the full article list. The user can
scan the profile from summary to detail without losing context.

**Why this priority**: This is the core value of the product — turning
scattered research data files into an organized, per-professor view. All other
features (sync, search) exist to keep and extend this page useful.

**Independent Test**: With a curated sample data set loaded, a professor page
renders all expected sections (name, current projects, article counts by year,
locations, article list) in hierarchical order and the data matches the sample
exactly.

**Acceptance Scenarios**:

1. **Given** a professor exists in the data source, **When** a user opens
   their dedicated page, **Then** the page shows the professor's name, current
   projects, article counts by year, research locations, and article list in
   that order.
2. **Given** a professor has articles published in multiple years, **When** the
   user views the profile, **Then** article counts are grouped by publication
   year and ordered from most to least recent.
3. **Given** the user views the profile on a small screen, **When** the page
   loads, **Then** all sections remain readable and navigable (Dynamic Type,
   VoiceOver labels, sufficient contrast).

---

### User Story 2 - Synchronize and Transform Data Files (Priority: P2)

An administrator triggers synchronization of the vendored source files
(projects, articles, research locations). The system validates, transforms,
and synchronizes the data into the canonical domain model, atomically — no
partial or mixed states are ever visible. The administrator sees the outcome
of the synchronization (success, record counts, errors).

**Why this priority**: The professor pages (US1) are the visible value, but
their data is only as good as the synchronization pipeline that feeds them.
This story makes the portal self-sustaining instead of relying on curated
samples.

**Independent Test**: An administrator triggers synchronization of the
vendored source files; after synchronization the portal reports a successful
sync, and every record in the files is queryable and correct (no duplicates,
no dropped records).

**Acceptance Scenarios**:

1. **Given** valid source files are available, **When** the administrator
   triggers synchronization, **Then** the system reports success with record
   counts per data type and no partial states are visible.
2. **Given** a source file contains malformed or incomplete records, **When**
   synchronization runs, **Then** the errors are reported with enough detail
   to locate the offending records, and valid records are still processed.
3. **Given** synchronization fails partway through, **When** the process
   completes, **Then** the previously published data remains fully intact and
   the failure is reported.

---

### User Story 3 - Find Professors and Track Data Freshness (Priority: P3)

A user searches the professor directory by name and opens profiles
from results. Administrators see when each data set was last synchronized;
re-synchronization is available only while the database is empty.

**Why this priority**: Search and discovery improve usability once profiles
exist, and sync status gives administrators confidence in data freshness. Both
extend US1 and US2 without changing their core behavior.

**Independent Test**: A user searches a professor by name fragment and reaches
the correct profile; an administrator sees the last-sync timestamp and is
refused a re-synchronization while data exists.

**Acceptance Scenarios**:

1. **Given** the portal contains multiple professors, **When** a user searches
   by a name fragment, **Then** matching professors are listed and each result
   links to the professor's page.
2. **Given** the database contains data, **When** an administrator views the
   data status or attempts a re-synchronization, **Then** the last-sync
   timestamp and record counts are shown, and the re-synchronization is
   refused without modifying any data.

---

### User Story 4 - Admin Registration and Professor Self-Management (Priority: P2)

An administrator logs in and registers professors into the portal. A
professor logs in and can view and edit only their own data; attempting to
modify another professor's data is rejected.

**Why this priority**: Registration and self-management are required for the
portal to be maintained over time, and the permission rules protect data
integrity. They extend the portal's lifecycle without changing the public
viewing experience.

**Independent Test**: An administrator registers a professor; the professor
logs in, edits their own data successfully, and is denied when attempting to
edit another professor's data.

**Acceptance Scenarios**:

1. **Given** an authenticated administrator, **When** they register a new
   professor, **Then** the professor appears in the portal and can log in.
2. **Given** an authenticated professor, **When** they edit their own data,
   **Then** the change is saved and visible on their public page.
3. **Given** an authenticated professor, **When** they attempt to modify
   another professor's data, **Then** the request is denied and no change is
   made.
4. **Given** a non-administrator, **When** they attempt to register a
   professor, **Then** the request is denied and no professor is created.

---

### Edge Cases

- What happens when a professor has no articles, no projects, or no locations?
  (Sections must render as empty states, not disappear or break.)
- What happens when a source file references a project or location that
  does not exist? (Record-level validation error, professor still published.)
- What happens when a professor appears in only one of the source files?
  (Partial profile with empty sections, never a dropped professor.)
- What happens when the same article appears in two source files?
  (Deduplication keeps exactly one canonical record.)
- What happens when a synchronization is triggered while a previous one is
  still running? (Second run is rejected or queued, never concurrent.)
- What happens when the data source contains sensitive personal data (CPF,
  RG, precise location)? (Masked in logs, errors, analytics, and any
  non-essential response by default.)
- What happens on very large files (e.g., thousands of records)? (The
  operation completes within the performance budget or is moved to an
  asynchronous flow with status feedback.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated page for each professor that
  exists in the data source.
- **FR-002**: Professor pages MUST present data hierarchically, in this
  order: name and affiliation, current projects, article counts by year,
  research locations, article list.
- **FR-003**: System MUST compute article counts grouped by publication year
  from the article records.
- **FR-004**: System MUST ingest data from source files covering (at minimum)
  projects, articles, and research locations.
- **FR-005**: System MUST transform ingested data into the canonical domain
  model before it is displayed or served.
- **FR-006**: System MUST perform any synchronization atomically — all
  records commit together or none do — so no partial or mixed states are
  ever visible.
- **FR-007**: System MUST report synchronization outcomes to the
  administrator: success, record counts per data type, and per-record errors.
- **FR-008**: System MUST reject a synchronization while another is running.
- **FR-009**: System MUST deduplicate records that appear in more than one
  source file.
- **FR-010**: System MUST support searching professors by name fragment, with
  results linking to the professor's page.
- **FR-011**: System MUST show administrators the last-synchronization
  timestamp. Re-synchronization MUST be refused while the database contains
  data (409); it is only possible after the database is empty (e.g., after a
  wipe).
- **FR-012**: Sensitive personal data in source files MUST be masked in logs,
  error messages, analytics events, and non-essential responses by default,
  and MUST be returned in full only to callers with an explicit, audited
  need (LGPD).
- **FR-013**: Professors' rights to access, correct, and request erasure of
  their personal data MUST be supported as first-class Service operations
  (LGPD). Sensitive fields (CPF, RG, precise location, financial details)
  MUST NEVER be visible or editable in the UI. Email and other non-sensitive
  profile fields ARE editable — by the owning professor after authentication
  (or an administrator) — and such edits affect ONLY the database, never the
  source data files.
- **FR-014**: System MUST render professor pages within 2 seconds end-to-end
  for 95% of requests, including during or after a synchronization.
- **FR-015**: Professor pages MUST be accessible: Dynamic Type, sufficient
  contrast, and VoiceOver labels, and MUST show system-standard loading
  feedback while data is being fetched.
- **FR-016**: System MUST support two roles: administrator and professor.
- **FR-017**: Only an administrator MAY register a new professor; a
  non-administrator attempting to register MUST be denied.
- **FR-018**: A professor MAY only modify their own data; attempting to
  modify another professor's data MUST be denied.
- **FR-019**: System MUST populate the database from the source data
  repository when the database is empty, and MUST refuse to repopulate (or
  leave data untouched) when the database already contains data.
- **FR-020**: System MUST authenticate users before granting access to
  administrative or self-management actions.
- **FR-021**: Source data files MUST be read-only inputs: no endpoint or UI
  MAY edit, upload, or replace them. All edits apply to the database only.

### Key Entities *(include if feature involves data)*

- **Professor**: A researcher with name, affiliation, current projects,
  articles, and research locations.
- **Project**: A research project a professor is involved in, with current
  status (active/completed) and related professors.
- **Article**: A publication with title, publication year, venue, and
  authors, sourced from the canonical article data.
- **ResearchLocation**: A place where a professor conducts research.
- **SyncState**: The outcome of a synchronization run (status, timestamps,
  record counts, errors).

## Constitution Compliance *(mandatory)*

- **CC-001 (TDD - Art. II)**: The plan generated from this spec MUST sequence
  a failing test before each implementation task (unit, contract, integration,
  and UI layers).
- **CC-002 (Data classification - Art. V)**: Research data (articles,
  projects) and research locations are personal data. Classification:
  professor names and article metadata are internal; CPF/RG, full contact
  details, and precise locations are sensitive. Masking rules apply from the
  first commit.
- **CC-003 (Performance - Art. IV)**: Professor page rendering is
  performance-sensitive (FR-014). Mitigation: pre-aggregated article counts
  by year, indexed lookups, pagination of article lists; synchronization is
  an async flow with status polling, never blocking page requests.
- **CC-004 (LGPD rights - Art. V)**: Access, correction, and erasure of
  professor personal data are first-class Service operations (FR-013).
- **CC-005 (Security denied-case - Art. V)**: Synchronization triggering
  (admin-only) and any unmasked personal-data access require a denied-case
  test (non-admin rejected, masked data verified in logs).
- **CC-006 (HIG - Art. I)**: Professor pages use platform-standard navigation
  and components; any custom control is justified and recorded in the spec.
- **CC-007 (Accessibility - Art. VI)**: Dynamic Type, contrast, and VoiceOver
  verification are planned for professor pages and the directory (FR-015).
- **CC-008 (Domain-first - Art. VII)**: Canonical domain entities (Professor,
  Article, ResearchLocation) and the projects concept (eo_lib `Initiative`)
  are sourced from the `research-domain` external package; no local
  redefinition; file-specific shapes map to canonical entities at the module
  boundary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of professor page views render completely within 2 seconds.
- **SC-002**: A professor page shows every expected section (name, current
  projects, article counts by year, locations, article list) for 100% of
  professors in the data source.
- **SC-003**: Article counts by year on a professor page match the source
  data exactly (0% discrepancy).
- **SC-004**: A synchronization of a representative data set (e.g., 5,000
  articles, 200 projects, 300 professors) completes with no data loss and
  ‌0 duplicates.
- **SC-005**: 100% of synchronization runs leave previously published data
  fully intact when the run fails.
- **SC-006**: Users can locate a professor by name fragment in under 5
  seconds.
- **SC-007**: Professors' access/correction/erasure requests are fulfilled
  within 30 days, per LGPD.
- **SC-008**: 100% of screens pass the accessibility checks (Dynamic Type,
  contrast, VoiceOver labels) before release.
- **SC-009**: 100% of non-authorized registration and cross-professor
  modification attempts are denied with no data change.
- **SC-010**: A fresh database populated from the source data repository
  contains every record present in the source files.

## Assumptions

- Source files arrive as structured data files (parquet and JSON canonical
  exports from the horizon_dashboard data repository); exact file list is
  pinned during planning.
- Source data files are read-only inputs (FR-021): the portal never uploads,
  edits, or replaces them; all professor edits apply to the database only.
- Synchronization is one-way: source files are the source of truth; the
  portal never writes back to them.
- The portal is publicly readable; synchronization, seeding, and professor
  registration are restricted to administrators.
- "Current projects" means projects whose status is active in the source
  data.
- A curated sample data set will be provided for development and for the
  independent test of US1.
- Canonical domain entities come from the `research-domain` external
  package; if the package is unavailable, a recorded deviation is required
  at planning (Constitution Article VII).
- Authentication uses standard session/credential-based login with role
  separation (administrator, professor); the first administrator account is
  bootstrapped during setup.
- Error handling uses user-friendly messages with the ability to retry
  failed synchronizations.