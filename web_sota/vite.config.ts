import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['goliath'],
    proxy: {
      // Lets relative fetch("/api/...") work in dev by forwarding to the
      // fleet backend on :10712 (overridden by VITE_API_TARGET in prod).
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:10712',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
