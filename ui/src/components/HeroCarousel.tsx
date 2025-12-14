import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api } from '../api';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';

export function HeroCarousel({ onEnter3D }: { onEnter3D?: () => void }) {
  const { photos: results } = usePhotoSearchContext();
  // Stable deterministic shuffle based on path hash to avoid using Math.random
  const photos = useMemo(() => {
    if (!results || results.length === 0) return [];
    const hash = (s: string) => {
      let h = 2166136261;
      for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
      }
      return h >>> 0;
    };
    const shuffled = [...results].sort((a, b) => hash(a.path) - hash(b.path));
    return shuffled.slice(0, 5);
  }, [results]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Remove the search effect since context handles initial fetch

  // photos are derived from results; no local setState to avoid setState-in-effect pattern

  useEffect(() => {
    if (photos.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % photos.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [photos]);

  if (photos.length === 0) return null;

  return (
    <div className='relative w-full h-[50vh] overflow-hidden bg-black'>
      <AnimatePresence mode='wait'>
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5 }}
          className='absolute inset-0'
        >
          <img
            src={api.getImageUrl(photos[currentIndex].path)}
            alt='Hero memory'
            className='w-full h-full object-cover opacity-80'
          />
          <div className='absolute inset-0 bg-gradient-to-t from-background to-transparent' />
        </motion.div>
      </AnimatePresence>

      <div className='absolute bottom-8 left-8 z-10'>
        <h2 className='text-4xl font-bold text-white mb-2 drop-shadow-lg'>
          Welcome Back
        </h2>
        <p className='text-white/80 text-lg drop-shadow-md mb-6'>
          Rediscover your memories from {photos[currentIndex]?.filename}
        </p>

        {onEnter3D && (
          <button
            onClick={onEnter3D}
            className='btn-glass btn-glass--muted text-white flex items-center gap-2 font-medium px-6 py-2'
          >
            Explore in 3D
          </button>
        )}
      </div>
    </div>
  );
}
