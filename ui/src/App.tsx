import { useState, useCallback, useEffect } from 'react'
import { ErrorBoundary } from "react-error-boundary";
import { motion, AnimatePresence, LayoutGroup } from 'framer-motion';
import { PhotoGrid } from './components/PhotoGrid'
import { ModernPhotoGrid } from './components/ModernPhotoGrid'
import { ModernGalleryDemo } from './components/ModernGalleryDemo'
import { SonicTimeline } from './components/SonicTimeline'
import { Spotlight } from './components/Spotlight'
import { StoryMode } from './components/StoryMode'
import { PhotoGlobe } from './components/PhotoGlobe'
import { PhotoDetail } from './components/PhotoDetail'
import { FirstRunModal } from './components/FirstRunModal'
import { BigSearchHero } from './components/BigSearchHero'
import { useDebounce } from './hooks/useDebounce';
import { usePhotoSearch } from './hooks/usePhotoSearch';
import { type Photo } from './api';
import { Globe2, LayoutGrid, Moon, Sun, Search, ArrowUpDown, Image, Film, Layers, Sparkles, Code } from 'lucide-react';
import { SearchToggle, type SearchMode } from './components/SearchToggle';

function ErrorFallback({ error, resetErrorBoundary }: { error: Error, resetErrorBoundary: () => void }) {
  return (
    <div role="alert" className="p-4 border border-destructive rounded bg-destructive/10 text-destructive">
      <p className="font-bold">Something went wrong:</p>
      <pre className="text-sm mt-2">{error.message}</pre>
      <button onClick={resetErrorBoundary} className="mt-4 px-4 py-2 bg-destructive text-destructive-foreground rounded">Try again</button>
    </div>
  )
}

function App() {
  const [searchQuery, setSearchQuery] = useState("")
  const [searchMode, setSearchMode] = useState<SearchMode>('metadata') // Metadata for browsing, semantic for searching
  const [viewMode, setViewMode] = useState<'story' | 'globe'>('story')
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number | null>(null)
  const [viewedPhotos, setViewedPhotos] = useState<Photo[]>([])
  const [isDark, setIsDark] = useState(true);
  const [galleryMode, setGalleryMode] = useState<'traditional' | 'modern' | 'demo'>('traditional')

  // Sorting and filtering state
  const [sortBy, setSortBy] = useState<string>('date_desc');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  const { results: photos, loading, error, setQuery, hasMore, loadMore } = usePhotoSearch({
    initialQuery: "",
    initialFetch: true,
    mode: searchMode,
    sortBy,
    typeFilter
  });

  const debouncedSearch = useDebounce(searchQuery, 500);

  useEffect(() => {
    setQuery(debouncedSearch);
  }, [debouncedSearch, setQuery]);

  const isSearching = debouncedSearch.length > 0;

  // Show BigSearchHero when: no photos yet AND not actively searching
  const showBigHero = photos.length === 0 && !isSearching && viewMode === 'story';

  const handlePhotoSelect = useCallback((photo: Photo) => {
    const index = photos.findIndex(p => p.path === photo.path);
    if (index >= 0) {
      setSelectedPhotoIndex(index);
      if (isSearching || viewMode === 'globe') {
        setViewedPhotos(photos);
      }
    }
  }, [photos, isSearching, viewMode]);

  const handleNavigate = useCallback((index: number) => {
    const contextPhotos = viewedPhotos.length > 0 ? viewedPhotos : photos;
    if (index >= 0 && index < contextPhotos.length) {
      setSelectedPhotoIndex(index);
    }
  }, [viewedPhotos, photos]);

  return (
    <LayoutGroup>
      <div className="flex flex-col min-h-screen bg-background text-foreground">
        <FirstRunModal
          onDismiss={() => { }}
          onSelectMode={(mode) => setSearchMode(mode)}
        />
        <Spotlight onPhotoSelect={handlePhotoSelect} />

        {/* Minimal Header when BigHero is showing */}
        {showBigHero ? (
          <header className="fixed top-0 left-0 right-0 z-50 p-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              {/* View Mode Toggle */}
              <div className="flex gap-1 bg-white/5 dark:bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/10">
                <button
                  onClick={() => setViewMode('story')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'story' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  <LayoutGrid size={14} />
                  Stories
                </button>
                <button
                  onClick={() => setViewMode('globe')}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all text-muted-foreground hover:text-foreground"
                  title="3D Globe View"
                >
                  <Globe2 size={14} />
                  Explore 3D
                </button>
              </div>

              {/* Theme Toggle */}
              <button
                onClick={() => {
                  const newIsDark = !isDark;
                  setIsDark(newIsDark);
                  document.documentElement.classList.toggle("dark", newIsDark);
                }}
                className="p-2 rounded-full bg-white/5 dark:bg-black/20 backdrop-blur-md border border-white/10 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Toggle theme"
              >
                {isDark ? <Sun size={16} /> : <Moon size={16} />}
              </button>
            </div>
          </header>
        ) : (
          /* Full Header with Search when photos are loaded */
          <header className="fixed top-0 left-0 right-0 z-50 p-4 bg-background/60 backdrop-blur-2xl border-b border-white/10 shadow-lg shadow-black/5 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="max-w-7xl mx-auto flex flex-col gap-3">
              {/* Top Row: Logo + View Toggle + Theme */}
              <div className="flex items-center justify-between">
                <h1 className="text-xl font-semibold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                  Living Museum
                </h1>

                <div className="flex items-center gap-3">
                  {/* Gallery Mode Toggle */}
                  <div className="flex gap-1 bg-white/5 dark:bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/10">
                    <button
                      onClick={() => setGalleryMode('traditional')}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${galleryMode === 'traditional' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                      title="Traditional Grid"
                    >
                      <LayoutGrid size={14} />
                      Classic
                    </button>
                    <button
                      onClick={() => setGalleryMode('modern')}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${galleryMode === 'modern' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                      title="Modern CSS Features"
                    >
                      <Sparkles size={14} />
                      Modern
                    </button>
                    <button
                      onClick={() => setGalleryMode('demo')}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${galleryMode === 'demo' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                      title="CSS Features Demo"
                    >
                      <Code size={14} />
                      Demo
                    </button>
                  </div>

                  {/* View Mode Toggle */}
                  <div className="flex gap-1 bg-white/5 dark:bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/10">
                    <button
                      onClick={() => setViewMode('story')}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'story' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                    >
                      <LayoutGrid size={14} />
                      Stories
                    </button>
                    <button
                      onClick={() => setViewMode('globe')}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${viewMode === 'globe' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'}`}
                    >
                      <Globe2 size={14} />
                      Globe
                    </button>
                  </div>

                  {/* Theme Toggle */}
                  <button
                    onClick={() => {
                      const newIsDark = !isDark;
                      setIsDark(newIsDark);
                      document.documentElement.classList.toggle("dark", newIsDark);
                    }}
                    className="p-2 rounded-full bg-white/5 dark:bg-black/20 backdrop-blur-md border border-white/10 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label="Toggle theme"
                  >
                    {isDark ? <Sun size={16} /> : <Moon size={16} />}
                  </button>
                </div>
              </div>

              {/* Search Row - Compact with shared layout animation */}
              <motion.div className="flex items-center gap-3" layoutId="search-container">
                <motion.div className="flex-1 relative group" layoutId="search-bar">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground group-focus-within:text-primary transition-colors z-10" />
                  <input
                    type="text"
                    placeholder="Search your photos..."
                    className="w-full bg-white/5 dark:bg-black/20 backdrop-blur-md border border-white/10 rounded-2xl pl-12 pr-12 py-3.5 text-base focus:ring-2 focus:ring-primary/40 focus:border-primary/30 focus:bg-white/10 dark:focus:bg-black/30 outline-none transition-all placeholder:text-muted-foreground/50 shadow-inner"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors z-10"
                      aria-label="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </motion.div>
                <SearchToggle value={searchMode} onChange={setSearchMode} />
              </motion.div>

              {/* Sort & Filter Row */}
              <div className="flex items-center gap-2 flex-wrap">
                {/* Type Filter Buttons */}
                <div className="flex gap-1 bg-white/5 dark:bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/10">
                  <button
                    onClick={() => setTypeFilter('all')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${typeFilter === 'all' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <Layers size={12} />
                    All
                  </button>
                  <button
                    onClick={() => setTypeFilter('photos')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${typeFilter === 'photos' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <Image size={12} />
                    Photos
                  </button>
                  <button
                    onClick={() => setTypeFilter('videos')}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${typeFilter === 'videos' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                  >
                    <Film size={12} />
                    Videos
                  </button>
                </div>

                {/* Sort Dropdown */}
                <div className="relative">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="appearance-none bg-white/5 dark:bg-black/20 backdrop-blur-md border border-white/10 rounded-full pl-8 pr-4 py-1.5 text-xs font-medium cursor-pointer focus:ring-2 focus:ring-primary/40 focus:outline-none text-foreground"
                  >
                    <option value="date_desc">Newest First</option>
                    <option value="date_asc">Oldest First</option>
                    <option value="name">Name (A-Z)</option>
                    <option value="size">Size (Largest)</option>
                  </select>
                  <ArrowUpDown size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                </div>
              </div>
            </div>
          </header>
        )}

        {/* Main Content Area */}
        <main className={`flex-1 ${showBigHero ? 'pt-16' : 'pt-36'} pb-24 px-4 sm:px-8 transition-all duration-300`}>
          <ErrorBoundary FallbackComponent={ErrorFallback}>
            {/* BigSearchHero - Shown when no photos loaded yet */}
            <AnimatePresence mode="wait">
              {showBigHero && (
                <motion.div
                  key="big-hero"
                  className="flex items-center justify-center min-h-[60vh]"
                  exit={{ opacity: 0, y: -30 }}
                  transition={{ duration: 0.3 }}
                >
                  <BigSearchHero
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    searchMode={searchMode}
                    setSearchMode={setSearchMode}
                    onSearch={() => { }}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Demo Gallery - Shows CSS features */}
            {galleryMode === 'demo' && (
              <ModernGalleryDemo 
                onUseModern={() => setGalleryMode('modern')}
              />
            )}

            {/* Globe View */}
            {viewMode === 'globe' && (
              <PhotoGlobe
                photos={photos}
                onPhotoSelect={handlePhotoSelect}
                onClose={() => setViewMode('story')}
              />
            )}

            {/* Search Results - with gallery mode selection */}
            {!showBigHero && viewMode !== 'globe' && galleryMode !== 'demo' && isSearching && (
              <div key="search-results" className="max-w-[1920px] mx-auto">
                <div className="mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <h2 className="text-2xl font-light text-foreground">
                    Results for <span className="font-medium text-primary">"{debouncedSearch}"</span>
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">{photos.length} photos found</p>
                </div>
                {galleryMode === 'traditional' ? (
                  <PhotoGrid
                    photos={photos}
                    loading={loading}
                    error={error}
                    onPhotoSelect={handlePhotoSelect}
                    hasMore={hasMore}
                    loadMore={loadMore}
                  />
                ) : (
                  <ModernPhotoGrid
                    photos={photos}
                    loading={loading}
                    error={error}
                    onPhotoSelect={handlePhotoSelect}
                    hasMore={hasMore}
                    loadMore={loadMore}
                  />
                )}
              </div>
            )}

            {/* Story Mode (Default Home with Photos) */}
            {!showBigHero && viewMode !== 'globe' && galleryMode !== 'demo' && !isSearching && (
              <div>
                {galleryMode === 'traditional' ? (
                  <StoryMode
                    key="story-mode"
                    photos={photos}
                    loading={loading}
                    onPhotoSelect={(photo) => handlePhotoSelect(photo)}
                    hasMore={hasMore}
                    loadMore={loadMore}
                  />
                ) : (
                  <ModernPhotoGrid
                    key="modern-story-mode"
                    photos={photos}
                    loading={loading}
                    onPhotoSelect={handlePhotoSelect}
                    hasMore={hasMore}
                    loadMore={loadMore}
                  />
                )}
              </div>
            )}
          </ErrorBoundary>
        </main>

        <PhotoDetail
          photos={viewedPhotos.length > 0 ? viewedPhotos : photos}
          currentIndex={selectedPhotoIndex}
          onNavigate={handleNavigate}
          onClose={() => { setSelectedPhotoIndex(null); setViewedPhotos([]); }}
        />

        {viewMode !== 'globe' && !showBigHero && (
          <ErrorBoundary FallbackComponent={ErrorFallback}>
            <SonicTimeline />
          </ErrorBoundary>
        )}
      </div>
    </LayoutGroup>
  )
}

export default App
