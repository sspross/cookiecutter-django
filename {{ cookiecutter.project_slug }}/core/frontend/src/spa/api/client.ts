import createClient from "openapi-fetch";
import { csrfFetch } from "./csrf";
import type { paths } from "./schema";

export const apiClient = createClient<paths>({
  baseUrl: "",
  fetch: csrfFetch as unknown as typeof fetch,
});

export function requireData<T>(data: T | undefined, endpoint: string): T {
  if (data === undefined) {
    throw new Error(`${endpoint} returned no response body`);
  }
  return data;
}
