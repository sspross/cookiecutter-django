import { resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Single Vite pipeline: React SPA + Tailwind v4 (via the @tailwindcss/vite
// plugin). The compiled CSS (built from spa/index.css's
// `@import "tailwindcss"`) is consumed by both the SPA mount template
// and Django-rendered pages (login).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  root: resolve("./src"),
  base: "/static/dist/js/", // Keep in sync with DJANGO_VITE settings
  resolve: {
    extensions: [".tsx", ".ts", ".jsx", ".js"],
    alias: {
      "@": resolve("./src/spa"),
    },
  },
  build: {
    assetsDir: "",
    manifest: "manifest.json",
    outDir: resolve("../static/dist/js"),
    emptyOutDir: true,
    target: "es2022",
    rollupOptions: {
      input: {
        main: resolve("./src/main.tsx"),
      },
    },
  },
  server: {
    // Vite dev server runs on a separate port; django-vite injects the
    // HMR client only when DEBUG=True.
    origin: "http://localhost:5173",
  },
  test: {
    environment: "jsdom",
    globals: true,
  },
});
