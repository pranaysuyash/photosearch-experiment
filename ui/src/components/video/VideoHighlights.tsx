/**
 * Video Highlights Component - Display and manage video highlights
 *
 * Shows automatically generated highlight segments for each person in a video,
 * with options to view, export, and manage the highlights.
 */
import { useState, useEffect } from 'react';
import {
  Loader,
  AlertCircle,
  Clock,
  Download,
  Film,
  Sparkles,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface Highlight {
  person_id: string;
  person_name: string;
  start_time: number;
  end_time: number;
  duration: number;
  highlight_type: string;
  confidence: number;
  description: string;
}

interface VideoHighlightsProps {
  videoPath: string;
  onClose?: () => void;
}

export default function VideoHighlights({
  videoPath,
  onClose,
}: VideoHighlightsProps) {
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPerson, setExpandedPerson] = useState<string | null>(null);
  const [exportingPersonId, setExportingPersonId] = useState<string | null>(
    null
  );
  const [maxPerPerson, setMaxPerPerson] = useState(3);

  useEffect(() => {
    fetchHighlights();
  }, [videoPath, maxPerPerson]);

  const fetchHighlights = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get<{ highlights: Highlight[]; total_highlights: number }>(
        `/api/video/${encodeURIComponent(videoPath)}/highlights`,
        {
          params: { max_per_person: maxPerPerson },
        }
      );

      if (Array.isArray(response.highlights) && response.highlights.length > 0) {
        setHighlights(response.highlights);
      } else {
        setHighlights([]);
      }
    } catch (err) {
      let errorMessage = 'Failed to load highlights';

      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null && 'response' in err) {
        const httpError = err as { response?: { status?: number; data?: { detail?: string } } };
        if (httpError.response?.status === 404) {
          errorMessage = 'Video file not found';
        } else {
          errorMessage =
            httpError.response?.data?.detail || 'Failed to load highlights';
        }
      }

      setError(errorMessage);
      console.error('Failed to fetch highlights:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${String(minutes).padStart(2, '0')}:${String(
        secs
      ).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
  };

  const handleExportHighlights = async (personId: string) => {
    try {
      setExportingPersonId(personId);
      const response = await api.post<{ status: string; message?: string; error?: string }>(
        `/api/video/${encodeURIComponent(videoPath)}/export-highlights`,
        { person_id: personId }
      );

      if (response.status === 'completed') {
        alert(`Highlights for ${personId} exported successfully!`);
      } else {
        alert(response.message || response.error || 'Failed to export highlights');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExportingPersonId(null);
    }
  };

  // Group highlights by person
  const highlightsByPerson = highlights.reduce((acc, highlight) => {
    if (!acc[highlight.person_id]) {
      acc[highlight.person_id] = [];
    }
    acc[highlight.person_id].push(highlight);
    return acc;
  }, {} as Record<string, Highlight[]>);

  if (loading) {
    return (
      <div className={`p-8 rounded-xl ${glass.light} border ${glass.border}`}>
        <div className='space-y-4'>
          <div className='flex items-center justify-center gap-3 text-gray-600'>
            <Loader className='w-5 h-5 animate-spin' />
            <span>Loading video highlights…</span>
          </div>
          <div className='animate-pulse space-y-3'>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className={`h-20 rounded-xl ${glass.light} border ${glass.border}`}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-6 rounded-xl ${glass.light} border ${glass.border}`}>
        <div className='flex items-center gap-3 text-red-600 mb-3'>
          <AlertCircle className='w-5 h-5' />
          <span className='font-medium'>Error</span>
        </div>
        <p className='text-sm text-red-600 mb-3'>{error}</p>
        <button
          onClick={fetchHighlights}
          className='px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors'
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Header and Controls */}
      <div className={`p-4 rounded-xl ${glass.light} border ${glass.border}`}>
        <div className='flex items-center justify-between mb-4'>
          <div className='flex items-center gap-3'>
            <Film className='w-6 h-6 text-indigo-600' />
            <div>
              <h2 className='text-lg font-semibold text-gray-900'>
                Video Highlights
              </h2>
              <p className='text-xs text-gray-600 mt-1'>
                {Object.keys(highlightsByPerson).length} people •{' '}
                {highlights.length} highlights
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className='text-gray-500 hover:text-gray-700 transition-colors'
            >
              ✕
            </button>
          )}
        </div>

        {/* Max Per Person Control */}
        <div>
          <label className='block text-sm font-medium text-gray-700 mb-2'>
            Highlights per person: {maxPerPerson}
          </label>
          <input
            type='range'
            min='1'
            max='10'
            value={maxPerPerson}
            onChange={(e) => setMaxPerPerson(Number(e.target.value))}
            className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
          />
        </div>
      </div>

      {/* No Highlights Message */}
      {Object.keys(highlightsByPerson).length === 0 ? (
        <div
          className={`p-8 rounded-xl ${glass.light} border ${glass.border} text-center`}
        >
          <Sparkles className='w-12 h-12 text-gray-300 mx-auto mb-3' />
          <p className='text-gray-600 text-sm'>
            No highlights detected in this video
          </p>
          <p className='text-gray-500 text-xs mt-2'>
            Highlights are generated based on detected faces and their
            prominence in the video
          </p>
        </div>
      ) : (
        <div className='space-y-3'>
          {/* People and Their Highlights */}
          {Object.entries(highlightsByPerson).map(
            ([personId, personHighlights]) => (
              <div
                key={personId}
                className={`rounded-xl ${glass.light} border ${glass.border} overflow-hidden hover:border-indigo-300 transition`}
              >
                {/* Person Header */}
                <button
                  onClick={() =>
                    setExpandedPerson(
                      expandedPerson === personId ? null : personId
                    )
                  }
                  className='w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors text-left'
                >
                  <div className='flex-1'>
                    <div className='flex items-center gap-3'>
                      <div className='w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold text-sm'>
                        {personHighlights[0].person_name
                          .charAt(0)
                          .toUpperCase()}
                      </div>
                      <div>
                        <h3 className='font-semibold text-gray-900'>
                          {personHighlights[0].person_name}
                        </h3>
                        <div className='flex items-center gap-3 text-xs text-gray-600 mt-0.5'>
                          <span className='flex items-center gap-1'>
                            <Film className='w-3 h-3' />
                            {personHighlights.length} highlight
                            {personHighlights.length > 1 ? 's' : ''}
                          </span>
                          <span className='flex items-center gap-1'>
                            <Clock className='w-3 h-3' />
                            {formatTime(
                              personHighlights.reduce(
                                (sum, h) => sum + h.duration,
                                0
                              )
                            )}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className='flex items-center gap-2'>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleExportHighlights(personId);
                      }}
                      disabled={exportingPersonId === personId}
                      className='p-2 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
                      title='Export highlights'
                    >
                      {exportingPersonId === personId ? (
                        <Loader className='w-4 h-4 animate-spin text-indigo-600' />
                      ) : (
                        <Download className='w-4 h-4 text-gray-600' />
                      )}
                    </button>
                    <div
                      className={`text-gray-400 transition-transform ${
                        expandedPerson === personId ? 'rotate-180' : ''
                      }`}
                    >
                      ▼
                    </div>
                  </div>
                </button>

                {/* Expanded Highlights List */}
                {expandedPerson === personId && (
                  <div className='px-4 pb-4 pt-2 border-t border-gray-200 space-y-3'>
                    {personHighlights.map((highlight, idx) => (
                      <div
                        key={idx}
                        className='p-3 bg-gray-50 rounded-lg border border-gray-200 hover:border-indigo-300 transition-colors'
                      >
                        <div className='flex items-start justify-between gap-3'>
                          <div className='flex-1 min-w-0'>
                            {/* Highlight Type Badge */}
                            <div className='flex items-center gap-2 mb-2'>
                              <span className='px-2 py-0.5 text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full'>
                                {highlight.highlight_type}
                              </span>
                              <span className='text-xs text-gray-600'>
                                {(highlight.confidence * 100).toFixed(0)}%
                                confidence
                              </span>
                            </div>

                            {/* Time Range */}
                            <div className='flex items-center gap-2 text-sm text-gray-700 mb-2'>
                              <Clock className='w-4 h-4 flex-shrink-0' />
                              <span>
                                {formatTime(highlight.start_time)} -{' '}
                                {formatTime(highlight.end_time)}
                              </span>
                              <span className='text-gray-600'>
                                ({formatTime(highlight.duration)})
                              </span>
                            </div>

                            {/* Description */}
                            {highlight.description && (
                              <p className='text-sm text-gray-600 mt-2'>
                                {highlight.description}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
