import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Куда проксировать API: локально — Laravel на :8000, в Docker — сервис app
const apiTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Проксируем /api запросы на Laravel — так фронт обращается к /api без CORS
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
