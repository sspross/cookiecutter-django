const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

let csrfCookieName = "";

export function setCsrfCookieName(name: string): void {
  csrfCookieName = name;
}

export function readCsrfCookie(cookieJar: string = document.cookie): string | null {
  const prefix = `${csrfCookieName}=`;
  const cookie = cookieJar
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

export class CsrfCookieMissingError extends Error {
  constructor() {
    super(
      `CSRF cookie '${csrfCookieName}' is missing. The SPA mount view sets it via ` +
        "@ensure_csrf_cookie; a missing cookie usually means the user is " +
        "no longer authenticated.",
    );
    this.name = "CsrfCookieMissingError";
  }
}

export interface CsrfFetchOptions extends RequestInit {
  cookieJar?: string;
}

// `openapi-fetch` calls a custom fetch with a `Request` and an empty `init`.
function methodOf(input: RequestInfo | URL, init: CsrfFetchOptions): string {
  if (init.method) return init.method.toUpperCase();
  if (typeof Request !== "undefined" && input instanceof Request) {
    return input.method.toUpperCase();
  }
  return "GET";
}

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
