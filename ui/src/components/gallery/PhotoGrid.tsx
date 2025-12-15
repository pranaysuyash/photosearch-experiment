import { motion, AnimatePresence } from 'framer-motion';
import Masonry from 'react-masonry-css';
import { type Photo, api } from '../../api';
import { useRef, useEffect, useState, useCallback, memo } from 'react';
import { Play, Check, Download, Trash2, Star, StarOff } from 'lucide-react';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { SortControls } from './SortControls';
import { MediaTypeFilter } from './MediaTypeFilter';
import { FavoritesFilter } from './FavoritesFilter';
import { FavoritesToggle } from './FavoritesToggle';
import { MatchExplanation } from '../search/MatchExplanation';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';
import { ContextMenu } from '../actions/ContextMenu';
import './modern-gallery.css';

interface PhotoGridProps {
  photos: Photo[];
  loading?: boolean;
  error?: Error | null;
  onPhotoSelect: (photo: Photo) => void;
  hasMore?: boolean;
  loadMore?: () => void;
  sortBy?: string;
  onSortChange?: (sortBy: string) => void;
  typeFilter?: string;
  onTypeFilterChange?: (typeFilter: string) => void;
  favoritesFilter?: string;
  onFavoritesFilterChange?: (favoritesFilter: string) => void;
  onPhotosDeleted?: () => void;
}

export function PhotoGrid({
  photos,
  loading,
  error,
  onPhotoSelect,
  hasMore,
  loadMore,
  sortBy,
  onSortChange,
  typeFilter,
  onTypeFilterChange,
  favoritesFilter,
  onFavoritesFilterChange,
  onPhotosDeleted,
}: PhotoGridProps) {
  const observerTarget = useRef<HTMLDivElement>(null);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [favoriting, setFavoriting] = useState(false);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<{
    photo: Photo;
    position: { x: number; y: number };
  } | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const { setBaseAccentUrl, setOverrideAccentUrl, clearOverrideAccent } =
    useAmbientThemeContext();

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading && loadMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    const target = observerTarget.current;
    if (target) {
      observer.observe(target);
    }

    return () => {
      if (target) {
        observer.unobserve(target);
      }
    };
  }, [hasMore, loading, loadMore]);

  // Set CSS custom property for scroll timeline
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.style.setProperty(
        '--scroll-timeline-name',
        'gallery-scroll'
      );
    }
  }, []);

  useEffect(() => {
    if (photos.length === 0) {
      setBaseAccentUrl(null);
      return;
    }
    setBaseAccentUrl(api.getImageUrl(photos[0].path, 96));
  }, [photos, setBaseAccentUrl]);

  const toggleSelection = (path: string) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const selectAll = useCallback(() => {
    setSelectedPaths(new Set(photos.map((p) => p.path)));
  }, [photos]);

  const clearSelection = useCallback(() => {
    setSelectedPaths(new Set());
    setSelectMode(false);
  }, []);

  const handleExport = useCallback(async () => {
    if (selectedPaths.size === 0) return;
    setExporting(true);
    try {
      const response = await api.bulkExportPhotos(Array.from(selectedPaths));
      // Create download link for the ZIP file
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute(
        'download',
        `photos_export_${selectedPaths.size}_files.zip`
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed:', e);
    } finally {
      setExporting(false);
    }
  }, [selectedPaths]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedPaths.size === 0) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete ${selectedPaths.size} photo${selectedPaths.size > 1 ? 's' : ''
      }? This action cannot be undone.`
    );

    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.deletePhotos(Array.from(selectedPaths), true);
      // Clear selection and notify parent to refresh
      clearSelection();
      onPhotosDeleted?.();
    } catch (e) {
      console.error('Bulk delete failed:', e);
    } finally {
      setDeleting(false);
    }
  }, [selectedPaths, clearSelection, onPhotosDeleted]);

  const handleBulkFavorite = useCallback(
    async (action: 'add' | 'remove') => {
      if (selectedPaths.size === 0) return;
      setFavoriting(true);
      try {
        await api.bulkFavorite(Array.from(selectedPaths), action);

        // Update local favorites state
        if (action === 'add') {
          setFavorites((prev) => new Set([...prev, ...selectedPaths]));
        } else {
          setFavorites((prev) => {
            const newSet = new Set(prev);
            selectedPaths.forEach((path) => newSet.delete(path));
            return newSet;
          });
        }

        clearSelection();
      } catch (e) {
        console.error('Bulk favorite failed:', e);
      } finally {
        setFavoriting(false);
      }
    },
    [selectedPaths, clearSelection]
  );

  const handleToggleFavorite = useCallback(async (photoPath: string) => {
    try {
      const result = await api.toggleFavorite(photoPath);
      if (result.is_favorited) {
        setFavorites((prev) => new Set(prev).add(photoPath));
      } else {
        setFavorites((prev) => {
          const newSet = new Set(prev);
          newSet.delete(photoPath);
          return newSet;
        });
      }
    } catch (e) {
      console.error('Failed to toggle favorite:', e);
    }
  }, []);

  const handleContextMenu = useCallback((event: React.MouseEvent, photo: Photo) => {
    event.preventDefault();
    event.stopPropagation();
    
    setContextMenu({
      photo,
      position: { x: event.clientX, y: event.clientY }
    });
  }, []);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleActionExecute = useCallback((actionId: string, result: any) => {
    console.log('Action executed:', actionId, result);
    
    // Handle specific action results
    if (result.success) {
      // You could show a toast notification here
      console.log('Action completed successfully:', result.message);
    } else {
      console.error('Action failed:', result.error);
    }
  }, []);

  // Load favorites status for visible photos
  useEffect(() => {
    const loadFavoritesStatus = async () => {
      const photoPaths = photos.map((p) => p.path);
      const newFavorites = new Set<string>();

      for (const path of photoPaths) {
        try {
          const result = await api.checkFavorite(path);
          if (result.is_favorited) {
            newFavorites.add(path);
          }
        } catch (e) {
          console.error(`Failed to check favorite status for ${path}:`, e);
        }
      }

      setFavorites(newFavorites);
    };

    if (photos.length > 0) {
      loadFavoritesStatus();
    }
  }, [photos]);

  if (error) {
    return (
      <div className='flex flex-col items-center justify-center p-12 text-center'>
        <div className='text-destructive text-4xl mb-4'>⚠️</div>
        <h3 className='text-lg font-bold'>Failed to load content</h3>
        <p className='text-muted-foreground'>{error.message}</p>
        <button
          onClick={() => window.location.reload()}
          className='mt-4 px-4 py-2 bg-secondary rounded hover:bg-secondary/80'
        >
          Retry
        </button>
      </div>
    );
  }

  const breakpointColumnsObj = {
    default: 5,
    1536: 5,
    1280: 4,
    1024: 3,
    768: 2,
    640: 1,
  };

  // Loading skeleton for initial load (no photos yet)
  if (loading && photos.length === 0) {
    return (
      <div ref={scrollContainerRef} className='container mx-auto px-4 pb-20'>
        <div className='modern-gallery-grid'>
          {[...Array(15)].map((_, i) => (
            <div
              key={i}
              className='gallery-item aspect-[3/4] bg-secondary/30 rounded-xl gallery-skeleton'
              data-item-index={i % 20}
            />
          ))}
        </div>
      </div>
    );
  }

  // Identify videos
  const isVideo = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ['mp4', 'mov', 'webm', 'mkv'].includes(ext || '');
  };

  if (photos.length === 0 && !loading) {
    return (
      <div className='flex flex-col items-center justify-center p-24 text-muted-foreground'>
        <p className='text-lg'>No photos found</p>
        <p className='text-sm opacity-50'>Try searching for something else</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollContainerRef}
      className='container mx-auto px-4 pb-32 relative pt-2'
    >
      {/* Enhanced Selection Controls */}
      <div className='mb-6 flex flex-wrap items-center gap-2 sm:gap-3'>
        <motion.button
          onClick={() => setSelectMode(!selectMode)}
          className={`btn-glass ${selectMode ? 'btn-glass--primary' : 'btn-glass--muted'
            } text-sm font-semibold transition-all duration-300`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {selectMode ? 'Cancel Select' : 'Select'}
        </motion.button>

        {selectMode && (
          <motion.div
            className='flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto'
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <button
              onClick={
                selectedPaths.size === photos.length
                  ? clearSelection
                  : selectAll
              }
              className='btn-glass btn-glass--muted text-sm font-medium'
            >
              {selectedPaths.size === photos.length
                ? 'Deselect All'
                : 'Select All'}
            </button>
            <span className='text-sm text-muted-foreground px-2'>
              {selectedPaths.size} selected
            </span>

            {/* Bulk Action Buttons */}
            {selectedPaths.size > 0 && (
              <motion.div
                className='flex flex-wrap items-center gap-2 sm:ml-4'
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.2 }}
              >
                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className='btn-glass btn-glass--primary text-sm font-medium'
                  title='Export selected photos as ZIP'
                >
                  <Download size={14} />
                  {exporting ? 'Exporting...' : 'Export'}
                </button>

                <button
                  onClick={() => handleBulkFavorite('add')}
                  disabled={favoriting}
                  className='btn-glass text-sm font-medium'
                  title='Add selected photos to favorites'
                >
                  <Star size={14} />
                  Favorite
                </button>

                <button
                  onClick={() => handleBulkFavorite('remove')}
                  disabled={favoriting}
                  className='btn-glass text-sm font-medium'
                  title='Remove selected photos from favorites'
                >
                  <StarOff size={14} />
                  Unfavorite
                </button>

                <button
                  onClick={handleBulkDelete}
                  disabled={deleting}
                  className='btn-glass btn-glass--danger text-sm font-medium'
                  title='Delete selected photos'
                >
                  <Trash2 size={14} />
                  {deleting ? 'Deleting...' : 'Delete'}
                </button>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* Media Type Filter */}
        {typeFilter && onTypeFilterChange && (
          <div className='w-full sm:flex-1 sm:flex sm:justify-center'>
            <MediaTypeFilter
              typeFilter={typeFilter}
              onTypeFilterChange={onTypeFilterChange}
            />
          </div>
        )}

        {/* Favorites Filter */}
        {favoritesFilter && onFavoritesFilterChange && (
          <div className='w-full sm:w-auto sm:flex sm:justify-center'>
            <FavoritesFilter
              favoritesFilter={favoritesFilter}
              onFavoritesFilterChange={onFavoritesFilterChange}
            />
          </div>
        )}

        {/* Sort Controls */}
        {sortBy && onSortChange && (
          <div className='w-full sm:ml-auto sm:w-auto'>
            <SortControls sortBy={sortBy} onSortChange={onSortChange} />
          </div>
        )}
      </div>

      {/* Enhanced Masonry Grid with Modern CSS */}
      <Masonry
        breakpointCols={breakpointColumnsObj}
        className='flex -ml-4 w-auto'
        columnClassName='pl-4 bg-clip-padding'
      >
        {photos.map((photo, i) => {
          const isSelected = selectedPaths.has(photo.path);
          return (
            <motion.div
              key={photo.path}
              layoutId={`photo-${photo.path}`}
              className={`gallery-item mb-4 break-inside-avoid relative group cursor-pointer ${isSelected ? 'selected' : ''
                }`}
              style={
                {
                  '--item-index': i,
                  '--row-span': Math.floor(Math.random() * 2) + 2, // Random row span for varied layout
                } as React.CSSProperties
              }
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.5,
                delay: i * 0.05,
                ease: 'easeOut',
                type: 'spring',
                stiffness: 100,
              }}
              onClick={() =>
                selectMode ? toggleSelection(photo.path) : onPhotoSelect(photo)
              }
              onContextMenu={(e) => handleContextMenu(e, photo)}
              onMouseEnter={() =>
                setOverrideAccentUrl(
                  'gridHover',
                  api.getImageUrl(photo.path, 96)
                )
              }
              onMouseLeave={() => clearOverrideAccent('gridHover')}
              onFocus={() =>
                setOverrideAccentUrl(
                  'gridHover',
                  api.getImageUrl(photo.path, 96)
                )
              }
              onBlur={() => clearOverrideAccent('gridHover')}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  if (selectMode) {
                    toggleSelection(photo.path);
                  } else {
                    onPhotoSelect(photo);
                  }
                }
              }}
              tabIndex={0}
              role='button'
              aria-label={`Select ${photo.filename}`}
            >
              <img
                src={api.getImageUrl(photo.path)}
                alt={photo.filename}
                className='gallery-image w-full h-auto object-cover rounded-xl'
                loading='lazy'
              />

              {/* Enhanced Selection Checkbox */}
              {selectMode && (
                <div
                  className={`gallery-select ${isSelected ? 'selected' : ''}`}
                >
                  {isSelected && <Check size={14} />}
                </div>
              )}

              {/* Advanced Overlay System */}
              <div className='gallery-overlay' />

              {/* Enhanced Video Badge */}
              {isVideo(photo.filename) && (
                <div className='gallery-video-badge'>
                  <Play size={16} fill='currentColor' />
                </div>
              )}

              {/* Favorites Toggle */}
              <div className='absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity'>
                <FavoritesToggle
                  isFavorited={favorites.has(photo.path)}
                  onToggle={() => handleToggleFavorite(photo.path)}
                />
              </div>

              {/* Advanced Metadata Grid using Subgrid */}
              <div className='gallery-metadata'>
                <div className='gallery-title'>{photo.filename}</div>
                <div className='gallery-path'>
                  {photo.path.split('/').slice(-2).join('/')}
                </div>

                {/* Match Explanation - Positioned at top of metadata */}
                {photo.matchExplanation && (
                  <div 
                    className='mb-3 w-full order-first'
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                  >
                    <MatchExplanation 
                      explanation={photo.matchExplanation}
                      isCompact={true}
                    />
                  </div>
                )}

                {/* Score Badge - Secondary position */}
                {photo.score > 0 && (
                  <div className='gallery-score flex items-center gap-2 mt-2'>
                    <div className='score-bar'>
                      <div
                        className={`score-fill score-fill-${Math.round(Math.round(photo.score * 100) / 10) * 10
                          }`}
                      />
                    </div>
                    <div className='score-text'>
                      {Math.round(photo.score * 100)}%
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </Masonry>

      {/* Enhanced Floating Export Button */}
      {selectMode && selectedPaths.size > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className='fixed bottom-28 right-6 z-50'
        >
          <motion.button
            onClick={handleExport}
            disabled={exporting}
            className='btn-glass btn-glass--primary flex items-center gap-3 px-6 py-3 font-semibold disabled:opacity-50'
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
          >
            {exporting ? (
              <>
                <div className='w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin' />
                Exporting...
              </>
            ) : (
              <>
                <Download size={18} />
                Export {selectedPaths.size} Photos
              </>
            )}
          </motion.button>
        </motion.div>
      )}

      {/* Enhanced Loading Sentinel */}
      <div
        ref={observerTarget}
        className='h-24 w-full flex items-center justify-center mt-8'
      >
        {loading && photos.length > 0 && (
          <LoadingSpinner message='Loading more memories...' />
        )}
        {!hasMore && photos.length > 0 && (
          <motion.div
            className='text-center py-8 opacity-60'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 0.6, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div
              className='w-2 h-2 bg-primary/40 rounded-full mx-auto mb-3'
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className='text-xs uppercase tracking-widest text-muted-foreground font-medium'>
              End of Collection
            </span>
          </motion.div>
        )}
      </div>

      {/* Context Menu */}
      <AnimatePresence>
        {contextMenu && (
          <ContextMenu
            photo={contextMenu.photo}
            position={contextMenu.position}
            onClose={handleCloseContextMenu}
            onActionExecute={handleActionExecute}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(PhotoGrid);
