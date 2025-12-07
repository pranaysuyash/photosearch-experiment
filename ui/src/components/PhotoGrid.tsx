import { useEffect } from 'react';
import { api } from '../api';
import { motion } from 'framer-motion';
import { usePhotoSearch } from '../hooks/usePhotoSearch';

export function PhotoGrid({ query = "" }: { query?: string }) {
  const { results: photos, loading, error, setQuery } = usePhotoSearch({ 
    initialQuery: query,
    debounceMs: 0 // Debounce handled by parent App.tsx
  });

  // Sync prop query to hook
  useEffect(() => {
    setQuery(query.trim());
  }, [query, setQuery]);

  if (error) {
    return (
        <div className="flex flex-col items-center justify-center p-12 text-destructive">
            <p>Failed to load photos.</p>
            <button onClick={() => window.location.reload()} className="mt-2 text-xs underline">Retry</button>
        </div>
    );
  }

  if (loading) {
      return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-4">
            {[...Array(10)].map((_, i) => (
                <div key={i} className="aspect-square bg-secondary/30 animate-pulse rounded-lg" />
            ))}
        </div>
      );
  }

  if (photos.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
            <p>No photos found</p>
        </div>
      );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-4 pb-32">
        {photos.map((photo, i) => (
            <motion.div 
                key={photo.path}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="aspect-square bg-secondary rounded-lg overflow-hidden relative group"
            >
                <img 
                    src={api.getImageUrl(photo.path)} 
                    alt={photo.filename}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    loading="lazy"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs truncate">
                    {photo.filename}
                </div>
            </motion.div>
        ))}
    </div>
  );
}
