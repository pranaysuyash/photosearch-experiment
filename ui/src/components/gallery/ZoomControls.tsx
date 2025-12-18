import { useEffect } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { usePhotoSearchContext, type GridZoomLevel } from '../../contexts/PhotoSearchContext';

const ZOOM_LEVELS: GridZoomLevel[] = ['compact', 'comfortable', 'spacious'];

const ZOOM_LABELS: Record<GridZoomLevel, string> = {
  compact: 'Dense',
  comfortable: 'Comfortable',
  spacious: 'Spacious',
};

const ZOOM_ICONS: Record<GridZoomLevel, typeof ZoomIn> = {
  compact: ZoomOut,
  comfortable: Maximize2,
  spacious: ZoomIn,
};

export function ZoomControls() {
  const { gridZoom, setGridZoom } = usePhotoSearchContext();

  const currentIndex = ZOOM_LEVELS.indexOf(gridZoom);

  const zoomIn = () => {
    const nextIndex = Math.min(currentIndex + 1, ZOOM_LEVELS.length - 1);
    setGridZoom(ZOOM_LEVELS[nextIndex]);
  };

  const zoomOut = () => {
    const prevIndex = Math.max(currentIndex - 1, 0);
    setGridZoom(ZOOM_LEVELS[prevIndex]);
  };

  const cycleZoom = () => {
    const nextIndex = (currentIndex + 1) % ZOOM_LEVELS.length;
    setGridZoom(ZOOM_LEVELS[nextIndex]);
  };

  // Keyboard shortcuts: + to zoom in, - to zoom out
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // + or = key (with or without shift)
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        zoomIn();
      }
      // - or _ key
      else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        zoomOut();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex]);

  const Icon = ZOOM_ICONS[gridZoom];

  return (
    <div className="flex items-center gap-1 glass-surface rounded-full p-1">
      {/* Zoom Out Button */}
      <button
        onClick={zoomOut}
        disabled={currentIndex === 0}
        className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-white/80 hover:text-white"
        title="Zoom out (smaller thumbnails)"
        aria-label="Zoom out"
      >
        <ZoomOut size={16} />
      </button>

      {/* Current Zoom Level Button (cycles through levels) */}
      <button
        onClick={cycleZoom}
        className="px-3 h-8 rounded-full flex items-center gap-1.5 hover:bg-white/10 transition-colors text-white/80 hover:text-white"
        title={`Current: ${ZOOM_LABELS[gridZoom]} - Click to cycle`}
        aria-label={`Grid zoom: ${ZOOM_LABELS[gridZoom]}`}
      >
        <Icon size={14} />
        <span className="text-xs font-medium">{ZOOM_LABELS[gridZoom]}</span>
      </button>

      {/* Zoom In Button */}
      <button
        onClick={zoomIn}
        disabled={currentIndex === ZOOM_LEVELS.length - 1}
        className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-white/80 hover:text-white"
        title="Zoom in (larger thumbnails)"
        aria-label="Zoom in"
      >
        <ZoomIn size={16} />
      </button>
    </div>
  );
}
