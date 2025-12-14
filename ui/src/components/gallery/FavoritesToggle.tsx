import { Star } from 'lucide-react';

interface FavoritesToggleProps {
  isFavorited: boolean;
  onToggle: () => void;
  className?: string;
}

export function FavoritesToggle({
  isFavorited,
  onToggle,
  className = '',
}: FavoritesToggleProps) {
  return (
    <button
      onClick={onToggle}
      className={`btn-glass w-8 h-8 p-0 justify-center rounded-full ${className}`}
      title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
    >
      <Star
        size={16}
        className={`transition-colors ${
          isFavorited
            ? 'fill-yellow-400 text-yellow-400'
            : 'text-muted-foreground hover:text-yellow-400'
        }`}
      />
    </button>
  );
}
