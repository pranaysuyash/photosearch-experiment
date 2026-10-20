/**
 * Main Application Entry Point
 *
 * Integrates all components with routing and state management
 */

import { MotionConfig } from 'framer-motion';
import MainRouter from './router/MainRouter';
import { PhotoSearchProvider } from './contexts/PhotoSearchContext';
import { PhotoViewerProvider } from './contexts/PhotoViewerContext';
import { AmbientThemeProvider } from './contexts/AmbientThemeContext';
import { useActionSystem } from './hooks/useActionSystem';

function App() {
  // Initialize the action system
  useActionSystem();

  return (
    <MotionConfig reducedMotion='user'>
      <PhotoSearchProvider>
        <AmbientThemeProvider>
          <PhotoViewerProvider>
            <MainRouter />
          </PhotoViewerProvider>
        </AmbientThemeProvider>
      </PhotoSearchProvider>
    </MotionConfig>
  );
}

export default App;
