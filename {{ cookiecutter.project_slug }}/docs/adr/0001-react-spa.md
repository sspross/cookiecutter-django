# 0001 — React SPA + shadcn/ui for the authenticated app

## Context

The authenticated app needs to grow beyond a single CRUD list. We expect
multiple views (settings, API key management, richer detail interactions),
and the project values the "professional tech tool" feel: sidebar shells,
dense tables, monochrome primary, monospace for technical fields. That
aesthetic is achievable in shadcn/ui at copy-paste cost; reinventing it
elsewhere is not.

A second axis: the same backend should be callable both from the browser
and from headless scripts. We do not want a `/api/v2/` split or two
separate validation surfaces.

## Decision

The authenticated app at `/` is a **React SPA** (TypeScript, shadcn/ui on
Tailwind v4, `react-router` v8, TanStack Query). Django serves a single
mount template; the SPA owns all client routing under `/`.

Concretely:

- **Scope.** SPA owns `/` (Dashboard) and `/api-access` (API key
  management). `/accounts/login/` and `/admin/` stay Django-rendered.
- **Auth.** SPA uses session cookies (`ninja.security.django_auth`) with
  CSRF via `X-CSRFToken` header. A second `HttpBearer` auth class accepts
  `Authorization: Bearer <prefix>_live_…` against the `UserApiKey` model.
  Both auth methods resolve to `request.user` and are accepted on the
  same endpoints — no `/api/v2/` split. The exception is the
  `/api/api-keys/*` router; see ADR-0002.
- **API contract.** `openapi-typescript` generates `schema.d.ts` from
  ninja's OpenAPI document, exported offline by `make schema`;
  `openapi-fetch` is the typed fetch wrapper. ninja schemas remain the
  single source of truth.
- **Server state.** TanStack Query owns cache and mutations. List/detail
  routes share cache by query key.
- **Build.** Single `@tailwindcss/vite` pipeline. Compiled CSS is shared
  between the SPA and the remaining Django-rendered pages (login).
- **Aesthetic.** System-aware dark/light, shadcn `zinc` base, monochrome
  primary, sidebar shell, Geist and Geist Mono (Inter as sans fallback).

## Consequences

Positive:

- Future routes (settings, detail views) are deep-linkable.
- shadcn component vocabulary makes the "professional tech tool" goal
  copy-paste-able.
- Typed API contract (generated, not hand-written) catches schema drift
  at compile time.
- Token-auth API path is first-class — headless callers and the SPA
  share one canonical data path.

Negative:

- Real SPA-shaped frontend infrastructure: TS toolchain, react-router,
  TanStack Query, shadcn CLI, generated OpenAPI types. Bigger surface to
  learn than a templates-only app.
- `vite build` blocks Django-rendered pages too (login depends on the
  SPA's compiled CSS). Build break = unstyled login.
