import path from 'path';
import { defineConfig, loadEnv, type ProxyOptions } from 'vite';
import react from '@vitejs/plugin-react';
import {
  assertApiBaseUsable,
  assertTargetConsistency,
  assetBaseForTarget,
  effectiveApiBase,
  targetForMode,
} from './src/platform/target';

// https://vite.dev/config/
// Two build targets, one config: the default mode is the desktop bundle Tauri
// embeds (served from `/`); `--mode web` is the companion bundle FastAPI mounts
// at `/app/` (see server/ui_static.py). The target decides BOTH the asset base
// and the API base — see src/platform/target.ts; nothing here is machine-local.

// The dev/preview server forwards API calls to the local backend. The port
// follows BACKEND_PORT so it stays in step with scripts/dev-restart.sh (which
// starts the backend on the same variable) — a hardcoded 8000 here broke the
// proxy whenever the backend ran on another port.
const BACKEND_ORIGIN =
  process.env.PHOTOSEARCH_BACKEND_ORIGIN ??
  `http://127.0.0.1:${process.env.BACKEND_PORT ?? 8000}`;

// API routes are mounted at the top level (not under /api), so the proxy list
// mirrors the real route prefixes. Shared by the dev server and the preview
// server so `npm run preview:web` can reach a running backend.
const apiProxy = (): Record<string, ProxyOptions> => ({
  '/api': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
  '/search': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
  '/image': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
  '/video': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
  '/file': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
});

// The companion bundle calls the API on its own origin, and the API mounts
// most of its routes at the top level (/sources, /browse, /albums, /pair, …),
// not under /api. In the preview server the app itself lives under /app/,
// so everything else is forwarded to the backend.
const previewProxy = (): Record<string, ProxyOptions> => ({
  '^(?!/app/).*': { target: BACKEND_ORIGIN, changeOrigin: true, secure: false },
});

export default defineConfig(({ mode }) => {
  const target = targetForMode(mode);

  return {
    base: assetBaseForTarget(target),
    plugins: [
      react(),
      {
        // The asset base and the API base are two faces of one target, and the
        // API base must match the target's topology. If they disagree, the
        // bundle either calls its own origin (companion with a host) or its
        // own asset protocol (desktop without one) — fail the build instead
        // of shipping that.
        name: 'photosearch:target-guard',
        configResolved(config) {
          assertTargetConsistency(target, config.base);
          const env = loadEnv(mode, process.cwd(), 'VITE_');
          const apiBase = effectiveApiBase(target, {
            VITE_API_URL: process.env.VITE_API_URL ?? env.VITE_API_URL,
          });
          assertApiBaseUsable(target, apiBase);
        },
      },
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      strictPort: true,
      host: '0.0.0.0',
      proxy: apiProxy(),
    },
    preview: {
      port: 4173,
      strictPort: true,
      host: '0.0.0.0',
      proxy: previewProxy(),
    },
    optimizeDeps: {
      include: ['react-virtualized-auto-sizer'],
    },
  };
});
