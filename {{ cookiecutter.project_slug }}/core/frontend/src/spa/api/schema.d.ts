// Hand-crafted placeholder so `tsc --noEmit` passes on a fresh clone before
// the ninja server has been started. After the first `runserver`, regenerate
// from the live OpenAPI document with `make schema`.
export interface paths {
  "/api/api-keys/": {
    get: {
      responses: {
        200: { content: { "application/json": components["schemas"]["ApiKeyOut"][] } };
      };
    };
    post: {
      requestBody: {
        content: { "application/json": components["schemas"]["ApiKeyCreateIn"] };
      };
      responses: {
        201: { content: { "application/json": components["schemas"]["ApiKeyMintOut"] } };
      };
    };
  };
  "/api/api-keys/{api_key_id}/revoke/": {
    post: {
      parameters: { path: { api_key_id: number } };
      responses: {
        200: { content: { "application/json": components["schemas"]["ApiKeyOut"] } };
      };
    };
  };
}
export interface components {
  schemas: {
    ApiKeyOut: {
      id: number;
      name: string;
      prefix: string;
      created_at: string;
      last_used_at: string | null;
      revoked_at: string | null;
    };
    ApiKeyCreateIn: { name: string };
    ApiKeyMintOut: {
      api_key: components["schemas"]["ApiKeyOut"];
      raw_token: string;
    };
  };
}
