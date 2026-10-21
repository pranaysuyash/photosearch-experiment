/**
 * Natural Language Face Search
 *
 * Parse and execute face queries like:
 * - "happy photos with John"
 * - "photos with 3 people"
 */
import { useEffect, useMemo, useState } from 'react';
import { Sparkles, X, RefreshCw, Camera } from 'lucide-react';
import { api, type NaturalLanguageFaceSearchResult, type Photo } from '../../api';
import { glass } from '@/design/glass';
import SecureLazyImage from '../gallery/SecureLazyImage';
import { usePhotoViewer } from '../../contexts/PhotoViewerContext';
import { useModalBehavior } from '../../hooks/useModalBehavior';

interface NaturalLanguageFaceSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

const QUERY_SUGGESTIONS = [
  'happy photos with John',
  'photos with 3 people',
  'everyone smiling',
  'kids under 10',
  'photos without Sarah',
];

export function NaturalLanguageFaceSearch({
  isOpen,
  onClose,
}: NaturalLanguageFaceSearchProps) {
  const photoViewer = usePhotoViewer();
  const panelRef = useModalBehavior(isOpen, onClose);
  const [queryText, setQueryText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<
    NonNullable<NaturalLanguageFaceSearchResult['photos']>
  >([]);
  const [parsed, setParsed] = useState<
    NaturalLanguageFaceSearchResult['parsed'] | null
  >(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setQueryText('');
      setResults([]);
      setParsed(null);
      setWarnings([]);
      setTotal(0);
      setSearched(false);
      setError(null);
    }
  }, [isOpen]);

  const runSearch = async (overrideQuery?: string) => {
    const trimmed = (overrideQuery ?? queryText).trim();
    if (!trimmed) return;
    if (overrideQuery) setQueryText(overrideQuery);

    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const response: NaturalLanguageFaceSearchResult =
        await api.searchFacesNaturalLanguage({
          query: trimmed,
          execute: true,
          limit: 100,
          offset: 0,
        });

      setParsed(response.parsed || null);
      setWarnings(response.warnings || []);
      setResults(response.photos || []);
      setTotal(response.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const summary = useMemo(() => {
    if (!parsed) return null;
    const parts: string[] = [];

    if (parsed.person_constraints?.length) {
      const include = parsed.person_constraints
        .filter((c) => c.required)
        .map((c) => c.name)
        .filter(Boolean);
      const exclude = parsed.person_constraints
        .filter((c) => !c.required)
        .map((c) => c.name)
        .filter(Boolean);
      if (include.length) parts.push(`include: ${include.join(', ')}`);
      if (exclude.length) parts.push(`exclude: ${exclude.join(', ')}`);
    }

    if (parsed.group_constraint) {
      const { exact_count, min_people, max_people } = parsed.group_constraint;
      if (exact_count !== null && exact_count !== undefined) {
        parts.push(`exactly ${exact_count} people`);
      } else if (min_people !== null || max_people !== null) {
        parts.push(
          `people ${min_people ?? 'any'}-${max_people ?? 'any'}`
        );
      }
    }

    if (parsed.emotion_constraints?.length) {
      parts.push(
        parsed.emotion_constraints
          .map((e) => (e.all_faces ? `all ${e.emotion}` : e.emotion))
          .join(', ')
      );
    }

    if (parsed.age_constraints?.length) {
      const ages = parsed.age_constraints
        .map((age) => {
          if (age.min_age !== null && age.max_age !== null) {
            return `${age.min_age}-${age.max_age}`;
          }
          if (age.min_age !== null) return `${age.min_age}+`;
          if (age.max_age !== null) return `<=${age.max_age}`;
          return null;
        })
        .filter(Boolean);
      if (ages.length) parts.push(`age ${ages.join(', ')}`);
    }

    return parts.length ? parts.join(' • ') : null;
  }, [parsed]);

  const buildViewerPhotos = (
    photos: NonNullable<NaturalLanguageFaceSearchResult['photos']>
  ) => {
    return photos.map((item) => {
      const filename = item.photo_path.split('/').pop() || item.photo_path;
      return {
        path: item.photo_path,
        filename,
        score: item.match_count,
        metadata: {},
      } satisfies Photo;
    });
  };

  const handleOpenPhoto = (photoPath: string) => {
    const viewerPhotos = buildViewerPhotos(results);
    const idx = viewerPhotos.findIndex((photo) => photo.path === photoPath);
    if (idx >= 0) {
      photoViewer.open(viewerPhotos, idx);
    } else {
      photoViewer.open(viewerPhotos, 0);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role='dialog'
        aria-modal='true'
        aria-label='Natural language face search'
        className={`${glass.surface} border border-white/20 rounded-xl max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className='flex items-center justify-between p-6 border-b border-white/10'>
          <div className='flex items-center gap-3'>
            <Sparkles className='text-primary' size={22} />
            <div>
              <h2 className='text-xl font-semibold text-foreground'>
                Natural Language Face Search
              </h2>
              <p className='text-sm text-muted-foreground'>
                Search people, emotions, age ranges, and group size together
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label='Close'
            className='btn-glass btn-glass--muted w-10 h-10 p-0 justify-center'
          >
            <X size={16} />
          </button>
        </div>

        <div className='p-6 overflow-y-auto max-h-[calc(90vh-200px)] space-y-5'>
          {error && (
            <div role='alert' className='p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm'>
              {error}
            </div>
          )}

          <div className='space-y-2'>
            <label htmlFor='nlfs-query' className='block text-sm font-medium text-foreground'>
              Natural language query
            </label>
            <input
              id='nlfs-query'
              type='search'
              placeholder="e.g. happy photos with John"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
            />
            <div className='flex flex-wrap items-center gap-2'>
              <span className='text-xs text-muted-foreground'>Try:</span>
              {QUERY_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type='button'
                  onClick={() => void runSearch(suggestion)}
                  className='text-xs px-2 py-1 rounded-full border border-white/10 bg-white/5 text-foreground hover:bg-white/10 transition-colors'
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {warnings.length > 0 && (
            <div className='p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-200 text-xs'>
              {warnings.join(' ')}
            </div>
          )}

          {summary && (
            <div className='p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
              <div className='text-sm font-medium text-blue-300 mb-1'>
                Parsed constraints
              </div>
              <div className='text-sm text-foreground'>{summary}</div>
              <div className='mt-2 text-xs text-muted-foreground'>
                Confidence: {Math.round((parsed?.parse_confidence ?? 0) * 100)}%
              </div>
            </div>
          )}

          {parsed?.unparsed_parts?.length ? (
            <div className='p-3 bg-white/5 border border-white/10 rounded-lg text-xs text-muted-foreground'>
              Unparsed terms: {parsed.unparsed_parts.join(', ')}
            </div>
          ) : null}

          {results.length > 0 && (
            <div className='space-y-4'>
              <div
                className='flex items-center gap-2 text-sm text-muted-foreground'
                role='status'
                aria-live='polite'
              >
                <Camera size={16} />
                <span>
                  Found {total || results.length} photo
                  {(total || results.length) === 1 ? '' : 's'}
                </span>
              </div>

              <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4'>
                {results.slice(0, 20).map((result) => (
                  <div
                    key={result.photo_path}
                    className='bg-white/5 border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors cursor-pointer'
                    role='button'
                    tabIndex={0}
                    onClick={() => handleOpenPhoto(result.photo_path)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        handleOpenPhoto(result.photo_path);
                      }
                    }}
                  >
                    <div className='aspect-square bg-black/20'>
                      <SecureLazyImage
                        path={result.photo_path}
                        size={300}
                        alt='Search result'
                        className='w-full h-full object-cover'
                        showBadge={false}
                      />
                    </div>
                    <div className='p-2 space-y-1'>
                      <div
                        className='text-xs text-muted-foreground truncate'
                        title={result.photo_path}
                      >
                        {result.photo_path.split('/').pop()}
                      </div>
                      <div className='text-xs text-muted-foreground'>
                        Matches: {result.match_count}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {results.length > 20 && (
                <div className='text-center text-sm text-muted-foreground'>
                  Showing first 20 of {results.length} results
                </div>
              )}
            </div>
          )}

          {searched && results.length === 0 && !loading && (
            <div className='text-sm text-muted-foreground text-center'>
              No results found. Try another query.
            </div>
          )}
        </div>

        <div className='flex items-center justify-between p-6 border-t border-white/10'>
          <button
            onClick={() => {
              setQueryText('');
              setResults([]);
              setParsed(null);
              setWarnings([]);
              setTotal(0);
              setSearched(false);
              setError(null);
            }}
            className='btn-glass btn-glass--muted px-4 py-2'
            disabled={loading}
          >
            Clear
          </button>

          <div className='flex gap-3'>
            <button
              onClick={onClose}
              className='btn-glass btn-glass--muted px-4 py-2'
              disabled={loading}
            >
              Close
            </button>
            <button
              onClick={() => void runSearch()}
              className='btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2'
              disabled={loading}
            >
              {loading && <RefreshCw size={14} className='animate-spin' />}
              {loading ? 'Searching…' : 'Run Search'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default NaturalLanguageFaceSearch;
