// Storage polyfill is in index.html (runs before this module)

import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';

// Enable why-did-you-render in development for tracing unwanted re-renders
if (import.meta.env.DEV) {
  // Initialize after app mounts to avoid hook order issues during hot reload
  if (typeof window !== 'undefined' && !(window as any).__WDYR_INIT__) {
    (window as any).__WDYR_INIT__ = true;

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

createRoot(document.getElementById('root')!).render(<App />);
