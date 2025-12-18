import { useEffect, useMemo, useState } from 'react';
import { Trash2, RotateCcw } from 'lucide-react';
import { api, type Photo, type TrashItem } from '../api';
import SecureLazyImage from '../components/gallery/SecureLazyImage';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';

function filenameFor(item: TrashItem) {
  const raw = item.original_path || item.trashed_path || '';
  const parts = raw.split('/');
  return parts[parts.length - 1] || raw;
}

export default function TrashPage() {
  const { openForPhoto } = usePhotoViewer();
  const [items, setItems] = useState<TrashItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const photosForViewer = useMemo<Photo[]>(
    () =>
      items.map((it) => ({
        path: it.trashed_path,
        filename: filenameFor(it),
        score: 0,
        metadata: {},
      })),
    [items]
  );

  const selectedIds = useMemo(
    () => Object.keys(selected).filter((k) => selected[k]),
    [selected]
  );

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listTrash();
      setItems(res.items || []);
      setSelected({});
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Trash');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const restoreItems = async (ids: string[]) => {
    if (!ids.length) return;
    setWorking(true);
    try {
      await api.trashRestore(ids);
      await refresh();
    } finally {
      setWorking(false);
    }
  };

  const deleteItems = async (ids?: string[]) => {
    const target = ids && ids.length ? ids : null;
    const confirmMsg = target
      ? `Permanently delete ${target.length} item(s) from Trash?`
      : 'Permanently delete everything in Trash?';
    if (!window.confirm(confirmMsg)) return;
    setWorking(true);
    try {
      await api.trashEmpty(target ?? undefined);
      await refresh();
    } finally {
      setWorking(false);
    }
  };

  return (
    <div className='min-h-screen w-full max-w-screen-2xl mx-auto px-6 py-8'>
      <div className='flex items-start justify-between gap-4 mb-6'>
        <div>
          <h1 className='text-2xl font-semibold text-foreground'>Trash</h1>
          <p className='text-sm text-muted-foreground'>
            Recently deleted items. Restore or permanently delete.
          </p>
        </div>

        <div className='flex items-center gap-2'>
          <button
            className='btn-glass btn-glass--muted text-sm px-4 py-2'
            onClick={() => refresh()}
            disabled={loading || working}
          >
            Refresh
          </button>
          <button
            className='btn-glass btn-glass--primary text-sm px-4 py-2'
            onClick={() => restoreItems(selectedIds)}
            disabled={working || selectedIds.length === 0}
            title='Restore selected'
          >
            <RotateCcw size={16} />
            Restore
          </button>
          <button
            className='btn-glass btn-glass--danger text-sm px-4 py-2'
            onClick={() =>
              deleteItems(selectedIds.length ? selectedIds : undefined)
            }
            disabled={working || items.length === 0}
            title='Delete permanently'
          >
            <Trash2 size={16} />
            {selectedIds.length ? 'Delete' : 'Empty'}
          </button>
        </div>
      </div>

      {error && (
        <div className='mb-4 btn-glass btn-glass--danger text-sm px-4 py-3'>
          {error}
        </div>
      )}

      {loading ? (
        <div className='text-sm text-muted-foreground'>Loading…</div>
      ) : items.length === 0 ? (
        <div className='glass-surface rounded-2xl p-10 text-center text-muted-foreground'>
          Trash is empty.
        </div>
      ) : (
        <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4'>
          {items.map((it, idx) => {
            const isSelected = Boolean(selected[it.id]);
            const label = filenameFor(it);
            return (
              <div
                key={it.id}
                className='group relative rounded-2xl overflow-hidden border border-white/5 bg-white/5 hover:bg-white/10 transition-colors'
              >
                <button
                  className='absolute inset-0'
                  onClick={() =>
                    openForPhoto(photosForViewer, photosForViewer[idx])
                  }
                  aria-label={`Open ${label}`}
                  title={label}
                />

                <div className='aspect-square relative'>
                  <SecureLazyImage
                    path={it.trashed_path}
                    size={380}
                    alt={label}
                    className='w-full h-full rounded'
                    showBadge={false}
                  />
                  <div className='absolute top-2 left-2 z-10'>
                    <label className='btn-glass btn-glass--muted w-9 h-9 p-0 justify-center cursor-pointer'>
                      <input
                        type='checkbox'
                        className='sr-only'
                        checked={isSelected}
                        onChange={(e) =>
                          setSelected((prev) => ({
                            ...prev,
                            [it.id]: e.target.checked,
                          }))
                        }
                        aria-label={`Select ${label}`}
                      />
                      <span className='text-xs'>{isSelected ? '✓' : ''}</span>
                    </label>
                  </div>
                </div>

                <div className='p-3 relative z-10 flex items-center justify-between gap-2'>
                  <div className='min-w-0'>
                    <div className='text-xs text-foreground truncate'>
                      {label}
                    </div>
                  </div>
                  <button
                    className='btn-glass btn-glass--primary text-xs px-3 py-2'
                    onClick={() => restoreItems([it.id])}
                    disabled={working}
                    title='Restore'
                  >
                    <RotateCcw size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
