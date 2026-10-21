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
  useNavigate,
} from 'react-router-dom';
import { Suspense, lazy, useEffect, type ReactNode } from 'react';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import Layout from '../components/layout/Layout';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import { setUnauthorizedHandler } from '../api';
import { shell } from '@/platform';

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
const Duplicates = lazy(() =>
  import('../pages/Duplicates').then((m) => ({
    default: m.Duplicates,
  }))
);
const People = lazy(() => import('../pages/People'));
const PersonDetail = lazy(() => import('../pages/PersonDetail'));
const UnidentifiedFaces = lazy(() => import('../pages/UnidentifiedFaces'));
const UnassignedFaces = lazy(() => import('../pages/UnassignedFaces'));
const AllFacePhotos = lazy(() => import('../pages/AllFacePhotos'));
const Singletons = lazy(() => import('../pages/Singletons'));
const LowConfidence = lazy(() => import('../pages/LowConfidence'));
const Import = lazy(() => import('../pages/Import'));
const Tags = lazy(() => import('../pages/Tags'));
const PerformanceDashboard = lazy(() => import('../pages/PerformanceDashboard'));

// Lazily load studio/utility features to keep initial bundle lean and avoid CSS bleed
const SavedSearches = lazy(() => import('../pages/SavedSearches'));
const JobMonitor = lazy(() => import('../components/features/JobMonitor'));
const IntentRecognition = lazy(() => import('../components/search/IntentRecognition'));
const FaceClustering = lazy(() => import('../components/features/FaceClustering'));
const ModalSystem = lazy(() => import('../components/common/ModalSystem'));
const CodeSplitting = lazy(() => import('../components/features/CodeSplitting'));
const TauriIntegration = lazy(() => import('../components/features/TauriIntegration'));

// Lazy load heavy advanced feature components for better performance
const AnalyticsDashboard = lazy(() => import('../components/advanced/AnalyticsDashboard'));
const OCRTextSearchPanel = lazy(() => import('../components/advanced/OCRTextSearchPanel'));

// Phase 8: Advanced Face Recognition UI Components
// These modules export named components (not default exports). React.lazy expects a default.
const PrivacyDashboard = lazy(() =>
  import('../components/privacy/PrivacyDashboard').then((m) => ({
    default: m.PrivacyDashboard,
  }))
);
const PerformanceDashboardAdvanced = lazy(() =>
  import('../components/performance/PerformanceDashboard').then((m) => ({
    default: m.PerformanceDashboard,
  }))
);

// Named-export feature modules being (re)mounted — adapters for React.lazy
const CollaborativeSpaces = lazy(() =>
  import('../components/collaboration/CollaborativeSpaces').then((m) => ({
    default: m.CollaborativeSpaces,
  }))
);
const PlaceClustering = lazy(() =>
  import('../components/locations/PlaceClustering').then((m) => ({
    default: m.PlaceClustering,
  }))
);
const VideoAnalysisPanel = lazy(() =>
  import('../components/video/VideoAnalysisPanel').then((m) => ({
    default: m.VideoAnalysisPanel,
  }))
);
const AIInsights = lazy(() =>
  import('../components/ai/AIInsights').then((m) => ({ default: m.AIInsights }))
);
const ModernGalleryDemo = lazy(() =>
  import('../components/gallery/ModernGalleryDemo').then((m) => ({
    default: m.ModernGalleryDemo,
  }))
);
const ResponsiveGallery = lazy(() =>
  import('../components/gallery/ResponsiveGallery').then((m) => ({
    default: m.ResponsiveGallery,
  }))
);

// Wrappers for lazy pages that need router/context data
const ResponsiveGalleryPage = () => {
  const { photos } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();
  return (
    <ResponsiveGallery
      photos={photos}
      onPhotoSelect={(photo) => {
        // ResponsiveGallery has its own minimal Photo shape — resolve to the
        // canonical api.Photo by path before opening the viewer.
        const match = photos.find((p) => p.path === photo.path);
        if (match) openForPhoto(photos, match);
      }}
    />
  );
};

const ModernGalleryDemoPage = () => {
  const navigate = useNavigate();
  return <ModernGalleryDemo onUseModern={() => navigate('/')} />;
};

const Settings = lazy(() => import('../pages/Settings'));
const About = lazy(() => import('../pages/About'));
const NotFound = lazy(() => import('../pages/NotFound'));
const PairPage = lazy(() => import('../pages/PairPage'));

/**
 * Developer showcases — dialog gallery, code-splitting metrics, Tauri setup
 * guide, gallery prototypes — are not user-facing features. Production builds
 * serve NotFound; `vite dev` keeps them reachable.
 */
const DevOnly = ({ children }: { children: ReactNode }) =>
  import.meta.env.DEV ? <>{children}</> : <NotFound />;

/**
 * A 401 from the principal gate means this browser is not paired. In the
 * Tauri shell the backend is loopback and the gate never fires, so a 401
 * there is a server bug worth leaving visible rather than hiding behind the
 * pairing page.
 */
const UnauthorizedBridge = () => {
  const navigate = useNavigate();
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (shell === 'tauri') return;
      const base = import.meta.env.BASE_URL.replace(/\/$/, '');
      const here = window.location.pathname;
      const inApp = here.startsWith(base) ? here.slice(base.length) || '/' : here;
      try {
        sessionStorage.setItem('lm:pairReturnTo', `${inApp}${window.location.search}`);
      } catch {
        // storage unavailable; land on the library afterwards
      }
      navigate('/pair', { replace: true });
    });
    return () => setUnauthorizedHandler(null);
  }, [navigate]);
  return null;
};

const suspenseFallback = (
  <div className='flex items-center justify-center py-12 text-sm text-muted-foreground'>
    Loading…
  </div>
);

const MainRouter = () => {
  return (
    <ErrorBoundary>
      {/* BASE_URL is '/' for the desktop bundle and '/app/' for the web build. */}
      <Router basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
        <UnauthorizedBridge />
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
              <Route path='/people/unassigned' element={<UnassignedFaces />} />
              <Route path='/people/all-photos' element={<AllFacePhotos />} />
              <Route path='/people/singletons' element={<Singletons />} />
              <Route path='/people/low-confidence' element={<LowConfidence />} />
              <Route path='/people/:clusterId' element={<PersonDetail />} />
              <Route path='/favorites' element={<Favorites />} />
              <Route path='/videos' element={<Videos />} />
              <Route path='/trash' element={<Trash />} />
              <Route path='/duplicates' element={<Duplicates />} />
              <Route path='/tags' element={<Tags />} />
              <Route path='/saved-searches' element={<SavedSearches />} />
              <Route path='/jobs' element={<JobMonitor />} />
              <Route path='/performance' element={<PerformanceDashboard />} />
              <Route path='/tasks' element={<Navigate to='/jobs' replace />} />
              <Route path='/import' element={<Import />} />

              {/* Library tools */}
              <Route path='/places' element={<PlaceClustering />} />
              <Route path='/collaboration' element={<CollaborativeSpaces />} />

              {/* Studio Features — feature surfaces */}
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
              <Route
                path='/studio/ocr-search'
                element={<Navigate to='/analytics/ocr' replace />}
              />
              <Route
                path='/studio/video-analysis'
                element={<VideoAnalysisPanel />}
              />
              <Route path='/studio/ai-insights' element={<AIInsights />} />

              {/* Studio Features — developer showcases, dev builds only */}
              <Route
                path='/studio/modal-system'
                element={
                  <DevOnly>
                    <ModalSystem />
                  </DevOnly>
                }
              />
              <Route
                path='/studio/code-splitting'
                element={
                  <DevOnly>
                    <CodeSplitting />
                  </DevOnly>
                }
              />
              <Route
                path='/studio/tauri-integration'
                element={
                  <DevOnly>
                    <TauriIntegration />
                  </DevOnly>
                }
              />
              <Route
                path='/studio/modern-gallery'
                element={
                  <DevOnly>
                    <ModernGalleryDemoPage />
                  </DevOnly>
                }
              />
              <Route
                path='/studio/responsive-gallery'
                element={
                  <DevOnly>
                    <ResponsiveGalleryPage />
                  </DevOnly>
                }
              />

              {/* Advanced Analytics Routes */}
              <Route path='/analytics/dashboard' element={<AnalyticsDashboard />} />
              <Route path='/analytics/albums' element={<Navigate to='/albums' replace />} />
              <Route path='/analytics/faces' element={<Navigate to='/faces/advanced' replace />} />
              <Route path='/analytics/duplicates' element={<Navigate to='/duplicates' replace />} />
              <Route path='/analytics/ocr' element={<OCRTextSearchPanel />} />

              {/* Phase 8: Advanced Face Recognition Routes */}
              <Route path='/faces/advanced' element={<Navigate to='/people' replace />} />
              <Route path='/privacy/dashboard' element={<PrivacyDashboard />} />
              <Route path='/performance/advanced' element={<PerformanceDashboardAdvanced />} />

              {/* Utility Routes */}
              <Route path='/settings' element={<Settings />} />
              <Route path='/about' element={<About />} />
              <Route path='/pair' element={<PairPage />} />

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
