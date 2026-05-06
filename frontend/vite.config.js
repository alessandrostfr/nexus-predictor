import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config kept minimal for the MVP.
export default defineConfig({
  plugins: [react()],
});
