import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    // lib/supabase.ts constructs its client at import time; give tests
    // dummy credentials so suites run identically with or without a local
    // .env (CI has none). No test ever talks to this URL.
    env: {
      VITE_SUPABASE_URL: 'http://localhost:54321',
      VITE_SUPABASE_ANON_KEY: 'test-anon-key',
      // LoginPage tests assert the open-signup layout (Google button);
      // a local .env with the beta lock on must not change what CI sees.
      VITE_INVITE_ONLY: 'false',
    },
  },
})
