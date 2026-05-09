/**
 * Typed API client.
 *
 * `openapi-fetch` is parameterised on the `paths` map generated from
 * ninja's OpenAPI schema (see schema.d.ts). The CSRF concern is hidden
 * inside the custom fetch — TanStack Query hooks just call methods on
 * `apiClient`.
 */

import createClient from "openapi-fetch";
import { csrfFetch } from "./csrf";
import type { components, paths } from "./schema";

export const apiClient = createClient<paths>({
  baseUrl: "",
  fetch: csrfFetch as unknown as typeof fetch,
});

export type ApiKey = components["schemas"]["ApiKeyOut"];
export type ApiKeyCreateIn = components["schemas"]["ApiKeyCreateIn"];
export type ApiKeyMintOut = components["schemas"]["ApiKeyMintOut"];
