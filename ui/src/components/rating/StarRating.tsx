/**
 * Star Rating Component
 *
 * Interactive 1-5 star rating display and editor following the glass design system.
 */
import React, { useState } from 'react';
import { Star, StarOff } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface StarRatingProps {
  photoPath: string;
  initialRating?: number;
  readonly?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function StarRating({
  photoPath,
  initialRating = 0,
  readonly = false,
  size = 'md',
  showLabel = true,
  className = ''
}: StarRatingProps) {
  const [rating, setRating] = useState(initialRating);
  const [hoverRating, setHoverRating] = useState(0);
  const [isUpdating, setIsUpdating] = useState(false);

  // Icon sizes based on component size
  const iconSize = {
    sm: 12,
    md: 16,
    lg: 20
  }[size];

  // Container padding based on component size
  const containerPadding = {
    sm: 'px-2 py-1',
    md: 'px-3 py-1.5',
    lg: 'px-4 py-2'
  }[size];

  const handleRatingChange = async (newRating: number) => {
    if (readonly || isUpdating || newRating === rating) return;

    setIsUpdating(true);
    try {
      await api.setPhotoRating(photoPath, newRating);
      setRating(newRating);
    } catch (error) {
      console.error('Failed to update rating:', error);
      // Optionally show error feedback to user
    } finally {
      setIsUpdating(false);
    }
  };

  const displayStars = readonly ? rating : (hoverRating || rating);

  return (
    <div
      className={`flex items-center gap-1 ${readonly ? '' : 'cursor-pointer'} ${className}`}
      title={readonly ? `Rating: ${rating}/5` : 'Click to rate'}
    >
      <div className="flex items-center">
        {[1, 2, 3, 4, 5].map((star) => {
          const isFilled = star <= displayStars;
          const isHovered = star <= hoverRating;

          return (
            <button
              key={star}
              onClick={() => handleRatingChange(star)}
              onMouseEnter={() => !readonly && setHoverRating(star)}
              onMouseLeave={() => !readonly && setHoverRating(0)}
              disabled={readonly || isUpdating}
              className={`
                transition-all duration-150 ease-in-out
                ${readonly ? 'cursor-default' : 'hover:scale-110'}
                ${isUpdating ? 'opacity-50 cursor-wait' : ''}
                ${!readonly && !isUpdating ? 'active:scale-95' : ''}
              `}
              aria-label={`Rate ${star} star${star !== 1 ? 's' : ''}`}
            >
              {isFilled ? (
                <Star
                  size={iconSize}
                  className={`
                    text-yellow-400 fill-yellow-400
                    ${isHovered && !readonly ? 'text-yellow-300 fill-yellow-300' : ''}
                    ${isUpdating ? 'animate-pulse' : ''}
                  `}
                />
              ) : (
                <StarOff
                  size={iconSize}
                  className={`
                    text-gray-400
                    ${isHovered && !readonly ? 'text-yellow-200 fill-yellow-200' : ''}
                  `}
                />
              )}
            </button>
          );
        })}
      </div>

      {showLabel && (
        <span className="text-xs text-muted-foreground ml-2">
          {rating > 0 ? `${rating}/5` : 'Not rated'}
        </span>
      )}

      {isUpdating && (
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse ml-2" />
      )}
    </div>
  );
}