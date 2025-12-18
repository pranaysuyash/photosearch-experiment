import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Edit2,
  Trash2,
  RefreshCw,
  Zap,
  Loader2,
  MoreVertical,
} from 'lucide-react';
import { api, type Album, type Photo } from '../../api';
import { PhotoGrid } from '../gallery/PhotoGrid';
import { usePhotoViewer } from '../../contexts/PhotoViewerContext';

interface AlbumDetailProps {
  albumId: string;
  onBack: () => void;
  onEdit?: (album: Album) => void;
  onDelete?: (album: Album) => void;
}

export function AlbumDetail({
  albumId,
  onBack,
  onEdit,
  onDelete,
}: AlbumDetailProps) {
  const [album, setAlbum] = useState<Album | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showMenu, setShowMenu] = useState(false);

  const { openForPhoto } = usePhotoViewer();

  // Load album and photos on mount
  useEffect(() => {
    loadAlbum();
  }, [albumId]);

  const loadAlbum = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getAlbum(albumId, true);
      setAlbum(data.album);
      setPhotos(data.photos || []);
    } catch (err) {
      console.error('Failed to load album:', err);
      setError('Failed to load album. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefreshSmartAlbum = async () => {
    if (!album || !album.is_smart) return;
    setIsRefreshing(true);
    try {
      await api.refreshSmartAlbum(albumId);
      await loadAlbum(); // Reload to get updated photos
    } catch (err) {
      console.error('Failed to refresh smart album:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleDeleteAlbum = async () => {
    if (!album) return;
    if (onDelete) {
      onDelete(album);
    } else {
      // Default delete behavior
      if (
        confirm(
          `Are you sure you want to delete "${album.name}"? Photos will not be deleted.`
        )
      ) {
        try {
          await api.deleteAlbum(albumId);
          onBack();
        } catch (err) {
          console.error('Failed to delete album:', err);
          alert('Failed to delete album. Please try again.');
        }
      }
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="glass-panel px-6 py-4 flex items-center gap-3">
          <Loader2 className="animate-spin text-white/60" size={20} />
          <span className="text-white/80">Loading album...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !album) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="glass-panel px-6 py-4 max-w-md text-center">
          <p className="text-red-400 mb-3">{error || 'Album not found'}</p>
          <button onClick={onBack} className="btn-glass">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full">
      {/* Header */}
      <div className="sticky top-0 z-40 backdrop-blur-xl bg-black/20 border-b border-white/10">
        <div className="max-w-screen-2xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Back + Title */}
            <div className="flex items-center gap-4">
              <button
                onClick={onBack}
                className="btn-glass w-10 h-10 p-0 justify-center"
                aria-label="Go back"
              >
                <ArrowLeft size={20} />
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold text-white">{album.name}</h1>
                  {album.is_smart && (
                    <div className="px-2 py-1 rounded-lg bg-yellow-500/20 border border-yellow-400/30">
                      <Zap size={14} className="text-yellow-400" />
                    </div>
                  )}
                </div>
                {album.description && (
                  <p className="text-sm text-white/60 mt-1">{album.description}</p>
                )}
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              {/* Photo count */}
              <span className="text-sm text-white/60 mr-2">
                {photos.length} {photos.length === 1 ? 'photo' : 'photos'}
              </span>

              {/* Refresh for smart albums */}
              {album.is_smart && (
                <button
                  onClick={handleRefreshSmartAlbum}
                  disabled={isRefreshing}
                  className="btn-glass w-10 h-10 p-0 justify-center"
                  aria-label="Refresh smart album"
                >
                  <RefreshCw
                    size={18}
                    className={isRefreshing ? 'animate-spin' : ''}
                  />
                </button>
              )}

              {/* Menu button for regular albums */}
              {!album.is_smart && (
                <div className="relative">
                  <button
                    onClick={() => setShowMenu(!showMenu)}
                    className="btn-glass w-10 h-10 p-0 justify-center"
                    aria-label="Album menu"
                  >
                    <MoreVertical size={18} />
                  </button>

                  {/* Dropdown menu */}
                  {showMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute right-0 mt-2 w-48 glass-panel shadow-lg rounded-lg overflow-hidden"
                      onMouseLeave={() => setShowMenu(false)}
                    >
                      <button
                        onClick={() => {
                          setShowMenu(false);
                          onEdit?.(album);
                        }}
                        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-white/5 text-white/80 hover:text-white transition-colors"
                      >
                        <Edit2 size={16} />
                        <span>Edit Album</span>
                      </button>
                      <button
                        onClick={() => {
                          setShowMenu(false);
                          handleDeleteAlbum();
                        }}
                        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-red-500/10 text-red-400 hover:text-red-300 transition-colors"
                      >
                        <Trash2 size={16} />
                        <span>Delete Album</span>
                      </button>
                    </motion.div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Photo Grid */}
      <div className="max-w-screen-2xl mx-auto px-6 py-8">
        {photos.length === 0 ? (
          <div className="flex items-center justify-center h-[60vh]">
            <div className="glass-panel p-8 max-w-md text-center">
              <p className="text-white/60 mb-2">No photos in this album</p>
              {album.is_smart && (
                <p className="text-sm text-white/40">
                  This smart album will automatically populate when matching photos are
                  found
                </p>
              )}
            </div>
          </div>
        ) : (
          <PhotoGrid
            photos={photos}
            onPhotoSelect={(photo) => openForPhoto(photos, photo)}
          />
        )}
      </div>
    </div>
  );
}
