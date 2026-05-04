import createClient, { type Middleware } from "openapi-fetch";

import type { paths } from "../../types/api";

function readCookie(name: string): string | null {
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/[$.*+?()[\]{}|\\]/g, "\\$&") + "=([^;]*)"),
  );
  return match && match[1] ? decodeURIComponent(match[1]) : null;
}

const csrfMiddleware: Middleware = {
  async onRequest({ request }) {
    const method = request.method.toUpperCase();
    if (method === "GET" || method === "HEAD" || method === "OPTIONS") {
      return undefined;
    }
    const token = readCookie("csrftoken");
    if (token) {
      request.headers.set("X-CSRFToken", token);
    }
    return request;
  },
};

export const api = createClient<paths>({
  baseUrl: "",
  credentials: "same-origin",
});

api.use(csrfMiddleware);
