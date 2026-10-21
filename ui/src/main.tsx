// Storage polyfill is in index.html (runs before this module)

import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';
import { shell } from '@/platform';

// Enable why-did-you-render in development for tracing unwanted re-renders
if (import.meta.env.DEV) {
  // Initialize after app mounts to avoid hook order issues during hot reload
  type WindowWithWdyr = Window & { __WDYR_INIT__?: boolean };

  if (typeof window !== 'undefined' && !(window as WindowWithWdyr).__WDYR_INIT__) {
    (window as WindowWithWdyr).__WDYR_INIT__ = true;

    // Delay initialization to ensure app is fully mounted
    setTimeout(async () => {
      try {
        const [wdyrModule, React] = await Promise.all([
          import('@welldone-software/why-did-you-render'),
          import('react'),
        ]);

        const init = wdyrModule.default;
        init(React, {
          trackAllPureComponents: true,
          // Exclude components that may have intentional re-renders
          exclude: [
            /^Router$/,
            /^Link$/,
            /^NavLink$/,
            /^Layout$/,
            /^PhotoGrid$/,
          ],
          trackHooks: true,
          // Log re-renders to console
          logOnDifferentValues: true,
          // Only track components that re-render more than once per second
          hotReloadBufferMs: 1000,
        });

        console.info(
          '✅ why-did-you-render enabled - watching for unnecessary re-renders'
        );
      } catch (err) {
        console.warn('❌ why-did-you-render failed to initialize:', err);
      }
    }, 2000); // Wait 2 seconds after app start
  }
}

// PWA: register the offline app-shell service worker for production builds.
// The Tauri desktop shell serves from a custom protocol and has no use for a
// web cache, so it is skipped there. BASE_URL keeps the script path correct
// for both targets (`/sw.js` for desktop, `/app/sw.js` for the companion).
if (import.meta.env.PROD && 'serviceWorker' in navigator && shell !== 'tauri') {
  window.addEventListener('load', () => {
    const swUrl = `${import.meta.env.BASE_URL}sw.js`;
    navigator.serviceWorker.register(swUrl).catch((err) => {
      console.warn('[pwa] service worker registration failed', err);
    });
  });
}

createRoot(document.getElementById('root')!).render(<App />);
