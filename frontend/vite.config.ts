import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    // supabase-js is ~200kB and loads at startup because the auth provider
    // needs a session before any route can render. Not worth code-splitting
    // right before a demo; raise the warning rather than adding complexity.
    // Monaco is ~3.3MB but lives entirely in lazy chunks that only load when
    // the Compiler view opens, so the initial bundle is unaffected.
    chunkSizeWarningLimit: 3400,
  },
  server: {
    port: 5173,
    // Fail loudly instead of silently drifting to 5174+ when someone
    // already holds the port. Confusing port drift wastes team time.
    strictPort: true,
    // Backend (FastAPI) runs on :8000. All API calls go through /api/*.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
