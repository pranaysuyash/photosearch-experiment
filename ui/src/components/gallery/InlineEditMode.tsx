import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sun,
  Contrast,
  Droplet,
  RotateCw,
  FlipHorizontal,
  Check,
  X,
  Undo,
  Palette,
  Zap
} from 'lucide-react';
import { api, type Photo } from '../../api';

interface InlineEditModeProps {
  photo: Photo;
  isActive: boolean;
  onSave: (edits: PhotoEdits) => void;
  onCancel: () => void;
  onToggle: () => void;
}

interface PhotoEdits {
  brightness: number;
  contrast: number;
  saturation: number;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
}

const DEFAULT_EDITS: PhotoEdits = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  rotation: 0,
  flipH: false,
  flipV: false
};

export const InlineEditMode: React.FC<InlineEditModeProps> = ({
  photo,
  isActive,
  onSave,
  onCancel,
  onToggle
}) => {
  const [edits, setEdits] = useState<PhotoEdits>(DEFAULT_EDITS);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Generate preview when edits change
  useEffect(() => {
    if (!isActive) return;

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    setIsProcessing(true);
    debounceRef.current = setTimeout(() => {
      setPreviewUrl(api.getImageUrl(photo.path, 400));
      setIsProcessing(false);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [edits, isActive, photo.path]);

  const handleEditChange = (key: keyof PhotoEdits, value: number | boolean) => {
    setEdits(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsProcessing(true);
    try {
      await onSave(edits);
      setEdits(DEFAULT_EDITS);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    if (
      hasChanges &&
      !window.confirm('Discard unsaved edits to this photo?')
    ) {
      return;
    }
    setEdits(DEFAULT_EDITS);
    setPreviewUrl(null);
    onCancel();
  };

  const hasChanges = Object.entries(edits).some(([key, value]) =>
    value !== DEFAULT_EDITS[key as keyof PhotoEdits]
  );

  return (
    <div className="relative group">
      {/* Photo with overlay */}
      <div className="relative overflow-hidden rounded-lg">
        <img
          src={previewUrl || api.getImageUrl(photo.path, 400)}
          alt={photo.filename}
          className="w-full h-full object-cover transition-[filter,transform] duration-300"
          style={{
            filter: `brightness(${1 + edits.brightness / 100}) contrast(${1 + edits.contrast / 100}) saturate(${1 + edits.saturation / 100})`,
            transform: `rotate(${edits.rotation}deg) scaleX(${edits.flipH ? -1 : 1}) scaleY(${edits.flipV ? -1 : 1})`
          }}
        />

        {/* Processing overlay */}
        {isProcessing && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          </div>
        )}

        {/* Edit trigger button */}
        {!isActive && (
          <button
            onClick={onToggle}
            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
            title="Quick edit"
            aria-label="Quick edit"
          >
            <Zap size={14} />
          </button>
        )}
      </div>

      {/* Inline edit controls */}
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="glass-surface rounded-b-lg p-3 space-y-3"
          >
            {/* Quick adjustment sliders */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Sun size={14} className="text-white/60" />
                <input
                  type="range"
                  min="-50"
                  max="50"
                  value={edits.brightness}
                  onChange={(e) => handleEditChange('brightness', parseInt(e.target.value))}
                  aria-label="Brightness"
                  className="flex-1 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-yellow-400"
                />
                <span className="text-xs text-white/60 w-8 text-right">
                  {edits.brightness > 0 ? '+' : ''}{edits.brightness}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Contrast size={14} className="text-white/60" />
                <input
                  type="range"
                  min="-50"
                  max="50"
                  value={edits.contrast}
                  onChange={(e) => handleEditChange('contrast', parseInt(e.target.value))}
                  aria-label="Contrast"
                  className="flex-1 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-blue-400"
                />
                <span className="text-xs text-white/60 w-8 text-right">
                  {edits.contrast > 0 ? '+' : ''}{edits.contrast}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Droplet size={14} className="text-white/60" />
                <input
                  type="range"
                  min="-50"
                  max="50"
                  value={edits.saturation}
                  onChange={(e) => handleEditChange('saturation', parseInt(e.target.value))}
                  className="flex-1 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-purple-400"
                />
                <span className="text-xs text-white/60 w-8 text-right">
                  {edits.saturation > 0 ? '+' : ''}{edits.saturation}
                </span>
              </div>
            </div>

            {/* Transform controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleEditChange('rotation', (edits.rotation + 90) % 360)}
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                  title="Rotate 90°"
                  aria-label="Rotate 90°"
                >
                  <RotateCw size={12} />
                </button>

                <button
                  onClick={() => handleEditChange('flipH', !edits.flipH)}
                  className={`btn-glass ${edits.flipH ? 'btn-glass--primary' : 'btn-glass--muted'} w-8 h-8 p-0 justify-center`}
                  title="Flip horizontal"
                  aria-label="Flip horizontal"
                  aria-pressed={edits.flipH}
                >
                  <FlipHorizontal size={12} />
                </button>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    if (
                      window.confirm('Reset all adjustments to defaults?')
                    ) {
                      setEdits(DEFAULT_EDITS);
                    }
                  }}
                  disabled={!hasChanges}
                  aria-label="Reset adjustments"
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center disabled:opacity-50"
                  title="Reset"
                >
                  <Undo size={12} />
                </button>

                <button
                  onClick={handleCancel}
                  aria-label="Cancel editing"
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                  title="Cancel"
                >
                  <X size={12} />
                </button>

                <button
                  onClick={handleSave}
                  disabled={!hasChanges || isProcessing}
                  aria-label="Save changes"
                  className="btn-glass btn-glass--primary w-8 h-8 p-0 justify-center disabled:opacity-50"
                  title="Save changes"
                >
                  <Check size={12} />
                </button>
              </div>
            </div>

            {/* Smart suggestions */}
            {hasChanges && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-white/60 flex items-center gap-2"
              >
                <Palette size={12} />
                <span>We'll save this as a new version</span>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
