# 0005 — Module boundaries enforced by tach; type-hint imports allowed across them

## Context

The template ships `tach` and a `tach.toml` that declares an explicit dependency
graph between Django apps. `tach check` (wired into `make lint` / pre-commit)
fails the build on any import that crosses a boundary the graph doesn't permit.
The baseline graph is one arrow: `core → api_keys` (`core` may import
`api_keys`; `api_keys` may import nothing). As the project grows, each
team-added `[[modules]]` block draws another boundary.

Two facts make `tach` confusing on first contact:

1. A forbidden import and a type annotation look identical in source —
   `from other_app.models import Thing` — but they are not the same thing. The
   first is a runtime dependency; the second, under a guard, is just a name used
   to describe a value. Developers hit a `tach check` failure on a model import
   and conclude "I can't reference that type at all," then either reach for
   `Any`, duplicate the type, or invert a dependency to dodge the check.
2. `tach` can enforce boundaries at **sub-package** granularity — e.g.
   `app.models` (the ORM) as a separate module from `app.services` (the write
   seam), so other apps must go *through* `services` and never touch `models`
   directly. There the "may I name a `models` type?" question is sharper still,
   because the layering rule deliberately forbids the runtime import while the
   type is exactly what you want to annotate.

## Decision

**Boundaries are a runtime-arrow rule, and `tach.toml` sets
`ignore_type_checking_imports = true` so that type-hint-only imports may cross a
boundary the runtime arrow forbids.**

- **A `TYPE_CHECKING` import of another module's type — including a `models`
  type — is allowed, even when the runtime import is forbidden.** Pair it with
  `from __future__ import annotations`:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from other_app.models import Thing  # for type hints only

  def handle(thing: Thing) -> None: ...
  ```

  Naming a model type in an annotation touches no ORM and creates no runtime
  dependency, so it does not violate the boundary. This is the point most people
  miss: **the boundary blocks runtime imports, not the ability to type-hint.**

- **A `TYPE_CHECKING` import may only travel the SAME direction as the runtime
  arrow, never against it.** In the baseline graph the arrow is `core →
  api_keys`, so `core` naming an `api_keys` type is honest. The forbidden move is
  the mirror image — `api_keys` reaching for a `core` type under the guard — which
  would hide an inverted `api_keys → core` dependency behind `TYPE_CHECKING` and
  lie about the real direction. The rule: **a type-hint import points the same way
  the runtime arrow already points (or would point); it never inverts a
  boundary.**

- **Sub-package granularity expresses layering rules.** When an app needs a hard
  "write through `services`, never touch the ORM directly" seam, declare
  `app.models` and `app.services` as distinct `[[modules]]`: `app.models` depends
  on nothing, `app.services` may depend on `app.models`, and other apps depend on
  `app.services` only. A direct `from app.models import …` from outside then fails
  `tach check`, while a `TYPE_CHECKING` import of an `app.models` type for an
  annotation stays legal (same-direction, no ORM at runtime). Add the sub-package
  blocks only once the packages exist — pointing `tach.toml` at absent paths
  breaks `tach check`.

- **A neutral top-level `types`/`contracts` module is not the answer to a
  boundary-crossing type hint.** It is a whole module for what is usually a
  single shared type. Reach for it when a genuinely shared contract object
  appears, not to dodge a type hint the guard already allows.

- **Tests, migrations, management commands, and `manage.py` are exempt**
  (`tach.toml` excludes them). A management command is a composition root that may
  wire anything; the seam is enforced where it matters — services, runners, and
  the app-to-app edges — not on glue.

## Consequences

Positive:

- The boundary is mechanical, not convention — `tach check` fails on a forbidden
  runtime import, so an inverted dependency can't land silently.
- Full type coverage survives the boundary: you annotate with the real type, not
  `Any` or a duplicate, because type-hint imports cross freely under the guard.
- Layering ("go through `services`") becomes enforceable at sub-package
  granularity when a write seam needs it, without coloring the rest of the graph.

Negative:

- The `from other_app.models import X` failure reads as "you can't use this
  type," which is wrong; this ADR (and the `tach.toml` header comment) is the
  answer, and without it someone "fixes" the boundary instead of guarding the
  import.
- `ignore_type_checking_imports = true` trusts that guarded imports are honest
  about direction. The same-direction rule is a convention `tach` can't check —
  review catches an inverted guard, not the tool.
