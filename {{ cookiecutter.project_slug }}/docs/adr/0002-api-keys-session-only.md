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

### Minting is throttled, listing and revoking are not

`POST /api/api-keys/` carries ninja's `AuthRateThrottle` at ten mints per
hour, keyed on the authenticated session. Session-only auth removes the
token-escalation path but not the session one: an attacker holding a
stolen cookie could otherwise mint keys in bulk and keep long-lived
credentials after the session itself is gone.

`GET /api/api-keys/` and `POST /api/api-keys/{id}/revoke/` stay
unthrottled. Revocation is the kill switch for a leaked credential, and
listing is how a user finds the key to revoke. Rate-limiting either one
would let an attacker who burns the budget block the user's own cleanup,
which costs more than the abuse it would prevent.

### Growth path: one NinjaAPI per audience

The single dual-auth surface holds while `/api/*` serves one audience: the
project's own users, reaching it either from the SPA (session) or from their
own scripts (bearer). A per-router `auth=` override is the right size for one
exception; it is the wrong size for a second audience.

When one appears (a partner API, a machine-to-machine integration, an internal
ops API), the documented move is a second `NinjaAPI` instance on its own path
prefix with its own `auth=` list, not more overrides on this one. Each instance
carries its own docs page and its own OpenAPI document, so the SPA's generated
`schema.d.ts` keeps describing only the endpoints the SPA can call, and an
audience's auth rule is stated once at its mount instead of being reassembled
from a default plus a list of exceptions.

Scoped keys are the other half. `UserApiKey` today grants all-or-nothing access
to everything the bearer path reaches; a second audience wants a key that names
which surface it may call, so a leaked partner key cannot reach the user API.
That means a scope field on `UserApiKey` and a check in `verify()`, plus each
instance's bearer class asserting its own scope. None of it is built yet: the
template ships the single-audience shape, and this paragraph records where to
go rather than pre-building for a second audience most projects never grow.

Two things to keep in mind when taking that step: the offline schema export
(`manage.py export_openapi_schema`) imports one `api` object and would need to
export each instance, and `/api/api-keys/*` stays session-only wherever it is
mounted, for the reason above.

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
