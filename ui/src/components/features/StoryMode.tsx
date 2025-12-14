import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Film } from 'lucide-react';
import { api, type Photo } from '../../api';

interface StoryModeProps {
  photos: Photo[];
  loading?: boolean;
  onPhotoSelect?: (photo: Photo) => void;
  hasMore?: boolean;
  loadMore?: () => void;
}

export function StoryMode({
  photos,
  loading,
  onPhotoSelect,
  hasMore,
  loadMore,
}: StoryModeProps) {
  const observerTarget = useRef<HTMLDivElement>(null);

  // Intersection observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading && loadMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    const target = observerTarget.current;
    if (target) observer.observe(target);

    return () => {
      if (target) observer.unobserve(target);
    };
  }, [hasMore, loading, loadMore]);

  if (loading && photos.length === 0) {
    return (
      <div className='text-center p-24 text-muted-foreground animate-pulse'>
        <div className='flex flex-col items-center gap-3'>
          <motion.div
            className='w-8 h-8 border-2 border-primary border-t-transparent rounded-full'
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          />
          <p>Curating your museum...</p>
        </div>
      </div>
    );
  }

  if (photos.length === 0 && !loading) {
    return (
      <div className='flex flex-col items-center justify-center p-24 text-muted-foreground'>
        <motion.div
          className='w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mb-4'
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Film size={24} />
        </motion.div>
        <p className='text-lg mb-2'>No photos found</p>
        <p className='text-sm opacity-75'>
          Start by scanning your media library
        </p>
      </div>
    );
  }

  return (
    <div className='w-full relative'>
      {/* Photo Grid using same pattern as working PhotoGrid */}
      {photos.length > 0 && (
        <div className='grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mt-6'>
          {photos.map((photo, index) => (
            <motion.div
              key={photo.path}
              className='group relative bg-card rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer'
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.05 }}
              whileHover={{ scale: 1.02, y: -4 }}
              onClick={() => onPhotoSelect?.(photo)}
            >
              {/* Image with lazy loading */}
              <img
                src={api.getImageUrl(photo.path, 800)}
                alt={photo.filename}
                className='w-full h-auto object-cover transition-transform duration-700 group-hover:scale-110'
                loading='lazy'
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />

              {/* Enhanced overlay */}
              <div className='absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300' />

              {/* Metadata */}
              <div className='absolute bottom-0 left-0 right-0 p-4 translate-y-4 group-hover:translate-y-0 transition-transform duration-300 opacity-0 group-hover:opacity-100'>
                <h3 className='text-white text-sm font-semibold truncate'>
                  {photo.filename}
                </h3>
                <p className='text-white/70 text-xs truncate mt-1'>
                  {photo.path.split('/').slice(-2).join('/')}
                </p>

                {/* Score visualization for semantic search results */}
                {photo.score > 0 && (
                  <div className='mt-2 flex items-center gap-2'>
                    <div className='h-1 flex-1 bg-white/30 rounded-full overflow-hidden'>
                      <div
                        className={`h-full bg-green-400 transition-all duration-500 score-fill-${Math.round(Math.round(photo.score * 100) / 10) * 10
                          }`}
                      />
                    </div>
                    <span className='text-[10px] text-white/90'>
                      {Math.round(photo.score * 100)}%
                    </span>
                  </div>
                )}
              </div>

              {/* Video indicator */}
              {photo.filename.match(/\.(mp4|mov|webm|mkv)$/i) && (
                <div className='absolute top-3 right-3 bg-black/50 backdrop-blur-sm rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity'>
                  <div className='w-2 h-2 bg-white rounded-full'></div>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Loading sentinel */}
      <div
        ref={observerTarget}
        className='h-24 w-full flex items-center justify-center mt-8'
      >
        {loading && photos.length > 0 && (
          <motion.div
            className='flex flex-col items-center gap-3'
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div
              className='w-6 h-6 border-2 border-primary border-t-transparent rounded-full'
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <span className='text-sm text-muted-foreground animate-pulse'>
              Loading more memories...
            </span>
          </motion.div>
        )}
        {!hasMore && photos.length > 0 && (
          <motion.div
            className='text-center py-8 opacity-60'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 0.6, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div
              className='w-2 h-2 bg-primary/40 rounded-full mx-auto mb-3'
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className='text-xs uppercase tracking-widest text-muted-foreground font-medium'>
              The End
            </span>
          </motion.div>
        )}
      </div>
    </div>
  );
}
