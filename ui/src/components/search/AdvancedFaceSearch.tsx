/**
 * Advanced Face Search Component
 *
 * Provides enhanced search capabilities including:
 * - Natural language query parsing
 * - Boolean search logic (AND/OR/NOT)
 * - Temporal filtering with date ranges
 * - Group composition searches
 * - Similarity-based searches
 * - Saved search presets
 *
 * Uses the glass design system and follows living language guidelines.
 */
import { useEffect, useState, useCallback } from 'react';
import {
  Search,
  Sparkles,
  Calendar,
  Users,
  Sliders,
  X,
  RefreshCw,
  Camera,
  Info,
  Lightbulb,
} from 'lucide-react';
import { api, type Photo } from '../../api';
import { glass } from '../../design/glass';
import SecureLazyImage from '../gallery/SecureLazyImage';
import { usePhotoViewer } from '../../contexts/PhotoViewerContext';

interface AdvancedFaceSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SearchResult {
  photo_path: string;
  match_score: number;
  match_reasons: string[];
  people_count: number;
  emotions_detected: string[];
  age_range: { min: number | null; max: number | null };
  quality_scores: number[];
  faces: Array<{
    face_id: string;
    person_name: string;
    age_estimate: number | null;
    emotion: string | null;
    gender: string | null;
    pose_type: string | null;
    overall_quality: number | null;
  }>;
}

interface QueryExplanation {
  original_query: string;
  interpretation: {
    people_to_include: string[];
    people_to_exclude: string[];
    emotions: string[];
    age_range: string;
    gender: string;
    pose_type: string;
    quality_threshold: number | null;
    date_range: string;
    group_size: string;
    boolean_operator: string;
  };
  search_strategy: string;
}

type SearchMode = 'natural' | 'boolean' | 'temporal' | 'similarity';

type SimilarFaceResult = {
  photo_path: string;
  similarity_score: number;
  quality_score?: number | null;
  face_id: string;
  person_name?: string | null;
};

const SEARCH_EXAMPLES = [
  'happy family photos from 2023',
  'photos with John and Mary but not Sarah',
  'childhood photos of Emma',
  'photos with exactly 3 people',
  'high quality profile shots',
  'everyone is smiling',
  'photos from last summer',
  'recent photos with children',
  'family gatherings',
  'photos without glasses'
];

export function AdvancedFaceSearch({ isOpen, onClose }: AdvancedFaceSearchProps) {
  const photoViewer = usePhotoViewer();
  const [searchMode, setSearchMode] = useState<SearchMode>('natural');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<QueryExplanation | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showExplanation, setShowExplanation] = useState(false);

  // Boolean search filters
  const [booleanFilters, setBooleanFilters] = useState({
    peopleInclude: '',
    peopleExclude: '',
    emotions: '',
    minAge: '',
    maxAge: '',
    gender: '',
    poseType: '',
    minQuality: '',
    groupSizeMin: '',
    groupSizeMax: '',
    groupSizeExact: '',
    booleanOperator: 'AND'
  });

  // Temporal search filters
  const [temporalFilters, setTemporalFilters] = useState({
    dateStart: '',
    dateEnd: '',
    relativePeriod: '',
    people: '',
    emotions: ''
  });

  // Similarity search
  const [similaritySearch, setSimilaritySearch] = useState({
    referenceFaceId: '',
    threshold: 0.8
  });

  useEffect(() => {
    if (!isOpen) {
      resetSearch();
    }
  }, [isOpen]);

  const extractErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof Error) return err.message;
    if (typeof err === 'object' && err && 'response' in err) {
      const response = (err as { response?: { data?: { detail?: string } } }).response;
      if (response?.data?.detail) return response.data.detail;
    }
    return fallback;
  };

  const resetSearch = () => {
    setQuery('');
    setResults([]);
    setTotal(0);
    setSearched(false);
    setError(null);
    setExplanation(null);
    setSuggestions([]);
    setShowExplanation(false);
    setBooleanFilters({
      peopleInclude: '',
      peopleExclude: '',
      emotions: '',
      minAge: '',
      maxAge: '',
      gender: '',
      poseType: '',
      minQuality: '',
      groupSizeMin: '',
      groupSizeMax: '',
      groupSizeExact: '',
      booleanOperator: 'AND'
    });
    setTemporalFilters({
      dateStart: '',
      dateEnd: '',
      relativePeriod: '',
      people: '',
      emotions: ''
    });
    setSimilaritySearch({
      referenceFaceId: '',
      threshold: 0.8
    });
  };

  const getSuggestions = useCallback(async (partialQuery: string) => {
    if (partialQuery.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      const response = await api.get<{ suggestions?: string[] }>(
        `/api/faces/search/suggestions?q=${encodeURIComponent(partialQuery)}`
      );
      const data = response as { suggestions?: string[] };
      setSuggestions(data.suggestions || []);
    } catch (err) {
      console.error('Error getting suggestions:', err);
      setSuggestions([]);
    }
  }, []);

  const explainQuery = async (queryText: string) => {
    if (!queryText.trim()) return;

    try {
      const response = await api.post<QueryExplanation>('/api/faces/search/explain', {
        query: queryText
      });
      const data = response as QueryExplanation;
      setExplanation(data);
    } catch (err) {
      console.error('Error explaining query:', err);
      setExplanation(null);
    }
  };

  const executeNaturalSearch = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const response = await api.post<{ results?: SearchResult[]; total?: number }>(
        '/api/faces/search/advanced',
        {
        query: query.trim(),
        limit: 100,
        offset: 0
        }
      );

      const data = response as { results?: SearchResult[]; total?: number };
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Search failed'));
    } finally {
      setLoading(false);
    }
  };

  const executeBooleanSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const params = new URLSearchParams();
      if (booleanFilters.peopleInclude) params.append('people_include', booleanFilters.peopleInclude);
      if (booleanFilters.peopleExclude) params.append('people_exclude', booleanFilters.peopleExclude);
      if (booleanFilters.emotions) params.append('emotions', booleanFilters.emotions);
      if (booleanFilters.minAge) params.append('min_age', booleanFilters.minAge);
      if (booleanFilters.maxAge) params.append('max_age', booleanFilters.maxAge);
      if (booleanFilters.gender) params.append('gender', booleanFilters.gender);
      if (booleanFilters.poseType) params.append('pose_type', booleanFilters.poseType);
      if (booleanFilters.minQuality) params.append('min_quality', booleanFilters.minQuality);
      if (booleanFilters.groupSizeMin) params.append('group_size_min', booleanFilters.groupSizeMin);
      if (booleanFilters.groupSizeMax) params.append('group_size_max', booleanFilters.groupSizeMax);
      if (booleanFilters.groupSizeExact) params.append('group_size_exact', booleanFilters.groupSizeExact);
      params.append('boolean_operator', booleanFilters.booleanOperator);
      params.append('limit', '100');
      params.append('offset', '0');

      const response = await api.get<{ results?: SearchResult[]; total?: number }>(
        `/api/faces/search/boolean?${params.toString()}`
      );

      const data = response as { results?: SearchResult[]; total?: number };
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Boolean search failed'));
    } finally {
      setLoading(false);
    }
  };

  const executeTemporalSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const params = new URLSearchParams();
      if (temporalFilters.dateStart) params.append('date_start', temporalFilters.dateStart);
      if (temporalFilters.dateEnd) params.append('date_end', temporalFilters.dateEnd);
      if (temporalFilters.relativePeriod) params.append('relative_period', temporalFilters.relativePeriod);
      if (temporalFilters.people) params.append('people', temporalFilters.people);
      if (temporalFilters.emotions) params.append('emotions', temporalFilters.emotions);
      params.append('limit', '100');
      params.append('offset', '0');

      const response = await api.get<{ results?: SearchResult[]; total?: number }>(
        `/api/faces/search/temporal?${params.toString()}`
      );

      const data = response as { results?: SearchResult[]; total?: number };
      setResults(data.results || []);
      setTotal(data.total || 0);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Temporal search failed'));
    } finally {
      setLoading(false);
    }
  };

  const executeSimilaritySearch = async () => {
    if (!similaritySearch.referenceFaceId) return;

    try {
      setLoading(true);
      setError(null);
      setResults([]);
      setSearched(true);

      const response = await api.post<{ similar_faces?: SimilarFaceResult[] }>(
        '/api/faces/search/similar',
        {
        reference_face_id: similaritySearch.referenceFaceId,
        threshold: similaritySearch.threshold,
        limit: 50
        }
      );

      const data = response as { similar_faces?: SimilarFaceResult[] };
      // Convert similarity results to search results format
      const similarFaces = data.similar_faces || [];
      const convertedResults: SearchResult[] = similarFaces.map((face) => ({
        photo_path: face.photo_path,
        match_score: face.similarity_score,
        match_reasons: [`${(face.similarity_score * 100).toFixed(1)}% similar`],
        people_count: 1,
        emotions_detected: [],
        age_range: { min: null, max: null },
        quality_scores: [face.quality_score || 0],
        faces: [{
          face_id: face.face_id,
          person_name: face.person_name ?? 'Unknown',
          age_estimate: null,
          emotion: null,
          gender: null,
          pose_type: null,
          overall_quality: face.quality_score ?? null
        }]
      }));

      setResults(convertedResults);
      setTotal(convertedResults.length);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Similarity search failed'));
    } finally {
      setLoading(false);
    }
  };

  const executeSearch = () => {
    switch (searchMode) {
      case 'natural':
        executeNaturalSearch();
        break;
      case 'boolean':
        executeBooleanSearch();
        break;
      case 'temporal':
        executeTemporalSearch();
        break;
      case 'similarity':
        executeSimilaritySearch();
        break;
    }
  };

  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (searchMode === 'natural') {
      getSuggestions(value);
      if (value.trim()) {
        explainQuery(value);
      } else {
        setExplanation(null);
      }
    }
  };

  const buildViewerPhotos = (photos: SearchResult[]) => {
    return photos.map((item) => {
      const filename = item.photo_path.split('/').pop() || item.photo_path;
      return {
        path: item.photo_path,
        filename,
        score: item.match_score,
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
    <div className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'>
      <div
        className={`${glass.surface} border border-white/20 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className='flex items-center justify-between p-6 border-b border-white/10'>
          <div className='flex items-center gap-3'>
            <Sparkles className='text-primary' size={24} />
            <div>
              <h2 className='text-xl font-semibold text-foreground'>
                Advanced Face Search
              </h2>
              <p className='text-sm text-muted-foreground'>
                Natural language queries, boolean logic, and temporal filtering
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className='btn-glass btn-glass--muted w-10 h-10 p-0 justify-center'
          >
            <X size={16} />
          </button>
        </div>

        {/* Search Mode Tabs */}
        <div className='flex border-b border-white/10'>
          {[
            { mode: 'natural' as SearchMode, label: 'Natural Language', icon: Search },
            { mode: 'boolean' as SearchMode, label: 'Boolean Logic', icon: Sliders },
            { mode: 'temporal' as SearchMode, label: 'Time-Based', icon: Calendar },
            { mode: 'similarity' as SearchMode, label: 'Similar Faces', icon: Users },
          ].map(({ mode, label, icon: Icon }) => (
            <button
              key={mode}
              onClick={() => setSearchMode(mode)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors ${
                searchMode === mode
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className='p-6 overflow-y-auto max-h-[calc(90vh-300px)] space-y-6'>
          {error && (
            <div className='p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm'>
              {error}
            </div>
          )}

          {/* Natural Language Search */}
          {searchMode === 'natural' && (
            <div className='space-y-4'>
              <div className='space-y-2'>
                <label className='block text-sm font-medium text-foreground'>
                  Search Query
                </label>
                <div className='relative'>
                  <input
                    type='text'
                    placeholder="e.g. happy family photos from 2023"
                    value={query}
                    onChange={(e) => handleQueryChange(e.target.value)}
                    className='w-full px-3 py-2 pr-10 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                  {explanation && (
                    <button
                      onClick={() => setShowExplanation(!showExplanation)}
                      className='absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground'
                    >
                      <Info size={16} />
                    </button>
                  )}
                </div>
                <p className='text-xs text-muted-foreground'>
                  Use natural language like "photos with John and Mary from last summer"
                </p>
              </div>

              {/* Query Explanation */}
              {explanation && showExplanation && (
                <div className='p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg space-y-2'>
                  <div className='text-sm font-medium text-blue-400'>
                    We understand your query as:
                  </div>
                  <div className='text-sm text-foreground'>
                    {explanation.search_strategy}
                  </div>
                  <div className='text-xs text-muted-foreground space-y-1'>
                    <div>People: {explanation.interpretation.people_to_include.join(', ') || 'any'}</div>
                    <div>Emotions: {explanation.interpretation.emotions.join(', ') || 'any'}</div>
                    <div>Age range: {explanation.interpretation.age_range}</div>
                    <div>Group size: {explanation.interpretation.group_size}</div>
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {suggestions.length > 0 && (
                <div className='space-y-2'>
                  <div className='text-sm font-medium text-foreground'>Suggestions:</div>
                  <div className='flex flex-wrap gap-2'>
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setQuery(suggestion)}
                        className='px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-full text-muted-foreground hover:text-foreground hover:border-white/20 transition-colors'
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Examples */}
              <div className='space-y-2'>
                <div className='text-sm font-medium text-foreground flex items-center gap-2'>
                  <Lightbulb size={16} />
                  Example Queries:
                </div>
                <div className='grid grid-cols-1 sm:grid-cols-2 gap-2'>
                  {SEARCH_EXAMPLES.map((example, index) => (
                    <button
                      key={index}
                      onClick={() => setQuery(example)}
                      className='text-left px-3 py-2 text-xs bg-white/5 border border-white/10 rounded-lg text-muted-foreground hover:text-foreground hover:border-white/20 transition-colors'
                    >
                      "{example}"
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Boolean Search */}
          {searchMode === 'boolean' && (
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    People to Include
                  </label>
                  <input
                    type='text'
                    placeholder="John, Mary, Sarah"
                    value={booleanFilters.peopleInclude}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, peopleInclude: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    People to Exclude
                  </label>
                  <input
                    type='text'
                    placeholder="Tom, Lisa"
                    value={booleanFilters.peopleExclude}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, peopleExclude: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>

                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Emotions
                  </label>
                  <input
                    type='text'
                    placeholder="happy, surprised, neutral"
                    value={booleanFilters.emotions}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, emotions: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>

                <div className='grid grid-cols-2 gap-2'>
                  <div>
                    <label className='block text-sm font-medium text-foreground mb-2'>
                      Min Age
                    </label>
                    <input
                      type='number'
                      placeholder="0"
                      value={booleanFilters.minAge}
                      onChange={(e) => setBooleanFilters(prev => ({ ...prev, minAge: e.target.value }))}
                      className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                  </div>
                  <div>
                    <label className='block text-sm font-medium text-foreground mb-2'>
                      Max Age
                    </label>
                    <input
                      type='number'
                      placeholder="100"
                      value={booleanFilters.maxAge}
                      onChange={(e) => setBooleanFilters(prev => ({ ...prev, maxAge: e.target.value }))}
                      className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                  </div>
                </div>
              </div>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Gender
                  </label>
                  <select
                    value={booleanFilters.gender}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, gender: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                  >
                    <option value=''>Any</option>
                    <option value='male'>Male</option>
                    <option value='female'>Female</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Pose Type
                  </label>
                  <select
                    value={booleanFilters.poseType}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, poseType: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                  >
                    <option value=''>Any</option>
                    <option value='frontal'>Frontal</option>
                    <option value='profile'>Profile</option>
                    <option value='three_quarter'>Three Quarter</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Boolean Operator
                  </label>
                  <select
                    value={booleanFilters.booleanOperator}
                    onChange={(e) => setBooleanFilters(prev => ({ ...prev, booleanOperator: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                  >
                    <option value='AND'>AND (all conditions)</option>
                    <option value='OR'>OR (any condition)</option>
                  </select>
                </div>

                <div className='grid grid-cols-3 gap-2'>
                  <div>
                    <label className='block text-sm font-medium text-foreground mb-2'>
                      Min People
                    </label>
                    <input
                      type='number'
                      placeholder="1"
                      value={booleanFilters.groupSizeMin}
                      onChange={(e) => setBooleanFilters(prev => ({ ...prev, groupSizeMin: e.target.value }))}
                      className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                  </div>
                  <div>
                    <label className='block text-sm font-medium text-foreground mb-2'>
                      Max People
                    </label>
                    <input
                      type='number'
                      placeholder="10"
                      value={booleanFilters.groupSizeMax}
                      onChange={(e) => setBooleanFilters(prev => ({ ...prev, groupSizeMax: e.target.value }))}
                      className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                  </div>
                  <div>
                    <label className='block text-sm font-medium text-foreground mb-2'>
                      Exact Count
                    </label>
                    <input
                      type='number'
                      placeholder="3"
                      value={booleanFilters.groupSizeExact}
                      onChange={(e) => setBooleanFilters(prev => ({ ...prev, groupSizeExact: e.target.value }))}
                      className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Temporal Search */}
          {searchMode === 'temporal' && (
            <div className='space-y-4'>
              <div className='grid grid-cols-1 lg:grid-cols-2 gap-4'>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Start Date
                  </label>
                  <input
                    type='date'
                    value={temporalFilters.dateStart}
                    onChange={(e) => setTemporalFilters(prev => ({ ...prev, dateStart: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    End Date
                  </label>
                  <input
                    type='date'
                    value={temporalFilters.dateEnd}
                    onChange={(e) => setTemporalFilters(prev => ({ ...prev, dateEnd: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>
              </div>

              <div>
                <label className='block text-sm font-medium text-foreground mb-2'>
                  Or Select Relative Period
                </label>
                <select
                  value={temporalFilters.relativePeriod}
                  onChange={(e) => setTemporalFilters(prev => ({ ...prev, relativePeriod: e.target.value }))}
                  className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground focus:outline-none focus:border-primary/50'
                >
                  <option value=''>Custom date range</option>
                  <option value='last_week'>Last Week</option>
                  <option value='last_month'>Last Month</option>
                  <option value='last_year'>Last Year</option>
                </select>
              </div>

              <div className='grid grid-cols-1 lg:grid-cols-2 gap-4'>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    People (optional)
                  </label>
                  <input
                    type='text'
                    placeholder="John, Mary"
                    value={temporalFilters.people}
                    onChange={(e) => setTemporalFilters(prev => ({ ...prev, people: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>
                <div>
                  <label className='block text-sm font-medium text-foreground mb-2'>
                    Emotions (optional)
                  </label>
                  <input
                    type='text'
                    placeholder="happy, surprised"
                    value={temporalFilters.emotions}
                    onChange={(e) => setTemporalFilters(prev => ({ ...prev, emotions: e.target.value }))}
                    className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                </div>
              </div>
            </div>
          )}

          {/* Similarity Search */}
          {searchMode === 'similarity' && (
            <div className='space-y-4'>
              <div>
                <label className='block text-sm font-medium text-foreground mb-2'>
                  Reference Face ID
                </label>
                <input
                  type='text'
                  placeholder="Enter face ID to find similar faces"
                  value={similaritySearch.referenceFaceId}
                  onChange={(e) => setSimilaritySearch(prev => ({ ...prev, referenceFaceId: e.target.value }))}
                  className='w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                />
                <p className='text-xs text-muted-foreground mt-1'>
                  You can get face IDs from the face recognition panel or API
                </p>
              </div>

              <div>
                <label className='block text-sm font-medium text-foreground mb-2'>
                  Similarity Threshold ({Math.round(similaritySearch.threshold * 100)}%)
                </label>
                <input
                  type='range'
                  min={0.5}
                  max={1.0}
                  step={0.05}
                  value={similaritySearch.threshold}
                  onChange={(e) => setSimilaritySearch(prev => ({ ...prev, threshold: Number(e.target.value) }))}
                  className='w-full'
                />
                <div className='flex justify-between text-xs text-muted-foreground mt-1'>
                  <span>Less similar (50%)</span>
                  <span>More similar (100%)</span>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div className='space-y-4'>
              <div className='flex items-center gap-2 text-sm text-muted-foreground'>
                <Camera size={16} />
                <span>
                  Found {total} photo{total === 1 ? '' : 's'}
                </span>
              </div>

              <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4'>
                {results.slice(0, 20).map((result, index) => (
                  <div
                    key={`${result.photo_path}-${index}`}
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
                      <div className='text-xs text-primary'>
                        Match: {Math.round(result.match_score * 100)}%
                      </div>
                      {result.match_reasons.length > 0 && (
                        <div className='text-[10px] text-muted-foreground'>
                          {result.match_reasons.slice(0, 2).join(', ')}
                        </div>
                      )}
                      <div className='text-[10px] text-muted-foreground'>
                        {result.people_count} people
                        {result.emotions_detected.length > 0 &&
                          ` • ${result.emotions_detected.slice(0, 2).join(', ')}`
                        }
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
              No results found. Try adjusting your search criteria.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className='flex items-center justify-between p-6 border-t border-white/10'>
          <button
            onClick={resetSearch}
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
              onClick={executeSearch}
              className='btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2'
              disabled={loading}
            >
              {loading && <RefreshCw size={14} className='animate-spin' />}
              {loading ? 'Searching...' : 'Search Photos'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdvancedFaceSearch;
