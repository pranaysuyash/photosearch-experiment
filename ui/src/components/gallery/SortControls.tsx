import { ArrowUpDown, Calendar, FileText, HardDrive } from 'lucide-react';

interface SortControlsProps {
  sortBy: string;
  onSortChange: (sortBy: string) => void;
  className?: string;
}

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Newest First', icon: Calendar },
  { value: 'date_asc', label: 'Oldest First', icon: Calendar },
  { value: 'name', label: 'Name (A-Z)', icon: FileText },
  { value: 'size', label: 'Size (Largest)', icon: HardDrive },
] as const;

export function SortControls({
  sortBy,
  onSortChange,
  className = '',
}: SortControlsProps) {
  return (
    <div className={`relative ${className}`}>
      <select
        value={sortBy}
        onChange={(e) => onSortChange(e.target.value)}
        aria-label='Sort by'
        className='btn-glass btn-glass--muted appearance-none pl-4 pr-8 py-2 text-sm font-medium cursor-pointer focus:ring-2 focus:ring-primary/40 focus:outline-none text-foreground'
      >
        {SORT_OPTIONS.map((option) => {
          return (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          );
        })}
      </select>
      <ArrowUpDown
        size={14}
        className='absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none'
      />
    </div>
  );
}
