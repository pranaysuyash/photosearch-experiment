/**
 * Advanced Intent-Based Search Component
 *
 * Provides an enhanced search interface that understands user intent
 * and provides contextual search capabilities.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Sparkles,
  Filter,
  Clock,
  MapPin,
  Users,
  Camera,
  Image,
  Calendar,
  Lightbulb,
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface IntentBadge {
  intent: string;
  type: string;
  label: string;
  icon: string;
}

interface SearchSuggestion {
  text: string;
  intent: string;
}

interface SearchIntentResult {
  primary_intent: string;
  secondary_intents: string[];
  confidence: number;
  badges: IntentBadge[];
  suggestions: string[];
}

interface IntentBasedSearchProps {
  onResults: (results: any[]) => void;
  initialQuery?: string;
}

export function IntentBasedSearch({ onResults, initialQuery = '' }: IntentBasedSearchProps) {
  const [query, setQuery] = useState(initialQuery);
  const [intent, setIntent] = useState<SearchIntentResult | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refinement, setRefinement] = useState('');
  const [previousResults, setPreviousResults] = useState<any[]>([]);

  const inputRef = useRef<HTMLInputElement>(null);

  // Detect intent as user types
  useEffect(() => {
    if (query.trim().length > 2) {
      detectIntent();
    } else {
      setIntent(null);
      setSuggestions([]);
    }
  }, [query]);

  const detectIntent = async () => {
    try {
      const result: SearchIntentResult = await api.get(`/intent/detect`, {
        params: { query }
      });
      setIntent(result);

      // Convert string suggestions to SearchSuggestion objects
      const suggestionObjects: SearchSuggestion[] = result.suggestions.map(s => ({
        text: s,
        intent: result.primary_intent
      }));
      setSuggestions(suggestionObjects);
    } catch (err) {
      console.error('Failed to detect intent:', err);
    }
  };

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const params = {
        query: searchQuery,
        intent_context: intent || {},
        filters: {},
        limit: 50,
        offset: 0
      };

      const response = await api.post('/search/intent', params);
      setPreviousResults(response.results);
      onResults(response.results);
    } catch (err) {
      console.error('Search failed:', err);
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefine = async () => {
    if (!refinement.trim() || previousResults.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const response = await api.post('/search/refine', {
        query,
        previous_results: previousResults,
        refinement
      });

      setPreviousResults(response.results);
      onResults(response.results);
      setRefinement('');
    } catch (err) {
      console.error('Refinement failed:', err);
      setError('Refinement failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    // Trigger search after setting new query
    setTimeout(() => handleSearch(suggestion), 100);
  };

  const getIntentIcon = (intentType: string) => {
    const intentIcons: Record<string, any> = {
      camera: Camera,
      date: Calendar,
      location: MapPin,
      people: Users,
      object: Image,
      scene: Image,
      event: Sparkles,
      technical: Lightbulb,
      color: Lightbulb,
      emotion: Lightbulb,
      activity: Lightbulb,
      generic: Search
    };

    return intentIcons[intentType] || Search;
  };

  return (
    <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
      <div className="space-y-4">
        {/* Search Input */}
        <div className="relative">
          <div className="relative flex items-center">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={20} />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSearch();
                }
              }}
              placeholder="Search photos by describing what you're looking for..."
              className={`w-full pl-12 pr-12 py-3 rounded-lg border border-white/10 bg-white/5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary ${glass.surface}`}
            />
            {query && (
              <button
                onClick={() => {
                  setQuery('');
                  setIntent(null);
                  setSuggestions([]);
                }}
                className="absolute right-10 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X size={18} />
              </button>
            )}
            <button
              onClick={() => handleSearch()}
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 btn-glass btn-glass--primary px-3 py-1.5 rounded-md flex items-center gap-1"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Search size={16} />
              )}
            </button>
          </div>

          {/* Intent Badges */}
          {intent && intent.badges.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {intent.badges.map((badge, index) => {
                const Icon = getIntentIcon(badge.intent);
                return (
                  <div
                    key={index}
                    className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm"
                  >
                    <Icon size={14} />
                    <span>{badge.label}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Suggestions Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className={`${glass.surfaceStrong} absolute z-10 mt-1 w-full border border-white/10 rounded-lg shadow-lg max-h-60 overflow-y-auto`}>
              {suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="px-4 py-3 hover:bg-white/5 cursor-pointer flex items-center gap-3"
                  onClick={() => handleSuggestionClick(suggestion.text)}
                >
                  <Lightbulb size={16} className="text-blue-400 flex-shrink-0" />
                  <span className="text-sm">{suggestion.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Advanced Filters Toggle */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            className="btn-glass btn-glass--muted text-sm px-3 py-1.5 flex items-center gap-2"
          >
            <Filter size={16} />
            Advanced Filters
            {showAdvancedFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          <div className="text-xs text-muted-foreground">
            {intent ? `Confidence: ${(intent.confidence * 100).toFixed(0)}%` : ''}
          </div>
        </div>

        {/* Advanced Filters Panel */}
        {showAdvancedFilters && (
          <div className={`${glass.surfaceStrong} rounded-lg p-4 border border-white/10`}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Date Range</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <input
                    type="date"
                    className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-muted-foreground mb-1">Location</label>
                <input
                  type="text"
                  placeholder="City, country..."
                  className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block text-xs text-muted-foreground mb-1">Camera Type</label>
                <select className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-sm focus:outline-none focus:ring-1 focus:ring-primary">
                  <option value="">Any camera</option>
                  <option value="canon">Canon</option>
                  <option value="nikon">Nikon</option>
                  <option value="sony">Sony</option>
                  <option value="iphone">iPhone</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Refinement Panel */}
        {previousResults.length > 0 && (
          <div className={`${glass.surfaceStrong} rounded-lg p-4 border border-white/10`}>
            <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
              <Lightbulb size={16} className="text-blue-400" />
              Refine Your Search
            </h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={refinement}
                onChange={(e) => setRefinement(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleRefine();
                  }
                }}
                placeholder="e.g., only photos from 2023, only beach photos..."
                className="flex-1 px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                onClick={handleRefine}
                disabled={loading || !refinement.trim()}
                className="btn-glass btn-glass--primary px-3 py-2 flex items-center gap-2"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Sparkles size={16} />
                    Refine
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
