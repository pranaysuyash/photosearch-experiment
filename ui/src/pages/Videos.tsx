import { useEffect, useRef } from 'react';
import PhotoGrid from '../components/gallery/PhotoGrid';
// Removed PageSearchWrapper - global DynamicNotchSearch in Layout.tsx handles search
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';

export default function VideosPage() {
  const {
    photos,
    loading,
    error,
    hasMore,
    loadMore,
    typeFilter,
    setTypeFilter,
  } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();
  const previousTypeFilterRef = useRef(typeFilter);

  useEffect(() => {
    const previous = previousTypeFilterRef.current;
    let cancelled = false;

    const rafId = window.requestAnimationFrame(() => {
      if (!cancelled) setTypeFilter('videos');
    });

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(rafId);
      // Schedule restore asynchronously to avoid synchronous setState in cleanup
      window.requestAnimationFrame(() => {
        if (!cancelled) setTypeFilter(previous);
      });
    };
  }, [setTypeFilter]);

  return (
    <div className='w-full'>
      <div className='mx-auto w-full'>
        <div className='mb-4 flex justify-center'>
          <div className='btn-glass btn-glass--muted text-xs px-3 py-2'>
            Videos
          </div>
        </div>
        <PhotoGrid
          photos={photos}
          loading={loading}
          error={error}
          onPhotoSelect={(photo) => openForPhoto(photos, photo)}
          hasMore={hasMore}
          loadMore={loadMore}
        />
      </div>
    </div>
  );
}
