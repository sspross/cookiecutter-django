import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In production we serve the SPA from `STATIC_ROOT/index.html` and the bundled
// assets live under `/static/assets/*`, so the build needs `base: '/static/'`.
// In dev the SPA is served by Vite at `/` and the dev server proxies the
// Django-owned paths to runserver, so dev needs `base: '/'`.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/" : "/",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    manifest: true,
    sourcemap: true,
  },
  server: {
    port: 5173,
    strictPort: true,
    host: true,
    // Same-origin shim for dev: forward Django-owned paths to runserver so
    // cookies, CSRF, and SameSite behave the way they will in prod. `/static`
    // is included so Django admin's CSS and JS render under DEBUG=True.
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/media": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
    },
  },
}));
