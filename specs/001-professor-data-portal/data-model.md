# Data Model: Professor Data Portal

**Phase 1 output** — entities, fields, relationships, validation, state
transitions. Canonical entities are NOT redefined locally: they are imported
from the `research_domain` package (pinned v0.14.2) per Constitution Article
VII. This document records the mapping and the portal-owned extensions.

## 1. Canonical entities (from `research_domain`, used as-is)

Sourced from `research_domain.domain.entities` (see its `docs/entities.md`).
All are SQLAlchemy-mapped against the `eo_lib` base; persistence goes through
our SQLite repository strategy implementing the package's repository
contracts.

| Entity | Base (eo_lib) | Key fields | Relationships |
|--------|---------------|------------|---------------|
| `Researcher` | `Person` | `id`, `name`, `resume`, `cnpq_url`, `google_scholar_url`, `citation_names`; emails (contact) | `knowledge_areas`, `articles` (N:M), `productions` (N:M), `academic_educations`, `proficiencies`, `awards`, `research_groups` |
| `Article` | `Base` | `id`, `title`, `doi`, `year`, `type` (`JOURNAL`/`CONFERENCE_EVENT`), `journal_conference`, `volume`, `pages` | `authors -> list[Researcher]` (via `article_authors`) |
| `Initiative` | `Base` (eo_lib) | `id`, `name`, `status`, `start_date`, `end_date` | `demandante -> Organization`, `knowledge_areas`, `external_groups` |
| `Advisorship` | `Initiative` | `type`, `program`, `defense_date`, `cancelled`, `cancellation_date`, `fellowship_id`, `institution_id` | `members -> list[AdvisorshipMember]`, `student`, `supervisor` |
| `ResearchGroup` | `Team` | `id`, `name`, `short_name`, `campus_id`, `cnpq_url`, `site` | `knowledge_areas` |
| `Campus` | `OrganizationalUnit` | `id`, `name`, `organization_id` | — |
| `Organization` / `University` | `Organization` | `id`, `name`, `short_name` | — |
| `KnowledgeArea` | `Base` | `id`, `name` | `initiatives`, `researchers` (N:M) |
| `ResearchProduction` | `Base` | `id`, `title`, `year`, `production_type_id`, `publisher`, `isbn`, `edition`, `book_title`, `pages`, `version`, `platform`, `link` | `authors -> list[Researcher]` |
| `Fellowship` | `Base` | `id`, `name`, `description`, `value`, `sponsor_id`, `cancelled`, `cancellation_date` | `sponsor -> Organization` |
| `AcademicEducation`, `Proficiency`, `Award`, `Language`, `EducationType`, `ProductionType`, `Role`, `AdvisorshipMember` | — | per package docs | per package docs |

**Domain concept → canonical entity mapping** (from research.md Decision 6):

- "Professor" → `Researcher`
- "Current projects" → `Initiative` with `status == active` (+ `Advisorship`
  as specialized initiatives)
- "Research locations" → `Campus` / `Organization`
- "Articles" → `Article`

## 2. Portal-owned entities (NOT canonical — portal scope only)

These belong to the portal, not the research domain; each is owned by the
module listed.

### `UserAccount` (owned by Auth module)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | int | PK |
| `username` | str | unique, non-empty |
| `password_hash` | str | bcrypt hash |
| `role` | enum | `ADMIN` \| `PROFESSOR` |
| `researcher_id` | int? | FK → `researchers.id`; set when the account belongs to a professor; NULL for pure admins |

Validation: username unique; password ≥ 8 chars at registration; a PROFESSOR
account MUST reference an existing `Researcher`.

### `SyncState` (owned by Ingestion module)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | int | PK |
| `status` | enum | `IDLE` \| `RUNNING` \| `SUCCEEDED` \| `FAILED` |
| `started_at` | datetime | set when RUNNING begins |
| `finished_at` | datetime? | set on terminal state |
| `counts` | json | per-entity record counts (researchers, articles, …) |
| `errors` | json | per-record error list (masked) |

Validation: exactly one RUNNING state at a time (service invariant); counts
and errors are only present in terminal states.

### `ArticleCountByYear` (owned by ResearchData module — pre-aggregation)

| Field | Type | Constraints |
|-------|------|-------------|
| `researcher_id` | int | FK → `researchers.id` |
| `year` | int | 4-digit |
| `count` | int | ≥ 0 |

PK: `(researcher_id, year)`. Rebuilt during seeding/sync from `Article`
author links; serves FR-003 within the 2s budget (Art. IV).

### `ResearcherCnpq` (owned by ResearchData module — CNPq id projection)

| Field | Type | Constraints |
|-------|------|-------------|
| `researcher_id` | int | PK, FK → `researchers.id` |
| `cnpq_id` | str(64) | unique, non-empty |

Portal-owned boundary table (Art. VII): the canonical `Researcher` carries
only `cnpq_url`. Populated during seeding by extracting the lattes id from
`cnpq_url` (`lattes.cnpq.br/<digits>`, within the seed transaction) and at
admin registration when a `cnpq_id` is given; used to link subsequent logins
for the same professor to the already-saved `Researcher` instead of creating
a duplicate. Only researchers whose source row carries a `cnpq_url` are
linkable by lattes id.

## 3. Validation rules (Model/Service invariants)

- Researcher name MUST be non-empty (Model layer).
- Article year MUST be a 4-digit integer; DOI format when present.
- Username MUST be unique; passwords hashed at rest, never logged.
- Registration (FR-017): only `role == ADMIN` may create a professor
  account (Auth Service invariant).
- Edit (FR-018): a request to modify `Researcher` data is allowed only if
  `requester.role == ADMIN` or `requester.researcher_id == target.id`
  (ResearchData Service invariant; denied otherwise).
- Seed (FR-019): `SyncState.status == IDLE` and database empty (no
  researchers and no user accounts) before starting.
- Sensitive fields (emails, CPF/RG, precise location) MUST be masked in
  logs, errors, and non-essential responses (observability layer).

## 4. State transitions

```text
SyncState: IDLE --start--> RUNNING --success--> SUCCEEDED
                                 \--failure--> FAILED
                    (FAILED/SUCCEEDED --start--> RUNNING on re-seed after DB wipe)

UserAccount: created (ADMIN only) -> active (login allowed)
             professor account always linked to Researcher
```

## 5. Data classification (Art. V)

| Data | Classification | Masking rule |
|------|----------------|--------------|
| Professor name, affiliation, articles, projects, groups | public | none (public portal) |
| Emails, contact details | sensitive | masked in logs/analytics; returned and editable only by owner/ADMIN (PATCH — DB only, never source files) |
| CPF/RG, precise location, financial details (fellowship values) | sensitive | never visible or editable in the UI; masked everywhere; full values only via LGPD access (owner/ADMIN, audited) |

Source data files (`backend/data/`) are read-only inputs (FR-021): no code
path writes to them; all edits apply to the SQLite database only.

## 6. Seeding mapping (source file → canonical entity)

| Source file (backend/data/) | Canonical entity |
|------------------------------|------------------|
| `researchers_canonical.parquet` | `Researcher` (+ Person fields) |
| `articles_canonical.parquet` + `production_authors_canonical.parquet` | `Article` + `article_authors` |
| `research_groups_canonical.parquet` | `ResearchGroup` |
| `campuses_canonical.parquet` | `Campus` |
| `organizations_canonical.parquet` | `Organization`/`University` |
| `knowledge_areas_canonical.parquet` | `KnowledgeArea` |
| `initiatives_canonical.parquet` | `Initiative` (status filter for "current") |
| `research_productions_canonical.parquet` | `ResearchProduction` |
| `advisorships_canonical.parquet` / `fellowships_canonical.parquet` | `Advisorship` / `Fellowship` |
| `_meta.json` | seed metadata (source commit, generated_at) |

Column names are mapped at ingestion time into canonical field names; the
mapping table lives in the Ingestion module and is covered by unit tests
against fixture files.