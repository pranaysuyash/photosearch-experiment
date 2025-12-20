import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, Hash, Loader2, Plus, X } from 'lucide-react';
import { api, type TagSummary } from '../../api';

interface AddToTagDialogProps {
  isOpen: boolean;
  photoPaths: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export function AddToTagDialog({
  isOpen,
  photoPaths,
  onClose,
  onSuccess,
}: AddToTagDialogProps) {
  const [tags, setTags] = useState<TagSummary[]>([]);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [newTagName, setNewTagName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setSelectedTags(new Set());
    setNewTagName('');
    setError(null);
    setIsLoading(true);
    api
      .listTags(200, 0)
      .then((res) => setTags(res.tags || []))
      .catch(() => setError('Failed to load tags. Please try again.'))
      .finally(() => setIsLoading(false));
  }, [isOpen]);

  const normalizedNewTag = useMemo(() => newTagName.trim(), [newTagName]);

  const toggle = (name: string) => {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const submit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const selected = new Set(selectedTags);
      if (normalizedNewTag) {
        await api.createTag(normalizedNewTag);
        selected.add(normalizedNewTag);
      }
      if (selected.size === 0) {
        setError('Select or create at least one tag');
        return;
      }
      await Promise.all(
        Array.from(selected).map((tag) => api.addPhotosToTag(tag, photoPaths))
      );
      onSuccess();
      onClose();
    } catch (e) {
      setError('Failed to add tags. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isSubmitting) onClose();
  };

  if (!isOpen) return null;

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className='fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm'
        onClick={handleBackdropClick}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className='glass-panel w-full max-w-md mx-4 p-6 max-h-[80vh] flex flex-col'
        >
          <div className='flex items-center justify-between mb-6'>
            <div className='flex items-center gap-3'>
              <div className='w-10 h-10 rounded-lg glass-surface flex items-center justify-center'>
                <Hash size={18} className='text-primary' />
              </div>
              <div>
                <h2 className='text-xl font-semibold text-white'>Add Tags</h2>
                <p className='text-sm text-white/60'>
                  {photoPaths.length}{' '}
                  {photoPaths.length === 1 ? 'item' : 'items'} selected
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className='text-white/60 hover:text-white transition-colors'
              aria-label='Close'
            >
              <X size={24} />
            </button>
          </div>

          <div className='mb-4 flex items-center gap-2'>
            <input
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              placeholder='Create a new tag…'
              className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-white/20'
              disabled={isSubmitting}
            />
            <button
              type='button'
              className='btn-glass btn-glass--muted text-sm px-3 py-2'
              onClick={() => {
                if (!normalizedNewTag) return;
                toggle(normalizedNewTag);
              }}
              disabled={!normalizedNewTag || isSubmitting}
              title='Select the new tag'
            >
              <Plus size={16} />
            </button>
          </div>

          <div className='flex-1 overflow-y-auto -mx-2 px-2 mb-6'>
            {isLoading ? (
              <div className='flex items-center justify-center py-10 text-white/60'>
                <Loader2 size={18} className='animate-spin mr-2' />
                Loading tags…
              </div>
            ) : tags.length === 0 ? (
              <div className='text-center py-10 text-white/60'>
                No tags yet. Create one above.
              </div>
            ) : (
              <div className='space-y-2'>
                {tags.map((t) => {
                  const isSelected = selectedTags.has(t.name);
                  return (
                    <motion.button
                      key={t.name}
                      onClick={() => toggle(t.name)}
                      disabled={isSubmitting}
                      className={`w-full px-4 py-3 rounded-lg border transition-all text-left flex items-center gap-3 ${isSelected
                          ? 'bg-fuchsia-500/20 border-fuchsia-500/40'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                        } disabled:opacity-50`}
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${isSelected
                            ? 'bg-fuchsia-500 border-fuchsia-500'
                            : 'border-white/30'
                          }`}
                      >
                        {isSelected && <Check size={14} className='text-white' />}
                      </div>
                      <div className='flex-1 min-w-0'>
                        <h3 className='text-white font-medium truncate'>
                          {t.name}
                        </h3>
                      </div>
                      <div className='text-xs text-white/50'>
                        {t.photo_count}
                      </div>
                    </motion.button>
                  );
                })}
              </div>
            )}
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className='px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 mb-4'
            >
              <p className='text-sm text-red-400'>{error}</p>
            </motion.div>
          )}

          <div className='flex gap-3'>
            <button
              type='button'
              onClick={onClose}
              disabled={isSubmitting}
              className='flex-1 btn-glass'
            >
              Cancel
            </button>
            <button
              type='button'
              onClick={submit}
              disabled={isSubmitting}
              className='flex-1 btn-glass btn-glass--primary px-6 py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2'
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className='animate-spin' />
                  <span>Saving…</span>
                </>
              ) : (
                <>
                  <Plus size={18} />
                  <span>Add Tags</span>
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

