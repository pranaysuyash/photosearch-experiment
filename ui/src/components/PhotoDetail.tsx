import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { type Photo, api } from "../api";

interface PhotoDetailProps {
    photo: Photo | null;
    onClose: () => void;
}

export function PhotoDetail({ photo, onClose }: PhotoDetailProps) {
    if (!photo) return null;

    return (
        <AnimatePresence>
            {photo && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/90 backdrop-blur-sm"
                    />
                    
                    <motion.div
                        layoutId={`photo-${photo.path}`}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="relative z-10 max-w-5xl w-full max-h-[90vh] flex flex-col items-center justify-center"
                    >
                        <button 
                            onClick={onClose}
                            className="absolute -top-12 right-0 p-2 text-white/50 hover:text-white transition-colors"
                        >
                            <X size={24} />
                        </button>
                        
                        <div className="relative rounded-lg overflow-hidden shadow-2xl bg-black">
                             <img 
                                src={api.getImageUrl(photo.path)} // Load full res here
                                alt={photo.filename}
                                className="max-h-[85vh] w-auto object-contain"
                            />
                        </div>
                        
                        <div className="mt-4 text-center">
                            <h3 className="text-white text-xl font-medium">{photo.filename}</h3>
                            <p className="text-white/50 text-sm mt-1">{photo.path}</p>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
