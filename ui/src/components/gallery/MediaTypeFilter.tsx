import { Image, Video, Layers } from 'lucide-react';

interface MediaTypeFilterProps {
  typeFilter: string;
  onTypeFilterChange: (typeFilter: string) => void;
  className?: string;
}

const TYPE_FILTERS = [
  { value: 'all', label: 'All', icon: Layers },
  { value: 'photos', label: 'Photos', icon: Image },
  { value: 'videos', label: 'Videos', icon: Video },
] as const;

export function MediaTypeFilter({
  typeFilter,
  onTypeFilterChange,
  className = '',
}: MediaTypeFilterProps) {
  return (
    <div className={`flex gap-1 p-1 rounded-full ${className}`}>
      {TYPE_FILTERS.map((filter) => {
        const Icon = filter.icon;
        const isActive = typeFilter === filter.value;

        return (
          <button
            key={filter.value}
            onClick={() => onTypeFilterChange(filter.value)}
            className={`btn-glass ${
              isActive ? 'btn-glass--primary' : 'btn-glass--muted'
            } text-xs font-medium`}
          >
            <Icon size={12} />
            {filter.label}
          </button>
        );
      })}
    </div>
  );
}
