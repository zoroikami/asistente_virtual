import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  base: './',
  // Build de la app
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
    },
  },
  server: {
    port: 1420,
    strictPort: true,
  },
  // Necesario para que Tauri funcione
  clearScreen: false,
  envPrefix: ['VITE_', 'TAURI_'],
});
