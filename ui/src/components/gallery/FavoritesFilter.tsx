import { Star, Layers } from 'lucide-react';

interface FavoritesFilterProps {
  favoritesFilter: string;
  onFavoritesFilterChange: (favoritesFilter: string) => void;
  className?: string;
}

const FAVORITES_FILTERS = [
  { value: 'all', label: 'All', icon: Layers },
  { value: 'favorites_only', label: 'Favorites', icon: Star },
] as const;

export function FavoritesFilter({
  favoritesFilter,
  onFavoritesFilterChange,
  className = '',
}: FavoritesFilterProps) {
  return (
    <div className={`flex gap-1 p-1 rounded-full ${className}`}>
      {FAVORITES_FILTERS.map((filter) => {
        const Icon = filter.icon;
        const isActive = favoritesFilter === filter.value;

        return (
          <button
            key={filter.value}
            onClick={() => onFavoritesFilterChange(filter.value)}
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
