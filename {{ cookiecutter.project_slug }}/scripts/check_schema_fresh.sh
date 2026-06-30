#!/usr/bin/env bash
#
# Fail if the committed generated API client (schema.d.ts) is stale relative
# to the ninja schema it is generated from. This is the guard that keeps
# `schemas.py` the single source of truth: edit a Schema, forget `make
# schema`, and `make precommit` catches it instead of the client silently
# drifting (as it did in the badispass project — see issue #31).
#
# It compares a fresh regeneration against a SNAPSHOT of the committed file,
# NOT against `git diff`: a `git diff --exit-code` check false-fails whenever
# schema.d.ts has legitimate uncommitted edits, and was rejected for that.
# The snapshot is always restored, so this never leaves the working tree
# modified — on success (regeneration == committed) or failure alike.
#
# Exactness depends on biome.json excluding schema.d.ts from formatting, so
# the committed file is raw openapi-typescript output (byte-identical to what
# this regenerates). Keep that per-file override.
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
