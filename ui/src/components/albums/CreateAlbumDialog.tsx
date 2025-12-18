import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2, Folder } from 'lucide-react';
import { api, type Album } from '../../api';

interface CreateAlbumDialogProps {
  isOpen: boolean;
  editAlbum?: Album | null; // If provided, edit mode
  onClose: () => void;
  onSuccess: (album: Album) => void;
}

export function CreateAlbumDialog({
  isOpen,
  editAlbum,
  onClose,
  onSuccess,
}: CreateAlbumDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEditMode = !!editAlbum;

  // Populate fields in edit mode
  useEffect(() => {
    if (editAlbum) {
      setName(editAlbum.name);
      setDescription(editAlbum.description || '');
    } else {
      setName('');
      setDescription('');
    }
    setError(null);
  }, [editAlbum, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Album name is required');
      return;
    }

    setIsSubmitting(true);
    try {
      if (isEditMode && editAlbum) {
        // Update existing album
        const result = await api.updateAlbum(editAlbum.id, {
          name: name.trim(),
          description: description.trim() || undefined,
        });
        onSuccess(result.album);
      } else {
        // Create new album
        const result = await api.createAlbum(name.trim(), description.trim() || undefined);
        onSuccess(result.album);
      }
      onClose();
    } catch (err: unknown) {
      console.error('Failed to save album:', err);
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to save album. Please try again.';
      setError(errorMessage);
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
          className="glass-panel w-full max-w-md mx-4 p-6"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <Folder size={20} className="text-white" />
              </div>
              <h2 className="text-xl font-semibold text-white">
                {isEditMode ? 'Edit Album' : 'Create Album'}
              </h2>
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

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Album Name */}
            <div>
              <label htmlFor="album-name" className="block text-sm font-medium text-white/80 mb-2">
                Album Name *
              </label>
              <input
                id="album-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Summer 2024"
                disabled={isSubmitting}
                className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all disabled:opacity-50"
                maxLength={100}
                autoFocus
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="album-desc" className="block text-sm font-medium text-white/80 mb-2">
                Description (Optional)
              </label>
              <textarea
                id="album-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a description for this album..."
                disabled={isSubmitting}
                rows={3}
                className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all resize-none disabled:opacity-50"
                maxLength={500}
              />
              <div className="text-xs text-white/40 mt-1">
                {description.length}/500 characters
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20"
              >
                <p className="text-sm text-red-400">{error}</p>
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1 btn-glass"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !name.trim()}
                className="flex-1 px-6 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>{isEditMode ? 'Saving...' : 'Creating...'}</span>
                  </>
                ) : (
                  <span>{isEditMode ? 'Save Changes' : 'Create Album'}</span>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
