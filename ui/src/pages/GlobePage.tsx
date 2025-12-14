import { motion } from 'framer-motion';
import { PhotoGlobe } from '../components/features/PhotoGlobe';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';

const GlobePage = () => {
  const {
    photos,
    loading,
    error,
  } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();

  const hasResults = photos.length > 0;

  return (
    <div className='w-full'>
      {!hasResults && !loading && (
        <div className='glass-surface rounded-2xl p-8 text-center text-muted-foreground max-w-2xl mx-auto'>
          <div className='text-lg font-semibold text-foreground mb-2'>
            No photos loaded yet
          </div>
          <div className='text-sm'>
            Search above to load your library, then explore it in Globe view.
          </div>
        </div>
      )}

      {error && (
        <div className='glass-surface glass-surface--strong rounded-2xl p-4 text-sm text-destructive'>
          {String(error)}
        </div>
      )}

      {hasResults && (
        <>
          {/* Larger globe container - spans full height since search is in header */}
          <motion.div
            className='w-full'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className='glass-surface rounded-3xl overflow-hidden mx-auto'>
              <div className='h-[calc(100vh-5rem)] min-h-[800px]'>
                <PhotoGlobe
                  photos={photos}
                  onPhotoSelect={(photo) => openForPhoto(photos, photo)}
                />
              </div>
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
};

export default GlobePage;
