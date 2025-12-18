import { useEffect, useRef } from 'react';
import PhotoGrid from '../components/gallery/PhotoGrid';
import { PageSearchWrapper } from '../components/layout/PageSearchWrapper';
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
    setTypeFilter('videos');
    return () => setTypeFilter(previousTypeFilterRef.current);
  }, [setTypeFilter]);

  return (
    <PageSearchWrapper>
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
    </PageSearchWrapper>
  );
}

