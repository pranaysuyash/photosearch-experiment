/**
 * Responsive Gallery Component
 *
 * A mobile-optimized gallery with touch-friendly controls and swipe gestures.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Grid3X3,
  List,
  ZoomOut,
  ZoomIn,
  X,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface Photo {
  path: string;
  filename: string;
  metadata?: unknown;
  score?: number;
  matchExplanation?: string;
}

interface GalleryProps {
  photos: Photo[];
  onPhotoSelect?: (photo: Photo, index: number) => void;
  initialViewMode?: 'grid' | 'list';
  gridSize?: 'small' | 'medium' | 'large';
}

export function ResponsiveGallery({
  photos = [],
  onPhotoSelect,
  initialViewMode = 'grid',
  gridSize = 'medium',
}: GalleryProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>(initialViewMode);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const galleryRef = useRef<HTMLDivElement>(null);
  const selectedPhotoRef = useRef<HTMLImageElement>(null);

  // Initialize with sample photos if none provided
  useEffect(() => {
    let cancelled = false;
    const rafId = window.requestAnimationFrame(() => {
      if (!cancelled) setIsLoading(false);
    });
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(rafId);
    };
  }, [photos.length]);

  const handleImageLoad = () => {
    // Could be used for progressive loading indicators
  };

  const handleImageError = (index: number) => {
    setError(`Failed to load photo at index ${index}`);
  };

  const handlePhotoClick = (photo: Photo, index: number) => {
    setSelectedPhoto(photo);
    setSelectedIndex(index);
    setZoomLevel(1);

    if (onPhotoSelect) {
      onPhotoSelect(photo, index);
    }
  };

  const closeModal = useCallback(() => {
    setSelectedPhoto(null);
    setSelectedIndex(-1);
  }, []);

  const selectNextPhoto = useCallback(() => {
    if (photos.length === 0) return;

    const nextIndex = (selectedIndex + 1) % photos.length;
    setSelectedPhoto(photos[nextIndex]);
    setSelectedIndex(nextIndex);
    setZoomLevel(1);
  }, [photos, selectedIndex]);

  const selectPrevPhoto = useCallback(() => {
    if (photos.length === 0) return;

    const prevIndex =
      selectedIndex <= 0 ? photos.length - 1 : selectedIndex - 1;
    setSelectedPhoto(photos[prevIndex]);
    setSelectedIndex(prevIndex);
    setZoomLevel(1);
  }, [photos, selectedIndex]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!selectedPhoto) return;

      if (e.key === 'Escape') {
        closeModal();
      } else if (e.key === 'ArrowRight') {
        selectNextPhoto();
      } else if (e.key === 'ArrowLeft') {
        selectPrevPhoto();
      } else if (e.key === '+') {
        setZoomLevel((prev) => Math.min(prev + 0.25, 3));
      } else if (e.key === '-' || e.key === '_') {
        setZoomLevel((prev) => Math.max(prev - 0.25, 1));
      }
    },
    [selectedPhoto, selectNextPhoto, selectPrevPhoto, closeModal]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  // Touch handling for swipe gestures
  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStart({
      x: e.touches[0].clientX,
      y: e.touches[0].clientY,
    });
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchStart) return;

    const touchX = e.touches[0].clientX;
    const touchY = e.touches[0].clientY;

    const diffX = touchX - touchStart.x;
    const diffY = touchY - touchStart.y;

    // Only consider horizontal swipes if the horizontal movement is significantly greater
    // than vertical movement
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
      if (diffX > 0) {
        // Swiped right - go to previous
        selectPrevPhoto();
      } else {
        // Swiped left - go to next
        selectNextPhoto();
      }
      setTouchStart(null);
    }
  };

  // Grid size classes
  const gridSizeClasses = {
    small: 'w-20 h-20 sm:w-24 sm:h-24',
    medium: 'w-24 h-24 sm:w-32 sm:h-32',
    large: 'w-32 h-32 sm:w-40 sm:h-40',
  };

  if (isLoading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin' />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-8 text-center`}
      >
        <div className='text-destructive mb-2'>⚠️</div>
        <h3 className='font-medium text-foreground mb-1'>
          Error Loading Gallery
        </h3>
        <p className='text-sm text-muted-foreground'>{error}</p>
        <button
          onClick={() => window.location.reload()}
          className='btn-glass btn-glass--primary mt-4 text-sm px-4 py-2 flex items-center gap-2 mx-auto'
        >
          <RotateCcw size={16} />
          Reload Gallery
        </button>
      </div>
    );
  }

  return (
    <div className='w-full'>
      {/* Toolbar */}
      <div
        className={`${glass.surface} rounded-t-xl border border-white/10 p-3 flex items-center justify-between`}
      >
        <div className='flex items-center gap-2'>
          <span className='text-sm text-muted-foreground'>
            {photos.length} {photos.length === 1 ? 'photo' : 'photos'}
          </span>
        </div>

        <div className='flex items-center gap-2'>
          {/* View mode toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            className={`btn-glass btn-glass--muted p-2 ${
              viewMode === 'grid' ? 'btn-glass--primary' : ''
            }`}
            aria-label={
              viewMode === 'grid'
                ? 'Switch to list view'
                : 'Switch to grid view'
            }
          >
            {viewMode === 'grid' ? <List size={18} /> : <Grid3X3 size={18} />}
          </button>
        </div>
      </div>

      {/* Gallery */}
      <div
        ref={galleryRef}
        className={`overflow-y-auto ${glass.surface} border-x border-white/10 ${
          viewMode === 'grid' ? 'p-3' : 'divide-y divide-white/10'
        }`}
        style={{ maxHeight: 'calc(100vh - 200px)' }}
      >
        {photos.length === 0 ? (
          <div className='flex flex-col items-center justify-center py-16 text-center'>
            <Grid3X3 size={48} className='text-muted-foreground mb-4' />
            <h3 className='text-lg font-medium text-foreground mb-2'>
              No Photos Found
            </h3>
            <p className='text-sm text-muted-foreground max-w-md'>
              Try adjusting your search or filter criteria to find photos.
            </p>
          </div>
        ) : viewMode === 'grid' ? (
          // Grid view
          <div className='grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2'>
            {photos.map((photo, index) => (
              <div
                key={index}
                className='aspect-square cursor-pointer rounded-lg overflow-hidden group relative'
                onClick={() => handlePhotoClick(photo, index)}
              >
                <img
                  src={api.getImageUrl(photo.path, 200)}
                  alt={photo.filename}
                  className={`${gridSizeClasses[gridSize]} w-full h-full object-cover rounded-lg border border-white/10`}
                  loading='lazy'
                  onLoad={handleImageLoad}
                  onError={() => handleImageError(index)}
                />
                <div className='absolute inset-0 bg-gradient-to-t from-black/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2'>
                  <div className='text-xs text-white line-clamp-2'>
                    {photo.filename}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          // List view
          <div>
            {photos.map((photo, index) => (
              <div
                key={index}
                className={`flex items-center gap-4 p-3 cursor-pointer hover:bg-white/5 rounded-lg ${
                  selectedPhoto?.path === photo.path ? 'bg-white/10' : ''
                }`}
                onClick={() => handlePhotoClick(photo, index)}
              >
                <div className='relative flex-shrink-0'>
                  <img
                    src={api.getImageUrl(photo.path, 80)}
                    alt={photo.filename}
                    className='w-16 h-16 object-cover rounded border border-white/10'
                    loading='lazy'
                    onLoad={handleImageLoad}
                    onError={() => handleImageError(index)}
                  />
                </div>
                <div className='min-w-0 flex-1'>
                  <div className='font-medium text-foreground truncate'>
                    {photo.filename}
                  </div>
                  <div className='text-xs text-muted-foreground'>
                    {photo.metadata?.image?.width}×
                    {photo.metadata?.image?.height}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selected Photo Modal */}
      {selectedPhoto && (
        <div
          className='fixed inset-0 z-[1500] bg-black/90 backdrop-blur-sm flex items-center justify-center p-4'
          onClick={closeModal}
        >
          <div
            className='relative max-w-6xl max-h-[90vh] w-full'
            onClick={(e) => e.stopPropagation()}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={() => setTouchStart(null)}
          >
            <button
              onClick={closeModal}
              className='absolute top-4 right-4 z-10 btn-glass btn-glass--muted w-10 h-10 flex items-center justify-center rounded-full'
            >
              <X size={20} />
            </button>

            {/* Zoom controls */}
            <div className='absolute top-4 left-1/2 transform -translate-x-1/2 z-10 flex gap-2'>
              <button
                onClick={() => setZoomLevel((prev) => Math.max(prev - 0.25, 1))}
                className='btn-glass btn-glass--primary p-2'
              >
                <ZoomOut size={20} />
              </button>
              <div className='btn-glass flex items-center px-3'>
                <span className='text-sm'>{Math.round(zoomLevel * 100)}%</span>
              </div>
              <button
                onClick={() => setZoomLevel((prev) => Math.min(prev + 0.25, 3))}
                className='btn-glass btn-glass--primary p-2'
              >
                <ZoomIn size={20} />
              </button>
            </div>

            {/* Navigation buttons */}
            <button
              onClick={selectPrevPhoto}
              className='absolute left-4 top-1/2 -translate-y-1/2 btn-glass btn-glass--primary w-10 h-10 flex items-center justify-center rounded-full'
            >
              <ChevronLeft size={20} />
            </button>
            <button
              onClick={selectNextPhoto}
              className='absolute right-4 top-1/2 -translate-y-1/2 btn-glass btn-glass--primary w-10 h-10 flex items-center justify-center rounded-full'
            >
              <ChevronRight size={20} />
            </button>

            {/* Image display */}
            <div className='flex items-center justify-center h-[70vh] w-full'>
              <img
                ref={selectedPhotoRef}
                src={api.getImageUrl(selectedPhoto.path, 1200)}
                alt={selectedPhoto.filename}
                className='max-h-[70vh] max-w-full object-contain'
                style={{
                  transform: `scale(${zoomLevel})`,
                  transition: 'transform 0.2s ease',
                }}
              />
            </div>

            {/* Photo info */}
            <div
              className={`${glass.surfaceStrong} border border-white/10 rounded-xl p-4 mt-4 max-w-2xl mx-auto`}
            >
              <div className='flex justify-between items-start'>
                <div>
                  <h3 className='font-semibold text-foreground text-lg'>
                    {selectedPhoto.filename}
                  </h3>
                  <p className='text-sm text-muted-foreground'>
                    {selectedPhoto.metadata?.image?.width}×
                    {selectedPhoto.metadata?.image?.height}
                  </p>
                </div>
                <div className='text-right'>
                  <p className='text-xs text-muted-foreground'>
                    {selectedIndex + 1} of {photos.length}
                  </p>
                </div>
              </div>

              {selectedPhoto.matchExplanation && (
                <div className='mt-3 text-sm text-muted-foreground'>
                  <p>{selectedPhoto.matchExplanation}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
