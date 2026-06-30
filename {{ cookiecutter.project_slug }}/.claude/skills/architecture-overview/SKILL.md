---
name: architecture-overview
description: Generate a self-contained HTML architecture overview that onboards a new developer to what the software does and how its core domain logic works. Use when the user wants an architecture artifact, an onboarding document, an "explain the app" deliverable, or asks to describe the system to a new developer. Focuses on the primary use case and domain logic, not frontend or API mechanics.
user-invocable: true
---

# Architecture Overview

Produce one self-contained HTML file that explains, to a developer on their first
day, **what this software achieves and how the core logic works**.

## Scope guard — read this first

In scope: the primary use case, the domain concepts, the main end-to-end flow,
and the few decisions that shape that logic.

Out of scope: frontend rendering, component trees, CSS/build tooling, HTTP/auth
wiring, endpoint-by-endpoint API reference — mention a surface only when a new
dev cannot follow the core flow without it. Stay conceptual; minimise file paths.

## Template baseline (what to subtract)

This skill ships in a project generated from `sspross/cookiecutter-django`. The
inventory below is what a fresh bake contains — treat it as a **prior, not a
verdict**. In the artifact, collapse it into a single one-line "Template plumbing
— not the point" callout and bias the whole narrative toward what the team built
or changed on top. `CONTEXT.md` is the arbiter: if the glossary promotes a
baseline item to a product concept, treat it as product.

Apps the template ships:

- `core` — Django shell that mounts the React SPA.
- `api_keys` — the **tracer-bullet example feature** (mint/verify/revoke of
  `UserApiKey`). A worked demo, not a product. Only treat as product if the
  glossary still frames the system around API keys or the team has extended its
  `services.py`/`jobs.py` with non-template concerns.

Plumbing the template ships unchanged: django-ninja with dual auth (session+CSRF
and bearer), including a `GET /api/me` whoami (`core/schemas.py`); RQ + Redis
async infrastructure with no jobs by default; React SPA on django-vite +
shadcn/Tailwind + TanStack Query, whose boot payload is split (build constants
server-rendered via `data-project-name`, per-user data fetched from the typed
`/api/me` with `useMe()` — no `window.__APP__`); dual deployment (Appliku and
docker-compose); the live-test harness (function-style on pytest-django
`live_server` + pytest-playwright `page`, artifacts via pyproject addopts — no
base class); `tach.toml` declaring module boundaries; `make
test`/`lint`/`format`/`precommit` guardrails; the `appliku` agent skill and the
`docs/agents/` docs; ADRs 0001 react-spa, 0002 api-keys-session-only, 0003
async-by-default, 0004 dual-deployment, 0005 tach-boundaries, 0006
boot-data-typed.

## Workflow

1. **Read the domain docs before any code.** Follow `docs/agents/domain.md`:
   read `CONTEXT.md` (or `CONTEXT-MAP.md` and each `CONTEXT.md` it points at),
   then `docs/adr/`, then `tach.toml` — every `[[modules]]` block past the
   baseline (`core` → `api_keys`) is by construction a team-added module.
   Proceed silently if any are absent.
2. **Then skim code only to fill gaps** in the core logic the docs do not make
   concrete; do not inventory the codebase. Anything matching the Template
   baseline above is scaffolding — collapse it into the one-line plumbing
   callout. `*/tests/live/` is the cleanest signal of "real software": the
   template ships the harness with zero tests, so anything there is the team
   exercising a domain flow worth corroborating against.
3. **Name the primary use case** in one sentence: the main job the software does
   for its user. Everything else in the document supports this sentence.
4. **Trace the main flow** end to end — the path from "user wants X" to "X has
   happened" through the domain. Note the key decision points and state changes.
5. **Confirm the framing with the user before drafting.** Show three things in a
   tight block: (a) the one-sentence primary use case you intend to commit to,
   (b) the section list you plan to produce, (c) any judgement calls worth
   flagging — e.g. promoting/demoting `api_keys` between scaffolding and product,
   skipping a half-built feature, or surfacing a CONTEXT.md/ADR contradiction.
   Use `AskUserQuestion` with the proposed framing as the recommended option.
   Adjust based on the answer; do not proceed to drafting until confirmed.
6. **Draft the sections** (see below). Use the exact terms from the `CONTEXT.md`
   glossary; never drift to synonyms it avoids. If the document would contradict
   an ADR, surface it explicitly rather than silently overriding it.
7. **Build the HTML**: read `.claude/skills/architecture-overview/assets/template.html`
   and replace its sentinels:
   - `%%PROJECT_NAME%%` — the project name
   - `%%GENERATED_ON%%` — today's date, `YYYY-MM-DD`
   - `%%TOC%%` — one `<li><a href="#id">Title</a></li>` per section
   - `%%CONTENT%%` — the `<section id="...">` blocks
8. **Write** the result to `docs/architecture-overview.html`.
9. **Report**: tell the user the path, that opening it in any browser renders the
   diagrams, and that it is a snapshot to regenerate when the domain model changes.

## Sections to produce

Each is a `<section id="...">` with an `<h2>`. Keep the whole document readable in
one sitting (aim for well under 1500 words of prose plus diagrams).

1. **What this software is for** — the primary use case in 1–2 short paragraphs.
   The problem it solves and for whom. No architecture yet.
2. **Core concepts** — the handful of domain nouns a new dev must know, defined in
   the glossary's words. A short definition list, not the full glossary.
3. **How the main flow works** — prose walkthrough of the primary end-to-end flow,
   plus **one Mermaid diagram** of that flow (required). Add a second diagram only
   if a distinct secondary flow is essential to the core purpose.
4. **Key decisions that shape the logic** — 2–4 ADR-derived bullets, each one line
   on *why* the logic is the way it is. Link the ADR by number, not by retelling it.
5. **Where the core logic lives** — a short paragraph naming the team-built
   modules a new dev should open first (the only place paths appear), plus a
   second Mermaid diagram: render `tach.toml`'s team-added `[[modules]]` as a
   `flowchart` with each module's `depends_on` as arrows. Skip the diagram if
   `tach.toml` contains only the baseline. End with one sentence naming the
   template plumbing (per Template baseline) so the new dev knows what to *not*
   spend time on.

## Mermaid guidance

Put diagrams in `<div class="mermaid">` blocks; the template handles theming.
Prefer `flowchart` or `sequenceDiagram` for the main flow; label nodes with
domain terms and use `[rectangle]`/`(rounded)` shapes and `-->|label|` edges.
Cap each diagram at roughly a dozen nodes.

## Output

`docs/architecture-overview.html` — single file, no build step, no external
assets except the Mermaid module loaded from a CDN at view time.
