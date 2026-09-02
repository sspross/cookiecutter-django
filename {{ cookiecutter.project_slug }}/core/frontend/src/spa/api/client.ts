/**
 * Typed API client, parameterised on the `paths` map generated from ninja's
 * OpenAPI schema. CSRF is hidden inside the custom fetch, so query hooks just
 * call methods on `apiClient`.
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
export type Me = components["schemas"]["MeOut"];
