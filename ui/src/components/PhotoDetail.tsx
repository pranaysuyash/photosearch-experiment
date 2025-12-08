import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Camera, MapPin, Calendar, HardDrive, Image as ImageIcon, ChevronLeft, ChevronRight } from "lucide-react";
import { type Photo, api } from "../api";

interface PhotoDetailProps {
    photos: Photo[];              // Full list for navigation
    currentIndex: number | null;  // Current photo index
    onNavigate: (index: number) => void;
    onClose: () => void;
}

// Helper to format file size
function formatBytes(bytes: number): string {
    if (!bytes) return "Unknown";
    const units = ["B", "KB", "MB", "GB"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return `${bytes.toFixed(1)} ${units[i]}`;
}

// Metadata section component
function MetadataSection({ icon: Icon, title, children }: { icon: any; title: string; children: React.ReactNode }) {
    return (
        <div className="mb-4">
            <h4 className="flex items-center gap-2 text-white/70 text-xs uppercase tracking-wider mb-2">
                <Icon size={14} />
                {title}
            </h4>
            <div className="space-y-1 text-sm">
                {children}
            </div>
        </div>
    );
}

function MetadataRow({ label, value }: { label: string; value: string | number | undefined | null }) {
    if (value === undefined || value === null || value === "") return null;
    return (
        <div className="flex justify-between items-center py-1 border-b border-white/5">
            <span className="text-white/50">{label}</span>
            <span className="text-white/90 font-mono text-xs">{String(value)}</span>
        </div>
    );
}

export function PhotoDetail({ photos, currentIndex, onNavigate, onClose }: PhotoDetailProps) {
    const photo = currentIndex !== null ? photos[currentIndex] : null;
    
    // Keyboard navigation
    useEffect(() => {
        if (currentIndex === null) return;
        
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'ArrowLeft' && currentIndex > 0) {
                onNavigate(currentIndex - 1);
            } else if (e.key === 'ArrowRight' && currentIndex < photos.length - 1) {
                onNavigate(currentIndex + 1);
            } else if (e.key === 'Escape') {
                onClose();
            }
        };
        
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentIndex, photos.length, onNavigate, onClose]);
    
    if (!photo) return null;

    // Extract metadata from photo object
    const metadata = photo.metadata || {};
    const fs = metadata.filesystem || {};
    const img = metadata.image || {};
    const exif = metadata.exif || {};
    const gps = metadata.gps || {};
    const calc = metadata.calculated || {};

    const hasPrev = currentIndex !== null && currentIndex > 0;
    const hasNext = currentIndex !== null && currentIndex < photos.length - 1;

    return (
        <AnimatePresence>
            {photo && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/95 backdrop-blur-md"
                    />
                    
                    <motion.div
                        layoutId={`photo-${photo.path}`}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="relative z-10 max-w-6xl w-full max-h-[95vh] flex gap-6"
                    >
                        <button 
                            onClick={onClose}
                            className="absolute -top-12 right-0 p-2 text-white/50 hover:text-white transition-colors"
                        >
                            <X size={24} />
                        </button>
                        
                        {/* Navigation - Previous */}
                        {hasPrev && (
                            <button
                                onClick={() => onNavigate(currentIndex! - 1)}
                                className="absolute left-4 top-1/2 -translate-y-1/2 z-20 p-3 bg-black/50 hover:bg-black/80 rounded-full text-white/70 hover:text-white transition-all backdrop-blur-lg"
                            >
                                <ChevronLeft size={24} />
                            </button>
                        )}
                        
                        {/* Navigation - Next */}
                        {hasNext && (
                            <button
                                onClick={() => onNavigate(currentIndex! + 1)}
                                className="absolute right-96 top-1/2 -translate-y-1/2 z-20 p-3 bg-black/50 hover:bg-black/80 rounded-full text-white/70 hover:text-white transition-all backdrop-blur-lg"
                            >
                                <ChevronRight size={24} />
                            </button>
                        )}
                        
                        {/* Image */}
                        <div className="flex-1 flex items-center justify-center rounded-xl overflow-hidden bg-black/50">
                             <img 
                                src={api.getImageUrl(photo.path, 1200)} // High res
                                alt={photo.filename}
                                className="max-h-[85vh] w-auto object-contain"
                            />
                        </div>
                        
                        {/* Metadata Panel */}
                        <div className="w-80 bg-white/5 backdrop-blur-xl rounded-xl p-5 overflow-y-auto max-h-[85vh] border border-white/10">
                            <h3 className="text-white text-lg font-semibold mb-1 truncate">{photo.filename}</h3>
                            <p className="text-white/40 text-xs mb-6 truncate">{photo.path}</p>
                            
                            {/* Score if semantic search */}
                            {photo.score !== undefined && photo.score > 0 && (
                                <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                                    <span className="text-blue-400 text-sm">Relevance Score: </span>
                                    <span className="text-white font-bold">{(photo.score * 100).toFixed(0)}%</span>
                                </div>
                            )}
                            
                            {/* Image Properties */}
                            {(img.width || img.format) && (
                                <MetadataSection icon={ImageIcon} title="Image">
                                    <MetadataRow label="Dimensions" value={img.width && img.height ? `${img.width} × ${img.height}` : undefined} />
                                    <MetadataRow label="Format" value={img.format} />
                                    <MetadataRow label="Mode" value={img.mode} />
                                    <MetadataRow label="Aspect Ratio" value={calc.aspect_ratio} />
                                    <MetadataRow label="Megapixels" value={calc.megapixels ? `${calc.megapixels} MP` : undefined} />
                                    <MetadataRow label="Orientation" value={calc.orientation} />
                                </MetadataSection>
                            )}
                            
                            {/* Camera/EXIF */}
                            {exif.image && (
                                <MetadataSection icon={Camera} title="Camera">
                                    <MetadataRow label="Make" value={exif.image?.Make} />
                                    <MetadataRow label="Model" value={exif.image?.Model} />
                                    <MetadataRow label="Software" value={exif.image?.Software} />
                                </MetadataSection>
                            )}
                            
                            {exif.exif && (
                                <MetadataSection icon={Camera} title="Exposure">
                                    <MetadataRow label="ISO" value={exif.exif?.ISOSpeedRatings} />
                                    <MetadataRow label="Aperture" value={exif.exif?.FNumber} />
                                    <MetadataRow label="Shutter" value={exif.exif?.ExposureTime} />
                                    <MetadataRow label="Focal Length" value={exif.exif?.FocalLength} />
                                </MetadataSection>
                            )}
                            
                            {/* GPS */}
                            {(gps.latitude || gps.longitude) && (
                                <MetadataSection icon={MapPin} title="Location">
                                    <MetadataRow label="Latitude" value={gps.latitude?.toFixed(6)} />
                                    <MetadataRow label="Longitude" value={gps.longitude?.toFixed(6)} />
                                    <MetadataRow label="Altitude" value={gps.altitude ? `${gps.altitude}m` : undefined} />
                                </MetadataSection>
                            )}
                            
                            {/* File System */}
                            <MetadataSection icon={HardDrive} title="File">
                                <MetadataRow label="Size" value={fs.size_human || formatBytes(fs.size_bytes)} />
                                <MetadataRow label="Created" value={fs.created?.split('T')[0]} />
                                <MetadataRow label="Modified" value={fs.modified?.split('T')[0]} />
                            </MetadataSection>
                            
                            {/* Age */}
                            {calc.file_age && (
                                <MetadataSection icon={Calendar} title="Age">
                                    <MetadataRow label="Age" value={calc.file_age.human_readable} />
                                </MetadataSection>
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

