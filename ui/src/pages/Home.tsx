/**
 * Home Page
 *
 * Main landing page with photo grid and search
 */

import PhotoGrid from '../components/gallery/PhotoGrid';
import { SonicTimeline } from '../components/gallery/SonicTimeline';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import { motion } from 'framer-motion';
import { api } from '../api';
import { useState, useEffect } from 'react';

const Home = () => {
  const {
    photos,
    loading,
    error,
    hasMore,
    loadMore,
  } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();
  const [libraryCount, setLibraryCount] = useState<number | null>(null);

  useEffect(() => {
    api
      .getStats()
      .then((s) => {
        setLibraryCount(s.active_files || 0);
      })
      .catch(() => setLibraryCount(0));
  }, []);

  const hasResults = photos.length > 0;
  const isLibraryEmpty = libraryCount === 0 && !loading;
  const showLoadingHero = loading && photos.length === 0;

  return (
    <div className='min-h-screen flex flex-col gap-6'>
      {isLibraryEmpty && (
        <div className='flex flex-col items-center justify-center min-h-[50vh] text-center gap-6'>
          <h1 className='text-4xl font-semibold bg-gradient-to-b from-foreground to-muted-foreground bg-clip-text text-transparent'>
            Welcome to Living Museum
          </h1>
          <p className='text-muted-foreground max-w-md'>
            Your library is empty. Scan a folder to start rediscovering your
            memories.
          </p>
          <button
            onClick={() => {
              // Trigger scan via Spotlight or direct API
              // For now, simpler to tell user to use shortcut, but a button is better.
              // We'll trust they can find the scan button in Spotlight or we can add a direct scan flow here if needed.
              // But since Spotlight is the main entry:
              window.dispatchEvent(
                new KeyboardEvent('keydown', { key: 'k', metaKey: true })
              );
            }}
            className='btn-glass btn-glass--primary px-8 py-3 text-lg'
          >
            Start Scanning (⌘K)
          </button>
        </div>
      )}

      {/* Loading state: keep the page calm (hero handles zero-photo loading) */}
      {showLoadingHero && <div className='h-8' />}

      <motion.div
        className='mt-2 flex-1'
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
      >
        <PhotoGrid
          photos={photos}
          loading={loading}
          error={error}
          onPhotoSelect={(photo) => openForPhoto(photos, photo)}
          hasMore={hasMore}
          loadMore={loadMore}
        />
      </motion.div>

      {/* Sonic Timeline (only when there are results) */}
      {hasResults && (
        <div className='mt-0 p-0'>
          <SonicTimeline />
        </div>
      )}
    </div>
  );
};

export default Home;
