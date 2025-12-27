import { useEffect, useMemo, useRef, useState } from 'react';
import { Hash, Plus } from 'lucide-react';
import PhotoGrid from '../components/gallery/PhotoGrid';
import { PageSearchWrapper } from '../components/layout/PageSearchWrapper';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import { api, type TagSummary } from '../api';

export default function TagsPage() {
  const {
    photos,
    loading,
    error,
    hasMore,
    loadMore,
    tag,
    setTag,
  } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();

  const previousTagRef = useRef(tag);
  const [tags, setTags] = useState<TagSummary[]>([]);
  const [tagsLoading, setTagsLoading] = useState(false);
  const [createName, setCreateName] = useState('');

  const selectedTag = tag;
  const selectedTagLabel = selectedTag ? `#${selectedTag}` : null;

  const refreshTags = async () => {
    setTagsLoading(true);
    try {
      const res = await api.listTags(500, 0);
      setTags(res.tags || []);
    } finally {
      setTagsLoading(false);
    }
  };

  useEffect(() => {
    refreshTags();
  }, []);

  useEffect(() => {
    const previousTag = previousTagRef.current;
    return () => setTag(previousTag ?? null);
  }, [setTag]);

  const sorted = useMemo(() => {
    return [...tags].sort((a, b) => (b.photo_count || 0) - (a.photo_count || 0));
  }, [tags]);

  const createTag = async () => {
    const name = createName.trim();
    if (!name) return;
    await api.createTag(name);
    setCreateName('');
    setTag(name);
    await refreshTags();
  };

  return (
    <PageSearchWrapper>
      <div className='max-w-screen-2xl mx-auto px-6 pb-24'>
        <div className='flex flex-wrap items-center justify-between gap-3 mb-6'>
          <div>
            <h1 className='text-2xl font-semibold text-foreground'>Tags</h1>
            <p className='text-sm text-muted-foreground'>
              Light-weight labels that work across local + cloud sources.
            </p>
          </div>

          {selectedTagLabel && (
            <div className='btn-glass btn-glass--muted text-xs px-3 py-2'>
              Filtering: <span className='text-foreground font-semibold'>{selectedTagLabel}</span>
            </div>
          )}
        </div>

        <div className='grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6'>
          <div className='glass-surface rounded-2xl p-4'>
            <div className='flex items-center gap-2 mb-3'>
              <Hash size={16} className='text-muted-foreground' />
              <div className='text-sm font-semibold text-foreground'>All tags</div>
              <div className='ml-auto text-xs text-muted-foreground'>
                {tagsLoading ? 'Loading…' : `${tags.length}`}
              </div>
            </div>

            <div className='flex items-center gap-2 mb-4'>
              <input
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') createTag();
                }}
                placeholder='Create a tag…'
                className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-white/20'
              />
              <button
                className='btn-glass btn-glass--primary text-sm px-3 py-2'
                onClick={createTag}
                disabled={!createName.trim()}
                title='Create tag'
              >
                <Plus size={16} />
              </button>
            </div>

            {sorted.length === 0 ? (
              <div className='text-sm text-muted-foreground p-6 text-center'>
                No tags yet.
              </div>
            ) : (
              <div className='space-y-2 max-h-[60vh] overflow-auto pr-1'>
                <button
                  className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl border transition-colors ${
                    !selectedTag
                      ? 'bg-white/10 border-white/20'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                  onClick={() => setTag(null)}
                >
                  <span className='text-sm text-foreground'>All</span>
                  <span className='text-xs text-muted-foreground'>
                    {sorted.reduce((acc, t) => acc + (t.photo_count || 0), 0)}
                  </span>
                </button>

                {sorted.map((t) => {
                  const active = t.name === selectedTag;
                  return (
                    <button
                      key={t.name}
                      className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-xl border transition-colors ${
                        active
                          ? 'bg-white/10 border-white/20'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                      }`}
                      onClick={() => setTag(t.name)}
                      title={`Filter by #${t.name}`}
                    >
                      <span className='text-sm text-foreground truncate'>
                        #{t.name}
                      </span>
                      <span className='text-xs text-muted-foreground'>
                        {t.photo_count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className='min-w-0'>
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
      </div>
    </PageSearchWrapper>
  );
}
