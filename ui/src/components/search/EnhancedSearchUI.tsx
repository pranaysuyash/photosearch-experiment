import { useState, useMemo, useRef } from 'react';
import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  X,
  Image as ImageIcon,
  Film,
  FileText,
  SortAsc,
  SortDesc,
  Hash,
  Star,
} from 'lucide-react';
import { SearchToggle, type SearchMode } from './SearchToggle';
import { SearchModeHelp } from './SearchModeHelp';
import { IntentRecognition } from './IntentRecognition';
import { MetadataFieldAutocomplete } from './MetadataFieldAutocomplete';
import { useLiveMatchCount } from '../../hooks/useLiveMatchCount';
import { glass } from '../../design/glass';

interface EnhancedSearchUIProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchMode: SearchMode;
  setSearchMode: (mode: SearchMode) => void;
  sortBy: string;
  setSortBy: (sort: string) => void;
  typeFilter: string;
  setTypeFilter: (filter: string) => void;
  favoritesFilter?: string;
  setFavoritesFilter?: (filter: string) => void;
  onSearch: () => void;
  isCompact?: boolean;
  heroTitle?: ReactNode;
  heroSubtitle?: ReactNode;
}

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Newest First', icon: SortDesc },
  { value: 'date_asc', label: 'Oldest First', icon: SortAsc },
  { value: 'name', label: 'Filename A-Z', icon: FileText },
  { value: 'size', label: 'Largest Files', icon: Hash },
];

const TYPE_FILTERS = [
  { value: 'all', label: 'All Media', icon: ImageIcon },
  { value: 'photos', label: 'Images Only', icon: ImageIcon },
  { value: 'videos', label: 'Videos Only', icon: Film },
];

const FAVORITES_FILTERS = [
  { value: 'all', label: 'All', icon: ImageIcon },
  { value: 'favorites_only', label: 'Favorites', icon: Star },
];

const SEARCH_SUGGESTIONS = [
  'sunset in paris',
  'birthday cake',
  'red cars',
  'smiling faces',
  'documents from 2023',
  'vacation photos',
  'family gatherings',
  'nature landscapes',
  'city streets',
  'food and drinks',
];

export function EnhancedSearchUI({
  searchQuery,
  setSearchQuery,
  searchMode,
  setSearchMode,
  sortBy,
  setSortBy,
  typeFilter,
  setTypeFilter,
  favoritesFilter,
  setFavoritesFilter,
  onSearch,
  isCompact = false,
  heroTitle = 'Rediscover your memories',
  heroSubtitle,
}: EnhancedSearchUIProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showHelpHint, setShowHelpHint] = useState(false);
  const [showFieldAutocomplete, setShowFieldAutocomplete] = useState(false);
  const [recognizedIntent, setRecognizedIntent] = useState<string | null>(null);
  const [autoHelpSeen, setAutoHelpSeen] = useState(() => {
    try {
      return localStorage.getItem('lm:searchHelpSeen') === '1';
    } catch {
      return false;
    }
  });

  // Live match count hook
  const { count: liveMatchCount, isLoading: isCountingMatches } = useLiveMatchCount({
    query: searchQuery,
    searchMode,
    debounceMs: 500
  });
  const filteredSuggestions = useMemo(() => {
    if (searchQuery.length > 0) {
      return SEARCH_SUGGESTIONS.filter((suggestion) =>
        suggestion.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    return SEARCH_SUGGESTIONS;
  }, [searchQuery]);
  const inputRef = useRef<HTMLInputElement>(null);

  // filteredSuggestions is computed with useMemo to avoid setState inside effects

  const handleSuggestionClick = (suggestion: string) => {
    setSearchQuery(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleIntentRecognized = (intent: string) => {
    setRecognizedIntent(intent);
    // Auto-switch modes based on intent
    if (intent.startsWith('find_technical') || intent.startsWith('find_date') || intent.startsWith('camera')) {
      setSearchMode('metadata');
    } else if (intent.startsWith('find_person') || intent.startsWith('find_emotion') || intent.startsWith('find_object')) {
      setSearchMode('semantic');
    }
  };

  const handleFieldSelected = (newQuery: string) => {
    setSearchQuery(newQuery);
    setShowFieldAutocomplete(false);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearch();
      setShowSuggestions(false);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      inputRef.current?.blur();
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    inputRef.current?.focus();
  };

  if (isCompact) {
    return (
      <div className='relative w-full max-w-3xl'>
        {/* Compact Search Bar */}
        <div className={`${glass.surface} flex items-center rounded-full shadow-lg p-1`}>
          <Search className='ml-4 text-muted-foreground w-5 h-5' />
          <input
            ref={inputRef}
            type='text'
            className='flex-1 bg-transparent border-none outline-none px-3 py-2 text-sm placeholder:text-muted-foreground/50'
            placeholder='Search photos...'
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (showHelpHint) setShowHelpHint(false);
              
              // Show field autocomplete for metadata mode
              if (searchMode === 'metadata' && e.target.value.length > 1) {
                setShowFieldAutocomplete(true);
                setShowSuggestions(false);
              } else {
                setShowFieldAutocomplete(false);
              }
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (!autoHelpSeen && searchQuery.length === 0) {
                setShowHelpHint(true);
                setAutoHelpSeen(true);
                try {
                  localStorage.setItem('lm:searchHelpSeen', '1');
                } catch {
                  // ignore
                }
                return;
              }
              if (searchQuery.length === 0) {
                setShowSuggestions(true);
              } else if (searchMode === 'metadata' && searchQuery.length > 1) {
                setShowFieldAutocomplete(true);
              }
            }}
            onBlur={() =>
              setTimeout(() => {
                setShowSuggestions(false);
                setShowHelpHint(false);
                setShowFieldAutocomplete(false);
              }, 150)
            }
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className='p-1 mr-2 text-muted-foreground hover:text-foreground transition-colors'
              title='Clear search'
              aria-label='Clear search'
            >
              <X size={16} />
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 mr-1 rounded-full transition-colors ${showFilters
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground'
              }`}
            title={showFilters ? 'Hide filters' : 'Show filters'}
            aria-label={showFilters ? 'Hide filters' : 'Show filters'}
          >
            <Filter size={16} />
          </button>
          <div className='mr-1'>
            <SearchModeHelp />
          </div>
          <button
            onClick={onSearch}
            className={`${glass.buttonPrimary} text-xs sm:text-sm font-semibold px-4 py-2 mr-1`}
            title='Search'
            aria-label='Search'
          >
            Search
          </button>
        </div>

        {/* Live Match Count - More Prominent and Always Visible */}
        <div className="flex items-center justify-center mt-3 mb-2 min-h-[40px]">
          <div className="flex items-center gap-3">
            {isCountingMatches ? (
              <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 px-4 py-2 rounded-full border border-blue-200 shadow-sm">
                <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                Analyzing your query...
              </div>
            ) : liveMatchCount !== null ? (
              <div className={`text-sm font-semibold px-4 py-2 rounded-full border shadow-sm ${
                liveMatchCount === 0 
                  ? 'text-red-700 bg-red-50 border-red-200' 
                  : 'text-green-700 bg-green-50 border-green-200'
              }`}>
                {liveMatchCount === 0 ? 'No matches found' : 
                 `${liveMatchCount} ${liveMatchCount === 1 ? 'match' : 'matches'} found`}
              </div>
            ) : searchQuery.trim() ? (
              <div className="text-sm text-gray-500 bg-gray-50 px-4 py-2 rounded-full border border-gray-200">
                Type to see live match count...
              </div>
            ) : null}
            {recognizedIntent && (
              <div className="text-sm text-purple-700 bg-purple-50 border border-purple-200 px-3 py-2 rounded-full shadow-sm">
                Intent: {recognizedIntent.replace('_', ' ')}
              </div>
            )}
          </div>
        </div>

        {/* Intent Recognition */}
        <IntentRecognition
          query={searchQuery}
          onIntentDetected={handleIntentRecognized}
        />

        {/* Field Autocomplete */}
        <div className="relative">
          <MetadataFieldAutocomplete
            query={searchQuery}
            onFieldSelected={handleFieldSelected}
            isVisible={showFieldAutocomplete && searchMode === 'metadata'}
          />
        </div>

        {/* First-run hint (compact mode) */}
        <AnimatePresence>
          {showHelpHint && !showFilters && !showSuggestions && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`absolute top-full mt-2 w-full ${glass.surfaceStrong} rounded-lg shadow-xl p-4 z-40`}
            >
              <div className='text-sm font-semibold text-foreground mb-2'>
                Search modes (quick guide)
              </div>
              <div className='text-sm text-muted-foreground space-y-1'>
                <div>
                  <span className='text-foreground font-semibold'>Metadata</span>{' '}
                  — filenames, folders, dates, cameras (fastest).
                </div>
                <div>
                  <span className='text-foreground font-semibold'>Semantic</span>{' '}
                  — meaning (“sunset in paris”, “birthday cake”).
                </div>
                <div>
                  <span className='text-foreground font-semibold'>Hybrid</span>{' '}
                  — best recall when you’re not sure.
                </div>
              </div>
              <div className='mt-3 text-xs text-muted-foreground'>
                Use <span className='text-foreground'>Filters</span> (funnel) to
                change mode, sort, and media type.
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Compact Filters Panel */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              className={`absolute top-full mt-2 w-full ${glass.surfaceStrong} rounded-lg shadow-xl p-4 z-50`}
            >
              <div className='space-y-4'>
                {/* Search Mode */}
                <div>
                  <label className='text-sm font-medium mb-2 block'>
                    Search Mode
                  </label>
                  <SearchToggle value={searchMode} onChange={setSearchMode} />
                </div>

                {/* Sort By */}
                <div>
                  <label className='text-sm font-medium mb-2 block'>
                    Sort By
                  </label>
                  <div className='flex gap-2 flex-wrap'>
                    {SORT_OPTIONS.map((option) => {
                      const Icon = option.icon;
                      return (
                        <button
                          key={option.value}
                          onClick={() => setSortBy(option.value)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs transition-all ${sortBy === option.value
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                            }`}
                          title={`Sort by ${option.label}`}
                          aria-label={`Sort by ${option.label}`}
                        >
                          <Icon size={12} />
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Type Filter */}
                <div>
                  <label className='text-sm font-medium mb-2 block'>
                    Media Type
                  </label>
                  <div className='flex gap-2'>
                    {TYPE_FILTERS.map((filter) => {
                      const Icon = filter.icon;
                      return (
                        <button
                          key={filter.value}
                          onClick={() => setTypeFilter(filter.value)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs transition-all ${typeFilter === filter.value
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                            }`}
                        >
                          <Icon size={12} />
                          {filter.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Favorites Filter */}
                {favoritesFilter && setFavoritesFilter && (
                  <div>
                    <label className='text-sm font-medium mb-2 block'>
                      Favorites
                    </label>
                    <div className='flex gap-2'>
                      {FAVORITES_FILTERS.map((filter) => {
                        const Icon = filter.icon;
                        return (
                          <button
                            key={filter.value}
                            onClick={() => setFavoritesFilter(filter.value)}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs transition-all ${favoritesFilter === filter.value
                              ? 'bg-primary text-primary-foreground'
                              : 'bg-muted hover:bg-muted/80 text-muted-foreground'
                              }`}
                          >
                            <Icon size={12} />
                            {filter.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Suggestions Dropdown */}
        <AnimatePresence>
          {showSuggestions && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className='absolute top-full mt-2 w-full glass-surface rounded-lg shadow-xl max-h-48 overflow-y-auto z-40'
            >
              {filteredSuggestions.map((suggestion: string, index: number) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className='w-full text-left px-4 py-2 hover:bg-muted transition-colors text-sm'
                >
                  <div className='flex items-center gap-2'>
                    <Search size={14} className='text-muted-foreground' />
                    {suggestion}
                  </div>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // Full Hero Version
  return (
    <motion.div
      className='flex flex-col items-center justify-center py-12 md:py-14 px-4'
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50, scale: 0.9 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      {heroTitle !== null && (
        <motion.h1
          className='text-4xl md:text-5xl font-semibold tracking-tight mb-3 text-center bg-gradient-to-b from-foreground to-muted-foreground bg-clip-text text-transparent'
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          {heroTitle}
        </motion.h1>
      )}

      {heroSubtitle && (
        <motion.p
          className='text-sm md:text-base text-muted-foreground/70 text-center mb-6'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.4 }}
        >
          {heroSubtitle}
        </motion.p>
      )}

      {/* Search Mode Selector - Visible Above Search */}
      <motion.div
        className='mb-4 flex items-center justify-center gap-3'
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <SearchToggle value={searchMode} onChange={setSearchMode} />
        <SearchModeHelp />
      </motion.div>

      <motion.div
        className='relative w-full max-w-4xl space-y-4'
        layoutId='search-container'
      >
        {/* Main Search Bar */}
        <motion.div className='relative group' layoutId='search-bar'>
          <div className='absolute inset-0 bg-primary/20 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 rounded-full' />

          <div className={`${glass.surface} relative flex items-center rounded-full shadow-2xl p-2 transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/50 focus-within:border-primary/50`}>
            <Search className='ml-4 text-muted-foreground w-6 h-6' />
            <input
              ref={inputRef}
              type='text'
              className='flex-1 bg-transparent border-none outline-none px-4 py-3 text-lg placeholder:text-muted-foreground/50'
              placeholder="Search for 'sunset in paris' or 'birthday cake'"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                
                // Show field autocomplete for metadata mode
                if (searchMode === 'metadata' && e.target.value.length > 1) {
                  setShowFieldAutocomplete(true);
                  setShowSuggestions(false);
                } else {
                  setShowFieldAutocomplete(false);
                }
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                if (searchQuery.length === 0) {
                  setShowSuggestions(true);
                } else if (searchMode === 'metadata' && searchQuery.length > 1) {
                  setShowFieldAutocomplete(true);
                }
              }}
              onBlur={() => setTimeout(() => {
                setShowSuggestions(false);
                setShowFieldAutocomplete(false);
              }, 150)}
              autoFocus
            />
            {searchQuery && (
              <button
                onClick={clearSearch}
                className='p-2 mr-2 text-muted-foreground hover:text-foreground transition-colors'
                title='Clear search'
                aria-label='Clear search'
              >
                <X size={18} />
              </button>
            )}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-3 mr-2 rounded-full transition-colors ${showFilters
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/10'
                }`}
              title={showFilters ? 'Hide filters' : 'Show filters'}
              aria-label={showFilters ? 'Hide filters' : 'Show filters'}
            >
              <Filter size={18} />
            </button>
            <button
              onClick={onSearch}
              className='bg-primary text-primary-foreground px-6 py-3 rounded-full font-medium hover:opacity-90 transition-opacity mr-2'
            >
              Search
            </button>
          </div>
        </motion.div>

        {/* Live Match Count & Intent Recognition */}
        <motion.div 
          className="w-full max-w-4xl"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {/* Live Match Count - Always Visible */}
          <div className="flex items-center justify-center gap-4 mb-4 min-h-[48px]">
            {isCountingMatches ? (
              <div className="flex items-center gap-2 text-sm text-blue-600 bg-blue-50 px-4 py-2 rounded-full border border-blue-200 shadow-sm">
                <div className="w-4 h-4 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                Analyzing your query...
              </div>
            ) : liveMatchCount !== null ? (
              <div className={`text-sm font-medium px-4 py-2 rounded-full shadow-sm ${
                liveMatchCount === 0 
                  ? 'text-red-600 bg-red-50 border border-red-200' 
                  : 'text-green-600 bg-green-50 border border-green-200'
              }`}>
                {liveMatchCount === 0 ? 'No matches found' : 
                 `${liveMatchCount} ${liveMatchCount === 1 ? 'match' : 'matches'} found`}
              </div>
            ) : searchQuery.trim() ? (
              <div className="text-sm text-muted-foreground bg-muted px-4 py-2 rounded-full border">
                Type to see live match count...
              </div>
            ) : null}
            {recognizedIntent && (
              <div className="text-sm text-blue-600 bg-blue-50 border border-blue-200 px-3 py-2 rounded-full shadow-sm">
                Intent: {recognizedIntent.replace('_', ' ')}
              </div>
            )}
          </div>

          {/* Intent Recognition */}
          <IntentRecognition
            query={searchQuery}
            onIntentDetected={handleIntentRecognized}
          />

          {/* Field Autocomplete */}
          <div className="relative">
            <MetadataFieldAutocomplete
              query={searchQuery}
              onFieldSelected={handleFieldSelected}
              isVisible={showFieldAutocomplete && searchMode === 'metadata'}
            />
          </div>
        </motion.div>

        {/* Advanced Filters Panel */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0, scale: 0.95 }}
              animate={{ opacity: 1, height: 'auto', scale: 1 }}
              exit={{ opacity: 0, height: 0, scale: 0.95 }}
              className={`${glass.surfaceStrong} rounded-2xl shadow-2xl p-6 overflow-hidden`}
            >
              <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                {/* Search Mode */}
                <div className='space-y-3'>
                  <label className='text-sm font-medium flex items-center gap-2'>
                    <Search size={16} />
                    Search Mode
                  </label>
                  <SearchToggle value={searchMode} onChange={setSearchMode} />
                </div>

                {/* Sort Options */}
                <div className='space-y-3'>
                  <label className='text-sm font-medium flex items-center gap-2'>
                    <SortAsc size={16} />
                    Sort By
                  </label>
                  <div className='flex flex-wrap gap-2'>
                    {SORT_OPTIONS.map((option) => {
                      const Icon = option.icon;
                      return (
                        <button
                          key={option.value}
                          onClick={() => setSortBy(option.value)}
                          className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-sm transition-all ${sortBy === option.value
                            ? 'bg-primary text-primary-foreground shadow-md'
                            : 'bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground'
                            }`}
                        >
                          <Icon size={14} />
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Type Filters */}
                <div className='space-y-3'>
                  <label className='text-sm font-medium flex items-center gap-2'>
                    <ImageIcon size={16} />
                    Media Type
                  </label>
                  <div className='flex flex-wrap gap-2'>
                    {TYPE_FILTERS.map((filter) => {
                      const Icon = filter.icon;
                      return (
                        <button
                          key={filter.value}
                          onClick={() => setTypeFilter(filter.value)}
                          className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-sm transition-all ${typeFilter === filter.value
                            ? 'bg-primary text-primary-foreground shadow-md'
                            : 'bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-foreground'
                            }`}
                        >
                          <Icon size={14} />
                          {filter.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search Suggestions */}
        <AnimatePresence>
          {showSuggestions && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`${glass.surface} rounded-2xl shadow-2xl p-4 max-h-48 overflow-y-auto`}
            >
              <div className='text-sm text-muted-foreground mb-2'>
                Try searching for:
              </div>
              <div className='grid grid-cols-2 md:grid-cols-3 gap-2'>
                {filteredSuggestions
                  .slice(0, 9)
                  .map((suggestion: string, index: number) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className='text-left p-2 rounded-lg hover:bg-white/5 transition-colors text-sm'
                    >
                      {suggestion}
                    </button>
                  ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <motion.p
        className='mt-6 text-sm text-muted-foreground/60 italic text-center'
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.4 }}
      >
        Advanced search with multiple modes • Keyboard shortcuts available
      </motion.p>
    </motion.div>
  );
}
