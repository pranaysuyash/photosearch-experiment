import { useState, useCallback, useEffect } from 'react'
import { ErrorBoundary } from "react-error-boundary";
import { PhotoGrid } from './components/PhotoGrid'
import { SonicTimeline } from './components/SonicTimeline'
import { Spotlight } from './components/Spotlight'
import { StoryMode } from './components/StoryMode'
import { PhotoGlobe } from './components/PhotoGlobe'
import { PhotoDetail } from './components/PhotoDetail'
import { FirstRunModal } from './components/FirstRunModal'
import { useDebounce } from './hooks/useDebounce';
import { usePhotoSearch } from './hooks/usePhotoSearch';
import { type Photo } from './api';
import { Globe2, LayoutGrid } from 'lucide-react';
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
  const [searchMode, setSearchMode] = useState<SearchMode>('semantic')
  const [viewMode, setViewMode] = useState<'story' | 'globe'>('story')
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number | null>(null)
  const [viewedPhotos, setViewedPhotos] = useState<Photo[]>([]) // Photos being viewed in modal
  
  // Unified Search Hook - Source of Truth
  const { results: photos, loading, error, setQuery } = usePhotoSearch({ 
    initialQuery: "", 
    initialFetch: true, 
    mode: searchMode 
  });

  const debouncedSearch = useDebounce(searchQuery, 500);

  // Sync search query to hook
  useEffect(() => {
    setQuery(debouncedSearch);
  }, [debouncedSearch, setQuery]);

  // If search is active (debounced input has value)
  const isSearching = debouncedSearch.length > 0;

  // Photo selection handler (finds index)
  const handlePhotoSelect = useCallback((photo: Photo) => {
    const index = photos.findIndex(p => p.path === photo.path);
    if (index >= 0) {
        setSelectedPhotoIndex(index);
        // When searching or in globe view, the context is "all search results"
        if (isSearching || viewMode === 'globe') {
            setViewedPhotos(photos);
        }
    }
  }, [photos, isSearching, viewMode]);

  // Navigation handler with bounds checking
  const handleNavigate = useCallback((index: number) => {
    const contextPhotos = viewedPhotos.length > 0 ? viewedPhotos : photos;
    if (index >= 0 && index < contextPhotos.length) {
      setSelectedPhotoIndex(index);
    }
  }, [viewedPhotos, photos]);

  // ... (JSX render) ...

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground dark">
    {/* ... (Header remains same) ... */}
      <FirstRunModal 
        onDismiss={() => {}} 
        onSelectMode={(mode) => setSearchMode(mode)} 
      />
      <Spotlight />
      
      {/* Header / Search Overlay */}
      <header className="fixed top-0 left-0 right-0 z-50 p-6 bg-background/60 backdrop-blur-xl border-b border-white/10 flex justify-between items-center transition-all duration-300">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white to-white/50 bg-clip-text text-transparent">
            Living Museum
          </h1>
          
          {/* View Mode Toggle */}
          <div className="flex gap-1 bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/5">
            <button 
              onClick={() => setViewMode('story')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${viewMode === 'story' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground hover:bg-white/5'}`}
            >
              <LayoutGrid size={14} />
              Stories
            </button>
            <button 
              onClick={() => setViewMode('globe')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${viewMode === 'globe' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground hover:bg-white/5'}`}
            >
              <Globe2 size={14} />
              Explore 3D
            </button>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-3">
            <div className="relative group">
                <input 
                    type="text" 
                    placeholder="Search memories..." 
                    className="bg-secondary/30 border border-white/5 rounded-full pl-6 pr-12 py-2.5 text-sm focus:ring-2 focus:ring-primary/50 focus:bg-secondary/50 outline-none w-80 transition-all shadow-lg backdrop-blur-md"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery ? (
                    <button 
                        onClick={() => setSearchQuery('')}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                        aria-label="Clear search"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                ) : (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-medium text-muted-foreground bg-black/20 px-1.5 py-0.5 rounded border border-white/5">⌘K</div>
                )}
            </div>
            
            <SearchToggle value={searchMode} onChange={setSearchMode} />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 pt-40 pb-24 px-4 sm:px-8">
        <ErrorBoundary FallbackComponent={ErrorFallback}>
            {viewMode === 'globe' ? (
                /* Globe View (works for both search and all photos) */
                <PhotoGlobe 
                    photos={photos} 
                    onPhotoSelect={handlePhotoSelect}
                    onClose={() => setViewMode('story')} 
                />
            ) : isSearching ? (
                 /* Search Results Grid */
                 <div key="search-results" className="max-w-[1920px] mx-auto">
                     <div className="mb-8 px-2 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h2 className="text-3xl font-light text-foreground">
                            Searching for <span className="font-medium italic text-primary">"{debouncedSearch}"</span>
                        </h2>
                     </div>
                     <PhotoGrid 
                        photos={photos} 
                        loading={loading} 
                        error={error} 
                        onPhotoSelect={handlePhotoSelect}
                     />
                </div>
            ) : (
                /* Story Mode (Default Home) */
                <StoryMode 
                    key="story-mode"
                    photos={photos}
                    loading={loading}
                    onPhotoSelect={(photo) => handlePhotoSelect(photo)}
                />
            )}
        </ErrorBoundary>
      </main>

      {/* Photo Detail Modal with Navigation */}
      <PhotoDetail 
        photos={viewedPhotos.length > 0 ? viewedPhotos : photos}
        currentIndex={selectedPhotoIndex}
        onNavigate={handleNavigate}
        onClose={() => { setSelectedPhotoIndex(null); setViewedPhotos([]); }} 
      />

      {/* Sonic Timeline Footer */}
      {viewMode !== 'globe' && (
        <ErrorBoundary FallbackComponent={ErrorFallback}>
          <SonicTimeline />
        </ErrorBoundary>
      )}
    </div>
  )
}

export default App
