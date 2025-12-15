import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/search': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/image': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/video': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/file': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  optimizeDeps: {
    include: ['react-window', 'react-virtualized-auto-sizer'],
  },
});
