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

// Lazily load Albums to keep initial bundle lean
const Albums = lazy(() => import('../pages/Albums'));
const Favorites = lazy(() => import('../pages/Favorites'));
const Videos = lazy(() => import('../pages/Videos'));
const Trash = lazy(() => import('../pages/Trash'));
const People = lazy(() => import('../pages/People'));
const PersonDetail = lazy(() => import('../pages/PersonDetail'));
const UnidentifiedFaces = lazy(() => import('../pages/UnidentifiedFaces'));
const AllFacePhotos = lazy(() => import('../pages/AllFacePhotos'));
const Import = lazy(() => import('../pages/Import'));
const Tags = lazy(() => import('../pages/Tags'));
const PerformanceDashboard = lazy(() => import('../pages/PerformanceDashboard'));

// Lazily load studio/utility features to keep initial bundle lean and avoid CSS bleed
const SavedSearches = lazy(() => import('../pages/SavedSearches'));
const JobMonitor = lazy(() => import('../components/features/JobMonitor'));
const IntentRecognition = lazy(() => import('../components/search/IntentRecognition'));
const FaceClustering = lazy(() => import('../components/features/FaceClustering'));
const OCRSearch = lazy(() => import('../components/features/OCRSearch'));
const ModalSystem = lazy(() => import('../components/common/ModalSystem'));
const CodeSplitting = lazy(() => import('../components/features/CodeSplitting'));
const TauriIntegration = lazy(() => import('../components/features/TauriIntegration'));

// Lazy load heavy advanced feature components for better performance
const AnalyticsDashboard = lazy(() => import('../components/advanced/AnalyticsDashboard'));
const SmartAlbumsBuilder = lazy(() => import('../components/advanced/SmartAlbumsBuilder'));
const FaceRecognitionPanel = lazy(() => import('../components/advanced/FaceRecognitionPanel'));
const DuplicateManagementPanel = lazy(() => import('../components/advanced/DuplicateManagementPanel'));
const OCRTextSearchPanel = lazy(() => import('../components/advanced/OCRTextSearchPanel'));
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
              <Route path='/albums' element={<Albums />} />
              <Route path='/people' element={<People />} />
              <Route path='/people/unidentified' element={<UnidentifiedFaces />} />
              <Route path='/people/all-photos' element={<AllFacePhotos />} />
              <Route path='/people/:clusterId' element={<PersonDetail />} />
              <Route path='/favorites' element={<Favorites />} />
              <Route path='/videos' element={<Videos />} />
              <Route path='/trash' element={<Trash />} />
              <Route path='/tags' element={<Tags />} />
              <Route path='/saved-searches' element={<SavedSearches />} />
              <Route path='/jobs' element={<JobMonitor />} />
              <Route path='/performance' element={<PerformanceDashboard />} />
              <Route path='/tasks' element={<Navigate to='/jobs' replace />} />
              <Route path='/import' element={<Import />} />

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

              {/* Advanced Analytics Routes */}
              <Route path='/analytics/dashboard' element={<AnalyticsDashboard />} />
              <Route path='/analytics/albums' element={<SmartAlbumsBuilder />} />
              <Route path='/analytics/faces' element={<FaceRecognitionPanel />} />
              <Route path='/analytics/duplicates' element={<DuplicateManagementPanel />} />
              <Route path='/analytics/ocr' element={<OCRTextSearchPanel />} />

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
