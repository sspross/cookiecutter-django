/**
 * CSRF helpers for the SPA's typed API client.
 *
 * Every mutating request (POST/PUT/PATCH/DELETE) must echo Django's
 * `csrftoken` cookie back via the `X-CSRFToken` header. Centralising
 * this in one place means no individual TanStack Query hook has to
 * remember it, and a missing cookie raises a clear error rather than
 * silently sending an empty header.
 *
 * `openapi-fetch` calls custom fetch implementations with a `Request`
 * object as the first argument (and an empty `init`), so we have to
 * read the method off the Request, not off `init`.
 */

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCsrfCookie(cookieJar: string = document.cookie): string | null {
  const match = cookieJar.match(/(?:^|;\s*)csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export class CsrfCookieMissingError extends Error {
  constructor() {
    super(
      "CSRF cookie 'csrftoken' is missing. The SPA mount view sets it via " +
        "@ensure_csrf_cookie; a missing cookie usually means the user is " +
        "no longer authenticated.",
    );
    this.name = "CsrfCookieMissingError";
  }
}

export interface CsrfFetchOptions extends RequestInit {
  /** Optional override for the cookie source (used by tests). */
  cookieJar?: string;
}

function methodOf(input: RequestInfo | URL, init: CsrfFetchOptions): string {
  if (init.method) return init.method.toUpperCase();
  if (typeof Request !== "undefined" && input instanceof Request) {
    return input.method.toUpperCase();
  }
  return "GET";
}

/**
 * `fetch` wrapper that injects `X-CSRFToken` on unsafe methods and
 * `credentials: same-origin` so the session cookie travels with the
 * request. On safe methods the header is omitted entirely.
 */
export async function csrfFetch(
  input: RequestInfo | URL,
  init: CsrfFetchOptions = {},
): Promise<Response> {
  const method = methodOf(input, init);
  const { cookieJar, ...rest } = init;

  if (!UNSAFE_METHODS.has(method)) {
    return fetch(input, { ...rest, credentials: "same-origin" });
  }

  const token = readCsrfCookie(cookieJar);
  if (!token) {
    throw new CsrfCookieMissingError();
  }

  // When `input` is a Request, its headers are immutable from outside;
  // build a fresh Request with the original method/body/headers and the
  // CSRF header tacked on.
  if (typeof Request !== "undefined" && input instanceof Request) {
    const headers = new Headers(input.headers);
    headers.set("X-CSRFToken", token);
    return fetch(
      new Request(input, {
        headers,
      }),
      { credentials: "same-origin" },
    );
  }

  const headers = new Headers(init.headers);
  headers.set("X-CSRFToken", token);
  return fetch(input, {
    ...rest,
    method,
    headers,
    credentials: "same-origin",
  });
}
