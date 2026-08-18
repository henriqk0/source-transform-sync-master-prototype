# Contract: Auth API

Base path: `/api` — Authentication and authorization for the portal.

## POST /api/auth/login

Authenticate with credentials; issues a JWT.

**Request** (`application/x-www-form-urlencoded`, OAuth2 password flow):

| Field | Type | Required |
|-------|------|----------|
| `username` | string | yes |
| `password` | string | yes |

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "access_token": "<jwt>", "token_type": "bearer", "role": "ADMIN"\|"PROFESSOR", "researcher_id": int\|null }` |
| 401 | `{ "detail": "Invalid username or password" }` |
| 422 | validation error (FastAPI default shape) |

**Contract tests**: 200 with valid credentials; 401 with wrong password;
401 with unknown user; token payload contains `role` and `researcher_id`
claims.

## GET /api/auth/me

Return the current authenticated user (Bearer token).

**Responses**:

| Code | Body |
|------|------|
| 200 | `{ "id": int, "username": str, "role": "ADMIN"\|"PROFESSOR", "researcher_id": int\|null }` |
| 401 | missing/invalid token |

**Contract tests**: 200 with valid token; 401 without/with invalid token.

## Error shape

All errors use FastAPI's `{ "detail": ... }` shape. Sensitive fields are
never echoed in error messages (masking layer).

## Authz rules enforced by this module

- `ADMIN` — everything incl. professor registration and seeding.
- `PROFESSOR` — read public data + modify own `Researcher` only.
- Anonymous — public read endpoints only.