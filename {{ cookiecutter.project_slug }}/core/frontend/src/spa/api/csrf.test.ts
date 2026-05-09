/**
 * vitest covers `csrfFetch` because it is the chokepoint for every
 * write the SPA makes; if it silently sends an empty header the bug is
 * invisible until the server rejects the next mutation.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { CsrfCookieMissingError, csrfFetch } from "./csrf";

describe("csrfFetch", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    globalThis.fetch = fetchSpy as unknown as typeof fetch;
  });

  it("does not include X-CSRFToken on a GET", async () => {
    await csrfFetch("/api/api-keys/", { cookieJar: "csrftoken=abc" });

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.has("X-CSRFToken")).toBe(false);
  });

  it("reads the csrftoken cookie and sets X-CSRFToken on a POST", async () => {
    await csrfFetch("/api/api-keys/", {
      method: "POST",
      cookieJar: "other=1; csrftoken=secret-token; foo=bar",
    });

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRFToken")).toBe("secret-token");
  });

  it("sends X-CSRFToken on PUT, PATCH and DELETE", async () => {
    for (const method of ["PUT", "PATCH", "DELETE"] as const) {
      fetchSpy.mockClear();
      await csrfFetch("/api/api-keys/1/", {
        method,
        cookieJar: "csrftoken=tok",
      });
      const init = fetchSpy.mock.calls[0][1] as RequestInit;
      const headers = new Headers(init.headers);
      expect(headers.get("X-CSRFToken")).toBe("tok");
    }
  });

  it("throws a clear error when the cookie is missing on a write", async () => {
    await expect(
      csrfFetch("/api/api-keys/", { method: "POST", cookieJar: "" }),
    ).rejects.toBeInstanceOf(CsrfCookieMissingError);
  });

  it("uses same-origin credentials so the session cookie is sent", async () => {
    await csrfFetch("/api/api-keys/", { cookieJar: "csrftoken=abc" });

    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("same-origin");
  });

  it("URL-decodes the cookie value", async () => {
    await csrfFetch("/api/api-keys/", {
      method: "POST",
      cookieJar: "csrftoken=hello%20world",
    });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("X-CSRFToken")).toBe("hello world");
  });

  it("reads method off a Request input (openapi-fetch passes a Request)", async () => {
    const req = new Request("http://localhost/api/api-keys/", {
      method: "POST",
      body: JSON.stringify({ name: "ci" }),
      headers: { "Content-Type": "application/json" },
    });
    await csrfFetch(req, { cookieJar: "csrftoken=tok" });

    const sentRequest = fetchSpy.mock.calls[0][0] as Request;
    expect(sentRequest).toBeInstanceOf(Request);
    expect(sentRequest.method).toBe("POST");
    expect(sentRequest.headers.get("X-CSRFToken")).toBe("tok");
  });
});
