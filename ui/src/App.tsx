import { useState, useEffect } from 'react'

function App() {
  const [status, setStatus] = useState<string>("Connecting to backend...")

  useEffect(() => {
    fetch('http://localhost:8000/')
      .then(res => res.json())
      .then(data => setStatus(`Backend connected: ${data.message}`))
      .catch(err => setStatus(`Backend error: ${err}`))
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground">
      <div className="p-8 border rounded-lg shadow-lg bg-card">
        <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
          Living Museum
        </h1>
        <p className="text-muted-foreground mb-4">
          Visual Interface Foundation
        </p>
        <div className="p-4 bg-secondary rounded text-sm font-mono">
          {status}
        </div>
      </div>
    </div>
  )
}

export default App
