/**
 * Photo Editor Component
 *
 * Basic photo editing with crop, brightness, contrast, and saturation adjustments.
 * Non-destructive editing that can be saved as new files.
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  Crop,
  Sun,
  Contrast,
  Droplet,
  RotateCw,
  RotateCcw,
  FlipHorizontal,
  FlipVertical,
  Check,
  Undo,
  Redo,
} from 'lucide-react';
import { glass } from '../../design/glass';
import { api, type PhotoEdit } from '../../api';
import { useToast } from '../ui/Toast';
import { TrafficLightButtons } from '../ui/TrafficLightButtons';

interface PhotoEditorProps {
  photoPath: string;
  imageUrl: string;
  onClose: () => void;
  onSave: (editedImageUrl: string) => void;
  isOpen: boolean;
}

interface EditSettings {
  brightness: number;
  contrast: number;
  saturation: number;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
  crop: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
}

const DEFAULT_SETTINGS: EditSettings = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  rotation: 0,
  flipH: false,
  flipV: false,
  crop: null,
};

export function PhotoEditor({
  photoPath,
  imageUrl,
  onClose,
  onSave,
  isOpen,
}: PhotoEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(
    null
  );
  const [settings, setSettings] = useState<EditSettings>({
    ...DEFAULT_SETTINGS,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingEdits, setIsLoadingEdits] = useState(false);
  const [cropMode, setCropMode] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [cropStart, setCropStart] = useState({ x: 0, y: 0 });
  const [cropEnd, setCropEnd] = useState({ x: 0, y: 0 });
  const [cropPresets] = useState([
    { name: '1:1', ratio: 1 },
    { name: '4:3', ratio: 4 / 3 },
    { name: '16:9', ratio: 16 / 9 },
    { name: '3:2', ratio: 3 / 2 },
    { name: 'Free', ratio: null },
  ]);
  const [showBeforeAfter, setShowBeforeAfter] = useState(false);
  const [history, setHistory] = useState<EditSettings[]>([DEFAULT_SETTINGS]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const { showToast, ToastContainer } = useToast();
  const [imageLoadError, setImageLoadError] = useState(false);

  // Load image when component opens
  useEffect(() => {
    if (isOpen && imageUrl) {
      setImageLoadError(false);
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        setOriginalImage(img);
        applyEdits(img, settings);
      };
      img.onerror = () => {
        console.error('Failed to load image:', imageUrl);
        setImageLoadError(true);
        // Try loading without crossOrigin attribute as fallback
        const fallbackImg = new Image();
        fallbackImg.onload = () => {
          setOriginalImage(fallbackImg);
          applyEdits(fallbackImg, settings);
          setImageLoadError(false);
        };
        fallbackImg.onerror = () => {
          console.error('Fallback image load also failed');
          showToast('Failed to load image for editing', 'error');
        };
        fallbackImg.src = imageUrl;
      };
      img.src = imageUrl;
    }
  }, [isOpen, imageUrl]);

  // Fetch saved edits when opening
  useEffect(() => {
    const loadEdits = async () => {
      if (!isOpen || !photoPath) return;
      setIsLoadingEdits(true);
      try {
        const res = await api.getPhotoEdit(photoPath);
        const loaded =
          (res && (res.edit_data || res.editData || res.data)) || null;
        if (loaded) {
          const merged = {
            ...DEFAULT_SETTINGS,
            ...(loaded.edit_data ?? loaded),
          } as EditSettings;
          setSettings(merged);
        } else {
          setSettings({ ...DEFAULT_SETTINGS });
        }
      } catch (error) {
        console.error('Failed to load saved edits', error);
        setSettings({ ...DEFAULT_SETTINGS });
      } finally {
        setIsLoadingEdits(false);
      }
    };

    loadEdits();
  }, [isOpen, photoPath]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        if (e.key === 'z' && !e.shiftKey) {
          e.preventDefault();
          undo();
        } else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') {
          e.preventDefault();
          redo();
        }
      } else if (!e.metaKey && !e.ctrlKey && !e.altKey) {
        // Quick action shortcuts (only when no modifiers)
        switch (e.key) {
          case 'r':
            e.preventDefault();
            rotateRight();
            break;
          case 'R':
            e.preventDefault();
            rotateLeft();
            break;
          case 'h':
            e.preventDefault();
            flipHorizontal();
            break;
          case 'v':
            e.preventDefault();
            flipVertical();
            break;
          case 'c':
            e.preventDefault();
            setCropMode(true);
            break;
          case 'Escape':
            if (cropMode) {
              e.preventDefault();
              setCropMode(false);
            }
            break;
        }
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, historyIndex, history, cropMode]);
  useEffect(() => {
    if (originalImage) {
      applyEdits(originalImage, settings);
    }
  }, [originalImage, settings]);

  const applyEdits = (img: HTMLImageElement, currentSettings: EditSettings) => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Calculate canvas size with rotation
    const angle = (currentSettings.rotation * Math.PI) / 180;
    const rotatedWidth =
      Math.abs(img.width * Math.cos(angle)) +
      Math.abs(img.height * Math.sin(angle));
    const rotatedHeight =
      Math.abs(img.width * Math.sin(angle)) +
      Math.abs(img.height * Math.cos(angle));

    canvas.width = rotatedWidth;
    canvas.height = rotatedHeight;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply transformations
    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate(angle);
    ctx.scale(currentSettings.flipH ? -1 : 1, currentSettings.flipV ? -1 : 1);

    // Apply filters
    ctx.filter = `brightness(${100 + currentSettings.brightness}%) contrast(${100 + currentSettings.contrast
      }%) saturate(${100 + currentSettings.saturation}%)`;

    // Apply crop if active
    if (currentSettings.crop) {
      const crop = currentSettings.crop;
      ctx.drawImage(
        img,
        crop.x,
        crop.y,
        crop.width,
        crop.height,
        -img.width / 2,
        -img.height / 2,
        img.width,
        img.height
      );
    } else {
      ctx.drawImage(img, -img.width / 2, -img.height / 2);
    }

    ctx.restore();
  };

  const updateSetting = (key: keyof EditSettings, value: any) => {
    const newSettings = { ...settings, [key]: value };

    // Add to history (remove any future history if we're not at the end)
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(newSettings);

    // Limit history to 20 steps
    if (newHistory.length > 20) {
      newHistory.shift();
    } else {
      setHistoryIndex(historyIndex + 1);
    }

    setHistory(newHistory);
    setSettings(newSettings);

    if (originalImage) {
      applyEdits(originalImage, newSettings);
    }
  };

  const undo = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      const previousSettings = history[newIndex];
      setHistoryIndex(newIndex);
      setSettings(previousSettings);
      showToast('Undid last change', 'info');

      if (originalImage) {
        applyEdits(originalImage, previousSettings);
      }
    }
  };

  const redo = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      const nextSettings = history[newIndex];
      setHistoryIndex(newIndex);
      setSettings(nextSettings);
      showToast('Redid change', 'info');

      if (originalImage) {
        applyEdits(originalImage, nextSettings);
      }
    }
  };

  const resetSettings = () => {
    const resetSettings = { ...DEFAULT_SETTINGS };
    setSettings(resetSettings);
    setCropMode(false);

    // Add reset to history
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(resetSettings);
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);

    showToast('All edits reset', 'info');
    if (originalImage) {
      applyEdits(originalImage, resetSettings);
    }
  };

  const rotateLeft = () => {
    updateSetting('rotation', (settings.rotation - 90) % 360);
  };

  const rotateRight = () => {
    updateSetting('rotation', (settings.rotation + 90) % 360);
  };

  const flipHorizontal = () => {
    updateSetting('flipH', !settings.flipH);
  };

  const flipVertical = () => {
    updateSetting('flipV', !settings.flipV);
  };

  const startCrop = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!cropMode || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setCropStart({ x, y });
    setCropEnd({ x, y });
    setIsDragging(true);
  };

  const updateCrop = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!cropMode || !isDragging || !canvasRef.current) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setCropEnd({ x, y });
  };

  const endCrop = () => {
    if (!cropMode || !isDragging || !originalImage || !canvasRef.current)
      return;

    setIsDragging(false);

    const minX = Math.min(cropStart.x, cropEnd.x);
    const minY = Math.min(cropStart.y, cropEnd.y);
    const width = Math.abs(cropEnd.x - cropStart.x);
    const height = Math.abs(cropEnd.y - cropStart.y);

    if (width > 10 && height > 10) {
      // Convert canvas coordinates to image coordinates
      const scaleX = originalImage.width / canvasRef.current.width;
      const scaleY = originalImage.height / canvasRef.current.height;

      updateSetting('crop', {
        x: minX * scaleX,
        y: minY * scaleY,
        width: width * scaleX,
        height: height * scaleY,
      });
    }

    setCropMode(false);
  };

  const clearCrop = () => {
    updateSetting('crop', null);
    setCropMode(false);
  };

  const saveEdit = async () => {
    if (!canvasRef.current) return;

    setIsProcessing(true);
    try {
      // Save edit instructions to server
      await api.savePhotoEdit(photoPath, settings as PhotoEdit);
      showToast('Photo edits saved successfully!', 'success');

      // For now, we'll still generate a local preview
      // In a full implementation, we could generate the edited image on the server
      // or apply the edits client-side and save the result
      const blob = await new Promise<Blob>((resolve) => {
        canvasRef.current!.toBlob((blob) => resolve(blob!), 'image/jpeg', 0.95);
      });

      // Create a URL for the edited image
      const editedImageUrl = URL.createObjectURL(blob);
      onSave(editedImageUrl);

      // Optionally, we could also save the actual image file
      // This would be handled by a backend service that applies the edits
    } catch (error) {
      console.error('Failed to save edit:', error);
      showToast('Failed to save edits. Please try again.', 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-[1300] flex items-center justify-center p-4'>
      <div
        className='absolute inset-0 bg-black/80 backdrop-blur-sm'
        onClick={onClose}
      />

      <div
        className='relative w-full max-w-7xl h-full max-h-[95vh] sm:max-h-[90vh] glass-surface glass-surface--strong rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col lg:flex-row'
      >
        {/* Mac-style Traffic Light Buttons */}
        <div className='absolute top-4 left-4 z-30'>
          <TrafficLightButtons
            onClose={onClose}
            showMinimize={false}
            showMaximize={false}
          />
        </div>

        {/* Header - Title only */}
        <div className='flex items-center justify-center px-5 py-3 border-b border-white/10'>
          <h3 className='text-lg font-semibold text-foreground'>
            Photo Editor
          </h3>
        </div>

        {/* Editor Content */}
        <div className='flex-1 flex flex-col lg:flex-row overflow-hidden'>
          {/* Image Preview Area - Uses CSS transforms for live preview */}
          <div className='flex-1 flex flex-col'>
            <div className='flex-1 flex items-center justify-center p-4 bg-black/30 overflow-hidden'>
              {/* CSS-based live preview (no canvas needed for display) */}
              <img
                src={imageUrl}
                alt='Photo being edited'
                className='max-w-full max-h-full object-contain rounded-lg'
                style={{
                  filter: `brightness(${100 + settings.brightness}%) contrast(${100 + settings.contrast}%) saturate(${100 + settings.saturation}%)`,
                  transform: `rotate(${settings.rotation}deg) scaleX(${settings.flipH ? -1 : 1}) scaleY(${settings.flipV ? -1 : 1})`,
                  transition: 'filter 0.15s ease, transform 0.15s ease',
                }}
              />
              {/* Hidden canvas for save operations */}
              <canvas ref={canvasRef} className='hidden' />
            </div>

            {/* Footer Controls - Undo/Redo/Reset */}
            <div className='flex items-center justify-between px-4 py-3 border-t border-white/10 bg-black/20'>
              <div className='flex items-center gap-2'>
                <button
                  onClick={undo}
                  disabled={historyIndex <= 0}
                  className='btn-glass btn-glass--muted text-xs px-3 py-2 flex items-center gap-1'
                  title='Undo (Ctrl+Z)'
                >
                  <Undo size={14} />
                  Undo
                </button>
                <button
                  onClick={redo}
                  disabled={historyIndex >= history.length - 1}
                  className='btn-glass btn-glass--muted text-xs px-3 py-2 flex items-center gap-1'
                  title='Redo (Ctrl+Y)'
                >
                  <Redo size={14} />
                  Redo
                </button>
                <button
                  onClick={resetSettings}
                  className='btn-glass btn-glass--muted text-xs px-3 py-2 flex items-center gap-1'
                  title='Reset all edits'
                >
                  Reset
                </button>
              </div>
              <div className='text-xs text-muted-foreground'>
                {historyIndex}/{history.length - 1} edits
              </div>
            </div>
          </div>

          {/* Crop overlay */}
          {cropMode && isDragging && !showBeforeAfter && (
            <div
              className='absolute border-2 border-primary bg-white/10 pointer-events-none'
              style={{
                left: Math.min(cropStart.x, cropEnd.x),
                top: Math.min(cropStart.y, cropEnd.y),
                width: Math.abs(cropEnd.x - cropStart.x),
                height: Math.abs(cropEnd.y - cropStart.y),
              }}
            >
              {/* Rule of thirds grid */}
              <div className='absolute inset-0 grid grid-cols-3 grid-rows-3'>
                {Array.from({ length: 9 }).map((_, i) => (
                  <div key={i} className='border border-white/30' />
                ))}
              </div>

              {/* Crop dimensions display */}
              <div className='absolute -bottom-6 left-0 text-xs text-white bg-black/70 px-2 py-1 rounded'>
                {Math.abs(cropEnd.x - cropStart.x)}×{Math.abs(cropEnd.y - cropStart.y)}
              </div>
            </div>
          )}

          {/* Crop mode instructions */}
          {cropMode && !isDragging && !showBeforeAfter && (
            <div className='absolute top-4 left-4 text-sm text-white bg-black/70 px-3 py-2 rounded-lg'>
              Click and drag to select crop area
            </div>
          )}
        </div>
      </div>

      {/* Controls Panel */}
      <div className='w-full lg:w-72 border-t lg:border-t-0 lg:border-l border-white/10 p-3 space-y-4 overflow-y-auto max-h-60 lg:max-h-full'>
        {/* Quick Actions */}
        <div>
          <h4 className='text-sm font-medium text-foreground mb-3'>
            Quick Actions
          </h4>
          <div className='grid grid-cols-2 gap-2'>
            <button
              onClick={rotateRight}
              className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center group relative'
              title='Rotate Right (R)'
            >
              <RotateCw size={14} className='mr-1' />
              Rotate Right
              <span className='absolute top-1 right-1 text-[10px] text-white/40 opacity-0 group-hover:opacity-100 transition-opacity'>
                R
              </span>
            </button>
            <button
              onClick={rotateLeft}
              className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center group relative'
              title='Rotate Left (Shift+R)'
            >
              <RotateCcw size={14} className='mr-1' />
              Rotate Left
              <span className='absolute top-1 right-1 text-[10px] text-white/40 opacity-0 group-hover:opacity-100 transition-opacity'>
                ⇧R
              </span>
            </button>
            <button
              onClick={flipHorizontal}
              className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center group relative'
              title='Flip Horizontal (H)'
            >
              <FlipHorizontal size={14} className='mr-1' />
              Flip H
              <span className='absolute top-1 right-1 text-[10px] text-white/40 opacity-0 group-hover:opacity-100 transition-opacity'>
                H
              </span>
            </button>
            <button
              onClick={flipVertical}
              className='btn-glass btn-glass--muted text-xs px-3 py-2 justify-center group relative'
              title='Flip Vertical (V)'
            >
              <FlipVertical size={14} className='mr-1' />
              Flip V
              <span className='absolute top-1 right-1 text-[10px] text-white/40 opacity-0 group-hover:opacity-100 transition-opacity'>
                V
              </span>
            </button>
          </div>
          <div className='mt-2 text-xs text-muted-foreground bg-white/5 p-2 rounded'>
            Tip: Use keyboard shortcuts: R (rotate), H (flip horizontal), V (flip vertical)
          </div>
        </div>

        {/* Crop */}
        <div>
          <h4 className='text-sm font-medium text-foreground mb-3'>Crop</h4>
          <div className='space-y-2'>
            {/* Crop Presets */}
            <div className='grid grid-cols-3 gap-1 mb-2'>
              {cropPresets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => {
                    // Set crop mode and ratio constraint
                    setCropMode(true);
                    // Store the ratio for use during cropping
                    (window as any).cropRatio = preset.ratio;
                  }}
                  className='btn-glass btn-glass--muted text-xs px-2 py-1'
                >
                  {preset.name}
                </button>
              ))}
            </div>

            {!settings.crop ? (
              <div className='space-y-2'>
                <button
                  onClick={() => setCropMode(true)}
                  className={`btn-glass ${cropMode ? 'btn-glass--primary' : 'btn-glass--muted'
                    } text-xs px-3 py-2 w-full justify-center group relative`}
                  title='Start Crop (C)'
                >
                  <Crop size={14} className='mr-1' />
                  {cropMode ? 'Click and drag to crop' : 'Start Crop'}
                  <span className='absolute top-1 right-1 text-[10px] text-white/40 opacity-0 group-hover:opacity-100 transition-opacity'>
                    C
                  </span>
                </button>
                {cropMode && (
                  <div className='text-xs text-muted-foreground bg-white/5 p-2 rounded'>
                    Press Escape to cancel crop mode
                  </div>
                )}
              </div>
            ) : (
              <div className='space-y-2'>
                <div className='text-xs text-muted-foreground bg-white/5 p-2 rounded'>
                  Crop: {Math.round(settings.crop?.width || 0)}×{Math.round(settings.crop?.height || 0)}px
                  <br />
                  Ratio: {((settings.crop?.width || 1) / (settings.crop?.height || 1)).toFixed(2)}:1
                </div>
                <button
                  onClick={clearCrop}
                  className='btn-glass btn-glass--danger text-xs px-3 py-2 w-full'
                >
                  Clear Crop
                </button>
              </div>
            )}
          </div>
        </div>

        {/* History */}
        <div>
          <h4 className='text-sm font-medium text-foreground mb-3'>History</h4>
          <div className='space-y-1 max-h-32 overflow-y-auto'>
            {history.map((step, index) => {
              const isActive = index === historyIndex;
              const stepName = index === 0 ? 'Original' : `Edit ${index}`;

              return (
                <button
                  key={index}
                  onClick={() => {
                    setHistoryIndex(index);
                    setSettings(step);
                    if (originalImage) {
                      applyEdits(originalImage, step);
                    }
                  }}
                  className={`w-full text-left px-2 py-1 rounded text-xs transition-colors ${isActive
                    ? 'bg-primary/20 text-primary border border-primary/30'
                    : 'hover:bg-white/5 text-muted-foreground'
                    }`}
                >
                  {stepName}
                  {isActive && <span className='float-right'>•</span>}
                </button>
              );
            })}
          </div>
          <div className='text-xs text-muted-foreground mt-2'>
            {history.length}/20 steps • Ctrl+Z/Y for undo/redo
          </div>
        </div>
        <div>
          <h4 className='text-sm font-medium text-foreground mb-3'>Preview</h4>
          <button
            onClick={() => setShowBeforeAfter(!showBeforeAfter)}
            className={`btn-glass ${showBeforeAfter ? 'btn-glass--primary' : 'btn-glass--muted'
              } text-xs px-3 py-2 w-full justify-center`}
          >
            {showBeforeAfter ? 'Show Live Preview' : 'Compare Before/After'}
          </button>
        </div>
        <div>
          <h4 className='text-sm font-medium text-foreground mb-3'>
            Adjustments
          </h4>
          <div className='space-y-4'>
            {/* Brightness */}
            <div>
              <div className='flex items-center justify-between mb-1'>
                <label className='text-xs text-muted-foreground flex items-center gap-1'>
                  <Sun size={12} />
                  Brightness
                </label>
                <div className='flex items-center gap-2'>
                  <input
                    type='number'
                    min='-100'
                    max='100'
                    value={settings.brightness}
                    onChange={(e) =>
                      updateSetting('brightness', parseInt(e.target.value) || 0)
                    }
                    className='w-12 h-6 text-xs bg-white/10 border border-white/20 rounded px-1 text-center text-white'
                  />
                </div>
              </div>
              <input
                type='range'
                min='-100'
                max='100'
                value={settings.brightness}
                onChange={(e) =>
                  updateSetting('brightness', parseInt(e.target.value))
                }
                className='w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer'
              />
            </div>

            {/* Contrast */}
            <div>
              <div className='flex items-center justify-between mb-1'>
                <label className='text-xs text-muted-foreground flex items-center gap-1'>
                  <Contrast size={12} />
                  Contrast
                </label>
                <div className='flex items-center gap-2'>
                  <input
                    type='number'
                    min='-100'
                    max='100'
                    value={settings.contrast}
                    onChange={(e) =>
                      updateSetting('contrast', parseInt(e.target.value) || 0)
                    }
                    className='w-12 h-6 text-xs bg-white/10 border border-white/20 rounded px-1 text-center text-white'
                  />
                </div>
              </div>
              <input
                type='range'
                min='-100'
                max='100'
                value={settings.contrast}
                onChange={(e) =>
                  updateSetting('contrast', parseInt(e.target.value))
                }
                className='w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer'
              />
            </div>

            {/* Saturation */}
            <div>
              <div className='flex items-center justify-between mb-1'>
                <label className='text-xs text-muted-foreground flex items-center gap-1'>
                  <Droplet size={12} />
                  Saturation
                </label>
                <div className='flex items-center gap-2'>
                  <input
                    type='number'
                    min='-100'
                    max='100'
                    value={settings.saturation}
                    onChange={(e) =>
                      updateSetting('saturation', parseInt(e.target.value) || 0)
                    }
                    className='w-12 h-6 text-xs bg-white/10 border border-white/20 rounded px-1 text-center text-white'
                  />
                </div>
              </div>
              <input
                type='range'
                min='-100'
                max='100'
                value={settings.saturation}
                onChange={(e) =>
                  updateSetting('saturation', parseInt(e.target.value))
                }
                className='w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer'
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className='pt-4'>
          <button
            onClick={saveEdit}
            disabled={isProcessing}
            className='btn-glass btn-glass--primary text-sm px-4 py-3 w-full justify-center'
          >
            {isProcessing ? (
              <div className='flex items-center gap-2'>
                <div className='w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin' />
                Processing...
              </div>
            ) : (
              <div className='flex items-center gap-2'>
                <Check size={16} />
                Save Edit
              </div>
            )}
          </button>
        </div>
      </div>

      {/* Toast notifications */}
      <ToastContainer />
    </div>
  );
}
