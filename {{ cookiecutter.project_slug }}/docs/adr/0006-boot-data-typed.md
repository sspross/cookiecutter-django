# 0006 — Boot data is typed: constants are server-rendered, per-user data goes through the API

## Context

The SPA needs two things at boot: the project name (for the sidebar logo /
title) and the signed-in user's name (for the "Signed in as …" footer).

The two values differ in nature: the project name is a **build-time
constant**, identical for every request; the username is **per-user data**.
Carrying both in one untyped `window` blob would put the per-user value
through a static channel and outside the project's typed API contract
(ADR-0001), where a field added on the Django side and read on the TS side
drifts with nothing to catch it.

## Decision

Split the boot payload by nature:

- **Build-time constants are server-rendered.** `project_name` (injected by
  the `core.context.site` context processor) is emitted as a
  `data-project-name` attribute on the `#app` mount node. `main.tsx` reads
  `mountNode.dataset.projectName`. No inline `<script>`, no `window` global,
  no TS fallback literal.
- **Per-user data goes through the typed API.** A `GET /api/me` endpoint
  (schema `core.schemas.MeOut`, dual auth like every other endpoint — so it
  also serves as a headless `whoami`) returns the current user. The SPA
  fetches it with a `useMe()` TanStack Query hook, exactly as it fetches any
  other server state. The type flows from the ninja schema through
  `openapi-typescript` into the FE, so a field added to `MeOut` is typed end
  to end.

`MeOut` starts with just `username` and grows as the SPA needs it (email,
`is_staff`, …); every field stays inside the OpenAPI contract.

## Consequences

Positive:

- One rule for the next person adding boot data: a constant? render it onto
  the mount node. Per-user or dynamic? add it to `MeOut`. No third
  untyped channel reappears.
- Schema drift on per-user boot data is caught at TS compile time, like the
  rest of the API (ADR-0001).
- `/api/me` doubles as a headless identity check for token callers.

Negative:

- The footer's "Signed in as …" now resolves after a fetch rather than on
  first paint — a negligible flash, accepted in exchange for the typing.
- One more endpoint and one more query hook than inlining the blob.

## Alternatives considered

- **An inlined `window` blob, typed by hand.** Rejected — any hand-written
  `declare global` is a second source of truth that drifts from the Django
  side with nothing to catch it; that is the exact failure ADR-0001 pays to
  avoid.
- **Server-render the username too (onto `data-username`).** Rejected — it
  is per-user data, not a build constant; routing it through the typed API
  keeps one rule and gives the SPA a real `whoami` for free.
- **Inline the whole user as a typed JSON island.** Rejected — saves one
  fetch but reintroduces a parallel, hand-maintained type for the user shape.
