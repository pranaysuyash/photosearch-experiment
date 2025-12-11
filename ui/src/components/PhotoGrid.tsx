import { motion } from 'framer-motion'
import Masonry from 'react-masonry-css'
import { type Photo, api } from '../api'
import { useRef, useEffect, useState } from 'react'
import { Play, Check, Download } from 'lucide-react'

interface PhotoGridProps {
  photos: Photo[]
  loading?: boolean
  error?: Error | null
  onPhotoSelect: (photo: Photo) => void
  hasMore?: boolean
  loadMore?: () => void
}

export function PhotoGrid({ photos, loading, error, onPhotoSelect, hasMore, loadMore }: PhotoGridProps) {
  const observerTarget = useRef<HTMLDivElement>(null);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);

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
        <div className="container mx-auto px-4 pb-20">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-4">
                {[...Array(15)].map((_, i) => (
                    <div key={i} className="aspect-[3/4] bg-secondary/30 animate-pulse rounded-xl" />
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
    <div className="container mx-auto px-4 pb-20 relative">
        {/* Selection Controls */}
        <div className="sticky top-20 z-30 mb-4 flex items-center gap-2">
          <button
            onClick={() => setSelectMode(!selectMode)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
              selectMode 
                ? 'bg-primary text-primary-foreground border-primary' 
                : 'bg-background/80 backdrop-blur-sm border-border hover:border-primary/50'
            }`}
          >
            {selectMode ? 'Cancel Select' : 'Select'}
          </button>
          
          {selectMode && (
            <>
              <button
                onClick={selectedPaths.size === photos.length ? clearSelection : selectAll}
                className="px-3 py-1.5 text-xs font-medium rounded-full bg-background/80 backdrop-blur-sm border border-border hover:border-primary/50 transition-colors"
              >
                {selectedPaths.size === photos.length ? 'Deselect All' : 'Select All'}
              </button>
              <span className="text-xs text-muted-foreground ml-2">
                {selectedPaths.size} selected
              </span>
            </>
          )}
        </div>

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
                    layoutId={`photo-${photo.path}`}
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: i * 0.05, ease: "easeOut" }}
                    onClick={() => selectMode ? toggleSelection(photo.path) : onPhotoSelect(photo)}
                    className={`mb-4 break-inside-avoid relative group rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 bg-card cursor-pointer ${
                      isSelected ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''
                    }`}
                >
                    <img 
                        src={api.getImageUrl(photo.path)} 
                        alt={photo.filename}
                        className="w-full h-auto object-cover transition-transform duration-700 group-hover:scale-110"
                        loading="lazy"
                    />
                    
                    {/* Selection Checkbox */}
                    {selectMode && (
                      <div className={`absolute top-2 left-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                        isSelected 
                          ? 'bg-primary border-primary text-primary-foreground' 
                          : 'bg-black/50 border-white/50 backdrop-blur-sm'
                      }`}>
                        {isSelected && <Check size={14} />}
                      </div>
                    )}
                    
                    {/* Overlay Gradient */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    
                    {/* Video Badge */}
                    {isVideo(photo.filename) && (
                        <div className="absolute top-2 right-2 bg-black/50 backdrop-blur-md rounded-full p-1.5 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                            <Play size={12} fill="currentColor" />
                        </div>
                    )}

                    {/* Metadata Overlay */}
                    <div className="absolute bottom-0 left-0 right-0 p-4 translate-y-4 group-hover:translate-y-0 transition-transform duration-300 opacity-0 group-hover:opacity-100">
                        <p className="text-white text-sm font-medium truncate">{photo.filename}</p>
                        <p className="text-white/70 text-xs truncate mt-0.5">{photo.path.split('/').slice(-2).join('/')}</p>
                        {photo.score > 0 && (
                            <div className="mt-1 flex items-center gap-1">
                                <div className="h-1 w-full bg-white/30 rounded-full overflow-hidden">
                                    <div 
                                        className="h-full bg-green-400" 
                                        style={{ width: `${Math.round(photo.score * 100)}%` }} 
                                    />
                                </div>
                                <span className="text-[10px] text-white/90">{Math.round(photo.score * 100)}%</span>
                            </div>
                        )}
                    </div>
                </motion.div>
            )})}
        </Masonry>

        {/* Floating Export Button */}
        {selectMode && selectedPaths.size > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="fixed bottom-28 right-6 z-50"
          >
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center gap-2 px-5 py-3 bg-primary text-primary-foreground rounded-full shadow-lg shadow-primary/30 hover:bg-primary/90 transition-colors font-medium disabled:opacity-50"
            >
              {exporting ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download size={18} />
                  Export {selectedPaths.size} Photos
                </>
              )}
            </button>
          </motion.div>
        )}

        {/* Loading Sentinel */}
        <div ref={observerTarget} className="h-24 w-full flex items-center justify-center mt-8">
            {loading && photos.length > 0 && (
                <div className="flex flex-col items-center gap-2">
                    <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs text-muted-foreground animate-pulse">Loading more memories...</span>
                </div>
            )}
            {!hasMore && photos.length > 0 && (
                <div className="text-center py-8 opacity-50">
                    <div className="w-2 h-2 bg-primary/20 rounded-full mx-auto mb-2" />
                    <span className="text-[10px] uppercase tracking-widest text-muted-foreground">End of Collection</span>
                </div>
            )}
        </div>
    </div>
  );
}
