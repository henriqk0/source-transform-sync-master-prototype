# Contract: LGPD Data Protection API

Base path: `/api` — first-class access and erasure operations (FR-013,
Constitution Art. V). These are Service-level operations; the UI MUST NEVER
display or edit sensitive fields (CPF, RG, precise location, financial
details). Email and other non-sensitive profile fields remain editable by the
owner via `PATCH /api/professors/{id}` (DB only — source files are read-only,
FR-021).

## GET /api/professors/{id}/personal-data

Fulfill an LGPD access request: return the subject's personal data record.
Allowed for the owning professor or an ADMIN (explicit, audited need).

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "researcher_id": int, "name": str, "emails": [str], "resume": str\|null, "sensitive_fields": [str] }` — full values only for owner/ADMIN; `sensitive_fields` lists the field names present (values never echoed) |
| 401 | unauthenticated |
| 403 | authenticated but neither owner nor ADMIN (denied case) |
| 404 | professor not found |

Every call is written to the audit log (masked) per Art. V.

## DELETE /api/professors/{id}/personal-data

Fulfill an LGPD erasure request: remove the professor's sensitive personal
data (emails, contact, precise location) and anonymize the linked user
account. Research production data (articles, projects) is NOT personal data
and remains. Allowed for the owning professor or an ADMIN.

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "status": "erased", "erased_fields": [str], "anonymized_account": bool }` |
| 401 | unauthenticated |
| 403 | authenticated but neither owner nor ADMIN (denied case) |
| 404 | professor not found |

**Contract tests**: 200 owner; 200 ADMIN; 403 cross-professor (denied case);
401 anon; audit log contains no sensitive values; after erasure, PATCH email
returns 404/400 (no longer editable).

## Notes

- Correction (LGPD) is fulfilled by the existing owner-scoped
  `PATCH /api/professors/{id}` for non-sensitive fields.
- Erasure and access never touch the source data files (FR-021).