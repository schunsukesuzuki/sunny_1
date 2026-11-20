import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: 'http://api:8000', changeOrigin: true, timeout: 1800000, proxyTimeout: 1800000 } }
  }
})
