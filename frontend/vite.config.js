import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendTarget = env.VITE_API_URL || 'http://127.0.0.1:8002'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target: backendTarget, changeOrigin: true },
        '/ingest': { target: backendTarget, changeOrigin: true },
        '/tasks': { target: backendTarget, changeOrigin: true },
        '/users': { target: backendTarget, changeOrigin: true },
        '/health': { target: backendTarget, changeOrigin: true }
      }
    }
  }
})
