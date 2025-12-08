import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Camera, MapPin, Calendar, HardDrive, Image as ImageIcon, ChevronLeft, ChevronRight, Music, FileText, Code } from "lucide-react";
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
                        
                        {/* Image or Video */}
                        <div className="flex-1 flex items-center justify-center rounded-xl overflow-hidden bg-black/50">
                            {api.isVideo(photo.path) ? (
                                <video 
                                    src={api.getVideoUrl(photo.path)}
                                    controls
                                    autoPlay
                                    className="max-h-[85vh] w-auto object-contain"
                                />
                            ) : (
                                <img 
                                    src={api.getImageUrl(photo.path, 1200)}
                                    alt={photo.filename}
                                    className="max-h-[85vh] w-auto object-contain"
                                />
                            )}
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
                            
                            {/* File Info */}
                            {metadata.file && (
                                <MetadataSection icon={HardDrive} title="File Info">
                                    <MetadataRow label="Name" value={metadata.file.name} />
                                    <MetadataRow label="Extension" value={metadata.file.extension} />
                                    <MetadataRow label="MIME Type" value={metadata.file.mime_type} />
                                </MetadataSection>
                            )}
                            
                            {/* Image Properties */}
                            {img.width && (
                                <MetadataSection icon={ImageIcon} title="Image">
                                    <MetadataRow label="Dimensions" value={`${img.width} × ${img.height}`} />
                                    <MetadataRow label="Format" value={img.format} />
                                    <MetadataRow label="Mode" value={img.mode} />
                                    <MetadataRow label="DPI" value={img.dpi?.join(' × ')} />
                                    <MetadataRow label="Bits/Pixel" value={img.bits_per_pixel} />
                                    <MetadataRow label="Has Animation" value={img.animation ? 'Yes' : 'No'} />
                                    <MetadataRow label="Frames" value={img.frames} />
                                </MetadataSection>
                            )}
                            
                            {/* Video Properties */}
                            {metadata.video?.format && (
                                <MetadataSection icon={Camera} title="Video">
                                    <MetadataRow label="Duration" value={calc.duration_human || `${Math.round(parseFloat(metadata.video.format.duration))}s`} />
                                    <MetadataRow label="Resolution" value={metadata.video.streams?.[0] ? `${metadata.video.streams[0].width} × ${metadata.video.streams[0].height}` : undefined} />
                                    <MetadataRow label="Codec" value={metadata.video.streams?.[0]?.codec_long_name} />
                                    <MetadataRow label="Format" value={metadata.video.format.format_long_name} />
                                    <MetadataRow label="Bitrate" value={metadata.video.format.bit_rate ? `${Math.round(parseInt(metadata.video.format.bit_rate) / 1000)} kbps` : undefined} />
                                    <MetadataRow label="Frame Rate" value={metadata.video.streams?.[0]?.r_frame_rate} />
                                    <MetadataRow label="Profile" value={metadata.video.streams?.[0]?.profile} />
                                    <MetadataRow label="Pixel Format" value={metadata.video.streams?.[0]?.pix_fmt} />
                                    <MetadataRow label="Color Space" value={metadata.video.streams?.[0]?.color_space} />
                                </MetadataSection>
                            )}
                            
                            {/* Video Tags (QuickTime/MP4 metadata) */}
                            {metadata.video?.format?.tags && (
                                <MetadataSection icon={Camera} title="Video Tags">
                                    <MetadataRow label="Device" value={metadata.video.format.tags['com.apple.quicktime.model'] || metadata.video.format.tags.encoder} />
                                    <MetadataRow label="Software" value={metadata.video.format.tags['com.apple.quicktime.software']} />
                                    <MetadataRow label="Creation Date" value={metadata.video.format.tags['com.apple.quicktime.creationdate'] || metadata.video.format.tags.creation_time?.split('T')[0]} />
                                </MetadataSection>
                            )}
                            
                            {/* Audio Properties */}
                            {metadata.audio && (
                                <MetadataSection icon={Music} title="Audio">
                                    <MetadataRow label="Duration" value={metadata.audio.length_human} />
                                    <MetadataRow label="Format" value={metadata.audio.format} />
                                    <MetadataRow label="Bitrate" value={metadata.audio.bitrate ? `${metadata.audio.bitrate} kbps` : undefined} />
                                    <MetadataRow label="Sample Rate" value={metadata.audio.sample_rate ? `${metadata.audio.sample_rate} Hz` : undefined} />
                                    <MetadataRow label="Channels" value={metadata.audio.channels} />
                                    <MetadataRow label="Bits/Sample" value={metadata.audio.bits_per_sample} />
                                </MetadataSection>
                            )}
                            
                            {/* Audio Tags */}
                            {metadata.audio?.tags && (
                                <MetadataSection icon={Music} title="Audio Tags">
                                    <MetadataRow label="Title" value={metadata.audio.tags.title} />
                                    <MetadataRow label="Artist" value={metadata.audio.tags.artist} />
                                    <MetadataRow label="Album" value={metadata.audio.tags.album} />
                                    <MetadataRow label="Year" value={metadata.audio.tags.year} />
                                    <MetadataRow label="Genre" value={metadata.audio.tags.genre} />
                                    <MetadataRow label="Track" value={metadata.audio.tags.track_number} />
                                    <MetadataRow label="Composer" value={metadata.audio.tags.composer} />
                                    <MetadataRow label="Album Art" value={metadata.audio.has_album_art ? 'Yes' : 'No'} />
                                </MetadataSection>
                            )}
                            
                            {/* PDF Properties */}
                            {metadata.pdf && (
                                <MetadataSection icon={FileText} title="PDF Document">
                                    <MetadataRow label="Pages" value={metadata.pdf.page_count} />
                                    <MetadataRow label="Title" value={metadata.pdf.title} />
                                    <MetadataRow label="Author" value={metadata.pdf.author} />
                                    <MetadataRow label="Creator" value={metadata.pdf.creator} />
                                    <MetadataRow label="Producer" value={metadata.pdf.producer} />
                                    <MetadataRow label="Subject" value={metadata.pdf.subject} />
                                    <MetadataRow label="Keywords" value={metadata.pdf.keywords} />
                                    <MetadataRow label="Encrypted" value={metadata.pdf.encrypted ? 'Yes' : 'No'} />
                                    <MetadataRow label="Page Size" value={metadata.pdf.page_width && metadata.pdf.page_height ? `${Math.round(metadata.pdf.page_width)} × ${Math.round(metadata.pdf.page_height)} pt` : undefined} />
                                </MetadataSection>
                            )}
                            
                            {/* SVG Properties */}
                            {metadata.svg && (
                                <MetadataSection icon={Code} title="SVG Vector">
                                    <MetadataRow label="Width" value={metadata.svg.width} />
                                    <MetadataRow label="Height" value={metadata.svg.height} />
                                    <MetadataRow label="ViewBox" value={metadata.svg.viewBox} />
                                    <MetadataRow label="Version" value={metadata.svg.version} />
                                    <MetadataRow label="Elements" value={metadata.svg.element_count} />
                                    <MetadataRow label="Paths" value={metadata.svg.path_count} />
                                    <MetadataRow label="Has Styles" value={metadata.svg.has_embedded_styles ? 'Yes' : 'No'} />
                                    <MetadataRow label="Has Scripts" value={metadata.svg.has_scripts ? 'Yes ⚠️' : 'No'} />
                                </MetadataSection>
                            )}
                            
                            {/* Calculated Stats */}
                            {calc && (
                                <MetadataSection icon={ImageIcon} title="Analysis">
                                    <MetadataRow label="Aspect Ratio" value={calc.aspect_ratio} />
                                    <MetadataRow label="Megapixels" value={calc.megapixels ? `${calc.megapixels} MP` : undefined} />
                                    <MetadataRow label="Orientation" value={calc.orientation} />
                                    <MetadataRow label="Size/Second" value={calc.size_per_second} />
                                </MetadataSection>
                            )}
                            
                            {/* Camera/EXIF */}
                            {exif.image && (
                                <MetadataSection icon={Camera} title="Camera">
                                    <MetadataRow label="Make" value={exif.image?.Make} />
                                    <MetadataRow label="Model" value={exif.image?.Model} />
                                    <MetadataRow label="Software" value={exif.image?.Software} />
                                    <MetadataRow label="Orientation" value={exif.image?.Orientation} />
                                </MetadataSection>
                            )}
                            
                            {exif.exif && (
                                <MetadataSection icon={Camera} title="Exposure">
                                    <MetadataRow label="ISO" value={exif.exif?.ISOSpeedRatings} />
                                    <MetadataRow label="Aperture" value={exif.exif?.FNumber} />
                                    <MetadataRow label="Shutter" value={exif.exif?.ExposureTime} />
                                    <MetadataRow label="Focal Length" value={exif.exif?.FocalLength} />
                                    <MetadataRow label="Flash" value={exif.exif?.Flash} />
                                    <MetadataRow label="Color Space" value={exif.exif?.ColorSpace} />
                                    <MetadataRow label="User Comment" value={exif.exif?.UserComment} />
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
                            <MetadataSection icon={HardDrive} title="Storage">
                                <MetadataRow label="Size" value={fs.size_human || formatBytes(fs.size_bytes)} />
                                <MetadataRow label="Created" value={fs.created?.split('T')[0]} />
                                <MetadataRow label="Modified" value={fs.modified?.split('T')[0]} />
                                <MetadataRow label="Accessed" value={fs.accessed?.split('T')[0]} />
                                <MetadataRow label="Owner" value={fs.owner} />
                                <MetadataRow label="Permissions" value={fs.permissions_human} />
                                <MetadataRow label="File Type" value={fs.file_type} />
                            </MetadataSection>
                            
                            {/* Hashes */}
                            {metadata.hashes && (
                                <MetadataSection icon={HardDrive} title="Hashes">
                                    <MetadataRow label="MD5" value={metadata.hashes.md5?.substring(0, 16) + '...'} />
                                    <MetadataRow label="SHA256" value={metadata.hashes.sha256?.substring(0, 16) + '...'} />
                                </MetadataSection>
                            )}
                            
                            {/* Thumbnail Info */}
                            {metadata.thumbnail?.has_embedded && (
                                <MetadataSection icon={ImageIcon} title="Thumbnail">
                                    <MetadataRow label="Embedded" value="Yes" />
                                    <MetadataRow label="Size" value={`${metadata.thumbnail.width} × ${metadata.thumbnail.height}`} />
                                </MetadataSection>
                            )}
                            
                            {/* Age */}
                            {calc.file_age && (
                                <MetadataSection icon={Calendar} title="Age">
                                    <MetadataRow label="File Age" value={calc.file_age.human_readable} />
                                    <MetadataRow label="Last Modified" value={calc.time_since_modified?.human_readable} />
                                </MetadataSection>
                            )}
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}

