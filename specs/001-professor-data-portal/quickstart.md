# Quickstart: Professor Data Portal

**Phase 1 output** — runnable validation scenarios proving the feature works
end-to-end. Full details in [contracts/](contracts/) and
[data-model.md](data-model.md); implementation specifics live in `tasks.md`.

## Prerequisites

- Python 3.11+, Node 20+, npm
- Access to `github.com/The-Band-Solution/ResearchDomain` (git dependency)

## Setup

```bash
# 1. Backend
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e "backend[dev]"          # installs research_domain dependency

# 2. Vendor source data (already committed under backend/data/):
#    files per data-model.md section 6, pinned commit recorded in backend/data/README.md

# 3. Frontend
cd frontend && npm install && cd ..

# 4. Bootstrap the first administrator
export ADMIN_USERNAME=admin ADMIN_PASSWORD=<strong-password>

# 5. Run
uvicorn portal.main:app --app-dir backend/src --port 8000 &   # backend
cd frontend && npm run dev                                     # frontend
```

## Local `.env`

`backend/.env` (gitignored) holds local settings: `PORTAL_DB_PATH`,
`PORTAL_JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `PORTAL_DATA_DIR`.
It is loaded automatically because `research_domain`/`eo_lib` call
`load_dotenv()` at import time; process environment variables win over it.

The pytest suite is hermetic to these variables — the `app` fixture strips
`ADMIN_USERNAME`/`ADMIN_PASSWORD`, so no admin bootstrap happens during tests
and the suite passes regardless of your local `.env`.

## Validation scenarios

### Scenario A — Seed the database (US2)

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -d \
  "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD" | jq -r .access_token)

curl -s -X POST localhost:8000/api/admin/seed -H "Authorization: Bearer $TOKEN"
# -> 202 {"status":"RUNNING",...}

curl -s localhost:8000/api/admin/sync-status -H "Authorization: Bearer $TOKEN"
# -> 200 {"status":"SUCCEEDED","counts":{...}}  (no records lost, 0 duplicates)

curl -s -X POST localhost:8000/api/admin/seed -H "Authorization: Bearer $TOKEN"
# -> 409 {"detail":"Database already seeded"}   (FR-019)
```

**Expected outcome**: counts match the source files; second seed refused.

### Scenario B — Professor profile page (US1)

```bash
curl -s localhost:8000/api/professors?q=Silva
# -> 200 {"items":[...],"total":...}

ID=$(curl -s localhost:8000/api/professors?page_size=1 | jq -r .items[0].id)
curl -s localhost:8000/api/professors/$ID
```

**Expected outcome**: sections in order name → current projects → article
counts by year → locations → articles; counts match `articles_canonical`
grouped by year for that researcher (SC-003); page renders in < 2s (SC-001).
Browser: open `http://localhost:3000/professors/$ID` — all sections render,
empty sections show empty states, Dynamic Type/VoiceOver work (a11y).

### Scenario C — Admin registration + self-management (US4)

```bash
curl -s -X POST localhost:8000/api/admin/professors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Maria Souza","username":"maria","password":"secret-123"}'
# -> 201 {"id":..,"role":"PROFESSOR","researcher_id":..}

MTOKEN=$(curl -s -X POST localhost:8000/api/auth/login -d \
  "username=maria&password=secret-123" | jq -r .access_token)

curl -s -X PATCH localhost:8000/api/professors/$ID \
  -H "Authorization: Bearer $MTOKEN" -H "Content-Type: application/json" \
  -d '{"resume":"Updated by owner"}'
# -> 200 (owner can edit own data)

curl -s -X PATCH localhost:8000/api/professors/999 \
  -H "Authorization: Bearer $MTOKEN" -H "Content-Type: application/json" \
  -d '{"resume":"Hack attempt"}'
# -> 403 (denied case — not own data)

curl -s -X POST localhost:8000/api/admin/professors -H "Authorization: Bearer $MTOKEN" ...
# -> 403 (denied case — only ADMIN registers)
```

**Expected outcome**: SC-009 holds — every unauthorized attempt denied with
no data change.

### Scenario D — LGPD access and erasure (FR-013)

```bash
# Owner retrieves their personal data (access request)
curl -s localhost:8000/api/professors/$ID/personal-data \
  -H "Authorization: Bearer $MTOKEN"
# -> 200 {"researcher_id":..,"name":"Maria Souza","emails":[...],"sensitive_fields":[...]}

# Cross-professor access is denied (denied case)
curl -s localhost:8000/api/professors/999/personal-data \
  -H "Authorization: Bearer $MTOKEN"
# -> 403

# Owner requests erasure; sensitive data + account are anonymized
curl -s -X DELETE localhost:8000/api/professors/$ID/personal-data \
  -H "Authorization: Bearer $MTOKEN"
# -> 200 {"status":"erased","erased_fields":[...],"anonymized_account":true}

# Audit log contains no sensitive values
# (verified by test_lgpd_erasure.py assertions)
```

**Expected outcome**: access returns full values only to owner/ADMIN;
cross-professor and anon requests denied (403/401); erasure anonymizes the
account; sensitive fields never appear in logs, errors, or the UI.

## Test commands

```bash
# Backend (unit + contract + integration, real SQLite)
pytest backend/tests/unit backend/tests/contract backend/tests/integration

# Latency regression (Art. IV — 2s p95 budget)
pytest backend/tests/contract/test_latency.py

# UI + accessibility (Playwright)
cd frontend && npx playwright test

# Lint/format gate (Art. III)
ruff check backend && ruff format --check backend
```

## Done when

- Scenarios A/B/C/D all pass against a fresh clone (empty DB → seed → pages
  → authz → LGPD access/erasure).
- All pytest + Playwright suites green; ruff clean; latency under budget.

## Validation results

End-to-end run against the vendored `backend/data/` sources on a fresh
database (2026-08-18), 19/19 checks passing:

- **Seed (US2)**: `SUCCEEDED`; counts match the source files — researchers
  2,472 (professors only), articles 2,298, initiatives 4,737, campuses 23,
  organizations 180, knowledge areas 1,530, research productions 1,180,
  fellowships 18. SC-004 scale: ≥300 professors satisfied; article total is
  the actual vendored-source total (2,298 < 5,000), documented here as
  agreed. Second seed refused with `409 Database already seeded`.
- **Professor pages (US1)**: search `q=Maria` → 87 hits; profile renders all
  sections (name → current projects → article counts by year → locations →
  articles); unknown id → 404.
- **Authz (US4)**: admin registers a professor (201); the professor logs in,
  patches own resume (200); cross-professor patch and non-admin registration
  denied (403) with no data change.
- **LGPD (FR-013)**: owner access returns the personal-data record; cross
  access denied (403); erasure anonymizes the linked account (login refused
  afterwards); audit log contains no sensitive values (emails, LGPD- ids,
  passwords verified absent).
- **Gates**: 141 backend tests + 22 Playwright tests green; ruff lint/format
  clean; latency regression under the 2s page / 5s search p95 budgets.