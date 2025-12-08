import { useState, useCallback } from 'react'
import { ErrorBoundary } from "react-error-boundary";
import { PhotoGrid } from './components/PhotoGrid'
import { SonicTimeline } from './components/SonicTimeline'
import { Spotlight } from './components/Spotlight'
import { StoryMode } from './components/StoryMode'
import { PhotoGlobe } from './components/PhotoGlobe'
import { PhotoDetail } from './components/PhotoDetail'
import { useDebounce } from './hooks/useDebounce';
import { usePhotoSearch } from './hooks/usePhotoSearch';
import { type Photo } from './api';
import { Globe2, LayoutGrid } from 'lucide-react';

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
  const [searchMode, setSearchMode] = useState<'semantic' | 'metadata'>('semantic')
  const [viewMode, setViewMode] = useState<'story' | 'globe'>('story')
  const [selectedPhotoIndex, setSelectedPhotoIndex] = useState<number | null>(null)
  const debouncedSearch = useDebounce(searchQuery, 500);

  // Fetch all photos for globe view
  const { results: allPhotos } = usePhotoSearch({ initialFetch: true, mode: 'semantic' });

  // If search is active (debounced input has value), show Grid.
  const isSearching = debouncedSearch.length > 0;

  // Photo selection handler (finds index)
  const handlePhotoSelect = useCallback((photo: Photo) => {
    const index = allPhotos.findIndex(p => p.path === photo.path);
    setSelectedPhotoIndex(index >= 0 ? index : null);
  }, [allPhotos]);

  // Navigation handler with bounds checking
  const handleNavigate = useCallback((index: number) => {
    if (index >= 0 && index < allPhotos.length) {
      setSelectedPhotoIndex(index);
    }
  }, [allPhotos.length]);

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground dark">
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
                    className="bg-secondary/30 border border-white/5 rounded-full px-6 py-2.5 text-sm focus:ring-2 focus:ring-primary/50 focus:bg-secondary/50 outline-none w-80 transition-all shadow-lg backdrop-blur-md"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-medium text-muted-foreground bg-black/20 px-1.5 py-0.5 rounded border border-white/5">⌘K</div>
            </div>
            
            {/* Search Mode Toggle */}
            <div className="flex gap-2 text-xs bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/5">
              <button 
                onClick={() => setSearchMode('semantic')}
                className={`px-3 py-1 rounded-full transition-all duration-300 ${searchMode === 'semantic' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground hover:bg-white/5'}`}
              >
                🧠 Semantic
              </button>
              <button 
                onClick={() => setSearchMode('metadata')}
                className={`px-3 py-1 rounded-full transition-all duration-300 ${searchMode === 'metadata' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground hover:bg-white/5'}`}
              >
                📋 Metadata
              </button>
            </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 pt-32 pb-24 px-4 sm:px-8">
        <ErrorBoundary FallbackComponent={ErrorFallback}>
            {isSearching ? (
                <div key="search-results" className="max-w-[1920px] mx-auto">
                     <div className="mb-8 px-2 flex items-baseline justify-between animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h2 className="text-3xl font-light text-foreground">
                            Searching for <span className="font-medium italic text-primary">"{debouncedSearch}"</span>
                        </h2>
                        <span className="text-sm text-muted-foreground bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
                            {searchMode === 'semantic' ? 'Semantic Matching' : 'Metadata Filtering'}
                        </span>
                     </div>
                     <PhotoGrid query={debouncedSearch} mode={searchMode} />
                </div>
            ) : viewMode === 'globe' ? (
                <PhotoGlobe 
                    photos={allPhotos} 
                    onPhotoSelect={handlePhotoSelect}
                    onClose={() => setViewMode('story')} 
                />
            ) : (
                <StoryMode key="story-mode" />
            )}
        </ErrorBoundary>
      </main>

      {/* Photo Detail Modal with Navigation */}
      <PhotoDetail 
        photos={allPhotos}
        currentIndex={selectedPhotoIndex}
        onNavigate={handleNavigate}
        onClose={() => setSelectedPhotoIndex(null)} 
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
