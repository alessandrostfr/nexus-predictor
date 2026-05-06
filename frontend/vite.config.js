import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config kept intentionally small and pinned to stable versions for Windows local development.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
});
