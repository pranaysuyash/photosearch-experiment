import { Sparkles, Database, Layers } from 'lucide-react';

export type SearchMode = 'metadata' | 'hybrid' | 'semantic';

interface SearchToggleProps {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export function SearchToggle({ value, onChange }: SearchToggleProps) {
  return (
    <div className="flex gap-1 bg-black/20 backdrop-blur-md p-1 rounded-full border border-white/5">
      <button
        onClick={() => onChange('metadata')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${
          value === 'metadata'
            ? 'bg-primary text-primary-foreground shadow-md'
            : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
        }`}
        title="Search by exact fields (fast)"
      >
        <Database size={14} />
        Metadata
      </button>

      <button
        onClick={() => onChange('hybrid')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${
          value === 'hybrid'
            ? 'bg-primary text-primary-foreground shadow-md'
            : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
        }`}
        title="Combine metadata and semantic results"
      >
        <Layers size={14} />
        Hybrid
      </button>

      <button
        onClick={() => onChange('semantic')}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs transition-all duration-300 ${
          value === 'semantic'
            ? 'bg-primary text-primary-foreground shadow-md'
            : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
        }`}
        title="Search by meaning and visual content (AI)"
      >
        <Sparkles size={14} />
        Semantic
      </button>
    </div>
  );
}
