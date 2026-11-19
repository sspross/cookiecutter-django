# API key management endpoints are session-only

The `/api/api-keys/*` router overrides the API's default auth with
`django_auth` only, so a valid bearer token cannot list, mint or revoke keys.
With the default, a leaked token could mint a sibling key the user has never
heard of, and revocation would stop being a kill switch. Headless scripts
therefore cannot rotate their own keys: rotation is a UI workflow.

Minting is throttled to ten per hour per user, because a stolen session
cookie could otherwise mint keys in bulk that outlive the session. Listing and
revoking stay unthrottled: they are how a user cleans up a leak, and a
throttle would let an attacker who burns the budget block that cleanup.

This override is the only one. A second audience (a partner API, a
machine-to-machine integration, an internal ops API) gets its own `NinjaAPI`
instance on its own path prefix, with its own `auth=` list and keys scoped to
that surface. Two exceptions on one default are a rule nobody can state, and a
separate instance keeps each audience's OpenAPI document separate, so the
SPA's generated `schema.d.ts` describes only what the SPA can call.
