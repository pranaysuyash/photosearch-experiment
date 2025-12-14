/**
 * Search Page
 *
 * Advanced search interface with all search features
 */

import { useState } from 'react';
import PhotoGrid from '../components/gallery/PhotoGrid';
import IntentRecognition from '../components/search/IntentRecognition';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import { PageSearchWrapper } from '../components/layout/PageSearchWrapper';

const Search = () => {
  const { photos, loading, error, hasMore, loadMore, searchQuery } =
    usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();

  const [intent, setIntent] = useState<string | null>(null);

  return (
    <PageSearchWrapper>
      <div className='mx-auto w-full'>
        {intent && (
          <div className='mb-4 flex justify-center'>
            <div className='btn-glass btn-glass--muted text-xs px-3 py-2'>
              Intent: {intent.replace('_', ' ')}
            </div>
          </div>
        )}

        {searchQuery && (
          <IntentRecognition
            query={searchQuery}
            onIntentDetected={(nextIntent: string) => setIntent(nextIntent)}
          />
        )}

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
};

export default Search;
