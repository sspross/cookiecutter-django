# Module boundaries are a runtime rule; type-hint imports may cross them

`tach check` enforces the dependency graph between the Django apps.
`tach.toml` sets `ignore_type_checking_imports = true`, so an import under
`TYPE_CHECKING` may cross a boundary the runtime graph forbids. Naming a type
in an annotation creates no runtime dependency. Without the flag a boundary
failure reads as "I cannot use this type at all", and people reach for `Any`,
duplicate the type, invert a dependency or add a neutral `types` module for a
single shared type.

A guarded import has to point the way the runtime arrow points, or would
point, and never against it: otherwise it hides an inverted dependency. `tach`
cannot check that direction, so review does.

How to declare a boundary: `docs/ARCHITECTURE.md` "Module boundaries".
