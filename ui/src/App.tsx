/**
 * Main Application Entry Point
 * 
 * Integrates all components with routing and state management
 */

import MainRouter from './router/MainRouter';
import { PhotoSearchProvider } from './contexts/PhotoSearchContext';
import { PhotoViewerProvider } from './contexts/PhotoViewerContext';
import { AmbientThemeProvider } from './contexts/AmbientThemeContext';

function App() {
  return (
    <PhotoSearchProvider>
      <AmbientThemeProvider>
        <PhotoViewerProvider>
          <MainRouter />
        </PhotoViewerProvider>
      </AmbientThemeProvider>
    </PhotoSearchProvider>
  );
}

export default App;
