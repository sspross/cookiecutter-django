import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In production we serve the SPA from `STATIC_ROOT/index.html` and the bundled
// assets live under `/static/assets/*`, so the build needs `base: '/static/'`.
// In dev the SPA is served by Vite at `/` and we let Caddy proxy everything
// non-API to it, so dev needs `base: '/'` for the dev URLs to work.
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
  },
}));
