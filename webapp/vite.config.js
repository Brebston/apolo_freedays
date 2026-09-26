import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Зібрані файли роздає Django (WhiteNoise) за префіксом /static/webapp/,
// а index.html — за адресою /app/. У режимі розробки (npm run dev)
// запити /api проксюються на локальний Django.
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/webapp/' : '/',
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
}))
