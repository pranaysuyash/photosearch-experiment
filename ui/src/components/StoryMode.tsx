import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { HeroCarousel } from "./HeroCarousel";
import { type Photo, api } from "../api";
import { usePhotoSearch } from "../hooks/usePhotoSearch";

import { MemoryMuseum } from "./MemoryMuseum";
import { PhotoDetail } from "./PhotoDetail";

interface GroupedPhotos {
  title: string;
  photos: Photo[];
}

export function StoryMode() {
  const [groups, setGroups] = useState<GroupedPhotos[]>([]);
  const [allPhotos, setAllPhotos] = useState<Photo[]>([]); // Store flat list for 3D
  /* Refactored to use usePhotoSearch hook */
  const { results: photos, loading } = usePhotoSearch({ initialQuery: "", initialFetch: true });
  const [show3D, setShow3D] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<Photo | null>(null);
  
  // Store flat list for 3D
  useEffect(() => {
    if (photos.length > 0) {
        setAllPhotos(photos);
    }
  }, [photos]);

  useEffect(() => {
    if (loading || photos.length === 0) return;

    // Mock grouping logic (since backend doesn't support it yet)
    // In a real app, this would use date-fns to parse metadata like: new Date(photo.metadata.created)
    // TODO: Implement real date parsing when backend returns 'created' timestamp
    const grouped: GroupedPhotos[] = [];
    
    // 1. Recent Highlights (simulate "Today")
    if (photos.length > 0) {
        grouped.push({
            title: "Recent Highlights",
            photos: photos.slice(0, 5)
        });
    }
    
    // 2. Last Month (simulate "November 2025")
    if (photos.length > 5) {
        grouped.push({
            title: "November 2025",
            photos: photos.slice(5, 12)
        });
    }

    // 3. Older Memories
    if (photos.length > 12) {
        grouped.push({
            title: "Archives",
            photos: photos.slice(12)
        });
    }

    setGroups(grouped);
  }, [photos, loading]);

  return (
    <div className="flex flex-col min-h-screen bg-background relative">
      <HeroCarousel onEnter3D={() => setShow3D(true)} />
      
      {show3D && (
          <MemoryMuseum 
            photos={allPhotos} 
            onClose={() => setShow3D(false)} 
            onPhotoSelect={setSelectedPhoto}
          />
      )}

      <PhotoDetail photo={selectedPhoto} onClose={() => setSelectedPhoto(null)} />
      
      <div className="container mx-auto px-4 py-8 pb-32">
        {loading && <div className="text-center p-10">Loading your story...</div>}
        
        {groups.map((group, groupIdx) => (
            <div key={groupIdx} className="mb-12">
                <h3 className="text-2xl font-bold mb-6 sticky top-20 z-10 bg-background/95 backdrop-blur py-2 border-b border-border/50">
                    {group.title}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {group.photos.map((photo, i) => (
                        <motion.div 
                            key={photo.path}
                            layoutId={`photo-${photo.path}`}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: i * 0.05 }}
                            onClick={() => setSelectedPhoto(photo)}
                            className={`aspect-square bg-secondary rounded-xl overflow-hidden relative group cursor-pointer ${
                                // Make the first item of first group large
                                groupIdx === 0 && i === 0 ? "md:col-span-2 md:row-span-2" : ""
                            }`}
                        >
                             <img 
                                src={api.getImageUrl(photo.path)} 
                                alt={photo.filename}
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                                loading="lazy"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                            <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                                <p className="text-white font-medium text-sm truncate">{photo.filename}</p>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        ))}
      </div>
    </div>
  );
}
