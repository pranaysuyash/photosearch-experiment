import { useEffect, useRef } from 'react';
import { Star } from 'lucide-react';
import { PhotoGrid } from '../components/gallery/PhotoGrid';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';

export default function FavoritesPage() {
  const {
    photos,
    loading,
    error,
    hasMore,
    loadMore,
    favoritesFilter,
    setFavoritesFilter,
  } = usePhotoSearchContext();

  const { openForPhoto } = usePhotoViewer();
  const previousFilterRef = useRef(favoritesFilter);

  useEffect(() => {
    setFavoritesFilter('favorites_only');
    return () => setFavoritesFilter(previousFilterRef.current);
  }, [setFavoritesFilter]);

  return (
    <div className="min-h-screen w-full">
      {/* Header */}
      <div className="max-w-screen-2xl mx-auto px-6 py-8">
        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-2xl glass-surface flex items-center justify-center">
            <Star size={24} className="text-yellow-400 fill-yellow-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Favorites</h1>
            <p className="text-white/60">
              {photos.length} {photos.length === 1 ? 'photo' : 'photos'} you've starred
            </p>
          </div>
        </div>

        {/* Photo Grid */}
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
