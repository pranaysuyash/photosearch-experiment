/**
 * Face Attribute Search Component
 *
 * Search photos by face attributes like age, emotion, pose, and quality.
 * Uses the glass design system and follows living language guidelines.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Sparkles,
  SlidersHorizontal,
  X,
  RefreshCw,
  Camera,
} from 'lucide-react';
import {
  api,
  type FaceAttributeQueryResult,
  type FaceAttributeSearchRequest,
  type FaceAttributeSearchResult,
  type Photo,
} from '../../api';
import { glass } from '../../design/glass';
import { useModalBehavior } from '../../hooks/useModalBehavior';
import SecureLazyImage from '../gallery/SecureLazyImage';
import { usePhotoViewer } from '../../contexts/PhotoViewerContext';

const EMOTIONS = [
  'happy',
  'sad',
  'angry',
  'surprised',
  'fearful',
  'disgusted',
  'neutral',
];

const POSE_TYPES = ['frontal', 'three_quarter', 'profile'] as const;
type PoseType = (typeof POSE_TYPES)[number];

const QUERY_SUGGESTIONS = [
  'happy kids under 10',
  'female profile portraits',
  'high quality frontal faces',
  'neutral expression',
  'senior portraits',
  'angry faces',
];

interface FaceAttributeSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

type SearchFilters = {
  minAge: string;
  maxAge: string;
  emotions: string[];
  gender: '' | 'male' | 'female';
  poseType: '' | PoseType;
  minQuality: number;
  minConfidence: number;
  showConfidence: boolean;
  minAgeConfidence: number;
  minEmotionConfidence: number;
  minPoseConfidence: number;
  minGenderConfidence: number;
};

const defaultFilters: SearchFilters = {
  minAge: '',
  maxAge: '',
  emotions: [],
  gender: '',
  poseType: '',
  minQuality: 0.6,
  minConfidence: 0.5,
  showConfidence: false,
  minAgeConfidence: 0.6,
  minEmotionConfidence: 0.6,
  minPoseConfidence: 0.6,
  minGenderConfidence: 0.6,
};

export function FaceAttributeSearch({
  isOpen,
  onClose,
}: FaceAttributeSearchProps) {
  const photoViewer = usePhotoViewer();
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<
    FaceAttributeSearchResult['photos']
  >([]);
  const [total, setTotal] = useState(0);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryText, setQueryText] = useState('');
  const [queryWarnings, setQueryWarnings] = useState<string[]>([]);

  useEffect(() => {
    if (!isOpen) {
      setFilters(defaultFilters);
      setResults([]);
      setTotal(0);
      setSearched(false);
      setError(null);
      setQueryText('');
      setQueryWarnings([]);
    }
  }, [isOpen]);

  const toggleEmotion = (emotion: string) => {
    setFilters((prev) => {
      const exists = prev.emotions.includes(emotion);
      return {
        ...prev,
        emotions: exists
          ? prev.emotions.filter((item) => item !== emotion)
          : [...prev.emotions, emotion],
      };
    });
  };

  const queryDescription = useMemo(() => {
    const parts: string[] = [];

    if (filters.minAge || filters.maxAge) {
      const min = filters.minAge || 'any';
      const max = filters.maxAge || 'any';
      parts.push(`age ${min}-${max}`);
    }

    if (filters.emotions.length > 0) {
      parts.push(`emotion: ${filters.emotions.join(', ')}`);
    }

    if (filters.gender) {
      parts.push(`gender: ${filters.gender}`);
    }

    if (filters.poseType) {
      parts.push(`pose: ${filters.poseType.replace('_', ' ')}`);
    }

    parts.push(`quality >= ${(filters.minQuality * 100).toFixed(0)}%`);

    return parts.length > 0 ? parts.join(' • ') : 'No filters selected';
  }, [filters]);

  const buildPayload = (): FaceAttributeSearchRequest => {
    const payload: FaceAttributeSearchRequest = {
      limit: 100,
      offset: 0,
    };

    if (filters.minAge) payload.min_age = Number(filters.minAge);
    if (filters.maxAge) payload.max_age = Number(filters.maxAge);
    if (filters.emotions.length > 0) payload.emotions = filters.emotions;
    if (filters.gender) payload.gender = filters.gender;
    if (filters.poseType) payload.pose_type = filters.poseType;
    if (!Number.isNaN(filters.minQuality)) {
      payload.min_quality = filters.minQuality;
    }
    if (!Number.isNaN(filters.minConfidence)) {
      payload.min_confidence = filters.minConfidence;
    }
    if (filters.showConfidence) {
      payload.min_age_confidence = filters.minAgeConfidence;
      payload.min_emotion_confidence = filters.minEmotionConfidence;
      payload.min_pose_confidence = filters.minPoseConfidence;
      payload.min_gender_confidence = filters.minGenderConfidence;
    }

    return payload;
  };

  const applyParsedFilters = (parsed: FaceAttributeQueryResult['filters']) => {
    const hasConfidence =
      parsed.min_age_confidence !== undefined ||
      parsed.min_emotion_confidence !== undefined ||
      parsed.min_pose_confidence !== undefined ||
      parsed.min_gender_confidence !== undefined;

    setFilters({
      minAge: parsed.min_age !== undefined ? String(parsed.min_age) : '',
      maxAge: parsed.max_age !== undefined ? String(parsed.max_age) : '',
      emotions: parsed.emotions ?? (parsed.emotion ? [parsed.emotion] : []),
      gender: (parsed.gender ?? '') as SearchFilters['gender'],
      poseType: (parsed.pose_type ?? '') as SearchFilters['poseType'],
      minQuality:
        parsed.min_quality !== undefined
          ? parsed.min_quality
          : defaultFilters.minQuality,
      minConfidence:
        parsed.min_confidence !== undefined
          ? parsed.min_confidence
          : defaultFilters.minConfidence,
      showConfidence: hasConfidence,
      minAgeConfidence:
        parsed.min_age_confidence ?? defaultFilters.minAgeConfidence,
      minEmotionConfidence:
        parsed.min_emotion_confidence ?? defaultFilters.minEmotionConfidence,
      minPoseConfidence:
        parsed.min_pose_confidence ?? defaultFilters.minPoseConfidence,
      minGenderConfidence:
        parsed.min_gender_confidence ?? defaultFilters.minGenderConfidence,
    });
  };

  const executeSearch = async (overrideQuery?: string) => {
    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const trimmedQuery = (overrideQuery ?? queryText).trim();
      if (overrideQuery) {
        setQueryText(overrideQuery);
      }
      if (trimmedQuery) {
        const response: FaceAttributeQueryResult =
          await api.searchPhotosByFaceAttributesQuery({
            query: trimmedQuery,
            limit: 100,
            offset: 0,
          });
        applyParsedFilters(response.filters);
        setQueryWarnings(response.warnings || []);
        setResults(response.photos || []);
        setTotal(response.total || 0);
        return;
      }

      const payload = buildPayload();
      const response = await api.searchPhotosByFaceAttributes(payload);

      setResults(response.photos || []);
      setTotal(response.total || 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const buildViewerPhotos = (photos: FaceAttributeSearchResult['photos']) => {
    return photos.map((item) => {
      const filename = item.photo_path.split('/').pop() || item.photo_path;
      return {
        path: item.photo_path,
        filename,
        score: 0,
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

  const clearFilters = () => {
    setFilters(defaultFilters);
    setResults([]);
    setTotal(0);
    setSearched(false);
    setError(null);
    setQueryText('');
    setQueryWarnings([]);
  };

  const runSuggestion = (suggestion: string) => {
    setQueryWarnings([]);
    void executeSearch(suggestion);
  };

  const panelRef = useModalBehavior(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'>
      <div
        ref={panelRef}
        role='dialog'
        aria-modal='true'
        aria-label='Face attribute search'
        className={`${glass.surface} border border-white/20 rounded-xl max-w-5xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className='flex items-center justify-between p-6 border-b border-white/10'>
          <div className='flex items-center gap-3'>
            <SlidersHorizontal className='text-primary' size={24} />
            <div>
              <h2 className='text-xl font-semibold text-foreground'>
                Face Attribute Search
              </h2>
              <p className='text-sm text-muted-foreground'>
                Find photos using age, emotion, pose, and quality filters
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

        {/* Content */}
        <div className='p-6 overflow-y-auto max-h-[calc(90vh-200px)] space-y-6'>
          {error && (
            <div role='alert' className='p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm'>
              {error}
            </div>
          )}

          {/* Natural Language Query */}
          <div className='space-y-2'>
            <label htmlFor='fas-query' className='block text-sm font-medium text-foreground'>
              Natural language (optional)
            </label>
            <input
              id='fas-query'
              type='text'
              placeholder="e.g. happy kids under 10, profile shots"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
            />
            <p className='text-xs text-muted-foreground'>
              When provided, we parse the query into filters before searching.
            </p>
            <div className='flex flex-wrap items-center gap-2'>
              <span className='text-xs text-muted-foreground'>Try:</span>
              {QUERY_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type='button'
                  onClick={() => runSuggestion(suggestion)}
                  className='text-xs px-2 py-1 rounded-full border border-white/10 bg-white/5 text-foreground hover:bg-white/10 transition-colors'
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {queryWarnings.length > 0 && (
            <div className='p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-200 text-xs'>
              {queryWarnings.join(' ')}
            </div>
          )}

          {/* Filters */}
          <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
            <div className='space-y-4'>
              <div>
                <label htmlFor='fas-age-min' className='block text-sm font-medium text-foreground mb-2'>
                  Age Range
                </label>
                <div className='grid grid-cols-2 gap-2'>
                  <input
                    id='fas-age-min'
                    type='number'
                    min={0}
                    max={120}
                    placeholder='Min'
                    value={filters.minAge}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        minAge: e.target.value,
                      }))
                    }
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                  <input
                    id='fas-age-max'
                    type='number'
                    min={0}
                    max={120}
                    placeholder='Max'
                    value={filters.maxAge}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        maxAge: e.target.value,
                      }))
                    }
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>
              </div>

              <div>
                <label htmlFor='fas-gender' className='block text-sm font-medium text-foreground mb-2'>
                  Gender
                </label>
                <select
                  id='fas-gender'
                  value={filters.gender}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      gender: e.target.value as SearchFilters['gender'],
                    }))
                  }
                  className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                >
                  <option value=''>Any</option>
                  <option value='female'>Female</option>
                  <option value='male'>Male</option>
                </select>
              </div>

              <div>
                <label htmlFor='fas-pose' className='block text-sm font-medium text-foreground mb-2'>
                  Pose
                </label>
                <select
                  id='fas-pose'
                  value={filters.poseType}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      poseType: e.target.value as SearchFilters['poseType'],
                    }))
                  }
                  className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                >
                  <option value=''>Any</option>
                  {POSE_TYPES.map((pose) => (
                    <option key={pose} value={pose}>
                      {pose.replace('_', ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className='space-y-4 lg:col-span-2'>
              <div>
                <span className='block text-sm font-medium text-foreground mb-2'>
                  Emotions
                </span>
                <div className='flex flex-wrap gap-2'>
                  {EMOTIONS.map((emotion) => {
                    const active = filters.emotions.includes(emotion);
                    return (
                      <button
                        key={emotion}
                        onClick={() => toggleEmotion(emotion)}
                        className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
                          active
                            ? 'bg-primary/20 border-primary/40 text-primary'
                            : 'bg-white/5 border-white/10 text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {emotion}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                <div>
                  <label htmlFor='fas-min-quality' className='block text-sm font-medium text-foreground mb-2'>
                    Min Quality ({Math.round(filters.minQuality * 100)}%)
                  </label>
                  <input
                    id='fas-min-quality'
                    type='range'
                    min={0}
                    max={1}
                    step={0.05}
                    value={filters.minQuality}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        minQuality: Number(e.target.value),
                      }))
                    }
                    aria-valuetext={`${Math.round(filters.minQuality * 100)} percent`}
                    className='w-full'
                  />
                </div>
                <div>
                  <label htmlFor='fas-min-match' className='block text-sm font-medium text-foreground mb-2'>
                    Min Match ({Math.round(filters.minConfidence * 100)}%)
                  </label>
                  <input
                    id='fas-min-match'
                    type='range'
                    min={0}
                    max={1}
                    step={0.05}
                    value={filters.minConfidence}
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        minConfidence: Number(e.target.value),
                      }))
                    }
                    aria-valuetext={`${Math.round(filters.minConfidence * 100)} percent`}
                    className='w-full'
                  />
                </div>
              </div>

              <button
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    showConfidence: !prev.showConfidence,
                  }))
                }
                className='btn-glass btn-glass--muted text-xs px-3 py-1.5 flex items-center gap-2'
              >
                <Sparkles size={14} />
                {filters.showConfidence
                  ? 'Hide confidence filters'
                  : 'Show confidence filters'}
              </button>

              {filters.showConfidence && (
                <div className='grid grid-cols-1 sm:grid-cols-2 gap-4'>
                  <div>
                    <label htmlFor='fas-age-confidence' className='block text-xs text-muted-foreground mb-1'>
                      Age confidence ({Math.round(filters.minAgeConfidence * 100)}%)
                    </label>
                    <input
                      id='fas-age-confidence'
                      type='range'
                      min={0}
                      max={1}
                      step={0.05}
                      value={filters.minAgeConfidence}
                      onChange={(e) =>
                        setFilters((prev) => ({
                          ...prev,
                          minAgeConfidence: Number(e.target.value),
                        }))
                      }
                      aria-valuetext={`${Math.round(filters.minAgeConfidence * 100)} percent`}
                      className='w-full'
                    />
                  </div>
                  <div>
                    <label htmlFor='fas-emotion-confidence' className='block text-xs text-muted-foreground mb-1'>
                      Emotion confidence ({Math.round(filters.minEmotionConfidence * 100)}%)
                    </label>
                    <input
                      id='fas-emotion-confidence'
                      type='range'
                      min={0}
                      max={1}
                      step={0.05}
                      value={filters.minEmotionConfidence}
                      onChange={(e) =>
                        setFilters((prev) => ({
                          ...prev,
                          minEmotionConfidence: Number(e.target.value),
                        }))
                      }
                      aria-valuetext={`${Math.round(filters.minEmotionConfidence * 100)} percent`}
                      className='w-full'
                    />
                  </div>
                  <div>
                    <label htmlFor='fas-pose-confidence' className='block text-xs text-muted-foreground mb-1'>
                      Pose confidence ({Math.round(filters.minPoseConfidence * 100)}%)
                    </label>
                    <input
                      id='fas-pose-confidence'
                      type='range'
                      min={0}
                      max={1}
                      step={0.05}
                      value={filters.minPoseConfidence}
                      onChange={(e) =>
                        setFilters((prev) => ({
                          ...prev,
                          minPoseConfidence: Number(e.target.value),
                        }))
                      }
                      aria-valuetext={`${Math.round(filters.minPoseConfidence * 100)} percent`}
                      className='w-full'
                    />
                  </div>
                  <div>
                    <label htmlFor='fas-gender-confidence' className='block text-xs text-muted-foreground mb-1'>
                      Gender confidence ({Math.round(filters.minGenderConfidence * 100)}%)
                    </label>
                    <input
                      id='fas-gender-confidence'
                      type='range'
                      min={0}
                      max={1}
                      step={0.05}
                      value={filters.minGenderConfidence}
                      onChange={(e) =>
                        setFilters((prev) => ({
                          ...prev,
                          minGenderConfidence: Number(e.target.value),
                        }))
                      }
                      aria-valuetext={`${Math.round(filters.minGenderConfidence * 100)} percent`}
                      className='w-full'
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className='p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
            <div className='text-sm font-medium text-blue-400 mb-1'>
              Search Preview
            </div>
            <div className='text-sm text-foreground'>{queryDescription}</div>
          </div>

          {/* Results */}
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
                      {result.faces?.length > 0 && (
                        <div className='text-[10px] text-muted-foreground'>
                          {result.faces
                            .slice(0, 2)
                            .map((face) => {
                              const bits: string[] = [];
                              if (face.emotion) bits.push(face.emotion);
                              if (face.age_estimate !== null && face.age_estimate !== undefined) {
                                bits.push(`${face.age_estimate}y`);
                              }
                              if (face.gender) bits.push(face.gender);
                              return bits.join(' · ');
                            })
                            .filter(Boolean)
                            .join(' / ')}
                        </div>
                      )}
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
              No results found. Try widening the filters.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className='flex items-center justify-between p-6 border-t border-white/10'>
          <button
            onClick={clearFilters}
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
              onClick={() => void executeSearch()}
              className='btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2'
              disabled={loading}
            >
              {loading && <RefreshCw size={14} className='animate-spin' />}
              {loading ? 'Searching…' : 'Search Photos'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FaceAttributeSearch;
