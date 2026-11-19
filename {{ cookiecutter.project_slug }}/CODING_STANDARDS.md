# Coding standards

Review rules that no linter enforces. The mechanical ones live in
`.pre-commit-config.yaml`, `pyproject.toml` (ruff), `biome.json`,
`tach.toml`, `ast-grep/rules/` and `core/tests/test_conventions.py`. The
conventions in `CLAUDE.md` apply too.

## API schemas

The ninja `Schema` classes in `*/schemas.py` are Python, written by hand. They
are the source: `make schema` generates the TS types (`schema.d.ts`) from them,
and ninja builds the `/api/docs` page from them (see `docs/ARCHITECTURE.md`
"Frontend & API contract"). Keep both rich:

- **Enum-ish fields use the model's `TextChoices` class as their type**
  (`status: Invoice.Status`). The values then have one source, and the
  generated TS is a union of the values. Use `Literal[...]` only where the API
  exposes fewer values than the model.
- **Document fields with `Field(description=...)`.** The description reaches
  OpenAPI, so it flows into both the generated TS (`@description` JSDoc on
  hover) and the `/api/docs` page. A docstring on the `Schema` or endpoint
  propagates the same way.
- **Optional artifact:** a Pydantic field with a default (`x: T | None = None`)
  renders as `x?:` *optional* in the generated TS even though the server always
  serializes it. Either coalesce at the use site or accept the widened type.
  Keep the default: dropping it to "fix" the type changes the API contract.

## Boot data

What the SPA needs at boot has two channels and no third:

- **A build-time constant is server-rendered** as a `data-*` attribute on the
  `#app` mount node. No inline `<script>`, no `window` global, no fallback
  literal in TS.
- **Per-user or dynamic data is a field on `MeOut`**, fetched from `/api/me`.
  It stays inside the OpenAPI contract, so a field added in Python and read in
  TS is typed end to end. An untyped blob drifts with nothing to catch it.

## Naming

- **The soft-delete name carries the visibility.** `revoked_at` /
  `is_revoked` keeps the row listed with a "Revoked" badge (`UserApiKey`, so
  the owner sees the audit trail). `deleted_at` / `is_deleted` hides the row
  from every user-facing read; only operators see it. No model uses
  `deleted_at` yet.

## Testing

No JS unit tests. Frontend correctness is exercised end-to-end by the Python
**live journey**, `core/tests/live/test_journey.py`. A live test is a
plain pytest function taking pytest-django's `live_server` and
pytest-playwright's `page` fixtures, no bespoke base class. It drives the real
SPA against a real Django server.

- **Assert in the journey only what a browser is needed for**: real rendering,
  focus, keyboard, viewport, static serving. A live test drives a browser,
  which costs far more than a `client` test.
- **Web-first assertions.** Use Playwright's auto-retrying `expect(locator)`
  (e.g. `to_be_visible()`, `to_contain_text()`, `to_have_count()`) rather than
  bare instant reads. The retry absorbs animation and transition timing.
- **Artifacts on failure** are captured natively by pytest-playwright into
  `test-results/` (a trace + screenshot; configured via the `--tracing` /
  `--screenshot` addopts in `pyproject.toml`). Inspect a trace with
  `uv run playwright show-trace test-results/<…>/trace.zip`.
- **Dev knobs** are Playwright-native: `uv run pytest --headed --slowmo 500`
  (wrapped by `make test.live.watch`), or `PWDEBUG=1` for the inspector.
- **Tests run in random order.** pytest prints `Using --randomly-seed=<seed>`;
  `uv run pytest --randomly-seed=<seed>` replays that order. With `-n 4` the
  split across workers depends on timing, so a failure may need a few runs with
  the same seed to come back. Fix an order-dependent test, do not pin it.
- **A warning fails the run.** Fix it. A third-party warning that cannot be
  fixed gets a narrow ignore under `filterwarnings` with a comment saying why.

Static correctness on the TS side is covered by `tsc --noEmit` and biome (both
run in pre-commit).

A unit test that cannot be expressed as a live test may bring vitest in, with
the reason stated in its PR.
