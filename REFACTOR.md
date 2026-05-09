# Cookiecutter-Django Refactor — Port Patterns from `manufacturer-summarizer`

> **Audience:** the agent executing this refactor. Read this entire file once before
> writing code. Every design decision below was already grilled and locked — do not
> re-litigate. If you discover a constraint that breaks a locked decision, stop and
> ask the user; do not improvise.

---

## 1. Context

Two repositories live side-by-side:

- **`/Users/sspross/projects/cookiecutter-django/`** — the cookiecutter template (this repo).
  It currently generates a thin Django + Tailwind/PostCSS + tiny-React-widget project.
- **`/Users/sspross/projects/manufacturer-summarizer/`** — the canonical real-world
  application built from the template. Has since evolved well past the template:
  RQ on Redis, dual-auth ninja API, full React SPA on shadcn/Tailwind v4, Playwright
  live-test infra, Appliku-shaped multi-process Dockerfile, ADRs, etc.

**The job:** port the patterns that have proven themselves in `manufacturer-summarizer`
back into the cookiecutter template, so the *next* project Silvan generates ships
with those patterns built in.

**Source-of-truth snapshot:** manufacturer-summarizer SHA `54cbf25` (2026-05-09).
When this REFACTOR.md says "copy from manufacturer", read from that working tree.

This is a **one-shot port**. After today, the two repos drift independently — no
sync workflow, no shared package. The user explicitly chose this (Workflow A).

---

## 2. Source of truth & substitution rules

### Path conventions in this document

- `MFS:` prefix → path inside `manufacturer-summarizer/`
- `TPL:` prefix → path inside `cookiecutter-django/{{ cookiecutter.project_slug }}/`
- `ROOT:` prefix → path inside `cookiecutter-django/` (template root, not generated)

### Substitution rules when copying files from MFS to TPL

When porting any file, apply these substitutions verbatim:

| In MFS source | In TPL destination |
|---|---|
| `manufacturer-summarizer` (project slug) | `{{ cookiecutter.project_slug }}` |
| `Manufacturer Summarizer` (project name) | `{{ cookiecutter.project_name }}` |
| `Architonic Competences` (PROJECT_NAME constant in `core/settings/base.py`) | `{{ cookiecutter.project_name }}` |
| `mfs_live_` (API key prefix) | `{{ cookiecutter.project_slug }}_live_` |
| `__MFS__` (window global for SPA config) | `__APP__` (project-agnostic) |
| `mfs-config` (json_script id in app.html) | `app-config` |
| Any reference to `queries/` app or its models (`Query`, `QueryType`, etc.) | **delete** — these are domain-specific to MFS and do not port |
| `silvan.spross@gmail.com` (hardcoded) | `{{ cookiecutter.author_email }}` |
| `sspross` (hardcoded username) | `{{ cookiecutter.django_username }}` |

### What does NOT port from MFS

Anything domain-specific to manufacturer-summarizer:

- `queries/` app and everything it owns (Query model, QueryType registry, GeminiConfig,
  QueryTypeConfig, signals.py, services/llm.py, services/run.py, jobs.py, types/, etc.)
- `dumpdata.json` rows beyond the seed admin user (no Query-Type configs)
- ADRs about Gemini, Query soft-delete, Query-Type toggles
- CONTEXT.md sections about Query, Query Type, Gemini, web search grounding,
  manufacturer-non-entity
- `google-genai`, `json-repair`, `djfernet` dependencies (LLM-specific)
- Any CSS/UI specific to the queries list/detail (e.g. `query-status-badge.tsx`,
  `create-modal.tsx`, `delete-query-modal.tsx`, `routes/list.tsx`, `routes/detail.tsx`)

What DOES port: api-keys feature, dual-auth, SPA shell, live-test infra, Docker
multi-process pattern, Appliku skill + yml, Makefile, pre-commit, ADRs about the
ported patterns (renumbered).

---

## 3. Locked decisions (do not re-open)

| # | Decision | Locked value |
|---|---|---|
| 1 | Template opinionation | **Pure Shape A**: no cookiecutter feature questions; opinionated always-on stack. README leads with Appliku, smini-compose listed as alternative. |
| 2 | SPA shape | **Hello SPA + load-bearing `api_keys/` feature**, not a fake demo. Real auth, real ninja API, real model. |
| 3 | API-keys deletion seam | **Cut A**: everything api-keys-related lives in `api_keys/` app (model, HttpBearer subclass, /api/api-keys/ endpoints, admin). `core/api.py` imports from it. Deletion = `rm -rf api_keys/` + 3 obvious edits, fails loud. |
| 4 | App shell | Sidebar + main + user menu top-right, ported from MFS, stripped to 2 nav items (Dashboard, API Access). |
| 5 | Routes | `/` is **Dashboard**, `/api-access/` is sibling. Both shipped real, no scaffolding. |
| 6 | Dashboard day-1 | **Option α**: inline cards in `routes/index.tsx`: "API Keys: N" (live, sharing TanStack cache with /api-access/) + "Recent Activity: empty". No abstractions. Dev grows by duplicating. |
| 7 | Docs | **Model 2**: 4 ADRs renumbered from 0001 (React SPA, API-keys session-only, Async by default, Dual-deployment). CONTEXT.md ships API Key + Soft-delete vocab + dual-auth Frontend/API contract section, all describing shipped code. |
| 8 | Dockerfile + compose | **Pattern M**: drop CMD from Dockerfile. Compose = db + redis + web (`./web.sh`) + worker (`./worker.sh`). `release.sh` runs as one-shot via `docker compose run --rm web ./release.sh`. Update fabfile.py accordingly. |
| 9 | Appliku skill location | Ship in generated project's `.claude/skills/appliku/`. Copy verbatim from MFS. |
| 10 | Makefile + pre-commit | Bring over MFS's Makefile additions + 4 local pre-commit hooks (tach, biome-check, tsc-typecheck, pip-audit-manual). |
| 11 | Login bootstrap | `hooks/post_gen_project.py` already computes PBKDF2 hash. Just add styled login.html, accounts/ URLs, LOGIN_*_URL settings, @login_required on SPA mount view. |
| 12 | API key prefix | `{{ cookiecutter.project_slug }}_live_` — full slug + `_live_`. Dev shortens post-gen if desired. |
| 13 | Live tests | Bring StaticLiveServer pattern (already 95% in TPL). Ship sample live test for api_keys mint flow. Add to cookiecutter root smoke pipeline. |
| 14 | shadcn components shipped | **8 components**: card, dialog, button, input, label, badge, table, skeleton. Drop select + separator (re-add via `npx shadcn add` if needed). |
| 15 | Theme | Dark mode + theme-toggle (matches MFS). All shadcn tokens paired light/dark. localStorage persistence. System pref default. |
| 16 | Drift management | **Workflow A**: one-shot port; no automated sync; no Guardrails. |

---

## 4. Implementation phases

Execute phases sequentially. After each phase, run its verification gate before
moving to the next. Phases are designed so a partial completion still leaves the
template in a valid state for the next phase to start from.

### Phase 0 — Branch + baseline snapshot

1. Create a branch in cookiecutter-django: `git checkout -b refactor/port-from-manufacturer`.
2. Run the existing baseline smoke test to confirm the starting point is green:
   `make test` from `ROOT:`. If red, stop and report — do not proceed on a red baseline.
3. Note the current MFS SHA `54cbf25` in `ROOT:docs/template-snapshot.md` (single
   line: `Ported from manufacturer-summarizer @ 54cbf25 on YYYY-MM-DD`).

**Verification gate:** `make test` green; `docs/template-snapshot.md` exists.

---

### Phase 1 — Delete obsolete content from current template

These files become irrelevant under the new design. Delete them outright:

- `TPL:core/templates/about.html`
- `TPL:core/views.py` (the `home`/`about` views — will be replaced)
- `TPL:core/templates/_base.html` (replaced by MFS-style _base.html in Phase 5)
- `TPL:core/frontend/src/js/` (entire directory — old widget/test pattern)
- `TPL:core/frontend/src/styles.css` (replaced by spa/index.css in Phase 5)
- `TPL:core/frontend/postcss.config.js`
- `TPL:core/frontend/eslint.config.mjs` (replaced by biome.json in Phase 5)
- `TPL:core/static/` (regenerated by build)
- Lines in `TPL:core/urls.py` for the `home` and `about` routes (will be re-added in Phase 6)

Update `TPL:core/templates/_header.html` and `_logo.html`: delete `_header.html`
(SPA owns navigation now), keep `_logo.html` as-is (used by login.html).

**Verification gate:** `git status` shows only deletions; do not commit yet.

---

### Phase 2 — Dependencies, settings, env

#### 2.1 `TPL:pyproject.toml`

Add to `dependencies`:
```toml
"django-ninja>=1.6.2",
"django-rq>=4.1.0",
"redis>=7.4.0",
```

Do NOT add: `google-genai`, `json-repair`, `djfernet` (LLM-specific, not ported).

`dev` group: unchanged (already has playwright, pytest-playwright, tach, pip-audit).

#### 2.2 `TPL:core/settings/base.py`

Port from `MFS:core/settings/base.py`. Key additions over current TPL version:

- Add to `env` declarations:
  ```python
  REDIS_URL=(str, "redis://localhost:6379/0"),
  DJANGO_VITE_DEV_MODE=(bool, None),
  ```
- Add `PROJECT_NAME = "{{ cookiecutter.project_name }}"`
- Add to `INSTALLED_APPS`: `"django_rq"`, `"api_keys"` (in that order, after `django_vite`, before `core`)
- Add `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "login"`
- Add the templates context_processor `"core.context.site"`
- Replace static `DJANGO_VITE` block with the MFS one (uses `_vite_dev_mode`)
- Add the `REDIS_URL` + `RQ_QUEUES` block from MFS (verbatim)

#### 2.3 `TPL:core/settings/test.py`

No changes needed — current TPL test settings already work. After Phase 2 completes,
verify the existing test settings still import cleanly with the new INSTALLED_APPS.

#### 2.4 `TPL:.env.example`

Replace with MFS's, minus the Gemini-specific lines:
```
DEBUG=True
SECRET_KEY=replace-with-secret-key
DATABASE_URL=sqlite:///db.sqlite3
# DATABASE_URL=postgresql://localhost:5432/{{ cookiecutter.project_slug }}
ALLOWED_HOSTS=
CSRF_TRUSTED_ORIGINS=

# Redis broker URL used by django-rq for async background jobs.
REDIS_URL=redis://localhost:6379/0

# Optional: decouples django-vite's dev_mode from DEBUG. Set to False to
# serve the built manifest from `npm run build` + collectstatic while
# keeping DEBUG=True. Unset = follows DEBUG.
# DJANGO_VITE_DEV_MODE=False
```

#### 2.5 `TPL:core/context.py` (new file)

Port from `MFS:core/context.py`. Adapt NAVITEMS to:
```python
NAVITEMS = [
    Navitem(name="home", label="Dashboard"),
    Navitem(name="api-access", label="API Access"),
]
```

#### 2.6 `TPL:tach.toml`

Update to:
```toml
exclude = [
    "**/__pycache__",
    "**/tests/**",
    "**/test_*",
    "**/migrations/**",
    "**/management/**",
    "manage.py",
]
exact = false
ignore_type_checking_imports = true
forbid_circular_dependencies = true

[[modules]]
path = "core"
depends_on = ["api_keys"]

[[modules]]
path = "api_keys"
depends_on = []
```

#### 2.7 `TPL:.gitignore`

Append (if not present):
```
test_artifacts/
core/static/dist/
core/frontend/node_modules/
```

#### 2.8 `TPL:.dockerignore`

Replace with `MFS:.dockerignore` verbatim — it's already project-agnostic.

**Verification gate:** `uv sync` succeeds. `uv run python manage.py check` succeeds
(will fail until `api_keys/` app exists in Phase 4 — defer this check to end of Phase 4).

---

### Phase 3 — Auth + login + dumpdata

#### 3.1 `TPL:core/templates/registration/login.html` (new file)

Copy from `MFS:core/templates/registration/login.html` verbatim. Uses `{% include "_logo.html" %}`
and `{% vite_asset "main.tsx" %}` so it shares the SPA's compiled CSS.

#### 3.2 `TPL:dumpdata.json`

Already has the right shape. Replace the placeholder fields with cookiecutter
variables (the `post_gen_project.py` will substitute the password hash):

```json
[
    {
        "model": "auth.user",
        "pk": 1,
        "fields": {
            "password": "replace-with-password-hash",
            "last_login": null,
            "is_superuser": true,
            "username": "{{ cookiecutter.django_username }}",
            "first_name": "",
            "last_name": "",
            "email": "{{ cookiecutter.author_email }}",
            "is_staff": true,
            "is_active": true,
            "date_joined": "2024-11-25T11:18:30.859Z",
            "groups": [],
            "user_permissions": []
        }
    }
]
```

(This is unchanged from current TPL — the existing `post_gen_project.py` already
handles the substitution.)

#### 3.3 `TPL:core/urls.py`

Replace the body of `urlpatterns` with:

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views
from core.api import api

urlpatterns = [
    path("", views.app_view, name="home"),
    path("api-access/", views.app_view, name="api-access"),
    path("api/", api.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    # django-rq's queue dashboard. Access is gated by django-rq itself
    # to staff users only, so it's safe to mount at the project root.
    path("django-rq/", include("django_rq.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Verification gate:** Defer to end of Phase 4 (the api import will fail until
`api_keys/` exists).

---

### Phase 4 — `api_keys/` app

This phase creates the Django app holding the load-bearing api-keys feature.

#### 4.1 Create `TPL:api_keys/` directory with these files

```
api_keys/
  __init__.py            # empty
  apps.py
  admin.py
  api.py                 # ninja Router for /api/api-keys/*
  auth.py                # HttpBearer subclass
  models.py              # UserApiKey
  schemas.py             # ApiKeyOut, ApiKeyCreateIn, ApiKeyMintOut
  services.py            # mint(), verify(), revoke() — domain logic
  migrations/
    __init__.py
    0001_initial.py      # generated
  tests/
    __init__.py
    test_models.py
    test_api.py
    test_services.py
    live/
      __init__.py
      test_mint_flow.py
```

#### 4.2 `api_keys/apps.py`

```python
from django.apps import AppConfig


class ApiKeysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api_keys"
```

#### 4.3 `api_keys/models.py`

Port `UserApiKey` from `MFS:queries/models.py` (search for `class UserApiKey`).
Single-model file. Fields: `user FK (PROTECT)`, `name`, `prefix`, `hash`, `created_at`,
`last_used_at`, `revoked_at`. Includes `is_revoked` `@property` and Meta `ordering = ["-created_at"]`.

Keep the soft-delete vocabulary comment block intact — it documents the "visible-but-marked"
revoked_at convention.

#### 4.4 `api_keys/services.py`

Port from `MFS:queries/services/api_keys.py`. Pure-Python, no Django ORM in
function signatures — takes/returns model instances.

Critical: `_PREFIX = "{{ cookiecutter.project_slug }}_live_"` constant at top.

Functions: `mint(user, name) -> MintResult`, `verify(raw_token: str) -> User | None`,
`revoke(api_key: UserApiKey) -> None`. The `MintResult` dataclass has `api_key` and
`raw_token` fields.

#### 4.5 `api_keys/auth.py`

Port from `MFS:queries/auth.py`. Adjust import: `from api_keys import services`
(was: `from queries.services import api_keys`).

#### 4.6 `api_keys/schemas.py`

Port the `ApiKeyOut`, `ApiKeyCreateIn`, `ApiKeyMintOut` classes from
`MFS:queries/schemas.py`. Drop everything else (Query schemas don't apply).

#### 4.7 `api_keys/api.py`

Port from `MFS:queries/api_keys_api.py`. Adjust imports:
- `from api_keys.models import UserApiKey`
- `from api_keys.schemas import ApiKeyCreateIn, ApiKeyMintOut, ApiKeyOut`
- `from api_keys import services as api_keys_services`

Replace `api_keys.mint(...)` → `api_keys_services.mint(...)` etc.

#### 4.8 `api_keys/admin.py`

Port the `UserApiKey` admin section from `MFS:queries/admin.py` only. Skip everything
else (Query admin, GeminiConfig admin, QueryTypeConfig admin). Keep the masked-display
helper and the create-action that mints a key + shows the raw token once.

#### 4.9 `api_keys/tests/test_models.py`, `test_api.py`, `test_services.py`

Port from `MFS:queries/tests/test_api_keys.py` (and split where it makes sense).
Adjust all imports to point at `api_keys.*`.

#### 4.10 `api_keys/tests/live/test_mint_flow.py`

Sample live test demonstrating the full stack. Subclass
`StaticLiveServerWithArtifactsOnErrorTestCase` from `core/tests/utils.py`. Flow:
1. Log in via `/accounts/login/` with seeded user.
2. Navigate to `/api-access/`.
3. Click "Mint Key" button, fill in name, submit.
4. Assert modal appears with raw token starting with `{{ cookiecutter.project_slug }}_live_`.
5. Close modal.
6. Assert new row appears in the keys list.
7. Click "Revoke" on the row.
8. Assert row shows "(revoked)" indicator.

Use `seed.json` test fixture for the user (or factory_boy — match existing TPL
pattern in `core/tests/test_views.py`).

#### 4.11 `TPL:core/api.py` (new file — the dual-auth NinjaAPI mount)

```python
from ninja import NinjaAPI
from ninja.security import django_auth

# Optional: the api_keys app provides bearer-token auth for headless callers.
# If you delete the api_keys app, change `auth=[...]` below to `auth=django_auth`
# and remove the api_keys router mount. See docs/adr/0002-api-keys-session-only.md.
from api_keys.api import router as api_keys_router
from api_keys.auth import ApiKeyBearer

# Both auth methods accepted on every endpoint. ninja tries each in order;
# the first that returns a truthy value wins. Bearer is tried before
# django_auth because ninja's session auth runs a CSRF check *before* it
# even reads the session cookie — so on a bearer-authed write request it
# would 403 before ApiKeyBearer ever ran. With bearer first, token-bound
# requests never invoke the CSRF check. Both paths resolve to the same
# `request.user`.
#
# Exception: the `/api/api-keys/*` router overrides this default to
# `django_auth` only — see ADR-0002.
api = NinjaAPI(auth=[ApiKeyBearer(), django_auth])
api.add_router("/api-keys/", api_keys_router)
```

#### 4.12 Generate the migration

`uv run python manage.py makemigrations api_keys`. Commit the resulting
`api_keys/migrations/0001_initial.py`.

**Verification gate:** `uv run python manage.py check` succeeds. `uv run pytest
api_keys/tests/test_models.py api_keys/tests/test_services.py api_keys/tests/test_api.py`
all pass. Live test deferred to Phase 10.

---

### Phase 5 — Frontend SPA infrastructure

#### 5.1 `TPL:core/frontend/package.json`

Replace with `MFS:core/frontend/package.json` verbatim. Adjust `name` field if
desired (currently `"frontend"`, fine to keep).

#### 5.2 `TPL:core/frontend/vite.config.mjs`

Replace with `MFS:core/frontend/vite.config.mjs` verbatim.

#### 5.3 `TPL:core/frontend/biome.json`

Copy from `MFS:core/frontend/biome.json` verbatim.

#### 5.4 `TPL:core/frontend/tsconfig.json`

Copy from `MFS:core/frontend/tsconfig.json` verbatim.

#### 5.5 `TPL:core/frontend/src/main.tsx`

Port from `MFS:core/frontend/src/main.tsx`. Substitutions:
- Rename `__MFS__` → `__APP__` global (also update the Window interface).
- Default project name: `config.projectName ?? "{{ cookiecutter.project_name }}"`.

#### 5.6 `TPL:core/frontend/src/spa/` directory

Create with:

```
spa/
  App.tsx               # routes only: / and /api-access/
  index.css             # Tailwind v4 + shadcn tokens (light + dark)
  api/
    client.ts           # ported, schema types only for ApiKey*
    csrf.ts             # ported verbatim
    schema.d.ts         # placeholder: `export interface paths {}`; regenerated by make schema
    csrf.test.ts        # ported verbatim
  components/
    ui/                 # 8 shadcn primitives (see 5.7)
    layout/
      app-shell.tsx     # ported; nav stripped to Dashboard + API Access
      logo.tsx          # ported
      icons.tsx         # ported (or trimmed to icons used)
      theme-toggle.tsx  # ported
    api-key-modals.tsx  # ported from MFS — the mint/revoke modals
  lib/
    utils.ts            # ported (cn() helper)
  queries/
    use-api-keys.ts     # ported TanStack hooks
  routes/
    index.tsx           # NEW: Dashboard with one live card + empty-state card
    api-access.tsx      # ported from MFS
```

#### 5.7 `TPL:core/frontend/src/spa/components/ui/` — 8 shadcn primitives

Copy these 8 files from `MFS:core/frontend/src/spa/components/ui/`:
- card.tsx
- dialog.tsx
- button.tsx
- input.tsx
- label.tsx
- badge.tsx
- table.tsx
- skeleton.tsx

Do NOT copy: `select.tsx`, `separator.tsx` (unused in template; dev re-adds via `npx shadcn add` if needed).

#### 5.8 `TPL:core/frontend/src/spa/api/client.ts`

Port from MFS. Strip Query types — only keep ApiKey types:
```typescript
export type ApiKey = components["schemas"]["ApiKeyOut"];
export type ApiKeyCreateIn = components["schemas"]["ApiKeyCreateIn"];
export type ApiKeyMintOut = components["schemas"]["ApiKeyMintOut"];
```
Drop `Query`, `QueryType`, `QueryCreateIn`, `TERMINAL_STATUSES`, `isTerminal`.

#### 5.9 `TPL:core/frontend/src/spa/api/schema.d.ts`

Initial placeholder — committed empty so `tsc` passes on fresh clone:
```typescript
export interface paths {}
export interface components {
  schemas: {
    ApiKeyOut: {
      id: number;
      name: string;
      prefix: string;
      created_at: string;
      last_used_at: string | null;
      revoked_at: string | null;
    };
    ApiKeyCreateIn: { name: string };
    ApiKeyMintOut: { api_key: components["schemas"]["ApiKeyOut"]; raw_token: string };
  };
}
```

(Yes, the placeholder is hand-crafted to match what `openapi-typescript` would
generate from the api_keys ninja API. After first server run, `make schema`
regenerates it from the live `/api/openapi.json`.)

#### 5.10 `TPL:core/frontend/src/spa/queries/use-api-keys.ts`

Port from `MFS:core/frontend/src/spa/queries/use-api-keys.ts` verbatim.

#### 5.11 `TPL:core/frontend/src/spa/components/api-key-modals.tsx`

Port from `MFS:core/frontend/src/spa/components/api-key-modals.tsx` verbatim.

#### 5.12 `TPL:core/frontend/src/spa/components/layout/app-shell.tsx`

Port from MFS but strip the sidebar nav to two items:
```tsx
const navItems = [
  { label: "Dashboard", path: "/", icon: HomeIcon },
  { label: "API Access", path: "/api-access", icon: KeyIcon },
];
```

Keep theme-toggle in user menu, keep username display, keep logout button.

#### 5.13 `TPL:core/frontend/src/spa/components/layout/{logo,icons,theme-toggle}.tsx`

Port verbatim. `icons.tsx` may be trimmed if some icons are queries-specific —
keep at minimum: HomeIcon, KeyIcon (or whatever the app-shell uses), Sun/Moon icons.

#### 5.14 `TPL:core/frontend/src/spa/index.css`

Port from `MFS:core/frontend/src/spa/index.css` verbatim. This includes the
Tailwind v4 import, shadcn light + dark theme variables, and font setup.

#### 5.15 `TPL:core/frontend/src/spa/App.tsx`

Replace MFS routes with the template's two routes:
```tsx
import { Route, Routes } from "react-router";
import { AppShell } from "@/components/layout/app-shell";
import { ApiAccessRoute } from "@/routes/api-access";
import { DashboardRoute } from "@/routes/index";

interface AppProps {
  projectName: string;
  username?: string;
}

export function App({ projectName, username }: AppProps) {
  return (
    <AppShell projectName={projectName} username={username}>
      <Routes>
        <Route path="/" element={<DashboardRoute />} />
        <Route path="/api-access" element={<ApiAccessRoute />} />
      </Routes>
    </AppShell>
  );
}
```

#### 5.16 `TPL:core/frontend/src/spa/lib/utils.ts`

Port verbatim from MFS (the `cn()` clsx + tailwind-merge helper).

**Verification gate:** `cd core/frontend && npm install && npm run build` succeeds.
`npm run lint` passes. `npx tsc --noEmit` passes.

---

### Phase 6 — Routes: Dashboard + API Access

#### 6.1 `TPL:core/frontend/src/spa/routes/api-access.tsx`

Port from `MFS:core/frontend/src/spa/routes/api-access.tsx` verbatim. This is the
list/mint/revoke UI for api keys. Uses `use-api-keys.ts` hooks and
`api-key-modals.tsx` for the mint/revoke modals.

#### 6.2 `TPL:core/frontend/src/spa/routes/index.tsx` (NEW — Dashboard, Option α)

```tsx
/**
 * Dashboard — / route.
 *
 * Day-1 shape: two inline cards (no abstractions). When you add your first
 * domain model, duplicate the API Keys card pattern below. When the third
 * card lands and you're sick of the duplication, *then* extract <StatCard>.
 */
import { useApiKeys } from "@/queries/use-api-keys";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardRoute() {
  const { data, isLoading } = useApiKeys();
  const activeCount = data?.filter((k) => !k.revoked_at).length ?? 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardDescription>API Keys</CardDescription>
          <CardTitle className="text-3xl">
            {isLoading ? <Skeleton className="h-9 w-12" /> : activeCount}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Active keys for headless API access.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Recent Activity</CardDescription>
          <CardTitle className="text-base font-normal text-muted-foreground">
            No recent activity yet.
          </CardTitle>
        </CardHeader>
      </Card>
    </div>
  );
}
```

#### 6.3 `TPL:core/views.py` (replace existing)

Single SPA mount view, ported from `MFS:queries/views.py` (renamed `app_view`):

```python
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@login_required
@ensure_csrf_cookie
def app_view(request: HttpRequest, **kwargs) -> HttpResponse:
    """Render the SPA mount template.

    A thin Django shell with `<div id="app">` plus the django-vite asset
    tag for `main.tsx`. `@ensure_csrf_cookie` guarantees the `csrftoken`
    cookie is set on first paint so SPA write requests can echo it via
    `X-CSRFToken`.

    Same view answers both `/` and `/api-access/` — react-router reads
    the path off `window.location` after mount; server-side routing only
    needs to match these two patterns to support hard reloads.
    """
    return render(
        request,
        "core/app.html",
        {
            "spa_config": {
                "projectName": settings.PROJECT_NAME,
                "username": request.user.username
                if request.user.is_authenticated
                else "",
            },
            "project_name": settings.PROJECT_NAME,
        },
    )
```

#### 6.4 `TPL:core/templates/core/app.html` (NEW)

Port from `MFS:queries/templates/queries/app.html`. Substitutions:
- `mfs-config` → `app-config`
- `__MFS__` → `__APP__`

```html
{% extends "_base.html" %}
{% load django_vite %}

{% block title %}{{ project_name }}{% endblock title %}

{% block extra_head %}
  {{ block.super }}
  {% vite_react_refresh %}
  {% vite_asset "main.tsx" %}
{% endblock extra_head %}

{% block body %}
  {{ spa_config|json_script:"app-config" }}
  <script>
    window.__APP__ = JSON.parse(document.getElementById("app-config").textContent);
  </script>
  <div id="app"></div>
{% endblock body %}
```

#### 6.5 `TPL:core/templates/_base.html`

Replace with `MFS:core/templates/_base.html` verbatim. Drop Alpine.js,
add `{% vite_hmr_client %}`, use Geist + Inter fonts.

**Verification gate:** Defer to Phase 12 final smoke. After Phase 6, the SPA should
*build* and `manage.py runserver` should serve `/` (will require login).

---

### Phase 7 — Dockerfile, compose, scripts (Pattern M)

#### 7.1 `TPL:Dockerfile`

Replace with `MFS:Dockerfile` verbatim. **Key:** no `EXPOSE`, no `CMD` at the end.
The image is a multi-process bundle; the orchestrator picks the command.

#### 7.2 `TPL:web.sh`

Already exists in TPL — keep as-is (matches MFS).

#### 7.3 `TPL:worker.sh` (NEW)

Copy from `MFS:worker.sh` verbatim.

#### 7.4 `TPL:release.sh`

Already exists in TPL — keep as-is (matches MFS).

#### 7.5 `TPL:docker-compose.yml`

Replace with the multi-process shape:

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: {{ cookiecutter.project_slug }}_db
      POSTGRES_USER: {{ cookiecutter.project_slug }}_user
      POSTGRES_PASSWORD: {{ cookiecutter.project_slug }}_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U {{ cookiecutter.project_slug }}_user -d {{ cookiecutter.project_slug }}_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: ./web.sh
    restart: always
    environment:
      DATABASE_URL: postgresql://{{ cookiecutter.project_slug }}_user:{{ cookiecutter.project_slug }}_password@db:5432/{{ cookiecutter.project_slug }}_db
      REDIS_URL: redis://redis:6379/0
      DEBUG: "False"
      SECRET_KEY: development-secret-key-please-change-in-production
      ALLOWED_HOSTS: localhost,127.0.0.1
    ports:
      - "8000:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

  worker:
    build: .
    command: ./worker.sh
    restart: always
    environment:
      DATABASE_URL: postgresql://{{ cookiecutter.project_slug }}_user:{{ cookiecutter.project_slug }}_password@db:5432/{{ cookiecutter.project_slug }}_db
      REDIS_URL: redis://redis:6379/0
      DEBUG: "False"
      SECRET_KEY: development-secret-key-please-change-in-production
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }

volumes:
  postgres_data:
```

#### 7.6 `TPL:fabfile.py`

Update the `migrate` task to use `release.sh`:

```python
@task
def release(context):
    """Run release tasks (migrations etc.) on the Mac mini server."""
    with connection.cd(TARGET_DIR):
        connection.run("docker compose run --rm web ./release.sh")
```

(Replace the `migrate` task; same one-liner pattern.)

**Verification gate:** Build verification deferred to Phase 12 — manual
`docker compose build` should succeed once the rest of the template is in place.

---

### Phase 8 — Appliku skill + appliku.yml

#### 8.1 `TPL:.claude/skills/appliku/`

Copy the entire directory `MFS:.claude/skills/appliku/` (including SKILL.md,
README.md, docs/) verbatim into `TPL:.claude/skills/appliku/`.

#### 8.2 `TPL:appliku.yml` (NEW)

Copy from `MFS:appliku.yml` verbatim. No substitutions needed — references
generic `db`/`redis` database names internal to Appliku.

**Verification gate:** Inspect `TPL:.claude/skills/appliku/SKILL.md` exists.

---

### Phase 9 — Makefile + pre-commit

#### 9.1 `TPL:Makefile`

Replace with `MFS:Makefile` verbatim. Substitutions:
- `manufacturer-summarizer` → `{{ cookiecutter.project_slug }}` (in db.* targets)

Verify all targets present:
- test, test.live.watch, lint, format, precommit
- frontend.install, frontend.build, frontend.dev
- db.recreate, db.initialize, db.snapshot, db.restore
- (add) `schema: cd core/frontend && npm run schema`

#### 9.2 `TPL:.pre-commit-config.yaml`

Replace with `MFS:.pre-commit-config.yaml` verbatim. This includes the 4 local
hooks: tach, pip-audit (manual stage), biome-check, tsc-typecheck.

#### 9.3 `TPL:scripts/pip_audit_fixable.py`

Already present — verify identical to MFS version (they are; if drift, take MFS).

**Verification gate:** `make lint` passes. `make format` makes no changes.
`make precommit` passes (manual stage too).

---

### Phase 10 — Live tests

#### 10.1 `TPL:core/tests/utils.py`

Add MFS's HEADLESS/HEADED/SLOWMO_MS env support to `setUpClass`. Diff against
`MFS:core/tests/utils.py`:

```python
# Replace the cls._browser = launch line with:
headless = os.environ.get("HEADLESS", "1") not in ("0", "false", "False")
if os.environ.get("HEADED") in ("1", "true", "True"):
    headless = False
slow_mo_ms = int(os.environ.get("SLOWMO_MS", "0"))
cls._playwright = sync_playwright().start()
cls._browser = cls._playwright.chromium.launch(
    headless=headless, slow_mo=slow_mo_ms
)
```

#### 10.2 `TPL:api_keys/tests/live/test_mint_flow.py`

Already specified in 4.10. This is the only live test shipping with the template
(beyond what `core/tests/test_views.py` already does).

#### 10.3 `TPL:core/tests/test_views.py`

Update existing tests for new home view: it requires login + redirects unauth
users to `/accounts/login/`. Single integration test:
- `test_home_redirects_anonymous` — GET `/` → 302 to login
- `test_home_renders_for_authenticated_user` — login as seeded user, GET `/`, assert 200 and SPA mount markup present

#### 10.4 `ROOT:Makefile` (the template's own smoke pipeline)

Append a step in the `2. Verification:` block, after the existing `make precommit` step:
```make
$(call run_step,uv run pytest core/tests/live api_keys/tests/live,passed)
```

**Verification gate:** From `ROOT:`, `make test` runs end-to-end with the new
live-test step passing.

---

### Phase 11 — Docs (ADRs + CONTEXT + CLAUDE + README)

#### 11.1 `TPL:docs/agents/`

Already exists — copy any missing files from `MFS:docs/agents/` (issue-tracker.md,
triage-labels.md, domain.md). Verify contents match TPL conventions; if MFS has
project-specific URLs (e.g. `sspross/manufacturer-summarizer`), substitute
`sspross/{{ cookiecutter.project_slug }}` or remove the project-specific reference.

#### 11.2 `TPL:docs/adr/` — write 4 ADRs

Create:
- `0001-react-spa.md` — adapted from `MFS:docs/adr/0003-react-spa.md`. Justifies
  Tailwind v4 + Vite + React + TanStack + shadcn over server-rendered alternatives.
- `0002-api-keys-session-only.md` — adapted from `MFS:docs/adr/0004-key-management-session-only.md`.
  Justifies the dual-auth pattern + the api_keys-router exception.
- `0003-async-by-default.md` — NEW. Justifies shipping django_rq + worker.sh +
  Redis service in compose, even though no jobs ship in the template (only
  infrastructure). Reasoning: most projects need async work eventually; retrofit
  is more painful than upfront cost.
- `0004-dual-deployment.md` — NEW. Justifies shipping both `appliku.yml`
  (canonical) and `docker-compose.yml` (self-host). README leads with Appliku.

Also create `TPL:docs/adr/README.md` explaining the ADR convention (one short
paragraph: "Architecture Decision Records — chronological, immutable; a new ADR
supersedes an old one rather than editing it.").

#### 11.3 `TPL:CONTEXT.md`

Adapt from `MFS:CONTEXT.md`. Keep:
- Glossary section: only the **API Key** entry, the **Soft-delete vocabulary**
  entry (both `revoked_at` and `deleted_at` halves; for `deleted_at` add a note
  "no model in the template uses this yet — adopt when you need 'hide from users'
  semantics.")
- Surfaces section, adapted to template's actual routes:
  - HTML pages: `/`, `/api-access/`, `/accounts/login/`, `/accounts/logout/`, `/admin/`, `/django-rq/`
  - API endpoints: `GET /api/api-keys/`, `POST /api/api-keys/`, `POST /api/api-keys/{id}/revoke/`
  - Dual-auth explanation block
  - App layout (the `core/`, `api_keys/`, `core/frontend/src/spa/` trees)
  - Frontend & API contract section (load-bearing — describes openapi-typescript flow)

Drop everything else (Query, QueryType, Gemini, Web search grounding, Manufacturer non-entity).

#### 11.4 `TPL:CLAUDE.md`

Adapt from `MFS:CLAUDE.md`. Substitutions:
- `manufacturer-summarizer` → `{{ cookiecutter.project_slug }}`
- `sspross/manufacturer-summarizer` (GitHub coords) → `sspross/{{ cookiecutter.project_slug }}`

Keep the structure exactly: Guardrails section (make test/lint/format/precommit),
Agent skills section (Issue tracker, Triage labels, Domain docs).

#### 11.5 `TPL:README.md`

Replace with a clean rewrite (the current TPL one is messy per the user's words).
Sections:

```markdown
# {{ cookiecutter.project_name }}

## Development

### Requirements

- Local Redis Server
- (Optional) Local Postgres Server, if SQLite is not enough
- `uv` (https://docs.astral.sh/uv/)

### Setup

- `cp .env.example .env` (already done by post_gen_project.py)
- `uv sync`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate` (Postgres only — skip if using SQLite)
- `make db.initialize`
- `make frontend.install`

### Work

- Start frontend watcher first: `make frontend.dev`
- `uv run python manage.py runserver`
- Log in at http://localhost:8000/accounts/login/ with `{{ cookiecutter.django_username }}` / `{{ cookiecutter.django_password }}`

### Tests

- `make test` — pytest suite
- `make test.live.watch` — live Playwright tests, headed + slowmo (debugging)
- `make precommit` — full pre-commit pipeline

### Frontend type generation

After adding/changing ninja API endpoints, regenerate the SPA's typed schema:
- `uv run python manage.py runserver` (in another terminal)
- `make schema`

## Deployment

This template ships configurations for two deployment paths. Pick one.

### Appliku (canonical)

`appliku.yml` is the single source of truth. Push to `main`; Appliku redeploys
and runs `release.sh` automatically.

First-time setup:
1. Push the repo to GitHub.
2. Create the application in Appliku, pointed at the repo.
3. Appliku reads `appliku.yml` and provisions the web/worker/release processes,
   Postgres database, and Redis instance.
4. Set `SECRET_KEY` in Appliku's environment variables (one-time):
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`
5. Add a domain in Appliku; `ALLOWED_HOSTS` is auto-populated from `from_domains: true`.
6. Deploy.

See `.claude/skills/appliku/SKILL.md` for the full Appliku CLI/SDK reference.

### Docker Compose (self-host, e.g. Mac mini via Tailscale)

For a Mac mini hosted behind Caddy + Tailscale:

1. `uv add fabric` (if not already)
2. Adjust `TARGET_SERVER` and `TARGET_DIR` in `fabfile.py`.
3. Clone the repo to `TARGET_DIR` on the host.
4. Pick an unused port in `docker-compose.yml`'s `ports` mapping.
5. Add your hostname to `ALLOWED_HOSTS` in `docker-compose.yml`.
6. Add a Caddy proxy rule.
7. Deploy: `uv run fab deploy && uv run fab release`.
```

**Verification gate:** README scans cleanly. `make test` from `ROOT:` still passes
(adds the new live-test step from Phase 10).

---

### Phase 12 — Final verification

Run the full template smoke pipeline from `ROOT:`:

```bash
make test
```

This generates a fresh project from the template, installs deps, applies migrations,
loads the dumpdata seed user, builds the frontend, runs pytest (incl. live tests),
runs lint, runs format, runs precommit, smoke-tests `make frontend.dev`, smoke-tests
`runserver`. **All steps must be green.**

If anything fails:
1. **Do not skip the failing step.** Fix the underlying cause.
2. The failing step's output is shown verbatim — read it.
3. If a live test fails, check `test_artifacts/` in the generated project's tmp dir
   (the smoke pipeline leaves it before cleanup).

Then, manually verify the user-facing happy path:

```bash
cd /tmp && rm -rf test-gen && mkdir test-gen && cd test-gen
uv run --with cookiecutter --with django python -m cookiecutter \
    /Users/sspross/projects/cookiecutter-django --no-input
cd django-website
uv sync
make db.initialize
make frontend.install
make frontend.dev &  # background
uv run python manage.py runserver &  # background
# In a browser:
#   - Visit http://localhost:8000/  → bounces to /accounts/login/
#   - Log in with sspross / bondens (cookiecutter defaults)
#   - See dashboard with "API Keys: 0" and "Recent Activity: empty"
#   - Toggle dark/light theme — works
#   - Navigate to /api-access/
#   - Click "Mint Key", name it, submit
#   - See modal with raw token starting with "django_website_live_"
#   - Close modal, see new row
#   - Return to dashboard, see "API Keys: 1"
#   - Click revoke on the row, see "(revoked)" indicator
```

If any step in this manual happy-path fails, fix before considering the refactor done.

---

## 5. Commit plan

Create one commit per phase, with a descriptive subject like:
- `phase 0: branch + baseline`
- `phase 1: delete obsolete content`
- `phase 2: dependencies + settings`
- `phase 3: auth + login`
- `phase 4: api_keys app`
- `phase 5: frontend SPA infrastructure`
- `phase 6: dashboard + api-access routes`
- `phase 7: Dockerfile + compose multi-process pattern`
- `phase 8: appliku skill + appliku.yml`
- `phase 9: Makefile + pre-commit`
- `phase 10: live tests + cookiecutter smoke pipeline update`
- `phase 11: docs (4 ADRs, CONTEXT, CLAUDE, README)`
- `phase 12: final verification`

Do not squash. The phase-by-phase log is itself documentation of how the template
was assembled.

After all phases: open a PR to `main`. The PR description should:
- Reference the manufacturer-summarizer SHA `54cbf25` as the source of truth
- List the 16 locked decisions from section 3
- Include the manual happy-path verification log

---

## 6. Things you should NOT do

These are anti-patterns this refactor explicitly avoids. If you find yourself
about to do one, stop and re-read the relevant locked decision.

- **Add new cookiecutter questions** (locked decision #1).
- **Make any feature optional via post_gen_project.py file deletion** (locked #1).
- **Ship a fake demo CRUD app** (locked #2 — api_keys IS the demo).
- **Couple api_keys to core in any way that makes deletion require >3 file edits**
  (locked #3).
- **Use a sidebar with placeholder items** (locked #4 — nav has 2 real items).
- **Make the dashboard show empty placeholder cards** (locked #6 — both cards real).
- **Bring over manufacturer-specific ADRs as-is** (locked #7 — adapt or skip).
- **Keep `EXPOSE`/`CMD` in the Dockerfile** (locked #8).
- **Ship the full Manufacturer's CLAUDE.md content with `manufacturer-summarizer`
  hardcoded** (substitute with cookiecutter variables).
- **Write a sync workflow / shared package between this template and manufacturer**
  (locked #16 — Workflow A, no automated sync).
- **Re-litigate any locked decision in code comments or commit messages.** If a
  decision turns out to be wrong, raise it with the user explicitly.

---

## 7. If you get stuck

If a step fails in a way the spec doesn't cover, or a constraint conflicts with a
locked decision, **stop and ask the user**. Do not improvise on locked decisions.
Improvising is acceptable only on:
- Naming of internal helpers and components
- Whitespace, formatting choices ruff/biome handle anyway
- Test factory scaffolding
- Inline code comments (write fewer, not more)

For everything else: ask.
