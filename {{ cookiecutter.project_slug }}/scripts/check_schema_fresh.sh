#!/usr/bin/env bash
#
# Fail if the committed API client (schema.d.ts) is stale relative to the ninja
# schema it is generated from, keeping `schemas.py` the single source of truth.
#
# Compares a fresh regeneration against a SNAPSHOT of the committed file, not
# against `git diff` — a diff check false-fails whenever schema.d.ts has
# legitimate uncommitted edits. The snapshot is restored on success and on
# failure alike, so this never leaves the working tree modified.
#
# Exactness depends on biome.json excluding schema.d.ts from formatting, so the
# committed file stays byte-identical to raw openapi-typescript output. Keep
# that per-file override.
set -euo pipefail

SCHEMA_FILE="core/frontend/src/spa/api/schema.d.ts"
OPENAPI_JSON="core/frontend/.openapi.json"

snapshot="$(mktemp)"
cp "$SCHEMA_FILE" "$snapshot"
cleanup() {
  mv "$snapshot" "$SCHEMA_FILE"
  rm -f "$OPENAPI_JSON"
}
trap cleanup EXIT

make schema

if ! diff -u "$snapshot" "$SCHEMA_FILE"; then
  echo >&2
  echo "ERROR: $SCHEMA_FILE is stale. Run 'make schema' and commit the result." >&2
  exit 1
fi

echo "schema.d.ts is fresh."
