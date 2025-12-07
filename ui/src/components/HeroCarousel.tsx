import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api";
import { usePhotoSearch } from "../hooks/usePhotoSearch";

export function HeroCarousel({ onEnter3D }: { onEnter3D?: () => void }) {
  const { search } = usePhotoSearch({ initialFetch: false });
  const [photos, setPhotos] = useState<any[]>([]); // Keep local state for shuffled
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // Fetch random or recent photos for the hero
    search("").then((res) => {
        if (res && res.length > 0) {
            // Shuffle and pick top 5
            const shuffled = [...res].sort(() => 0.5 - Math.random());
            setPhotos(shuffled.slice(0, 5));
        }
    });
  }, [search]);

  useEffect(() => {
    if (photos.length <= 1) return;
    const timer = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % photos.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [photos]);

  if (photos.length === 0) return null;

  return (
    <div className="relative w-full h-[50vh] overflow-hidden bg-black">
      <AnimatePresence mode="wait">
        <motion.div
          key={currentIndex}
          initial={{ opacity: 0, scale: 1.1 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.5 }}
          className="absolute inset-0"
        >
          <img
            src={api.getImageUrl(photos[currentIndex].path)}
            alt="Hero memory"
            className="w-full h-full object-cover opacity-80"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background to-transparent" />
        </motion.div>
      </AnimatePresence>

      <div className="absolute bottom-8 left-8 z-10">
        <h2 className="text-4xl font-bold text-white mb-2 drop-shadow-lg">
            Welcome Back
        </h2>
        <p className="text-white/80 text-lg drop-shadow-md mb-6">
            Rediscover your memories from {photos[currentIndex]?.filename}
        </p>
        
        {onEnter3D && (
            <button
                onClick={onEnter3D}
                className="px-6 py-2 bg-white/20 hover:bg-white/40 text-white border border-white/50 rounded-full backdrop-blur-md transition-all flex items-center gap-2 font-medium"
            >
                <span>✨</span> Explore in 3D
            </button>
        )}
      </div>
    </div>
  );
}
