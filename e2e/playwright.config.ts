import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 30000,
  use: {
    baseURL: process.env.BASE_URL || 'https://veckosmak.vercel.app',
  },
})
