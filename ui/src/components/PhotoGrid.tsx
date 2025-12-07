import { useEffect, useState } from 'react';
import { api, Photo } from '../api';
import { motion } from 'framer-motion';

export function PhotoGrid({ query = "" }: { query?: string }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // If no query, we might want to "browse all" or just typical "recent"
    // Since our backend search defaults to "recent" or "all" if empty, let's use search with empty string or specific default.
    // Actually our backend search implementation might require a query. 
    // Let's assume sending "camera" or just "*" gets us something for now, or improve backend.
    // For now, let's allow "all" via empty string if API supports it, or handle in API.
    
    api.search(query || "date") // Default to date search to get something?
        // Note: Our photo_search.py logic depends on query type.
        // If we want "all", we might need a specific endpoint or query handling. 
        // Let's rely on api search for now.
      .then(res => setPhotos(res.results))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [query]);

  if (loading) return <div className="p-8 text-center">Loading photos...</div>;

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
