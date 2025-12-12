import { useEffect, useRef, useMemo } from "react";
import { motion } from "framer-motion";
import { FixedSizeList as List } from "react-window";

// Define the type locally since react-window 1.8.8 doesn't export it properly
interface ListChildComponentProps<T = any> {
  index: number;
  style: React.CSSProperties;
  data: T;
}
import AutoSizer from "react-virtualized-auto-sizer";
import { type Photo } from "../api";

interface StoryModeProps {
  photos: Photo[];
  loading?: boolean;
  onPhotoSelect?: (photo: Photo) => void;
  hasMore?: boolean;
  loadMore?: () => void;
}

export function StoryMode({ photos, loading, onPhotoSelect, hasMore, loadMore }: StoryModeProps) {
  const observerTarget = useRef<HTMLDivElement>(null);

  // Intersection observer for infinite scroll
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

  // Memoize photo grid for performance
  const photoGrid = useMemo(() => {
    if (photos.length === 0) return null;

    return (
      <AutoSizer>
        {({ height, width }) => (
          <div
            style={{ height: height, width: width, overflow: 'auto' }}
            className="space-y-4 p-4"
          >
            {/* Dynamic grid based on available width */}
            <div 
              className="grid gap-4"
              style={{
                gridTemplateColumns: `repeat(auto-fill, minmax(280px, 1fr))`,
              }}
            >
              {photos.map((photo, index) => (
                <motion.div
                  key={photo.path}
                  className="group relative bg-card rounded-xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 cursor-pointer"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.05 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  onClick={() => onPhotoSelect?.(photo)}
                >
                  {/* Image with lazy loading */}
                  <div className="aspect-[4/3] overflow-hidden">
                    <img
                      src={`http://127.0.0.1:8000/image/thumbnail?path=${encodeURIComponent(photo.path)}&size=800`}
                      alt={photo.filename}
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                  
                  {/* Enhanced overlay */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  
                  {/* Metadata */}
                  <div className="absolute bottom-0 left-0 right-0 p-4 translate-y-4 group-hover:translate-y-0 transition-transform duration-300 opacity-0 group-hover:opacity-100">
                    <h3 className="text-white text-sm font-semibold truncate">{photo.filename}</h3>
                    <p className="text-white/70 text-xs truncate mt-1">
                      {photo.path.split('/').slice(-2).join('/')}
                    </p>
                    
                    {/* Score visualization for semantic search results */}
                    {photo.score > 0 && (
                      <div className="mt-2 flex items-center gap-2">
                        <div className="h-1 flex-1 bg-white/30 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-green-400 transition-all duration-500" 
                            style={{ width: `${Math.round(photo.score * 100)}%` }} 
                          />
                        </div>
                        <span className="text-[10px] text-white/90">{Math.round(photo.score * 100)}%</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Video indicator */}
                  {photo.filename.match(/\.(mp4|mov|webm|mkv)$/i) && (
                    <div className="absolute top-3 right-3 bg-black/50 backdrop-blur-sm rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="w-2 h-2 bg-white rounded-full"></div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
            
            {/* Loading sentinel */}
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
                  <span className="text-xs uppercase tracking-widest text-muted-foreground font-medium">The End</span>
                </motion.div>
              )}
            </div>
          </div>
        )}
      </AutoSizer>
    );
  }, [photos, onPhotoSelect, loading, hasMore]);

  if (loading && photos.length === 0) {
    return (
      <div className="text-center p-24 text-muted-foreground animate-pulse">
        <div className="flex flex-col items-center gap-3">
          <motion.div 
            className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
          <p>Curating your museum...</p>
        </div>
      </div>
    );
  }

  if (photos.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center p-24 text-muted-foreground">
        <div className="text-6xl mb-4">📸</div>
        <p className="text-lg mb-2">No photos found</p>
        <p className="text-sm opacity-75">Start by scanning your media library</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col bg-background relative h-full min-h-0">
      {/* Loading State for initial fetch */}
      {loading && photos.length === 0 && (
        <div className="text-center p-24 text-muted-foreground animate-pulse">
          <p>Curating your museum...</p>
        </div>
      )}

      {/* Virtualized Photo Grid */}
      {photos.length > 0 && (
        <div className="flex-1 mt-6">
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