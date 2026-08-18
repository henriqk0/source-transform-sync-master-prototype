<!--
  ============================================================================
  SYNC IMPACT REPORT (latest amendment: v1.0.0 -> v1.1.0, 2026-08-18)
  ============================================================================
  Amendment type: MINOR (new article added)

  Added sections:
    - Article VII. Domain-First Data Modeling (canonical domain entities
      sourced from the `research-domain` external package)

  Modified principles: none

  Removed sections: none

  Templates updated:
    - ✅ .specify/templates/plan-template.md  (Domain model source context
      line; Article VII gate added to Constitution Check)
    - ✅ .specify/templates/spec-template.md  (CC-008 domain-first check added)

  Deferred TODOs: none

  ----------------------------------------------------------------------------
  Prior amendment: (unfilled template) -> v1.0.0, 2026-08-18 [initial adoption]
    - Added: Articles I-VI + Governance (Article VII content: supersession,
      amendment versioning, Constitution Check, complexity justification)
    - ✅ plan-template.md, spec-template.md, tasks-template.md,
      .opencode/commands/speckit.tasks.md updated
  ============================================================================
-->

# Source Transform Sync Master Constitution

This constitution defines the non-negotiable principles governing how this
project is designed, built, tested, and shipped. All specifications, plans, and
implementation tasks produced through Speckit MUST comply with these articles.
Any deviation requires an explicit, documented exception approved during the
planning phase — silent violations are not permitted.

## Core Principles

### I. Architecture: Modular Monolith

The system MUST be built as a modular monolith: a single deployable unit
composed of clearly bounded, independently reasoned-about modules. Modules
communicate through explicit interfaces (function/service calls within the
process), never through ad-hoc shared state or direct cross-module database
access.

Each module MUST own its data. Cross-module data access happens only through
the owning module's Service layer — never by another module querying its tables
or repositories directly.

Module boundaries MUST be drawn around business capabilities (e.g. Billing,
Users, Notifications), not technical layers. A module is only extracted into a
separate deployable service if a documented, concrete scaling or team-ownership
need arises — the monolith is the default, not a temporary state to be
apologized for.

Backend modules MUST follow MVC + Repository & Service pattern:

- **Model** — the domain/data entities and validation rules; no framework or
  transport concerns.
- **Repository** — the only layer allowed to speak to the persistence layer
  (SQL/ORM). Repositories return domain models, never raw rows or ORM-specific
  types, to the layers above them.
- **Service** — owns business logic and orchestration. Services call one or
  more Repositories, enforce invariants, and are the only layer permitted to be
  called from other modules.
- **Controller** — translates transport (HTTP/GraphQL/etc.) requests into
  Service calls and Service results into responses. Controllers MUST NOT
  contain business logic or talk to Repositories directly.

Dependency direction is one-way: Controller → Service → Repository → Model. A
lower layer MUST NEVER import from or call a higher layer.

UI MUST adhere to Apple's Human Interface Guidelines (HIG). This applies
whether the client is native (SwiftUI/UIKit) or a platform-appropriate
equivalent for web/hybrid surfaces:

- Use platform-standard navigation patterns, spacing, typography scale, and
  system components before introducing custom ones.
- Respect system-level behaviors: Dynamic Type, Dark Mode, safe areas,
  accessibility (VoiceOver), and standard gestures.
- Every screen is reviewed for HIG conformance before being marked done; a
  custom control is only justified when no HIG-compliant pattern covers the
  interaction, and the justification is recorded in the spec.

### II. Test-Driven Development (Non-Negotiable)

No production code is written before a failing test exists for it. The cycle is
strictly: write a test → watch it fail (Red) → write the minimal code to pass
it (Green) → refactor with tests green throughout (Refactor).

Every plan generated from a spec MUST sequence test-writing tasks before their
corresponding implementation tasks. A task list that places implementation
before its test is malformed and must be corrected before work begins.

Test coverage is layered to match the architecture:

- **Unit tests** for Models, Services, and Repositories in isolation
  (Repositories tested against a real or containerized database instance — not
  mocked SQL — to catch mapping and constraint errors).
- **Contract tests** for every Controller endpoint, verifying request/response
  shape and status codes independent of business logic.
- **Integration tests** for cross-module Service-to-Service flows.
- **UI tests** for critical user journeys, including accessibility assertions
  (Dynamic Type rendering, VoiceOver labels).

A pull request MUST NOT merge with failing tests, skipped tests without a
linked ticket explaining why, or a drop in coverage on touched files.

Bugs are never fixed directly. A regression test that reproduces the bug is
written first (and confirmed to fail), then the fix is applied.

### III. Code Quality

Code MUST be self-documenting first, commented second: comments explain why,
not what. Code that needs a comment to explain what it does should usually be
rewritten to be clearer instead.

Every module's public interface (its Service methods, in particular) MUST be
documented with inputs, outputs, error conditions, and invariants — this is the
contract other modules are allowed to rely on.

Static analysis, linting, and formatting are enforced automatically in CI and
MUST pass before merge. No style discussions happen in review that a linter
could have caught.

Cyclomatic complexity and function length are kept low by default; a Service
method or Controller action that grows past a reasonable size is a signal to
decompose it, not to add another if branch.

Dead code, commented-out code, and speculative ("just in case") code are not
permitted in merged work.

### IV. Performance Requirements

All user-facing API responses MUST complete in under 2 seconds end-to-end
(p95), measured from request received to response sent. This is a hard budget,
not an aspiration:

- Endpoints expected to approach or risk exceeding the budget MUST be
  identified during planning, with a stated mitigation (indexing, caching,
  pagination, async processing) before implementation begins.
- Any operation that cannot fit the 2-second budget (e.g. bulk exports, heavy
  reports) MUST be moved to an asynchronous/background flow with a
  status-polling or notification mechanism — it is never allowed to block the
  synchronous request path.
- Performance is verified, not assumed: endpoints identified as
  performance-sensitive get a load or latency test in CI, and regressions
  against the 2-second budget block merge.
- Database access goes through Repositories using indexed queries; N+1 query
  patterns are treated as bugs and must be caught in review or by automated
  query-count assertions in Repository tests.
- UI responsiveness follows the same discipline: any operation that could take
  a perceptible amount of time on-device MUST show system-standard
  loading/progress feedback per the HIG rather than a frozen interface.

### V. Data Integrity & Security (LGPD Compliance)

Data integrity is guaranteed at the persistence boundary. All writes go through
the Repository layer, which enforces schema constraints, foreign keys, and
transactional boundaries. Multi-step writes that must succeed or fail together
MUST be wrapped in a database transaction — partial writes are treated as a
data-integrity bug.

Services enforce business invariants before delegating to Repositories; invalid
states MUST be rejected at the Model/Service layer, not merely caught by
database constraints as a last resort.

Sensitive personal data MUST be masked or redacted by default, in compliance
with Brazil's LGPD (Lei Geral de Proteção de Dados):

- Sensitive fields (CPF, RG, full financial details, health data, precise
  location, etc.) are masked in logs, error messages, analytics events, and any
  non-essential API response by default. Full values are only ever returned to
  a caller with an explicit, audited need and purpose.
- Logging and monitoring tooling MUST pass through a masking layer before any
  request/response payload is persisted or shipped to a third-party service —
  this is not optional per-call behavior, it is enforced centrally.
- Data retention, the right to access, correction, and deletion (portability
  and erasure requests) MUST be implemented as first-class Service operations
  for any module that stores personal data, not handled as one-off manual
  database edits.
- Every new field or table that stores personal data is classified
  (public / internal / sensitive) as part of the spec before implementation,
  and the masking/access rules for that classification are applied from the
  first commit — not retrofitted later.
- Security-relevant changes (auth, permissions, data access, masking rules)
  require an explicit test asserting the denied case, not only the happy path.

### VI. User Experience Consistency

The UI is a single coherent experience across the product: shared design tokens
(color, spacing, type scale), shared component patterns, and shared interaction
conventions are used everywhere a suitable one already exists, rather than
reinvented per screen.

Apple HIG conformance (Article I.5) is the baseline for every screen;
consistency within the app takes precedence over a locally "nicer" one-off
pattern.

Error states, empty states, and loading states are treated as required design
deliverables for every screen — not an afterthought added during implementation.

Accessibility is a release-blocking requirement, not a nice-to-have: Dynamic
Type, sufficient contrast, and VoiceOver labels are verified before a screen
ships.

### VII. Domain-First Data Modeling

The domain model is defined before implementation, and its canonical form
comes from the `research-domain` external package — the single source of truth
for domain entities.

- The Model layer of every module MUST source canonical domain entities from
  the `research-domain` package. Modules MUST NOT redefine, duplicate, or
  shadow a canonical entity locally.
- Feature-specific shapes that are not part of the canonical model are
  introduced as explicit projections or local types mapped to canonical
  entities at the module boundary (e.g., in a Repository or Service mapper) —
  never by reinterpreting or widening a canonical entity's meaning.
- Evolution of canonical entities is governed by the `research-domain` package
  lifecycle. Modules adopt new definitions via package upgrades; the impact of
  an upgrade is assessed and tested before merge, and the package version is
  pinned and recorded in the plan.
- Repository and Service layers exchange canonical domain entities. Transport
  shapes (request/response DTOs) are Controller-layer concerns and MUST NOT be
  promoted into the domain model.
- `data-model.md` (plan Phase 1) MUST document the mapping between module
  models and the canonical entities they source from `research-domain`.

## Governance

This constitution supersedes individual preferences, prior conventions, and
expedience under deadline pressure. When a spec or plan conflicts with it, the
constitution wins and the spec/plan is revised.

Amendments require a version bump and a recorded rationale:

- **MAJOR** — an article is removed or redefined in a backward-incompatible
  way.
- **MINOR** — a new article or a materially expanded principle is added.
- **PATCH** — clarification or wording fix with no semantic change.

Every plan produced by Speckit MUST include a "Constitution Check" step
confirming the plan does not violate any article above, or stating the
specific, approved exception if it does.

Complexity introduced beyond what's outlined here (a new module boundary, a
deviation from MVC + Repository & Service, an async exception to the 2-second
budget) MUST be justified in writing in the relevant spec — "it's simpler this
way" is not sufficient justification on its own.

**Version**: 1.1.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
