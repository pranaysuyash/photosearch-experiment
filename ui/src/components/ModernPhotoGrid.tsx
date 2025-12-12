import { motion } from 'framer-motion'
import Masonry from 'react-masonry-css'
import { type Photo, api } from '../api'
import { useRef, useEffect, useState } from 'react'
import { Play, Check, Download } from 'lucide-react'
import '../modern-gallery.css'

interface PhotoGridProps {
  photos: Photo[]
  loading?: boolean
  error?: Error | null
  onPhotoSelect: (photo: Photo) => void
  hasMore?: boolean
  loadMore?: () => void
}

export function ModernPhotoGrid({ photos, loading, error, onPhotoSelect, hasMore, loadMore }: PhotoGridProps) {
  const observerTarget = useRef<HTMLDivElement>(null);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading && loadMore) {
          loadMore();
        }
      },
      { threshold: 0.1 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current);
      }
    };
  }, [hasMore, loading, loadMore]);

  // Set CSS custom property for scroll timeline
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.style.setProperty('--scroll-timeline-name', 'gallery-scroll');
    }
  }, []);

  const toggleSelection = (path: string) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedPaths(new Set(photos.map(p => p.path)));
  };

  const clearSelection = () => {
    setSelectedPaths(new Set());
    setSelectMode(false);
  };

  const handleExport = async () => {
    if (selectedPaths.size === 0) return;
    setExporting(true);
    try {
      await api.exportPhotos(Array.from(selectedPaths));
    } catch (e) {
      console.error('Export failed:', e);
    } finally {
      setExporting(false);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <div className="text-destructive text-4xl mb-4">⚠️</div>
        <h3 className="text-lg font-bold">Failed to load content</h3>
        <p className="text-muted-foreground">{error.message}</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-secondary rounded hover:bg-secondary/80"
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
    640: 1
  };
  
  // Loading skeleton for initial load (no photos yet)
  if (loading && photos.length === 0) {
    return (
      <div ref={scrollContainerRef} className="container mx-auto px-4 pb-20">
        <div className="modern-gallery-grid">
          {[...Array(15)].map((_, i) => (
            <div 
              key={i} 
              className="gallery-item aspect-[3/4] bg-secondary/30 rounded-xl gallery-skeleton"
              style={{ '--item-index': i } as React.CSSProperties}
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
  }

  if (photos.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center p-24 text-muted-foreground">
        <p className="text-lg">No photos found</p>
        <p className="text-sm opacity-50">Try searching for something else</p>
      </div>
    );
  }

  return (
    <div ref={scrollContainerRef} className="container mx-auto px-4 pb-20 relative">
      {/* Enhanced Selection Controls */}
      <div className="sticky top-20 z-30 mb-6 flex items-center gap-3">
        <motion.button
          onClick={() => setSelectMode(!selectMode)}
          className={`px-4 py-2 text-sm font-semibold rounded-full border transition-all duration-300 ${
            selectMode 
              ? 'bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/25' 
              : 'bg-background/80 backdrop-blur-md border-border hover:border-primary/50 hover:shadow-md'
          }`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {selectMode ? 'Cancel Select' : 'Select'}
        </motion.button>
        
        {selectMode && (
          <motion.div 
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <button
              onClick={selectedPaths.size === photos.length ? clearSelection : selectAll}
              className="px-3 py-2 text-sm font-medium rounded-full bg-background/80 backdrop-blur-md border border-border hover:border-primary/50 transition-all hover:shadow-md"
            >
              {selectedPaths.size === photos.length ? 'Deselect All' : 'Select All'}
            </button>
            <span className="text-sm text-muted-foreground px-2">
              {selectedPaths.size} selected
            </span>
          </motion.div>
        )}
      </div>

      {/* Enhanced Masonry Grid with Modern CSS */}
      <Masonry
        breakpointCols={breakpointColumnsObj}
        className="flex -ml-4 w-auto"
        columnClassName="pl-4 bg-clip-padding"
      >
        {photos.map((photo, i) => {
          const isSelected = selectedPaths.has(photo.path);
          return (
            <motion.div 
              key={photo.path}
              className={`gallery-item mb-4 break-inside-avoid relative group cursor-pointer ${
                isSelected ? 'selected' : ''
              }`}
              style={{ 
                '--item-index': i,
                '--row-span': Math.floor(Math.random() * 2) + 2 // Random row span for varied layout
              } as React.CSSProperties}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ 
                duration: 0.5, 
                delay: i * 0.05, 
                ease: "easeOut",
                type: "spring",
                stiffness: 100
              }}
              onClick={() => selectMode ? toggleSelection(photo.path) : onPhotoSelect(photo)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectMode ? toggleSelection(photo.path) : onPhotoSelect(photo);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`Select ${photo.filename}`}
            >
              <img 
                src={api.getImageUrl(photo.path)} 
                alt={photo.filename}
                className="gallery-image w-full h-auto object-cover rounded-xl"
                loading="lazy"
              />
              
              {/* Enhanced Selection Checkbox */}
              {selectMode && (
                <div className={`gallery-select ${
                  isSelected ? 'selected' : ''
                }`}>
                  {isSelected && <Check size={14} />}
                </div>
              )}
              
              {/* Advanced Overlay System */}
              <div className="gallery-overlay" />
              
              {/* Enhanced Video Badge */}
              {isVideo(photo.filename) && (
                <div className="gallery-video-badge">
                  <Play size={16} fill="currentColor" />
                </div>
              )}

              {/* Advanced Metadata Grid using Subgrid */}
              <div className="gallery-metadata">
                <div className="gallery-title">{photo.filename}</div>
                <div className="gallery-path">
                  {photo.path.split('/').slice(-2).join('/')}
                </div>
                
                {/* Enhanced Score Visualization */}
                {photo.score > 0 && (
                  <div className="gallery-score">
                    <div className="score-bar">
                      <div 
                        className="score-fill" 
                        style={{ width: `${Math.round(photo.score * 100)}%` }} 
                      />
                    </div>
                    <div className="score-text">
                      {Math.round(photo.score * 100)}%
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )
        })}
      </Masonry>

      {/* Enhanced Floating Export Button */}
      {selectMode && selectedPaths.size > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className="fixed bottom-28 right-6 z-50"
        >
          <motion.button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-3 px-6 py-3 bg-primary text-primary-foreground rounded-full shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all font-semibold disabled:opacity-50 backdrop-blur-md border border-primary/20"
            whileHover={{ scale: 1.05, y: -2 }}
            whileTap={{ scale: 0.95 }}
          >
            {exporting ? (
              <>
                <div className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
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
      <div ref={observerTarget} className="h-24 w-full flex items-center justify-center mt-8">
        {loading && photos.length > 0 && (
          <motion.div 
            className="flex flex-col items-center gap-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            <motion.div 
              className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            />
            <span className="text-sm text-muted-foreground animate-pulse">Loading more memories...</span>
          </motion.div>
        )}
        {!hasMore && photos.length > 0 && (
          <motion.div 
            className="text-center py-8 opacity-60"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 0.6, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <motion.div 
              className="w-2 h-2 bg-primary/40 rounded-full mx-auto mb-3"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="text-xs uppercase tracking-widest text-muted-foreground font-medium">End of Collection</span>
          </motion.div>
        )}
      </div>
    </div>
  );
}