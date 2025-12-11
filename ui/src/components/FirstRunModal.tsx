import { useState, useEffect } from 'react';
import { Sparkles, X, Database } from 'lucide-react';

interface FirstRunModalProps {
  onDismiss: () => void;
  onSelectMode: (mode: 'metadata' | 'semantic') => void;
}

export function FirstRunModal({ onDismiss, onSelectMode }: FirstRunModalProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if user has seen this before
    const hasSeenModal = localStorage.getItem('photosearch_first_run_seen');
    if (!hasSeenModal) {
      setIsVisible(true);
    }
  }, []);

  const handleSelect = (mode: 'metadata' | 'semantic') => {
    localStorage.setItem('photosearch_first_run_seen', 'true');
    onSelectMode(mode);
    setIsVisible(false);
  };

  const handleDismiss = () => {
    localStorage.setItem('photosearch_first_run_seen', 'true');
    onDismiss();
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="relative bg-popover border border-border rounded-2xl shadow-2xl max-w-md w-full p-6 animate-in zoom-in-95 duration-300">
        <button 
          onClick={handleDismiss}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={20} />
        </button>

        <div className="text-center mb-6">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-xl font-semibold mb-2">Welcome to Living Museum</h2>
          <p className="text-sm text-muted-foreground">
            Choose how you'd like to search your photos
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => handleSelect('semantic')}
            className="w-full p-4 rounded-xl border border-primary/30 bg-primary/5 hover:bg-primary/10 transition-all text-left group"
          >
            <div className="flex items-center gap-3 mb-2">
              <Sparkles className="w-5 h-5 text-primary" />
              <span className="font-medium">Semantic Search</span>
              <span className="ml-auto text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">Recommended</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Search by meaning: "sunset at beach", "happy family moments"
            </p>
          </button>

          <button
            onClick={() => handleSelect('metadata')}
            className="w-full p-4 rounded-xl border border-border hover:border-border/80 hover:bg-muted/30 transition-all text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Database className="w-5 h-5 text-muted-foreground" />
              <span className="font-medium">Metadata Search</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Search by filename, date, camera model - fast and precise
            </p>
          </button>
          
          <div className="relative flex items-center gap-4 py-2">
            <div className="h-px bg-border flex-1" />
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Setup</span>
            <div className="h-px bg-border flex-1" />
          </div>

          <button
            onClick={() => {
                const defaultPath = window.location.hostname === 'localhost' 
                    ? '/Users/pranay/Projects/photosearch_experiment/media' 
                    : 'media';
                import('../api').then(({api}) => {
                     api.scan(defaultPath)
                        .then(() => alert("Scan started in background!"))
                        .catch(err => alert("Scan failed: " + err));
                });
            }}
            className="w-full py-3 rounded-xl border border-dashed border-primary/50 text-primary hover:bg-primary/5 transition-colors font-medium text-sm flex items-center justify-center gap-2"
          >
            <span>⚡️</span> Scan Default Library
          </button>
        </div>

        <p className="text-xs text-center text-muted-foreground mt-4">
          You can change this anytime using the toggle in the header
        </p>
      </div>
    </div>
  );
}
