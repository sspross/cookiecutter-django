# 0002 — API key management endpoints are session-only

## Context

The headless API mounted at `/api/*` accepts both session cookies and
bearer tokens (see ADR-0001). Uniformity is a goal: one canonical data
path, one set of endpoints.

Self-service API key management lives at `/api/api-keys/*`: a user can
list, mint, and revoke their own keys. Naively following the global
default `auth=[ApiKeyBearer(), django_auth]` would mean a valid bearer
token can be used to mint another bearer token.

That is a token-escalation hazard. The whole point of `revoke()` is that
a leaked credential becomes worthless once the user notices and revokes
it. If the leaked credential can mint a sibling key behind the user's
back, revocation is no longer a backstop — the attacker just rotates to
a freshly-minted key the user has never heard of.

## Decision

The `/api/api-keys/*` router overrides the global auth list with
**`auth=django_auth` only**. Bearer tokens are rejected with `401` on
list, mint, and revoke, even when valid.

Concretely:

- The router is mounted on the same `NinjaAPI` instance as everything
  else; only its `auth=` overrides the default.
- Endpoints: `GET /api/api-keys/`, `POST /api/api-keys/`,
  `POST /api/api-keys/{id}/revoke/`.
- Each endpoint scopes by `request.user`; revoking a key the requester
  does not own returns `404` (not `403`) so existence is not disclosed.
- The Django admin mint/revoke flow (`UserApiKeyAdmin`) is unaffected —
  it remains the operator backstop for cross-user revoke and emergency
  provisioning.

## Consequences

Positive:

- A leaked bearer token cannot self-escalate by minting siblings;
  revocation by the user remains a clean kill.
- The boundary is explicit and testable: a per-router test asserts that
  bearer auth is rejected even with a valid token.
- The asymmetry is documented in one place; future readers do not have
  to reverse-engineer it from `core/api.py`.

Negative:

- The "every endpoint accepts both auth methods" property of the API is
  no longer uniformly true. CONTEXT.md and the `api_keys/api.py` module
  docstring both have to call out the exception.
- Headless scripts cannot rotate their own keys via the API — they have
  to log into the SPA (or ask an operator). This is the intended
  trade-off; key rotation is a UI workflow, not a programmable one.

## Alternatives considered

- **Keep the global dual-auth on `/api/api-keys/*`.** Rejected — the
  token-escalation risk above is the whole motivation for this ADR.
- **Allow bearer auth but require step-up re-auth.** Rejected for v1: it
  adds a re-auth flow we do not otherwise need; the session-only path
  already covers every realistic use case (the user is in the SPA when
  they want to manage keys).
- **Move `/api/api-keys/*` to a separate `NinjaAPI` instance.** Rejected
  — same outcome at higher cost (a second mount, a second OpenAPI
  schema). The per-router override is the smallest change that
  achieves the policy.
