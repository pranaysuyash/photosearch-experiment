import { useState } from 'react'
import { PhotoGrid } from './components/PhotoGrid'
import { SonicTimeline } from './components/SonicTimeline'

function App() {
  const [searchQuery, setSearchQuery] = useState("")

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground dark">
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
        <PhotoGrid query={searchQuery} />
      </main>

      {/* Sonic Timeline Footer */}
      <SonicTimeline />
    </div>
  )
}

export default App
