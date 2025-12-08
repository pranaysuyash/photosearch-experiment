import { motion } from 'framer-motion';
import Masonry from 'react-masonry-css';
import { type Photo, api } from '../api';

interface PhotoGridProps {
  photos: Photo[];
  loading?: boolean;
  error?: Error | null;
  onPhotoSelect: (photo: Photo) => void;
}

export function PhotoGrid({ photos, loading, error, onPhotoSelect }: PhotoGridProps) {
  if (error) {
    return (
        <div className="flex flex-col items-center justify-center p-12 text-destructive">
            <p>Failed to load photos.</p>
            <button onClick={() => window.location.reload()} className="mt-2 text-xs underline">Retry</button>
        </div>
    );
  }

  const breakpointColumnsObj = {
    default: 5,
    1536: 5,
    1280: 4,
    1024: 3,
    768: 2,
    640: 1
  };

  if (loading) {
      return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-4">
            {[...Array(10)].map((_, i) => (
                <div key={i} className="aspect-[3/4] bg-secondary/30 animate-pulse rounded-xl" />
            ))}
        </div>
      );
  }

  if (photos.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center p-24 text-muted-foreground">
            <p className="text-lg">No photos found</p>
            <p className="text-sm opacity-50">Try searching for something else</p>
        </div>
      );
  }

  return (
    <div className="p-4 pb-32">
        <Masonry
            breakpointCols={breakpointColumnsObj}
            className="flex -ml-4 w-auto"
            columnClassName="pl-4 bg-clip-padding"
        >
            {photos.map((photo, i) => (
                <motion.div 
                    key={photo.path}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: i * 0.05, ease: "easeOut" }}
                    onClick={() => onPhotoSelect(photo)}
                    className="mb-4 break-inside-avoid relative group rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-shadow duration-300 bg-card cursor-pointer"
                >
                    <img 
                        src={api.getImageUrl(photo.path)} 
                        alt={photo.filename}
                        className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-110"
                        loading="lazy"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <div className="absolute bottom-0 left-0 right-0 p-4 translate-y-4 group-hover:translate-y-0 transition-transform duration-300 opacity-0 group-hover:opacity-100">
                        <p className="text-white text-sm font-medium truncate">{photo.filename}</p>
                        <p className="text-white/70 text-xs truncate mt-0.5">{photo.path.split('/').slice(-2).join('/')}</p>
                    </div>
                </motion.div>
            ))}
        </Masonry>
    </div>
  );
}
