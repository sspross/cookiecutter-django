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

/**
 * A 2xx without a body breaks the OpenAPI contract, so it is an error rather
 * than a rendering state; throwing turns it into a query error instead of a
 * silent `undefined`.
 */
export function requireData<T>(data: T | undefined, endpoint: string): T {
  if (data === undefined) {
    throw new Error(`${endpoint} returned no response body`);
  }
  return data;
}
