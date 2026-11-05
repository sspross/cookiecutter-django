import { resolve } from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  root: resolve("./src"),
  base: "/static/dist/js/", // Keep in sync with DJANGO_VITE in core/settings/base.py
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
    origin: "http://localhost:5173",
  },
});
