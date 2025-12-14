/**
 * Intent Recognition Component
 *
 * Detects user intent from search queries and provides suggestions
 */

import { useState, useEffect, useCallback } from 'react';
import './IntentRecognition.css';

interface IntentRecognitionProps {
  query: string;
  onIntentDetected: (intent: string) => void;
}

export const IntentRecognition = ({
  query,
  onIntentDetected,
}: IntentRecognitionProps) => {
  const [intent, setIntent] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [badges, setBadges] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const detectIntent = useCallback(
    async (searchQuery: string) => {
      try {
        setLoading(true);
        setError(null);

        // Detect intent
        const intentResponse = await fetch(
          `/api/intent/detect?query=${encodeURIComponent(searchQuery)}`
        );
        if (!intentResponse.ok) {
          // API endpoint not available; silently return
          setLoading(false);
          return;
        }

        let intentData;
        try {
          intentData = await intentResponse.json();
        } catch (err) {
          // Invalid JSON response; silently return
          console.debug('Intent detect JSON parse error', err);
          setLoading(false);
          return;
        }

        setIntent(intentData.intent);

        // Get suggestions (non-critical)
        try {
          const suggestionsResponse = await fetch(
            `/api/intent/suggestions?query=${encodeURIComponent(searchQuery)}`
          );
          if (suggestionsResponse.ok) {
            const suggestionsData = await suggestionsResponse.json();
            setSuggestions(suggestionsData.suggestions || []);
          }
        } catch (err) {
          // ignore suggestions errors
          console.debug('Intent suggestions fetch error', err);
        }

        // Get badges (non-critical)
        try {
          const badgesResponse = await fetch(
            `/api/intent/badges?query=${encodeURIComponent(searchQuery)}`
          );
          if (badgesResponse.ok) {
            const badgesData = await badgesResponse.json();
            setBadges(badgesData.badges || []);
          }
        } catch (err) {
          // ignore badge errors
          console.debug('Intent badges fetch error', err);
        }

        // Notify parent component
        if (onIntentDetected) {
          onIntentDetected(intentData.intent);
        }
      } catch (err) {
        // Silently ignore all errors; Intent detection is optional
        console.debug('Intent detection skipped (API not available):', err);
      } finally {
        setLoading(false);
      }
    },
    [onIntentDetected]
  );

  // Detect intent when query changes
  useEffect(() => {
    if (query && query.trim().length > 2) {
      detectIntent(query);
    } else {
      setIntent(null);
      setSuggestions([]);
      setBadges([]);
    }
  }, [query, detectIntent]);

  const getIntentIcon = (intentName: string) => {
    const icons: Record<string, string> = {
      find_person: '👤',
      find_location: '📍',
      find_object: '🔍',
      find_event: '🎉',
      find_date: '📅',
      find_color: '�',
      find_emotion: '😊',
      find_style: '🎭',
      find_quality: '⭐',
      find_technical: '🔧',
      find_creative: '💡',
      find_organize: '�',
    };
    return icons[intentName] || '🔮';
  };

  const getIntentDescription = (intentName: string) => {
    const descriptions: Record<string, string> = {
      find_person: 'Looking for specific people in photos',
      find_location: 'Searching for photos from specific locations',
      find_object: 'Finding photos containing specific objects',
      find_event: 'Looking for photos from specific events',
      find_date: 'Searching for photos from specific dates or time periods',
      find_color: 'Finding photos with specific colors or color schemes',
      find_emotion: 'Looking for photos that convey specific emotions',
      find_style: 'Searching for photos with specific artistic styles',
      find_quality: 'Finding photos based on technical quality',
      find_technical: 'Searching based on technical metadata',
      find_creative: 'Looking for creative or artistic photos',
      find_organize: 'Organizing or managing photo collections',
    };
    return descriptions[intentName] || 'Analyzing your search intent';
  };

  if (loading) {
    return (
      <div className='intent-loading'>Analyzing your search intent...</div>
    );
  }

  if (error) {
    return <div className='intent-error'>Error: {error.message}</div>;
  }

  if (!intent) {
    return null;
  }

  return (
    <div className='intent-recognition'>
      <div className='intent-header'>
        <div
          className={`intent-icon intent-${intent.replace(/_/g, '-')}`}
          aria-hidden='true'
          title={intent.replace('_', ' ')}
        >
          {getIntentIcon(intent)}
        </div>
        <div className='intent-info'>
          <h3 className='intent-name'>{intent.replace('_', ' ')}</h3>
          <p className='intent-description'>{getIntentDescription(intent)}</p>
        </div>
      </div>

      {suggestions.length > 0 && (
        <div className='intent-suggestions'>
          <h4>Suggestions:</h4>
          <div className='suggestion-list'>
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                className='suggestion-item'
                onClick={() => {
                  if (onIntentDetected) {
                    onIntentDetected(suggestion);
                  }
                }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {badges.length > 0 && (
        <div className='intent-badges'>
          <h4>Related:</h4>
          <div className='badge-list'>
            {badges.map((badge, index) => (
              <span key={index} className='badge-item'>
                {badge}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default IntentRecognition;
