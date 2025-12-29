/**
 * Events Component - Display detected events based on face co-occurrence
 *
 * Shows detected gatherings and events where multiple people appear together
 * in photos within a certain time window.
 */
import { useState, useEffect } from 'react';
import {
  Calendar,
  Users,
  Image as ImageIcon,
  Sparkles,
  Loader,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface DetectedEvent {
  event_id: string;
  start_time: string;
  end_time: string;
  photo_count: number;
  people_count: number;
  people_involved: string[];
  photos: string[];
  event_type: string;
  confidence_score: number;
}

interface EventsProps {
  onClose?: () => void;
}

export default function Events({ onClose }: EventsProps) {
  const [events, setEvents] = useState<DetectedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minPeople, setMinPeople] = useState(3);
  const [timeWindowHours, setTimeWindowHours] = useState(24);
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);

  useEffect(() => {
    fetchEvents();
  }, [minPeople, timeWindowHours]);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/api/analytics/events', {
        params: {
          min_people: minPeople,
          time_window_hours: timeWindowHours,
        },
      });

      if (response.data.success) {
        setEvents(response.data.events || []);
      } else {
        setError(response.data.detail || 'Failed to fetch events');
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else if (typeof err === 'object' && err !== null && 'response' in err) {
        const httpError = err as any;
        setError(httpError.response?.data?.detail || 'Failed to fetch events');
      } else {
        setError('Failed to fetch events');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const getEventTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      large_gathering: 'Large Gathering',
      party: 'Party',
      small_gathering: 'Small Gathering',
      meeting: 'Meeting',
    };
    return labels[type] || type;
  };

  const getEventTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      large_gathering: 'from-purple-500 to-pink-500',
      party: 'from-pink-500 to-rose-500',
      small_gathering: 'from-blue-500 to-cyan-500',
      meeting: 'from-green-500 to-emerald-500',
    };
    return colors[type] || 'from-gray-500 to-slate-500';
  };

  if (loading) {
    return (
      <div className={`p-6 rounded-xl ${glass.light} border ${glass.border}`}>
        <div className='space-y-4'>
          <div className='flex items-center justify-center gap-3 text-gray-600'>
            <Loader className='w-5 h-5 animate-spin' />
            <span>Loading events...</span>
          </div>
          <div className='animate-pulse space-y-3'>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className={`h-24 rounded-xl ${glass.light} border ${glass.border}`}
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
        <div className='text-red-600 text-sm'>{error}</div>
        <button
          onClick={fetchEvents}
          className='mt-3 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors'
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Controls */}
      <div
        className={`p-4 rounded-xl ${glass.light} border ${glass.border} space-y-4`}
      >
        <div className='flex items-center justify-between'>
          <h3 className='text-lg font-semibold text-gray-900'>
            Event Detection Settings
          </h3>
          <Sparkles className='w-5 h-5 text-indigo-600' />
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
          {/* Min People */}
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-2'>
              Minimum People: {minPeople}
            </label>
            <input
              type='range'
              min='2'
              max='10'
              value={minPeople}
              onChange={(e) => setMinPeople(Number(e.target.value))}
              className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
            />
          </div>

          {/* Time Window */}
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-2'>
              Time Window: {timeWindowHours} hours
            </label>
            <select
              value={timeWindowHours}
              onChange={(e) => setTimeWindowHours(Number(e.target.value))}
              className={`w-full px-3 py-2 rounded-lg ${glass.light} border ${glass.border} text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500`}
            >
              <option value={6}>6 hours</option>
              <option value={12}>12 hours</option>
              <option value={24}>24 hours</option>
              <option value={48}>48 hours</option>
              <option value={72}>72 hours</option>
            </select>
          </div>
        </div>
      </div>

      {/* Events List */}
      {events.length === 0 ? (
        <div
          className={`p-8 rounded-xl ${glass.light} border ${glass.border} text-center`}
        >
          <Calendar className='w-12 h-12 text-gray-300 mx-auto mb-3' />
          <p className='text-gray-600 text-sm'>
            No events detected with current settings
          </p>
          <p className='text-gray-500 text-xs mt-2'>
            Try lowering the minimum people count or increasing the time window
          </p>
        </div>
      ) : (
        <div className='space-y-4'>
          <div className='flex items-center justify-between'>
            <h3 className='text-lg font-semibold text-gray-900'>
              Detected Events ({events.length})
            </h3>
          </div>

          <div className='space-y-3'>
            {events.map((event) => (
              <div
                key={event.event_id}
                className={`p-4 rounded-xl ${glass.light} border ${glass.border} hover:border-indigo-300 transition-all cursor-pointer`}
                onClick={() =>
                  setExpandedEvent(
                    expandedEvent === event.event_id ? null : event.event_id
                  )
                }
              >
                {/* Event Header */}
                <div className='flex items-start justify-between gap-4'>
                  <div className='flex-1'>
                    {/* Event Type Badge */}
                    <div className='flex items-center gap-3 mb-2'>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold text-white bg-gradient-to-r ${getEventTypeColor(
                          event.event_type
                        )}`}
                      >
                        {getEventTypeLabel(event.event_type)}
                      </span>
                      <span className='text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded'>
                        Confidence: {(event.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* Event Time Range */}
                    <div className='flex items-center gap-2 text-sm text-gray-600 mb-2'>
                      <Calendar className='w-4 h-4' />
                      <span>
                        {formatDate(event.start_time)} -{' '}
                        {formatDate(event.end_time)}
                      </span>
                    </div>

                    {/* Event Stats */}
                    <div className='flex flex-wrap gap-4 text-sm'>
                      <div className='flex items-center gap-2 text-gray-600'>
                        <Users className='w-4 h-4' />
                        <span>{event.people_count} people</span>
                      </div>
                      <div className='flex items-center gap-2 text-gray-600'>
                        <ImageIcon className='w-4 h-4' />
                        <span>{event.photo_count} photos</span>
                      </div>
                    </div>
                  </div>

                  {/* Expand Arrow */}
                  <div
                    className={`text-gray-400 transition-transform ${
                      expandedEvent === event.event_id ? 'rotate-180' : ''
                    }`}
                  >
                    ▼
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedEvent === event.event_id && (
                  <div className='mt-4 pt-4 border-t border-gray-200 space-y-4'>
                    {/* People Involved */}
                    {event.people_involved.length > 0 && (
                      <div>
                        <h4 className='text-sm font-semibold text-gray-900 mb-2'>
                          People Involved
                        </h4>
                        <div className='flex flex-wrap gap-2'>
                          {event.people_involved.map((personId) => (
                            <span
                              key={personId}
                              className='px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium'
                            >
                              {personId}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Photos Grid */}
                    {event.photos.length > 0 && (
                      <div>
                        <h4 className='text-sm font-semibold text-gray-900 mb-2'>
                          Photos from this Event
                        </h4>
                        <div className='grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2'>
                          {event.photos.slice(0, 8).map((photoPath, idx) => (
                            <div
                              key={idx}
                              className='relative aspect-square rounded-lg overflow-hidden bg-gray-100 hover:opacity-80 transition-opacity group cursor-pointer'
                            >
                              <img
                                src={`/api/photo/thumbnail?path=${encodeURIComponent(
                                  photoPath
                                )}`}
                                alt={`Event photo ${idx + 1}`}
                                className='w-full h-full object-cover'
                                onError={(e) => {
                                  e.currentTarget.src =
                                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23f3f4f6" width="100" height="100"/%3E%3Ctext x="50" y="50" text-anchor="middle" dy=".3em" fill="%239ca3af" font-size="12"%3ENo image%3C/text%3E%3C/svg%3E';
                                }}
                              />
                              <div className='absolute inset-0 bg-gradient-to-t from-black/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-2'>
                                <span className='text-white text-xs font-medium'>
                                  {photoPath.split('/').pop()}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                        {event.photos.length > 8 && (
                          <p className='text-xs text-gray-500 mt-2'>
                            +{event.photos.length - 8} more photos
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
