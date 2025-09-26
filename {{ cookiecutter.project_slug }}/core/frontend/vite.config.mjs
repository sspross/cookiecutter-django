import { resolve } from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  root: resolve('./src'),
  base: '/static/dist/js/', // Keep in sync DJANGO_VITE settings
  resolve: {
    extensions: ['.jsx', '.js'],
  },
  build: {
    assetsDir: '',
    manifest: 'manifest.json',
    outDir: resolve('../static/dist/js'),
    emptyOutDir: true,
    target: 'es2015',
    rollupOptions: {
      input: {
        test: resolve('./src/js/test.js'),
        widget: resolve('./src/js/widget/main.jsx'),
      },
      output: {
        chunkFileNames: undefined,
      },
    },
  },
});
