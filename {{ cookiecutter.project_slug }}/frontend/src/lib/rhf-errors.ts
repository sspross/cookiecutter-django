/**
 * Map a Django Ninja 422 response into per-field React Hook Form errors.
 *
 * Both Pydantic 422s (raised at deserialization) and Django
 * `ValidationError`s mapped through `core.api.handle_django_validation_error`
 * arrive in the same shape:
 *
 *   { "detail": [{ "loc": ["body", "name"], "msg": "...", "type": "..." }] }
 *
 * The first element of `loc` is always the request part (`body`, `query`,
 * `path`); the rest is the dotted field path inside the form payload.
 * Errors with no field path land on RHF's `root.serverError`.
 */

import type { FieldValues, Path, UseFormReturn } from "react-hook-form";

interface ApiErrorDetailItem {
  loc?: unknown;
  msg?: unknown;
}

export function applyApiErrorsToForm<T extends FieldValues>(
  form: Pick<UseFormReturn<T>, "setError">,
  error: unknown,
): boolean {
  const detail = extractDetail(error);
  if (!detail) return false;

  let applied = false;
  for (const raw of detail) {
    if (!raw || typeof raw !== "object") continue;
    const item = raw as ApiErrorDetailItem;
    if (!Array.isArray(item.loc) || typeof item.msg !== "string") continue;

    const fieldParts = item.loc.slice(1).map(String);
    const field = fieldParts.join(".");
    if (field) {
      form.setError(field as Path<T>, { type: "server", message: item.msg });
    } else {
      form.setError("root.serverError" as Path<T>, {
        type: "server",
        message: item.msg,
      });
    }
    applied = true;
  }
  return applied;
}

function extractDetail(error: unknown): unknown[] | null {
  if (!error || typeof error !== "object") return null;
  const detail = (error as { detail?: unknown }).detail;
  return Array.isArray(detail) ? detail : null;
}
