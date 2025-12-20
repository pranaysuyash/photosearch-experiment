import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2, FolderPlus, Check, Folder, Plus } from 'lucide-react';
import { api, type Album } from '../../api';

interface AddToAlbumDialogProps {
  isOpen: boolean;
  photoPaths: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export function AddToAlbumDialog({
  isOpen,
  photoPaths,
  onClose,
  onSuccess,
}: AddToAlbumDialogProps) {
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load albums on open
  useEffect(() => {
    if (isOpen) {
      loadAlbums();
      setSelectedAlbumIds(new Set());
      setError(null);
    }
  }, [isOpen]);

  const loadAlbums = async () => {
    setIsLoading(true);
    try {
      const data = await api.listAlbums(false); // Exclude smart albums
      setAlbums(data.albums || []);
    } catch (err) {
      console.error('Failed to load albums:', err);
      setError('Failed to load albums. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAlbum = (albumId: string) => {
    const newSet = new Set(selectedAlbumIds);
    if (newSet.has(albumId)) {
      newSet.delete(albumId);
    } else {
      newSet.add(albumId);
    }
    setSelectedAlbumIds(newSet);
  };

  const handleSubmit = async () => {
    if (selectedAlbumIds.size === 0) {
      setError('Please select at least one album');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Add photos to each selected album
      await Promise.all(
        Array.from(selectedAlbumIds).map((albumId) =>
          api.addPhotosToAlbum(albumId, photoPaths)
        )
      );
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Failed to add photos to albums:', err);
      setError('Failed to add photos. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isSubmitting) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={handleBackdropClick}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="glass-panel w-full max-w-md mx-4 p-6 max-h-[80vh] flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg glass-surface flex items-center justify-center">
                <FolderPlus size={20} className="text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">Add to Albums</h2>
                <p className="text-sm text-white/60">
                  {photoPaths.length} {photoPaths.length === 1 ? 'photo' : 'photos'}{' '}
                  selected
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="text-white/60 hover:text-white transition-colors"
              aria-label="Close"
            >
              <X size={24} />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto -mx-2 px-2 mb-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="animate-spin text-white/60" size={24} />
              </div>
            ) : albums.length === 0 ? (
              <div className="text-center py-12">
                <Folder size={48} className="mx-auto mb-4 text-white/40" />
                <p className="text-white/60 mb-4">No albums yet</p>
                <p className="text-sm text-white/40">
                  Create an album first to add photos
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {albums.map((album) => {
                  const isSelected = selectedAlbumIds.has(album.id);
                  return (
                    <motion.button
                      key={album.id}
                      onClick={() => toggleAlbum(album.id)}
                      disabled={isSubmitting}
                      className={`w-full px-4 py-3 rounded-lg border transition-all text-left flex items-center gap-3 ${isSelected
                          ? 'bg-blue-500/20 border-blue-500/50'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                        } disabled:opacity-50`}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      {/* Checkbox */}
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${isSelected
                            ? 'bg-blue-500 border-blue-500'
                            : 'border-white/30'
                          }`}
                      >
                        {isSelected && <Check size={14} className="text-white" />}
                      </div>

                      {/* Album Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-white font-medium truncate">
                          {album.name}
                        </h3>
                        {album.description && (
                          <p className="text-sm text-white/50 truncate">
                            {album.description}
                          </p>
                        )}
                      </div>

                      {/* Photo count */}
                      <div className="text-xs text-white/50">
                        {album.photo_count}
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-4"
            >
              <p className="text-sm text-red-400">{error}</p>
            </motion.div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 btn-glass"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || selectedAlbumIds.size === 0 || albums.length === 0}
              className="flex-1 btn-glass btn-glass--primary px-6 py-3 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <Plus size={18} />
                  <span>
                    Add to {selectedAlbumIds.size}{' '}
                    {selectedAlbumIds.size === 1 ? 'Album' : 'Albums'}
                  </span>
                </>
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
