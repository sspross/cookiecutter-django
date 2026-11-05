#!/usr/bin/env bash
set -euo pipefail

# Needs the schema.d.ts override in biome.json: the file must stay byte-identical
# to raw openapi-typescript output.
SCHEMA_FILE="core/frontend/src/spa/api/schema.d.ts"
OPENAPI_JSON="core/frontend/.openapi.json"

# A snapshot, because `git diff` false-fails when schema.d.ts has uncommitted edits.
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
