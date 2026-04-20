import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // accessible inside Docker container
    port: 5173,
    proxy: {
      '/api': 'http://app:8000' // FastAPI Endpoint
    }
  }
})
