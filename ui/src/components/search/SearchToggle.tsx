import { Sparkles, Database, Layers } from 'lucide-react';

export type SearchMode = 'metadata' | 'hybrid' | 'semantic';

interface SearchToggleProps {
  value: SearchMode;
  onChange: (mode: SearchMode) => void;
}

export function SearchToggle({ value, onChange }: SearchToggleProps) {
  return (
    <div className='flex gap-1 p-1 rounded-full'>
      <button
        onClick={() => onChange('metadata')}
        className={`btn-glass ${
          value === 'metadata' ? 'btn-glass--primary' : 'btn-glass--muted'
        } text-xs`}
        title='Search by exact fields (fast)'
      >
        <Database size={14} />
        Metadata
      </button>

      <button
        onClick={() => onChange('hybrid')}
        className={`btn-glass ${
          value === 'hybrid' ? 'btn-glass--primary' : 'btn-glass--muted'
        } text-xs`}
        title='Combine metadata and semantic results'
      >
        <Layers size={14} />
        Hybrid
      </button>

      <button
        onClick={() => onChange('semantic')}
        className={`btn-glass ${
          value === 'semantic' ? 'btn-glass--primary' : 'btn-glass--muted'
        } text-xs`}
        title='Search by meaning and visual content (AI)'
      >
        <Sparkles size={14} />
        Semantic
      </button>
    </div>
  );
}
