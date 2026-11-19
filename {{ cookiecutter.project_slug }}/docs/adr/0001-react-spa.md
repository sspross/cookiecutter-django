# React SPA with shadcn/ui for the authenticated app

The authenticated app is a React SPA (TypeScript, shadcn/ui on Tailwind v4,
`react-router`, TanStack Query) on a single Django mount template; login and
admin stay Django-rendered. We expect several dense, deep-linkable views with
a "professional tech tool" look, which shadcn/ui gives at copy-paste cost and
Django templates do not. The SPA and headless scripts call the same `/api/`
endpoints, by session or bearer token, with TS types generated from ninja's
OpenAPI document, so there is no second API and no second validation surface
(one exception: ADR-0002).

The cost is a full frontend toolchain. `vite build` also gates the
Django-rendered login page: it loads the SPA bundle for its CSS and answers
500 without a built manifest.

How it is laid out: `docs/ARCHITECTURE.md` "Frontend & API contract".
