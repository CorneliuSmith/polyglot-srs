import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  build: {
    // Vite preloads every dynamic chunk reachable from the entry. The
    // native chunk can only run inside a Capacitor shell, so preloading it
    // makes web visitors fetch code that will never execute.
    modulePreload: {
      resolveDependencies: (_url, deps) =>
        deps.filter((d) => !d.includes('/native-')),
    },
    rollupOptions: {
      output: {
        // Keep third-party libraries in a stable vendor chunk so they stay
        // cached across app deploys, and split the heavy on-screen-keyboard
        // dependency out of every bundle that doesn't need it.
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('simple-keyboard')) return 'keyboard'
          // The native plugins are dynamically imported and can only run in
          // a Capacitor shell. Without their own chunk they land in vendor
          // anyway — every web visitor downloading code that checks whether
          // it is on a phone and then returns.
          if (id.includes('@capacitor')) return 'native'
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
