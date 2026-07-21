import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    rollupOptions: {
      output: {
        // Keep third-party libraries in a stable vendor chunk so they stay
        // cached across app deploys, and split the heavy on-screen-keyboard
        // dependency out of every bundle that doesn't need it.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('simple-keyboard')) return 'keyboard'
          return 'vendor'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
