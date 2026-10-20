import React, { useRef, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MousePointer,
  Square,
  Circle,
  Zap,
  Wand2,
  Check,
  X
} from 'lucide-react';
import type { Photo } from '../../api';

interface SmartSelectionCanvasProps {
  photos: Photo[];
  photoPositions: Map<string, { x: number; y: number; width: number; height: number }>;
  onSelectionChange: (selectedPhotos: Photo[]) => void;
  isActive: boolean;
  onToggle: () => void;
}

type SelectionMode = 'lasso' | 'rectangle' | 'circle' | 'smart';

interface Point {
  x: number;
  y: number;
}

interface SelectionPath {
  points: Point[];
  mode: SelectionMode;
  completed: boolean;
}

export const SmartSelectionCanvas: React.FC<SmartSelectionCanvasProps> = ({
  photos,
  photoPositions,
  onSelectionChange,
  isActive,
  onToggle
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [selectionMode, setSelectionMode] = useState<SelectionMode>('lasso');
  const [currentPath, setCurrentPath] = useState<SelectionPath | null>(null);
  const [selectedPhotos, setSelectedPhotos] = useState<Photo[]>([]);
  const [previewSelection, setPreviewSelection] = useState<Photo[]>([]);

  // Initialize canvas
  useEffect(() => {
    if (!isActive || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }
  }, [isActive]);

  // Draw selection path
  useEffect(() => {
    if (!canvasRef.current || !currentPath) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw selection path
    ctx.strokeStyle = '#3b82f6';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (currentPath.points.length > 1) {
      ctx.beginPath();

      if (selectionMode === 'rectangle') {
        const start = currentPath.points[0];
        const end = currentPath.points[currentPath.points.length - 1];
        ctx.rect(start.x, start.y, end.x - start.x, end.y - start.y);
      } else if (selectionMode === 'circle') {
        const start = currentPath.points[0];
        const end = currentPath.points[currentPath.points.length - 1];
        const radius = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
        ctx.arc(start.x, start.y, radius, 0, 2 * Math.PI);
      } else {
        // Lasso or smart selection
        ctx.moveTo(currentPath.points[0].x, currentPath.points[0].y);
        currentPath.points.forEach(point => {
          ctx.lineTo(point.x, point.y);
        });
        if (currentPath.completed) {
          ctx.closePath();
        }
      }

      ctx.stroke();

      // Fill with semi-transparent color
      if (currentPath.completed || selectionMode !== 'lasso') {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
        ctx.fill();
      }
    }

    // Highlight selected photos
    previewSelection.forEach(photo => {
      const pos = photoPositions.get(photo.path);
      if (pos) {
        ctx.strokeStyle = '#10b981';
        ctx.lineWidth = 3;
        ctx.strokeRect(pos.x - 2, pos.y - 2, pos.width + 4, pos.height + 4);
      }
    });
  }, [currentPath, previewSelection, photoPositions, selectionMode]);

  const getPhotosInSelection = useCallback((path: SelectionPath): Photo[] => {
    if (!path.completed && selectionMode === 'lasso') return [];

    return photos.filter(photo => {
      const pos = photoPositions.get(photo.path);
      if (!pos) return false;

      const centerX = pos.x + pos.width / 2;
      const centerY = pos.y + pos.height / 2;

      switch (selectionMode) {
        case 'rectangle': {
          const start = path.points[0];
          const end = path.points[path.points.length - 1];
          const minX = Math.min(start.x, end.x);
          const maxX = Math.max(start.x, end.x);
          const minY = Math.min(start.y, end.y);
          const maxY = Math.max(start.y, end.y);
          return centerX >= minX && centerX <= maxX && centerY >= minY && centerY <= maxY;
        }

        case 'circle': {
          const start = path.points[0];
          const end = path.points[path.points.length - 1];
          const radius = Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2));
          const distance = Math.sqrt(Math.pow(centerX - start.x, 2) + Math.pow(centerY - start.y, 2));
          return distance <= radius;
        }

        case 'lasso':
        case 'smart': {
          // Point-in-polygon test
          let inside = false;
          for (let i = 0, j = path.points.length - 1; i < path.points.length; j = i++) {
            if (((path.points[i].y > centerY) !== (path.points[j].y > centerY)) &&
                (centerX < (path.points[j].x - path.points[i].x) * (centerY - path.points[i].y) / (path.points[j].y - path.points[i].y) + path.points[i].x)) {
              inside = !inside;
            }
          }
          return inside;
        }

        default:
          return false;
      }
    });
  }, [photos, photoPositions, selectionMode]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!isActive) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setIsDrawing(true);
    setCurrentPath({
      points: [{ x, y }],
      mode: selectionMode,
      completed: false
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDrawing || !currentPath) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const newPath = {
      ...currentPath,
      points: selectionMode === 'lasso' || selectionMode === 'smart'
        ? [...currentPath.points, { x, y }]
        : [currentPath.points[0], { x, y }]
    };

    setCurrentPath(newPath);

    // Update preview selection
    if (selectionMode !== 'lasso') {
      const selected = getPhotosInSelection({ ...newPath, completed: true });
      setPreviewSelection(selected);
    }
  };

  const handleMouseUp = () => {
    if (!isDrawing || !currentPath) return;

    setIsDrawing(false);

    const completedPath = { ...currentPath, completed: true };
    setCurrentPath(completedPath);

    const selected = getPhotosInSelection(completedPath);
    setPreviewSelection(selected);
  };

  const confirmSelection = () => {
    setSelectedPhotos(previewSelection);
    onSelectionChange(previewSelection);
    setCurrentPath(null);
    setPreviewSelection([]);
  };

  const cancelSelection = () => {
    setCurrentPath(null);
    setPreviewSelection([]);
    setIsDrawing(false);
  };

  const clearSelection = () => {
    setSelectedPhotos([]);
    onSelectionChange([]);
    setCurrentPath(null);
    setPreviewSelection([]);
  };

  if (!isActive) {
    return (
      <button
        onClick={onToggle}
        className="fixed bottom-4 right-4 btn-glass btn-glass--primary w-12 h-12 p-0 justify-center z-50"
        title="Smart selection"
        aria-label="Smart selection"
      >
        <Wand2 size={20} />
      </button>
    );
  }

  return (
    <>
      {/* Selection canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 z-40 cursor-crosshair"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{ pointerEvents: isActive ? 'auto' : 'none' }}
      />

      {/* Selection tools */}
      <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50">
        <div className="glass-surface rounded-2xl p-2 flex items-center gap-2">
          <button
            onClick={() => setSelectionMode('lasso')}
            className={`btn-glass ${selectionMode === 'lasso' ? 'btn-glass--primary' : 'btn-glass--muted'} w-10 h-10 p-0 justify-center`}
            title="Lasso selection"
            aria-label="Lasso selection"
            aria-pressed={selectionMode === 'lasso'}
          >
            <MousePointer size={16} />
          </button>

          <button
            onClick={() => setSelectionMode('rectangle')}
            className={`btn-glass ${selectionMode === 'rectangle' ? 'btn-glass--primary' : 'btn-glass--muted'} w-10 h-10 p-0 justify-center`}
            title="Rectangle selection"
            aria-label="Rectangle selection"
            aria-pressed={selectionMode === 'rectangle'}
          >
            <Square size={16} />
          </button>

          <button
            onClick={() => setSelectionMode('circle')}
            className={`btn-glass ${selectionMode === 'circle' ? 'btn-glass--primary' : 'btn-glass--muted'} w-10 h-10 p-0 justify-center`}
            title="Circle selection"
            aria-label="Circle selection"
            aria-pressed={selectionMode === 'circle'}
          >
            <Circle size={16} />
          </button>

          <button
            onClick={() => setSelectionMode('smart')}
            className={`btn-glass ${selectionMode === 'smart' ? 'btn-glass--primary' : 'btn-glass--muted'} w-10 h-10 p-0 justify-center`}
            title="Smart selection"
            aria-label="Smart selection"
            aria-pressed={selectionMode === 'smart'}
          >
            <Zap size={16} />
          </button>

          <div className="w-px h-6 bg-white/20 mx-1" />

          <button
            onClick={onToggle}
            className="btn-glass btn-glass--muted w-10 h-10 p-0 justify-center"
            title="Exit selection mode"
            aria-label="Exit selection mode"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Selection actions */}
      <AnimatePresence>
        {(previewSelection.length > 0 || selectedPhotos.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50"
          >
            <div className="glass-surface rounded-2xl p-4 flex items-center gap-4">
              <div className="text-sm text-white/90">
                {previewSelection.length > 0
                  ? `${previewSelection.length} photos selected`
                  : `${selectedPhotos.length} photos selected`
                }
              </div>

              <div className="flex items-center gap-2">
                {previewSelection.length > 0 ? (
                  <>
                    <button
                      onClick={cancelSelection}
                      className="btn-glass btn-glass--muted px-3 py-2 text-sm"
                    >
                      <X size={14} className="mr-1" />
                      Cancel
                    </button>
                    <button
                      onClick={confirmSelection}
                      className="btn-glass btn-glass--primary px-3 py-2 text-sm"
                    >
                      <Check size={14} className="mr-1" />
                      Select
                    </button>
                  </>
                ) : (
                  <button
                    onClick={clearSelection}
                    className="btn-glass btn-glass--muted px-3 py-2 text-sm"
                  >
                    Clear Selection
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
