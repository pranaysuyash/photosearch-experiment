import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { HeroCarousel } from "./HeroCarousel";
import { type Photo, api } from "../api";
import { usePhotoSearch } from "../hooks/usePhotoSearch";

interface GroupedPhotos {
  title: string;
  photos: Photo[];
}

export function StoryMode() {
  const [groups, setGroups] = useState<GroupedPhotos[]>([]);
  const { results: photos, loading } = usePhotoSearch({ initialQuery: "", initialFetch: true });
  
  useEffect(() => {
    if (loading) return;
    
    if (photos.length === 0) {
        setGroups([]);
        return;
    }

    // Group by mock categories (real implementation would use dates)
    const shuffled = [...photos].sort(() => Math.random() - 0.5);
    const mockGroups: GroupedPhotos[] = [
      { title: "Recent Memories", photos: shuffled.slice(0, 8) },
      { title: "Highlights", photos: shuffled.slice(8, 16) },
      { title: "Explore", photos: shuffled.slice(16, 24) },
    ].filter(g => g.photos.length > 0);

    setGroups(mockGroups);
  }, [photos, loading]);

  return (
    <div className="flex flex-col min-h-screen bg-background relative">
      <HeroCarousel onEnter3D={() => {}} />
      
      <div className="container mx-auto px-4 py-8 pb-32">
        {loading && (
            <div className="text-center p-24 text-muted-foreground animate-pulse">
                <p>Curating your museum...</p>
            </div>
        )}

        {!loading && photos.length === 0 && (
            <div className="text-center p-24 flex flex-col items-center">
                <div className="w-16 h-16 bg-secondary/50 rounded-full flex items-center justify-center mb-4">
                    <span className="text-2xl">📸</span>
                </div>
                <h3 className="text-xl font-bold mb-2">Your Museum is Empty</h3>
                <p className="text-muted-foreground max-w-md mx-auto mb-6">
                    Add photos to the <code>media/</code> folder or run a scan to get started.
                </p>
            </div>
        )}

        {groups.map((group, i) => (
          <motion.section
            key={group.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="mb-12"
          >
            <h2 className="text-2xl font-bold mb-4 px-2">{group.title}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {group.photos.map((photo) => (
                <motion.div
                  key={photo.path}
                  layoutId={`photo-${photo.path}`}
                  className="aspect-square rounded-lg overflow-hidden cursor-pointer relative group"
                  whileHover={{ scale: 1.02 }}
                  transition={{ type: "spring", stiffness: 300 }}
                >
                  <img
                    src={api.getImageUrl(photo.path, 300)}
                    alt={photo.filename}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                    <p className="absolute bottom-2 left-2 right-2 text-white text-xs truncate">
                      {photo.filename}
                    </p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.section>
        ))}
      </div>
    </div>
  );
}
