/**
 * Story Mode Page
 *
 * Full-screen immersive story mode for browsing photos
 */

import { StoryMode } from '../components/features/StoryMode';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import { PageSearchWrapper } from '../components/layout/PageSearchWrapper';

const StoryModePage = () => {
  const { photos, loading, error, hasMore, loadMore } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();

  return (
    <PageSearchWrapper>
      <div className='mx-auto w-full max-w-7xl'>
        <div className='mb-4 text-center'>
          <h1 className='text-xl font-semibold tracking-tight text-foreground'>
            Story mode
          </h1>
          <p className='text-sm text-muted-foreground'>
            A more cinematic way to browse — fewer controls, more flow.
          </p>
        </div>

        <StoryMode
          photos={photos}
          loading={loading}
          onPhotoSelect={(photo) => openForPhoto(photos, photo)}
          hasMore={hasMore}
          loadMore={loadMore}
        />

        {error && (
          <div className='glass-surface glass-surface--strong rounded-2xl p-4 mt-4 text-sm text-destructive'>
            {String(error)}
          </div>
        )}
      </div>
    </PageSearchWrapper>
  );
};

export default StoryModePage;
