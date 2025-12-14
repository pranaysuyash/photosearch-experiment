/**
 * Main Router Component
 *
 * Handles all application routing and navigation
 */

import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import Layout from '../components/layout/Layout';

// Core experiences (keep eagerly loaded)
import Home from '../pages/Home';
import Search from '../pages/Search';
import StoryModePage from '../pages/StoryModePage';
import GlobePage from '../pages/GlobePage';

// Lazily load studio/utility features to keep initial bundle lean and avoid CSS bleed
const SavedSearches = lazy(() => import('../pages/SavedSearches'));
const JobMonitor = lazy(() => import('../components/features/JobMonitor'));
const IntentRecognition = lazy(() => import('../components/search/IntentRecognition'));
const FaceClustering = lazy(() => import('../components/features/FaceClustering'));
const OCRSearch = lazy(() => import('../components/features/OCRSearch'));
const ModalSystem = lazy(() => import('../components/common/ModalSystem'));
const CodeSplitting = lazy(() => import('../components/features/CodeSplitting'));
const TauriIntegration = lazy(() => import('../components/features/TauriIntegration'));
const Settings = lazy(() => import('../pages/Settings'));
const About = lazy(() => import('../pages/About'));
const NotFound = lazy(() => import('../pages/NotFound'));

const suspenseFallback = (
  <div className='flex items-center justify-center py-12 text-sm text-muted-foreground'>
    Loading…
  </div>
);

const MainRouter = () => {
  return (
    <ErrorBoundary>
      <Router>
        <Layout>
          <Suspense fallback={suspenseFallback}>
            <Routes>
              {/* Main Routes */}
              <Route path='/' element={<Home />} />
              <Route path='/search' element={<Search />} />
              <Route path='/globe' element={<GlobePage />} />
              <Route path='/story-mode' element={<StoryModePage />} />
              <Route path='/saved-searches' element={<SavedSearches />} />
              <Route path='/jobs' element={<JobMonitor />} />
              <Route path='/tasks' element={<Navigate to='/jobs' replace />} />

              {/* Studio Features */}
              <Route
                path='/studio/intent-recognition'
                element={
                  <IntentRecognition query='' onIntentDetected={() => { }} />
                }
              />
              <Route
                path='/studio/face-clustering'
                element={<FaceClustering />}
              />
              <Route path='/studio/ocr-search' element={<OCRSearch />} />
              <Route path='/studio/modal-system' element={<ModalSystem />} />
              <Route
                path='/studio/code-splitting'
                element={<CodeSplitting />}
              />
              <Route
                path='/studio/tauri-integration'
                element={<TauriIntegration />}
              />

              {/* Utility Routes */}
              <Route path='/settings' element={<Settings />} />
              <Route path='/about' element={<About />} />

              {/* Redirects */}
              <Route path='/home' element={<Navigate to='/' replace />} />
              {/* /jobs now canonical; keep /tasks alias above */}

              {/* 404 Not Found */}
              <Route path='*' element={<NotFound />} />
            </Routes>
          </Suspense>
        </Layout>
      </Router>
    </ErrorBoundary>
  );
};

export default MainRouter;
