/**
 * Star Rating Component
 *
 * Interactive 1-5 star rating display with color-coded feedback.
 * Color gradient: 1★ red, 2★ orange, 3★ amber, 4★ yellow, 5★ green
 */
import React, { useState } from 'react';
import { Star } from 'lucide-react';
import { api } from '../../api';

interface StarRatingProps {
  photoPath: string;
  initialRating?: number;
  readonly?: boolean;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

// Color coding by rating level
const ratingColors: Record<number, string> = {
  1: 'text-red-500 fill-red-500',
  2: 'text-orange-500 fill-orange-500',
  3: 'text-amber-500 fill-amber-500',
  4: 'text-yellow-400 fill-yellow-400',
  5: 'text-emerald-500 fill-emerald-500',
};

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

  const iconSize = {
    sm: 14,
    md: 18,
    lg: 22
  }[size];

  const handleRatingChange = async (newRating: number) => {
    if (readonly || isUpdating || newRating === rating) return;

    setIsUpdating(true);
    try {
      await api.setPhotoRating(photoPath, newRating);
      setRating(newRating);
    } catch (error) {
      console.error('Failed to update rating:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const displayRating = hoverRating || rating;
  const activeColor = ratingColors[displayRating] || '';

  return (
    <div
      className={`flex items-center gap-2 ${readonly ? '' : 'cursor-pointer'} ${className}`}
      title={readonly ? `Rating: ${rating}/5` : 'Click to rate'}
    >
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => {
          const isFilled = star <= displayRating;

          return (
            <button
              key={star}
              onClick={() => handleRatingChange(star)}
              onMouseEnter={() => !readonly && setHoverRating(star)}
              onMouseLeave={() => !readonly && setHoverRating(0)}
              disabled={readonly || isUpdating}
              className={`
                transition-all duration-150 ease-in-out p-0.5
                ${readonly ? 'cursor-default' : 'hover:scale-110'}
                ${isUpdating ? 'opacity-50 cursor-wait' : ''}
                ${!readonly && !isUpdating ? 'active:scale-95' : ''}
              `}
              aria-label={`Rate ${star} star${star !== 1 ? 's' : ''}`}
            >
              <Star
                size={iconSize}
                className={`
                  transition-colors duration-150
                  ${isFilled ? activeColor : 'text-white/20'}
                  ${isFilled ? '' : 'fill-transparent'}
                  ${isUpdating ? 'animate-pulse' : ''}
                `}
              />
            </button>
          );
        })}
      </div>

      {showLabel && (
        <span className="text-xs text-white/50 ml-1">
          {rating > 0 ? `${rating}/5` : 'Not rated'}
        </span>
      )}

      {isUpdating && (
        <div className="w-2 h-2 rounded-full bg-white/50 animate-pulse ml-1" />
      )}
    </div>
  );
}