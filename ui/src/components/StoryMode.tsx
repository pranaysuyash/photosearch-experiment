import { useEffect, useRef, useCallback, useMemo } from "react";
import { motion } from "framer-motion";
import { FixedSizeList as List, ListChildComponentProps } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
import { type Photo } from "../api";

interface StoryModeProps {
  photos: Photo[];
  loading?: boolean;
  onPhotoSelect?: (photo: Photo) => void;
  hasMore?: boolean;
  loadMore?: () => void;
}

// Constants for virtualization
const ROW_HEIGHT = 320; // Height of each row including gap
const PHOTOS_PER_ROW = 4;

interface RowData {
  photos: Photo[];
  onPhotoSelect?: (photo: Photo) => void;
}

// Memoized row component for virtualization
const PhotoRow = ({ index, style, data }: { index: number; style: React.CSSProperties; data: RowData }) => {
  const startIdx = index * PHOTOS_PER_ROW;
  const rowPhotos = data.photos.slice(startIdx, startIdx + PHOTOS_PER_ROW);

  if (rowPhotos.length === 0) return null;

  return (
    <div style={style} className="px-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 h-[300px]">
        {rowPhotos.map((photo, i) => (
          <motion.div
            key={photo.path}
            className={`relative group rounded-2xl overflow-hidden cursor-pointer bg-muted ${(startIdx + i) % 3 === 0 ? 'md:col-span-2' : ''
              }`}
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            onClick={() => data.onPhotoSelect?.(photo)}
          >
            <img
              src={`http://127.0.0.1:8000/image/thumbnail?path=${encodeURIComponent(photo.path)}&size=800`}
              alt={photo.filename}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className="absolute bottom-4 left-4 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              <p className="font-medium">{photo.filename}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export function StoryMode({ photos, loading, onPhotoSelect, hasMore, loadMore }: StoryModeProps) {
  const observerTarget = useRef<HTMLDivElement>(null);
  const listRef = useRef<List>(null);

  // Calculate total rows needed
  const rowCount = useMemo(() => Math.ceil(photos.length / PHOTOS_PER_ROW), [photos.length]);

  // Data object for virtualized list
  const itemData = useMemo<RowData>(() => ({
    photos,
    onPhotoSelect,
  }), [photos, onPhotoSelect]);

  // Handle scroll to load more
  const handleItemsRendered = useCallback(({ visibleStopIndex }: { visibleStopIndex: number }) => {
    // Load more when near the end
    if (visibleStopIndex >= rowCount - 2 && hasMore && !loading && loadMore) {
      loadMore();
    }
  }, [rowCount, hasMore, loading, loadMore]);

  // Infinite Scroll Observer (fallback for when virtualization is disabled)
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

  if (!loading && photos.length === 0) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-background">
        <div className="text-center flex flex-col items-center">
          <div className="w-20 h-20 bg-secondary/50 rounded-full flex items-center justify-center mb-6">
            <span className="text-3xl">📸</span>
          </div>
          <h3 className="text-2xl font-semibold mb-3">Your Museum is Empty</h3>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            Add photos to the <code className="bg-muted px-2 py-0.5 rounded">media/</code> folder and click scan to get started.
          </p>
          <button
            onClick={() => {
              const defaultPath = window.location.hostname === 'localhost'
                ? '/Users/pranay/Projects/photosearch_experiment/media'
                : 'media';

              import('../api').then(({ api }) => {
                api.scan(defaultPath).then(() => {
                  window.location.reload();
                }).catch(err => alert("Scan failed: " + err));
              });
            }}
            className="px-8 py-3 bg-primary text-primary-foreground rounded-full font-medium hover:bg-primary/90 transition-all shadow-lg shadow-primary/25 flex items-center gap-2 text-lg"
          >
            <span>✨</span> Scan Library
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col bg-background relative h-[calc(100vh-80px)]">
      {/* Loading State for initial fetch */}
      {loading && photos.length === 0 && (
        <div className="text-center p-24 text-muted-foreground animate-pulse">
          <p>Curating your museum...</p>
        </div>
      )}

      {/* Virtualized Photo Grid */}
      {photos.length > 0 && (
        <div className="flex-1">
          <AutoSizer>
            {({ height, width }) => (
              <List
                ref={listRef}
                height={height}
                width={width}
                itemCount={rowCount + 1} // +1 for loading indicator row
                itemSize={ROW_HEIGHT}
                itemData={itemData}
                onItemsRendered={handleItemsRendered}
                overscanCount={2}
              >
                {({ index, style, data }: ListChildComponentProps<RowData>) => {
                  // Last row is the loading indicator
                  if (index === rowCount) {
                    return (
                      <div style={style} ref={observerTarget} className="h-24 w-full flex items-center justify-center">
                        {loading && (
                          <div className="flex flex-col items-center gap-2">
                            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                            <span className="text-xs text-muted-foreground animate-pulse">Unearthing more stories...</span>
                          </div>
                        )}
                        {!hasMore && photos.length > 0 && (
                          <div className="text-center py-8 opacity-50">
                            <span className="text-[10px] uppercase tracking-widest text-muted-foreground">The End</span>
                          </div>
                        )}
                      </div>
                    );
                  }
                  return <PhotoRow index={index} style={style} data={data} />;
                }}
              </List>
            )}
          </AutoSizer>
        </div>
      )}
    </div>
  );
}
