import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Loader2, FolderOpen } from 'lucide-react';
import { api, type Album } from '../../api';
import { AlbumCard } from './AlbumCard';

interface AlbumGridProps {
  onAlbumClick: (album: Album) => void;
  onCreateAlbum: () => void;
}

export function AlbumGrid({ onAlbumClick, onCreateAlbum }: AlbumGridProps) {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load albums on mount
  useEffect(() => {
    loadAlbums();
  }, []);

  const loadAlbums = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listAlbums(true);
      setAlbums(data.albums || []);
    } catch (err) {
      console.error('Failed to load albums:', err);
      setError('Failed to load albums. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="glass-panel px-6 py-4 flex items-center gap-3">
          <Loader2 className="animate-spin text-white/60" size={20} />
          <span className="text-white/80">Loading albums...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="glass-panel px-6 py-4 max-w-md text-center">
          <p className="text-red-400 mb-3">{error}</p>
          <button onClick={loadAlbums} className="btn-glass">
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (albums.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-6">
        <div className="glass-panel p-8 max-w-md text-center">
          <FolderOpen size={48} className="mx-auto mb-4 text-white/40" />
          <h3 className="text-xl font-semibold text-white mb-2">No Albums Yet</h3>
          <p className="text-white/60 mb-6">
            Create your first album to organize your photos
          </p>
          <button
            onClick={onCreateAlbum}
            className="btn-glass inline-flex items-center gap-2"
          >
            <Plus size={20} />
            Create Album
          </button>
        </div>
      </div>
    );
  }

  // Separate smart and regular albums
  const smartAlbums = albums.filter((a) => a.is_smart);
  const regularAlbums = albums.filter((a) => !a.is_smart);

  return (
    <div className="w-full space-y-8 pb-24">
      {/* Smart Albums Section */}
      {smartAlbums.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white/90">Smart Albums</h2>
            <span className="text-sm text-white/50">{smartAlbums.length}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <AnimatePresence mode="popLayout">
              {smartAlbums.map((album) => (
                <motion.div
                  key={album.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.2 }}
                >
                  <AlbumCard album={album} onClick={() => onAlbumClick(album)} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </section>
      )}

      {/* Regular Albums Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white/90">My Albums</h2>
          <span className="text-sm text-white/50">{regularAlbums.length}</span>
        </div>

        {regularAlbums.length === 0 ? (
          <div className="glass-panel p-8 text-center">
            <p className="text-white/60 mb-4">No custom albums yet</p>
            <button
              onClick={onCreateAlbum}
              className="btn-glass inline-flex items-center gap-2"
            >
              <Plus size={20} />
              Create Album
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <AnimatePresence mode="popLayout">
              {regularAlbums.map((album) => (
                <motion.div
                  key={album.id}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.2 }}
                >
                  <AlbumCard album={album} onClick={() => onAlbumClick(album)} />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </section>

      {/* Floating Action Button */}
      <motion.button
        onClick={onCreateAlbum}
        className="fixed bottom-8 right-8 w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg hover:shadow-xl flex items-center justify-center z-50"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Create new album"
      >
        <Plus size={28} className="text-white" />
      </motion.button>
    </div>
  );
}
