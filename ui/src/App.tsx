import { useState } from 'react'
import { ErrorBoundary } from "react-error-boundary";
import { PhotoGrid } from './components/PhotoGrid'
import { SonicTimeline } from './components/SonicTimeline'
import { Spotlight } from './components/Spotlight'
import { StoryMode } from './components/StoryMode'
import { useDebounce } from './hooks/useDebounce';

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
  const debouncedSearch = useDebounce(searchQuery, 500);

  // If search is active (debounced input has value), show Grid.
  // Otherwise, show the default Story Mode.
  const isSearching = debouncedSearch.length > 0;

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground dark">
      <Spotlight />
      
      {/* Header / Search Overlay Placeholder */}
      <header className="fixed top-0 left-0 right-0 z-50 p-4 bg-background/80 backdrop-blur border-b border-border flex justify-between items-center">
        <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-blue-500 bg-clip-text text-transparent">
          Living Museum
        </h1>
        <div className="relative">
             <input 
                type="text" 
                placeholder="Search memories..." 
                className="bg-secondary/50 border-none rounded-full px-4 py-1.5 text-sm focus:ring-1 focus:ring-primary outline-none w-64"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
             />
             <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">⌘K</div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 pt-20 pb-24">
        <ErrorBoundary FallbackComponent={ErrorFallback}>
            {isSearching ? (
                <div key="search-results">
                     <div className="container px-4 py-2 text-sm text-muted-foreground">
                        Searching for "{debouncedSearch}"...
                     </div>
                     <PhotoGrid query={debouncedSearch} />
                </div>
            ) : (
                <StoryMode key="story-mode" />
            )}
        </ErrorBoundary>
      </main>

      {/* Sonic Timeline Footer - Always visible for now, or maybe only in Story Mode? Let's keep it. */}
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <SonicTimeline />
      </ErrorBoundary>
    </div>
  )
}

export default App
