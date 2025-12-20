import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Camera,
  MapPin,
  Calendar,
  HardDrive,
  Image as ImageIcon,
  ExternalLink,
  Copy,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Star,
  StarOff,
  FolderPlus,
  Hash,
  Trash2,
  Minus,
  Plus,
  RotateCw,
  FlipHorizontal,
  FlipVertical,
  Maximize2,
  Minimize2,
  Music,
  FileText,
  Code,
  HelpCircle,
  Edit3,
  UserCircle2,
} from 'lucide-react';
import SecureLazyImage from './SecureLazyImage';
import { type Photo, api } from '../../api';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';
import { createPortal } from 'react-dom';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import { AddToAlbumDialog } from '../albums/AddToAlbumDialog';
import { AddToTagDialog } from '../tags/AddToTagDialog';
import { StarRating } from '../rating/StarRating';
import { PhotoEditor } from '../editing/PhotoEditor';
import { NotesEditor } from '../notes/NotesEditor';
import { useToast } from '../ui/Toast';
import ImageAnalysis from './AIAnalysis';

interface PhotoDetailProps {
  photos: Photo[]; // Full list for navigation
  currentIndex: number | null; // Current photo index
  onNavigate: (index: number) => void;
  onClose: () => void;
}

// Minimal typing for metadata used in the detail view.
interface PhotoMetadata {
  file?: { name?: string; extension?: string; mime_type?: string };
  filesystem?: {
    size_bytes?: number;
    size_human?: string;
    created?: string;
    modified?: string;
    accessed?: string;
    owner?: string;
    permissions_human?: string;
    file_type?: string;
  };
  image?: {
    width?: number;
    height?: number;
    format?: string;
    mode?: string;
    dpi?: number[];
    bits_per_pixel?: number;
    animation?: boolean;
    frames?: number;
  };
  exif?: { image?: Record<string, unknown>; exif?: Record<string, unknown> };
  gps?: { latitude?: number; longitude?: number; altitude?: number };
  calculated?: {
    duration_human?: string;
    aspect_ratio?: string;
    megapixels?: number;
    orientation?: string;
    size_per_second?: string;
    file_age?: { human_readable?: string };
    time_since_modified?: { human_readable?: string };
  };
  video?: {
    format?: {
      duration?: string;
      format_long_name?: string;
      bit_rate?: string;
      tags?: Record<string, string>;
    };
    streams?: Array<Record<string, unknown>>;
  };
  audio?: {
    length_human?: string;
    format?: string;
    bitrate?: number;
    sample_rate?: number;
    channels?: number;
    bits_per_sample?: number;
    tags?: Record<string, unknown>;
    has_album_art?: boolean;
  };
  pdf?: {
    page_count?: number;
    title?: string;
    author?: string;
    creator?: string;
    producer?: string;
    subject?: string;
    keywords?: string;
    encrypted?: boolean;
    page_width?: number;
    page_height?: number;
  };
  svg?: {
    width?: number;
    height?: number;
    viewBox?: string;
    version?: string;
    element_count?: number;
    path_count?: number;
    has_embedded_styles?: boolean;
    has_scripts?: boolean;
  };
  thumbnail?: { has_embedded?: boolean; width?: number; height?: number };
  hashes?: { md5?: string; sha256?: string };
}

// Helper to format file size
function formatBytes(bytes: number): string {
  if (!bytes) return 'Unknown';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024;
    i++;
  }
  return `${bytes.toFixed(1)} ${units[i]}`;
}

// Metadata section component with collapsible header
function MetadataSection({
  icon: Icon,
  title,
  children,
  defaultOpen = false,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className='mb-3 glass-surface rounded-xl overflow-hidden'>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className='w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors text-left'
      >
        <div className='flex items-center gap-3'>
          <div className='glass-surface rounded-lg p-2'>
            <Icon size={14} className='text-primary/70' />
          </div>
          <span className='text-white/80 font-medium text-sm uppercase tracking-wider'>
            {title}
          </span>
        </div>
        <div 
          className='transition-transform duration-200'
          style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
          <ChevronDown size={16} className='text-white/50' />
        </div>
      </button>
      
      {isOpen && (
        <div className='px-3 pb-3 space-y-1 text-sm border-t border-white/5'>
          {children}
        </div>
      )}
    </div>
  );
}

function MetadataRow({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null || value === '') return null;

  let displayValue: string;
  if (typeof value === 'string') displayValue = value;
  else if (typeof value === 'number')
    displayValue = Number.isFinite(value) ? String(value) : 'Unknown';
  else if (typeof value === 'boolean') displayValue = value ? 'Yes' : 'No';
  else {
    try {
      displayValue = JSON.stringify(value);
    } catch {
      displayValue = String(value);
    }
  }

  return (
    <div className='flex justify-between items-start py-1.5 border-b border-white/5 last:border-0'>
      <span className='text-white/40 text-xs mt-0.5'>{label}</span>
      <span className='text-white/90 font-mono text-xs text-right max-w-[60%] break-words select-text'>
        {displayValue}
      </span>
    </div>
  );
}

export function PhotoDetail({
  photos,
  currentIndex,
  onNavigate,
  onClose,
}: PhotoDetailProps) {
  const photo = currentIndex !== null ? photos[currentIndex] : null;
  const { refresh } = usePhotoSearchContext();
  const { setOverrideAccentUrl, clearOverrideAccent } =
    useAmbientThemeContext();
  const [showExplanation, setShowExplanation] = useState(false);
  const [photoNote, setPhotoNote] = useState<string | null>(null);
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [rating, setRating] = useState(0);
  const [showEditor, setShowEditor] = useState(false);
  const [showAddToAlbum, setShowAddToAlbum] = useState(false);
  const [showAddToTag, setShowAddToTag] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [busy, setBusy] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [imageKey, setImageKey] = useState(0);
  const [photoTags, setPhotoTags] = useState<string[]>([]);
  const [tagsLoading, setTagsLoading] = useState(false);
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const [faceClusters, setFaceClusters] = useState<any[]>([]);
  const [isMetadataPanelVisible, setIsMetadataPanelVisible] = useState(true);
  const [facesLoading, setFacesLoading] = useState(false);
  const { showToast, ToastContainer } = useToast();

  useEffect(() => {
    let mounted = true;
    async function setAccent() {
      if (!photo) return;
      try {
        const url = await api.getSignedImageUrl(photo.path, 96);
        if (!mounted) return;
        setOverrideAccentUrl(
          'photoDetail',
          url || api.getImageUrl(photo.path, 96)
        );
      } catch {
        if (!mounted) return;
        setOverrideAccentUrl('photoDetail', api.getImageUrl(photo.path, 96));
      }
    }

    if (photo) {
      setAccent();
    } else {
      clearOverrideAccent('photoDetail');
    }

    return () => {
      mounted = false;
      clearOverrideAccent('photoDetail');
    };
  }, [photo, setOverrideAccentUrl, clearOverrideAccent]);

  useEffect(() => {
    if (!photo) return;
    setZoom(1);
    setRotation(0);
    setFlipH(false);
    setFlipV(false);
    setShowAddToAlbum(false);
    setShowAddToTag(false);
    setFavoriteLoading(true);
    api
      .checkFavorite(photo.path)
      .then((res) => setIsFavorited(Boolean(res.is_favorited)))
      .catch(() => setIsFavorited(false))
      .finally(() => setFavoriteLoading(false));

    // Load rating
    api
      .getPhotoRating(photo.path)
      .then(setRating)
      .catch(() => setRating(0));

    // Load note
    api
      .getPhotoNote(photo.path)
      .then((res) => setPhotoNote(res.note))
      .catch(() => setPhotoNote(null));

    setTagsLoading(true);
    api
      .getPhotoTags(photo.path)
      .then((res) => setPhotoTags(res.tags || []))
      .catch(() => setPhotoTags([]))
      .finally(() => setTagsLoading(false));
  }, [photo]);

  const refreshFaces = async () => {
    if (!photo) return;
    setFacesLoading(true);
    try {
      const res = await api.getFacesForImage(photo.path);
      const clustersRoot = (res && res.clusters) || res;
      const normalized = Array.isArray(clustersRoot?.clusters)
        ? clustersRoot.clusters
        : Array.isArray(clustersRoot)
        ? clustersRoot
        : Array.isArray(clustersRoot?.clusters?.clusters)
        ? clustersRoot.clusters.clusters
        : [];
      setFaceClusters(normalized || []);
    } catch {
      setFaceClusters([]);
    } finally {
      setFacesLoading(false);
    }
  };

  useEffect(() => {
    if (!photo) {
      setFaceClusters([]);
      return;
    }
    refreshFaces();
  }, [photo]);
  const refreshTags = async () => {
    if (!photo) return;
    setTagsLoading(true);
    try {
      const res = await api.getPhotoTags(photo.path);
      setPhotoTags(res.tags || []);
    } catch {
      setPhotoTags([]);
    } finally {
      setTagsLoading(false);
    }
  };

  useEffect(() => {
    const onFsChange = () =>
      setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    if (currentIndex === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showExplanation) {
          setShowExplanation(false);
        } else {
          onClose();
        }
      } else if (
        e.key === 'ArrowLeft' &&
        currentIndex > 0 &&
        !showExplanation
      ) {
        onNavigate(currentIndex - 1);
      } else if (
        e.key === 'ArrowRight' &&
        currentIndex < photos.length - 1 &&
        !showExplanation
      ) {
        onNavigate(currentIndex + 1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex, photos.length, onNavigate, onClose, showExplanation]);

  if (!photo) return null;

  // Extract metadata from photo object
  const metadata = (photo.metadata || {}) as PhotoMetadata;
  const fs = metadata.filesystem || {};
  const img = metadata.image || {};
  const exif = metadata.exif || {};
  const gps = metadata.gps || {};
  const calc = metadata.calculated || {};
  const hasAnyMetadata =
    Boolean(metadata.file) ||
    Boolean(metadata.filesystem) ||
    Boolean(metadata.image && Object.keys(metadata.image).length > 0) ||
    Boolean(metadata.video) ||
    Boolean(metadata.audio) ||
    Boolean(metadata.pdf) ||
    Boolean(metadata.svg) ||
    Boolean(metadata.exif) ||
    Boolean(metadata.hashes) ||
    Boolean(metadata.gps);

  const originalOpenUrl = api.isVideo(photo.path)
    ? api.getVideoUrl(photo.path)
    : api.getFileUrl(photo.path);
  const originalDownloadUrl = api.getFileUrl(photo.path, { download: true });
  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(photo.path);
      showToast('Path copied to clipboard ✓', 'success');
    } catch {
      showToast('Failed to copy path', 'error');
    }
  };

  const hasPrev = currentIndex !== null && currentIndex > 0;
  const hasNext = currentIndex !== null && currentIndex < photos.length - 1;

  const toggleFavorite = async () => {
    if (!photo || favoriteLoading || busy) return;
    setFavoriteLoading(true);
    try {
      const res = await api.toggleFavorite(photo.path);
      setIsFavorited(Boolean(res.is_favorited));
      showToast(
        res.is_favorited ? 'Added to favorites ✓' : 'Removed from favorites',
        'success'
      );
    } catch {
      showToast('Failed to update favorite status', 'error');
    } finally {
      setFavoriteLoading(false);
    }
  };

  const moveToTrash = async () => {
    if (!photo || busy) return;
    const ok = window.confirm(
      `Move "${photo.filename}" to Trash? You can restore it from Trash.`
    );
    if (!ok) return;
    setBusy(true);
    try {
      await api.trashMove([photo.path]);
      onClose();
      refresh();
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  };

  const removeFromLibrary = async () => {
    if (!photo || busy) return;
    const ok = window.confirm(
      `Remove "${photo.filename}" from the library index? This does not use Trash.`
    );
    if (!ok) return;
    setBusy(true);
    try {
      await api.removeFromLibrary([photo.path]);
      onClose();
      refresh();
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  };

  const rotateImage = async () => {
    if (!photo || busy) return;
    setBusy(true);
    try {
      await api.rotatePhoto(photo.path, 90, true);
      // Force image refresh to show the rotated version
      setImageKey((prev) => prev + 1);
      refresh();
    } catch (error) {
      console.error('Failed to rotate image:', error);
      alert('Failed to rotate image. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const flipImage = async (direction: 'horizontal' | 'vertical') => {
    if (!photo || busy) return;
    setBusy(true);
    try {
      await api.flipPhoto(photo.path, direction, true);
      // Force image refresh to show the flipped version
      setImageKey((prev) => prev + 1);
      refresh();
    } catch (error) {
      console.error('Failed to flip image:', error);
      alert('Failed to flip image. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const rotateRight = () => setRotation((r) => (r + 90) % 360);
  const zoomIn = () =>
    setZoom((z) => Math.min(4, Math.round((z + 0.25) * 100) / 100));
  const zoomOut = () =>
    setZoom((z) => Math.max(1, Math.round((z - 0.25) * 100) / 100));
  const resetView = () => {
    setZoom(1);
    setRotation(0);
    setFlipH(false);
    setFlipV(false);
  };

  const flipHorizontal = () => setFlipH((h) => !h);
  const flipVertical = () => setFlipV((v) => !v);

  const toggleFullscreen = async () => {
    const el = viewerRef.current;
    if (!el) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await el.requestFullscreen();
      }
    } catch {
      // ignore
    }
  };

  return (
    <>
      <AnimatePresence>
        {photo && (
          <div className='fixed inset-0 z-[100] flex items-center justify-center p-4'>
            <motion.div
              onClick={onClose}
              className='absolute inset-0 bg-black/70 backdrop-blur-md'
            />

            <motion.div
              layoutId={`photo-${photo.path}`}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className='relative z-10 max-w-6xl w-full max-h-[95vh] flex gap-4 md:gap-6'
              onClick={(e) => e.stopPropagation()}
            >
              {/* Mac-style traffic light buttons */}
              <div className='absolute top-4 left-4 z-30 flex items-center gap-2 group/traffic-lights'>
                <button
                  onClick={onClose}
                  className='w-3 h-3 rounded-full bg-red-500 hover:bg-red-600 transition-colors flex items-center justify-center group relative'
                  aria-label='Close photo detail'
                >
                  <X size={8} className='text-red-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                  <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none'>
                    Close
                  </span>
                </button>
                <button
                  onClick={() => setIsMetadataPanelVisible(!isMetadataPanelVisible)}
                  className='w-3 h-3 rounded-full bg-yellow-500 hover:bg-yellow-600 transition-colors flex items-center justify-center group relative'
                  aria-label={isMetadataPanelVisible ? 'Hide metadata panel' : 'Show metadata panel'}
                >
                  <Minus size={8} className='text-yellow-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                  <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none'>
                    {isMetadataPanelVisible ? 'Hide Info' : 'Show Info'}
                  </span>
                </button>
                <button
                  onClick={toggleFullscreen}
                  disabled={busy}
                  className='w-3 h-3 rounded-full bg-green-500 hover:bg-green-600 transition-colors flex items-center justify-center group relative'
                  aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                >
                  {isFullscreen ? (
                    <Minimize2 size={8} className='text-green-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                  ) : (
                    <Maximize2 size={8} className='text-green-900 opacity-0 group-hover:opacity-100 transition-opacity' />
                  )}
                  <span className='absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 bg-black/90 text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none'>
                    {isFullscreen ? 'Exit Full' : 'Fullscreen'}
                  </span>
                </button>
              </div>

              {/* Navigation - Previous */}
              {hasPrev && (
                <button
                  onClick={() => onNavigate(currentIndex! - 1)}
                  className='absolute left-4 top-1/2 -translate-y-1/2 z-20 btn-glass btn-glass--muted w-12 h-12 p-0 justify-center text-white/80'
                  title='Previous photo'
                  aria-label='Previous photo'
                >
                  <ChevronLeft size={24} />
                </button>
              )}

              {/* Navigation - Next */}
              {hasNext && (
                <button
                  onClick={() => onNavigate(currentIndex! + 1)}
                  className='absolute right-[22rem] top-1/2 -translate-y-1/2 z-20 btn-glass btn-glass--muted w-12 h-12 p-0 justify-center text-white/80'
                  title='Next photo'
                  aria-label='Next photo'
                >
                  <ChevronRight size={24} />
                </button>
              )}

              {/* Image or Video */}
              <div
                ref={viewerRef}
                className='flex-1 flex items-center justify-center rounded-2xl overflow-auto glass-surface'
              >
                {api.isVideo(photo.path) ? (
                  <video
                    src={api.getVideoUrl(photo.path)}
                    controls
                    autoPlay
                    className='max-h-[85vh] w-auto object-contain'
                  />
                ) : (
                  <div
                    className='max-h-[85vh] w-auto object-contain'
                    style={{
                      transform: `scale(${zoom}) rotate(${rotation}deg) scaleX(${
                        flipH ? -1 : 1
                      }) scaleY(${flipV ? -1 : 1})`,
                      transformOrigin: 'center',
                      transition: 'transform 120ms ease',
                    }}
                  >
                    <SecureLazyImage
                      key={imageKey}
                      path={photo.path}
                      size={1200}
                      alt={photo.filename}
                    />
                  </div>
                )}
              </div>

              {/* Metadata Panel */}
              {isMetadataPanelVisible && (
                <div className='w-80 glass-surface rounded-2xl p-5 overflow-y-auto max-h-[85vh]'>
                <h3 className='text-white text-lg font-semibold mb-1 truncate'>
                  {photo.filename}
                </h3>
                <div className='mb-6'>
                  <div className='flex items-center gap-2 group'>
                    <div className='flex-1 overflow-hidden'>
                      <p className='text-white/40 text-xs select-text whitespace-nowrap transition-transform duration-2000 ease-linear group-hover:animate-scroll-text'>
                        <a
                          href={originalOpenUrl}
                          target='_blank'
                          rel='noopener noreferrer'
                          className='hover:text-white/70 hover:underline underline-offset-4 cursor-pointer'
                          onClick={(e) => {
                            const sel = window.getSelection?.()?.toString() ?? '';
                            if (sel.trim().length > 0) e.preventDefault();
                          }}
                          title='Open original in new tab'
                        >
                          {photo.path}
                        </a>
                      </p>
                    </div>
                    {/* Desktop: Hover-revealed copy icon */}
                    <button
                      onClick={copyPath}
                      className='hidden md:flex opacity-0 group-hover:opacity-100 transition-opacity btn-glass btn-glass--muted w-6 h-6 p-0 justify-center flex-shrink-0'
                      title='Copy file path'
                      aria-label='Copy file path'
                    >
                      <Copy size={12} />
                    </button>
                    {/* Mobile: Always visible copy icon */}
                    <button
                      onClick={copyPath}
                      className='md:hidden btn-glass btn-glass--muted w-8 h-8 p-0 justify-center flex-shrink-0'
                      title='Copy file path'
                      aria-label='Copy file path'
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                  <div className='mt-2 flex items-center gap-2 flex-wrap'>
                    <a
                      href={originalOpenUrl}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='btn-glass btn-glass--muted text-xs px-3 py-2'
                      title='Open original in new tab'
                      aria-label='Open original in new tab'
                    >
                      <ExternalLink size={14} />
                      Open
                    </a>
                    <button
                      onClick={toggleFavorite}
                      disabled={favoriteLoading || busy}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2'
                      title={isFavorited ? 'Unfavorite' : 'Favorite'}
                      aria-label={isFavorited ? 'Unfavorite' : 'Favorite'}
                    >
                      {isFavorited ? <StarOff size={14} /> : <Star size={14} />}
                      {isFavorited ? 'Unfavorite' : 'Favorite'}
                    </button>
                  </div>

                  <div className='mt-3 grid grid-cols-2 gap-2'>
                    <button
                      onClick={() => setShowAddToAlbum(true)}
                      disabled={busy}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Add to album'
                    >
                      <FolderPlus size={14} />
                      Album
                    </button>
                    <button
                      onClick={() => setShowEditor(true)}
                      disabled={busy || api.isVideo(photo.path)}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Edit photo'
                    >
                      <Edit3 size={14} />
                      Edit
                    </button>
                    <button
                      onClick={() => setShowAddToTag(true)}
                      disabled={busy}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Add tags'
                    >
                      <Hash size={14} />
                      Tags
                    </button>
                    <button
                      onClick={rotateImage}
                      disabled={busy || api.isVideo(photo.path)}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Rotate image 90° clockwise'
                    >
                      <RotateCw size={14} />
                      Rotate
                    </button>
                    <button
                      onClick={() => flipImage('horizontal')}
                      disabled={busy || api.isVideo(photo.path)}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Flip image horizontally'
                    >
                      <FlipHorizontal size={14} />
                      Flip H
                    </button>
                    <button
                      onClick={() => flipImage('vertical')}
                      disabled={busy || api.isVideo(photo.path)}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Flip image vertically'
                    >
                      <FlipVertical size={14} />
                      Flip V
                    </button>
                    <button
                      onClick={moveToTrash}
                      disabled={busy}
                      className='btn-glass btn-glass--danger text-xs px-3 py-2 justify-center'
                      title='Move to Trash'
                    >
                      <Trash2 size={14} />
                      Trash
                    </button>
                    <button
                      onClick={removeFromLibrary}
                      disabled={busy}
                      className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                      title='Remove from library'
                    >
                      <Trash2 size={14} />
                      Remove
                    </button>
                  </div>

                  {/* Rating Section */}
                  <div className='mt-3 glass-surface rounded-xl p-3'>
                    <div className='flex items-center justify-between gap-2'>
                      <div className='text-xs uppercase tracking-wider text-white/60 flex items-center gap-2'>
                        <Star size={12} />
                        Rating
                      </div>
                      <StarRating
                        photoPath={photo.path}
                        initialRating={rating}
                        size='sm'
                        showLabel={true}
                      />
                    </div>
                  </div>

                  {/* Notes */}
                  <div className='mt-3'>
                    <NotesEditor
                      photoPath={photo.path}
                      initialNote={photoNote || ''}
                      size='md'
                      showLabel={true}
                    />
                  </div>

                  {(tagsLoading ||
                    photoTags.length > 0 ||
                    facesLoading ||
                    faceClusters.length > 0) && (
                    <div className='mt-3 glass-surface rounded-xl p-3 space-y-3'>
                      {(tagsLoading || photoTags.length > 0) && (
                        <div>
                          <div className='flex items-center justify-between gap-2 mb-2'>
                            <div className='text-xs uppercase tracking-wider text-white/60 flex items-center gap-2'>
                              <Hash size={12} />
                              Tags
                            </div>
                            <button
                              className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center'
                              onClick={refreshTags}
                              disabled={busy || tagsLoading}
                              title='Refresh tags'
                              aria-label='Refresh tags'
                            >
                              <RotateCw size={14} />
                            </button>
                          </div>
                          {tagsLoading ? (
                            <div className='text-xs text-white/50'>
                              Loading…
                            </div>
                          ) : (
                            <div className='flex flex-wrap gap-2'>
                              {photoTags.map((t) => (
                                <div
                                  key={t}
                                  className='flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1'
                                >
                                  <span className='text-xs text-white/85'>
                                    #{t}
                                  </span>
                                  <button
                                    className='btn-glass btn-glass--muted w-7 h-7 p-0 justify-center'
                                    title='Remove tag'
                                    aria-label='Remove tag'
                                    disabled={busy}
                                    onClick={async () => {
                                      if (!photo) return;
                                      setBusy(true);
                                      try {
                                        await api.removePhotosFromTag(t, [
                                          photo.path,
                                        ]);
                                        await refreshTags();
                                      } finally {
                                        setBusy(false);
                                      }
                                    }}
                                  >
                                    <X size={12} />
                                  </button>
                                </div>
                              ))}
                              {photoTags.length === 0 && (
                                <div className='text-xs text-white/50'>
                                  No tags yet.
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {(facesLoading || faceClusters.length > 0) && (
                        <div>
                          <div className='flex items-center justify-between gap-2 mb-2'>
                            <div className='text-xs uppercase tracking-wider text-white/60 flex items-center gap-2'>
                              <UserCircle2 size={12} />
                              People
                            </div>
                            <button
                              className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center'
                              onClick={refreshFaces}
                              disabled={busy || facesLoading}
                              title='Refresh faces'
                              aria-label='Refresh faces'
                            >
                              <RotateCw size={14} />
                            </button>
                          </div>
                          {facesLoading ? (
                            <div className='text-xs text-white/50'>
                              Scanning…
                            </div>
                          ) : faceClusters.length === 0 ? (
                            <div className='text-xs text-white/50'>
                              No faces detected.
                            </div>
                          ) : (
                            <div className='flex flex-wrap gap-2'>
                              {faceClusters.map((c, idx) => (
                                <div
                                  key={c.id || idx}
                                  className='flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-2 py-1'
                                >
                                  <span className='text-xs text-white/85'>
                                    {c.label ||
                                      c.cluster_label ||
                                      `Person ${c.id || idx + 1}`}
                                  </span>
                                  {typeof c.face_count === 'number' && (
                                    <span className='text-[10px] text-white/60'>
                                      {c.face_count} face
                                      {c.face_count === 1 ? '' : 's'}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {!api.isVideo(photo.path) && (
                    <div className='mt-3 space-y-2'>
                      <div className='grid grid-cols-3 gap-2'>
                        <button
                          onClick={zoomOut}
                          disabled={busy || zoom <= 1}
                          className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                          title='Zoom out'
                        >
                          <Minus size={14} />
                        </button>
                        <button
                          onClick={resetView}
                          disabled={
                            busy ||
                            (zoom === 1 && rotation === 0 && !flipH && !flipV)
                          }
                          className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                          title='Reset view'
                        >
                          {Math.round(zoom * 100)}%
                        </button>
                        <button
                          onClick={zoomIn}
                          disabled={busy || zoom >= 4}
                          className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                          title='Zoom in'
                        >
                          <Plus size={14} />
                        </button>
                        <button
                          onClick={rotateRight}
                          disabled={busy}
                          className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                          title='Rotate right 90°'
                        >
                          <RotateCw size={14} />
                          Rotate
                        </button>
                      </div>
                      <div className='grid grid-cols-3 gap-2'>
                        <button
                          onClick={flipHorizontal}
                          disabled={busy}
                          className={`btn-glass ${
                            flipH ? 'btn-glass--primary' : 'btn-glass--muted'
                          } text-xs px-3 py-2 justify-center`}
                          title='Flip horizontally'
                        >
                          <FlipHorizontal size={14} />
                          Flip H
                        </button>
                        <button
                          onClick={flipVertical}
                          disabled={busy}
                          className={`btn-glass ${
                            flipV ? 'btn-glass--primary' : 'btn-glass--muted'
                          } text-xs px-3 py-2 justify-center`}
                          title='Flip vertically'
                        >
                          <FlipVertical size={14} />
                          Flip V
                        </button>
                        <button
                          onClick={toggleFullscreen}
                          disabled={busy}
                          className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center'
                          title={
                            isFullscreen ? 'Exit fullscreen' : 'Fullscreen'
                          }
                        >
                          {isFullscreen ? (
                            <Minimize2 size={14} />
                          ) : (
                            <Maximize2 size={14} />
                          )}
                          {isFullscreen ? ' Exit' : ' Full'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Score if semantic search */}
                {photo.score !== undefined && photo.score > 0 && (
                  <div className='mb-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
                    <div className='flex items-center justify-between'>
                      <div>
                        <span className='text-blue-400 text-sm'>
                          Relevance Score:{' '}
                        </span>
                        <span className='text-white font-bold'>
                          {(photo.score * 100).toFixed(0)}%
                        </span>
                      </div>
                      {photo.matchExplanation && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowExplanation(true);
                          }}
                          className='btn-glass btn-glass--muted px-2 py-1 text-xs flex items-center gap-1'
                          title='Why this matched'
                        >
                          <HelpCircle size={12} />
                          Why
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {!hasAnyMetadata && (
                  <div className='mb-4 p-3 bg-white/5 border border-white/10 rounded-lg text-sm text-white/70'>
                    No metadata indexed for this file yet. Run{' '}
                    <span className='text-white/90'>
                      Spotlight → Scan Library
                    </span>{' '}
                    to extract metadata and enable richer search/filters.
                  </div>
                )}

                {/* Image Analysis Section */}
                <ImageAnalysis photo={photo} isOpen={currentIndex !== null} />

                {/* Download Button */}
                <a
                  href={originalDownloadUrl}
                  download={photo.filename}
                  className='w-full mb-4 btn-glass btn-glass--primary px-4 py-2.5 text-sm font-semibold flex items-center justify-center gap-2'
                >
                  <HardDrive size={16} />
                  Download Original
                </a>

                {/* File Info */}
                {metadata.file && (
                  <MetadataSection
                    icon={HardDrive}
                    title='File Info'
                    defaultOpen={true}
                  >
                    <MetadataRow label='Name' value={metadata.file.name} />
                    <MetadataRow
                      label='Extension'
                      value={metadata.file.extension}
                    />
                    <MetadataRow
                      label='MIME Type'
                      value={metadata.file.mime_type}
                    />
                  </MetadataSection>
                )}

                {/* Image Properties */}
                {img.width && (
                  <MetadataSection
                    icon={ImageIcon}
                    title='Image'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Dimensions'
                      value={`${img.width} × ${img.height}`}
                    />
                    <MetadataRow label='Format' value={img.format} />
                    <MetadataRow label='Mode' value={img.mode} />
                    <MetadataRow label='DPI' value={img.dpi?.join(' × ')} />
                    <MetadataRow
                      label='Bits/Pixel'
                      value={img.bits_per_pixel}
                    />
                    <MetadataRow
                      label='Has Animation'
                      value={img.animation ? 'Yes' : 'No'}
                    />
                    <MetadataRow label='Frames' value={img.frames} />
                  </MetadataSection>
                )}

                {/* Video Properties */}
                {metadata.video?.format && (
                  <MetadataSection
                    icon={Camera}
                    title='Video'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Duration'
                      value={
                        calc.duration_human ||
                        (metadata.video?.format?.duration
                          ? `${Math.round(
                              parseFloat(metadata.video.format.duration)
                            )}s`
                          : undefined)
                      }
                    />
                    <MetadataRow
                      label='Resolution'
                      value={
                        metadata.video.streams?.[0]
                          ? `${metadata.video.streams[0].width} × ${metadata.video.streams[0].height}`
                          : undefined
                      }
                    />
                    <MetadataRow
                      label='Codec'
                      value={metadata.video.streams?.[0]?.codec_long_name}
                    />
                    <MetadataRow
                      label='Format'
                      value={metadata.video.format.format_long_name}
                    />
                    <MetadataRow
                      label='Bitrate'
                      value={
                        metadata.video.format.bit_rate
                          ? `${Math.round(
                              parseInt(metadata.video.format.bit_rate) / 1000
                            )} kbps`
                          : undefined
                      }
                    />
                    <MetadataRow
                      label='Frame Rate'
                      value={metadata.video.streams?.[0]?.r_frame_rate}
                    />
                    <MetadataRow
                      label='Profile'
                      value={metadata.video.streams?.[0]?.profile}
                    />
                    <MetadataRow
                      label='Pixel Format'
                      value={metadata.video.streams?.[0]?.pix_fmt}
                    />
                    <MetadataRow
                      label='Color Space'
                      value={metadata.video.streams?.[0]?.color_space}
                    />
                  </MetadataSection>
                )}

                {/* Video Tags (QuickTime/MP4 metadata) */}
                {metadata.video?.format?.tags && (
                  <MetadataSection icon={Camera} title='Video Tags'>
                    <MetadataRow
                      label='Device'
                      value={
                        metadata.video.format.tags[
                          'com.apple.quicktime.model'
                        ] || metadata.video.format.tags.encoder
                      }
                    />
                    <MetadataRow
                      label='Software'
                      value={
                        metadata.video.format.tags[
                          'com.apple.quicktime.software'
                        ]
                      }
                    />
                    <MetadataRow
                      label='Creation Date'
                      value={
                        metadata.video.format.tags[
                          'com.apple.quicktime.creationdate'
                        ] ||
                        metadata.video.format.tags.creation_time?.split('T')[0]
                      }
                    />
                  </MetadataSection>
                )}

                {/* Audio Properties */}
                {metadata.audio && (
                  <MetadataSection
                    icon={Music}
                    title='Audio'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Duration'
                      value={metadata.audio.length_human}
                    />
                    <MetadataRow label='Format' value={metadata.audio.format} />
                    <MetadataRow
                      label='Bitrate'
                      value={
                        metadata.audio.bitrate
                          ? `${metadata.audio.bitrate} kbps`
                          : undefined
                      }
                    />
                    <MetadataRow
                      label='Sample Rate'
                      value={
                        metadata.audio.sample_rate
                          ? `${metadata.audio.sample_rate} Hz`
                          : undefined
                      }
                    />
                    <MetadataRow
                      label='Channels'
                      value={metadata.audio.channels}
                    />
                    <MetadataRow
                      label='Bits/Sample'
                      value={metadata.audio.bits_per_sample}
                    />
                  </MetadataSection>
                )}

                {/* Audio Tags */}
                {metadata.audio?.tags && (
                  <MetadataSection
                    icon={Music}
                    title='Audio Tags'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Title'
                      value={metadata.audio.tags.title}
                    />
                    <MetadataRow
                      label='Artist'
                      value={metadata.audio.tags.artist}
                    />
                    <MetadataRow
                      label='Album'
                      value={metadata.audio.tags.album}
                    />
                    <MetadataRow
                      label='Year'
                      value={metadata.audio.tags.year}
                    />
                    <MetadataRow
                      label='Genre'
                      value={metadata.audio.tags.genre}
                    />
                    <MetadataRow
                      label='Track'
                      value={metadata.audio.tags.track_number}
                    />
                    <MetadataRow
                      label='Composer'
                      value={metadata.audio.tags.composer}
                    />
                    <MetadataRow
                      label='Album Art'
                      value={metadata.audio.has_album_art ? 'Yes' : 'No'}
                    />
                  </MetadataSection>
                )}

                {/* PDF Properties */}
                {metadata.pdf && (
                  <MetadataSection
                    icon={FileText}
                    title='PDF Document'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Pages'
                      value={metadata.pdf.page_count}
                    />
                    <MetadataRow label='Title' value={metadata.pdf.title} />
                    <MetadataRow label='Author' value={metadata.pdf.author} />
                    <MetadataRow label='Creator' value={metadata.pdf.creator} />
                    <MetadataRow
                      label='Producer'
                      value={metadata.pdf.producer}
                    />
                    <MetadataRow label='Subject' value={metadata.pdf.subject} />
                    <MetadataRow
                      label='Keywords'
                      value={metadata.pdf.keywords}
                    />
                    <MetadataRow
                      label='Encrypted'
                      value={metadata.pdf.encrypted ? 'Yes' : 'No'}
                    />
                    <MetadataRow
                      label='Page Size'
                      value={
                        metadata.pdf.page_width && metadata.pdf.page_height
                          ? `${Math.round(
                              metadata.pdf.page_width
                            )} × ${Math.round(metadata.pdf.page_height)} pt`
                          : undefined
                      }
                    />
                  </MetadataSection>
                )}

                {/* SVG Properties */}
                {metadata.svg && (
                  <MetadataSection
                    icon={Code}
                    title='SVG Vector'
                    defaultOpen={true}
                  >
                    <MetadataRow label='Width' value={metadata.svg.width} />
                    <MetadataRow label='Height' value={metadata.svg.height} />
                    <MetadataRow label='ViewBox' value={metadata.svg.viewBox} />
                    <MetadataRow label='Version' value={metadata.svg.version} />
                    <MetadataRow
                      label='Elements'
                      value={metadata.svg.element_count}
                    />
                    <MetadataRow
                      label='Paths'
                      value={metadata.svg.path_count}
                    />
                    <MetadataRow
                      label='Has Styles'
                      value={metadata.svg.has_embedded_styles ? 'Yes' : 'No'}
                    />
                    <MetadataRow
                      label='Has Scripts'
                      value={metadata.svg.has_scripts ? 'Yes ⚠️' : 'No'}
                    />
                  </MetadataSection>
                )}

                {/* Calculated Stats */}
                {calc && (
                  <MetadataSection icon={ImageIcon} title='Analysis'>
                    <MetadataRow
                      label='Aspect Ratio'
                      value={calc.aspect_ratio}
                    />
                    <MetadataRow
                      label='Megapixels'
                      value={
                        calc.megapixels ? `${calc.megapixels} MP` : undefined
                      }
                    />
                    <MetadataRow label='Orientation' value={calc.orientation} />
                    <MetadataRow
                      label='Size/Second'
                      value={calc.size_per_second}
                    />
                  </MetadataSection>
                )}

                {/* Camera/EXIF */}
                {exif.image && (
                  <MetadataSection icon={Camera} title='Camera'>
                    <MetadataRow label='Make' value={exif.image?.Make} />
                    <MetadataRow label='Model' value={exif.image?.Model} />
                    <MetadataRow
                      label='Software'
                      value={exif.image?.Software}
                    />
                    <MetadataRow
                      label='Orientation'
                      value={exif.image?.Orientation}
                    />
                  </MetadataSection>
                )}

                {exif.exif && (
                  <MetadataSection icon={Camera} title='Exposure'>
                    <MetadataRow
                      label='ISO'
                      value={exif.exif?.ISOSpeedRatings}
                    />
                    <MetadataRow label='Aperture' value={exif.exif?.FNumber} />
                    <MetadataRow
                      label='Shutter'
                      value={exif.exif?.ExposureTime}
                    />
                    <MetadataRow
                      label='Focal Length'
                      value={exif.exif?.FocalLength}
                    />
                    <MetadataRow label='Flash' value={exif.exif?.Flash} />
                    <MetadataRow
                      label='Color Space'
                      value={exif.exif?.ColorSpace}
                    />
                    <MetadataRow
                      label='User Comment'
                      value={exif.exif?.UserComment}
                    />
                  </MetadataSection>
                )}

                {/* GPS */}
                {(gps.latitude || gps.longitude) && (
                  <MetadataSection
                    icon={MapPin}
                    title='Location'
                    defaultOpen={true}
                  >
                    <MetadataRow
                      label='Latitude'
                      value={gps.latitude?.toFixed(6)}
                    />
                    <MetadataRow
                      label='Longitude'
                      value={gps.longitude?.toFixed(6)}
                    />
                    <MetadataRow
                      label='Altitude'
                      value={gps.altitude ? `${gps.altitude}m` : undefined}
                    />
                  </MetadataSection>
                )}

                {/* File System */}
                <MetadataSection icon={HardDrive} title='Storage'>
                  <MetadataRow
                    label='Size'
                    value={fs.size_human || formatBytes(fs.size_bytes ?? 0)}
                  />
                  <MetadataRow
                    label='Created'
                    value={fs.created?.split('T')[0]}
                  />
                  <MetadataRow
                    label='Modified'
                    value={fs.modified?.split('T')[0]}
                  />
                  <MetadataRow
                    label='Accessed'
                    value={fs.accessed?.split('T')[0]}
                  />
                  <MetadataRow label='Owner' value={fs.owner} />
                  <MetadataRow
                    label='Permissions'
                    value={fs.permissions_human}
                  />
                  <MetadataRow label='File Type' value={fs.file_type} />
                </MetadataSection>

                {/* Hashes */}
                {metadata.hashes && (
                  <MetadataSection icon={HardDrive} title='Hashes'>
                    <MetadataRow
                      label='MD5'
                      value={metadata.hashes.md5?.substring(0, 16) + '...'}
                    />
                    <MetadataRow
                      label='SHA256'
                      value={metadata.hashes.sha256?.substring(0, 16) + '...'}
                    />
                  </MetadataSection>
                )}

                {/* Thumbnail Info */}
                {metadata.thumbnail?.has_embedded && (
                  <MetadataSection icon={ImageIcon} title='Thumbnail'>
                    <MetadataRow label='Embedded' value='Yes' />
                    <MetadataRow
                      label='Size'
                      value={`${metadata.thumbnail.width} × ${metadata.thumbnail.height}`}
                    />
                  </MetadataSection>
                )}

                {/* Age */}
                {calc.file_age && (
                  <MetadataSection icon={Calendar} title='Age'>
                    <MetadataRow
                      label='File Age'
                      value={calc.file_age.human_readable}
                    />
                    <MetadataRow
                      label='Last Modified'
                      value={calc.time_since_modified?.human_readable}
                    />
                  </MetadataSection>
                )}
              </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AddToAlbumDialog
        isOpen={showAddToAlbum}
        photoPaths={[photo.path]}
        onClose={() => setShowAddToAlbum(false)}
        onSuccess={() => setShowAddToAlbum(false)}
      />

      <AddToTagDialog
        isOpen={showAddToTag}
        photoPaths={[photo.path]}
        onClose={() => setShowAddToTag(false)}
        onSuccess={async () => {
          setShowAddToTag(false);
          await refreshTags();
        }}
      />

      {/* Match Explanation Modal */}
      {showExplanation &&
        photo?.matchExplanation &&
        createPortal(
          <div
            className='fixed inset-0 z-[9999] flex items-center justify-center p-4'
            style={{ pointerEvents: 'auto' }}
          >
            {/* Backdrop */}
            <div
              className='absolute inset-0 bg-black/70 backdrop-blur-sm'
              onClick={() => setShowExplanation(false)}
            />
            {/* Modal */}
            <div
              className='relative w-full max-w-lg glass-surface glass-surface--strong rounded-2xl shadow-2xl p-6 max-h-[80vh] overflow-y-auto'
              onClick={(e) => e.stopPropagation()}
            >
              <div className='flex items-center justify-between mb-4'>
                <div className='flex items-center gap-2'>
                  <div
                    className={`w-3 h-3 rounded-full ${
                      photo.matchExplanation.type === 'metadata'
                        ? 'bg-blue-500'
                        : photo.matchExplanation.type === 'semantic'
                        ? 'bg-purple-500'
                        : 'bg-gradient-to-r from-blue-500 to-purple-500'
                    }`}
                  />
                  <h3 className='text-lg font-bold text-white/95'>
                    Why this matched
                  </h3>
                </div>
                <button
                  onClick={() => setShowExplanation(false)}
                  className='btn-glass p-2 rounded-lg hover:bg-white/20'
                >
                  <X size={14} className='text-white/80' />
                </button>
              </div>

              <div className='space-y-2'>
                {photo.matchExplanation.reasons &&
                photo.matchExplanation.reasons.length > 0 ? (
                  photo.matchExplanation.reasons.map((reason, idx) => {
                    const Icon =
                      reason.category.toLowerCase().includes('camera') ||
                      reason.category.toLowerCase().includes('lens')
                        ? Camera
                        : reason.category.toLowerCase().includes('location') ||
                          reason.category.toLowerCase().includes('gps')
                        ? MapPin
                        : reason.category.toLowerCase().includes('date') ||
                          reason.category.toLowerCase().includes('time')
                        ? Calendar
                        : FileText;
                    return (
                      <div key={idx} className='glass-surface rounded-lg p-3'>
                        <div className='flex items-start gap-2'>
                          <div className='flex-shrink-0 p-1.5 glass-surface rounded'>
                            <Icon size={14} className='text-white/80' />
                          </div>
                          <div className='flex-1 min-w-0'>
                            <div className='flex items-center gap-2 mb-1'>
                              <span className='text-sm font-bold text-white/95'>
                                {reason.category}
                              </span>
                              <span className='text-xs px-1.5 py-0.5 rounded bg-white/20 backdrop-blur-sm font-semibold text-white/90'>
                                {Math.round(reason.confidence * 100)}%
                              </span>
                            </div>
                            <p className='text-sm text-white/80 leading-relaxed'>
                              {reason.matched}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className='glass-surface rounded-lg p-3 text-center'>
                    <p className='text-white/70 text-sm'>
                      No detailed explanation available
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Photo Editor */}
      {photo && (
        <PhotoEditor
          photoPath={photo.path}
          imageUrl={api.getImageUrl(photo.path, 1200)}
          isOpen={showEditor}
          onClose={() => setShowEditor(false)}
          onSave={(editedImageUrl) => {
            // Handle saved edit
            setShowEditor(false);
            // Optionally refresh or show success message
          }}
        />
      )}
      
      {/* Toast notifications */}
      <ToastContainer />
    </>
  );
}
