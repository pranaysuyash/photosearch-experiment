/**
 * Mobile-First Photo Editor Component
 *
 * Enhanced photo editor optimized for mobile devices with:
 * - Touch gestures (pinch-to-zoom, pan, rotate)
 * - Mobile-friendly UI with bottom sheet controls
 * - Responsive design for all screen sizes
 * - Gesture-based editing (swipe for adjustments)
 * - Haptic feedback support
 * - Performance optimizations for mobile
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { PanInfo } from 'framer-motion';
import {
  X,
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
  ZoomIn,
  ZoomOut,
  Move,
  Maximize2,
  Minimize2,
  Settings,
  ChevronUp,
  ChevronDown,
  Smartphone,
  Monitor,
} from 'lucide-react';
import { glass } from '../../design/glass';
import { api, type PhotoEdit } from '../../api';

interface MobilePhotoEditorProps {
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
  zoom: number;
  panX: number;
  panY: number;
}

interface TouchState {
  initialDistance: number;
  initialZoom: number;
  initialPanX: number;
  initialPanY: number;
  lastTouchTime: number;
  touchCount: number;
}

const DEFAULT_SETTINGS: EditSettings = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  rotation: 0,
  flipH: false,
  flipV: false,
  crop: null,
  zoom: 1,
  panX: 0,
  panY: 0,
};

const ADJUSTMENT_PRESETS = [
  { name: 'Auto', brightness: 10, contrast: 15, saturation: 5 },
  { name: 'Vivid', brightness: 5, contrast: 25, saturation: 30 },
  { name: 'Warm', brightness: 15, contrast: 10, saturation: 20 },
  { name: 'Cool', brightness: 0, contrast: 20, saturation: -10 },
  { name: 'B&W', brightness: 5, contrast: 30, saturation: -100 },
];

export function MobilePhotoEditor({
  photoPath,
  imageUrl,
  onClose,
  onSave,
  isOpen,
}: MobilePhotoEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const touchStateRef = useRef<TouchState>({
    initialDistance: 0,
    initialZoom: 1,
    initialPanX: 0,
    initialPanY: 0,
    lastTouchTime: 0,
    touchCount: 0,
  });

  const [originalImage, setOriginalImage] = useState<HTMLImageElement | null>(
    null
  );
  const [settings, setSettings] = useState<EditSettings>({
    ...DEFAULT_SETTINGS,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingEdits, setIsLoadingEdits] = useState(false);
  const [cropMode, setCropMode] = useState(false);
  const [editMode, setEditMode] = useState<
    'view' | 'adjust' | 'transform' | 'crop'
  >('view');
  const [activeAdjustment, setActiveAdjustment] = useState<
    'brightness' | 'contrast' | 'saturation' | null
  >(null);
  const [showControls, setShowControls] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [deviceOrientation, setDeviceOrientation] = useState<
    'portrait' | 'landscape'
  >('portrait');

  // Detect mobile device and orientation
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768 || 'ontouchstart' in window;
      setIsMobile(mobile);
      setDeviceOrientation(
        window.innerWidth < window.innerHeight ? 'portrait' : 'landscape'
      );
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    window.addEventListener('orientationchange', checkMobile);

    return () => {
      window.removeEventListener('resize', checkMobile);
      window.removeEventListener('orientationchange', checkMobile);
    };
  }, []);

  // Load image when component opens
  useEffect(() => {
    if (isOpen && imageUrl) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        setOriginalImage(img);
        applyEdits(img, settings);
      };
      img.src = imageUrl;
    }
  }, [isOpen, imageUrl]);

  // Load saved edits
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

  // Re-apply edits when settings change
  useEffect(() => {
    if (originalImage) {
      applyEdits(originalImage, settings);
    }
  }, [originalImage, settings]);

  // Haptic feedback (if supported)
  const hapticFeedback = useCallback(
    (type: 'light' | 'medium' | 'heavy' = 'light') => {
      if ('vibrate' in navigator) {
        const patterns = { light: 10, medium: 50, heavy: 100 };
        navigator.vibrate(patterns[type]);
      }
    },
    []
  );

  const applyEdits = (img: HTMLImageElement, currentSettings: EditSettings) => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Calculate canvas size with rotation and zoom
    const angle = (currentSettings.rotation * Math.PI) / 180;
    const rotatedWidth =
      Math.abs(img.width * Math.cos(angle)) +
      Math.abs(img.height * Math.sin(angle));
    const rotatedHeight =
      Math.abs(img.width * Math.sin(angle)) +
      Math.abs(img.height * Math.cos(angle));

    canvas.width = rotatedWidth * currentSettings.zoom;
    canvas.height = rotatedHeight * currentSettings.zoom;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply transformations
    ctx.save();
    ctx.translate(
      canvas.width / 2 + currentSettings.panX,
      canvas.height / 2 + currentSettings.panY
    );
    ctx.rotate(angle);
    ctx.scale(
      (currentSettings.flipH ? -1 : 1) * currentSettings.zoom,
      (currentSettings.flipV ? -1 : 1) * currentSettings.zoom
    );

    // Apply filters
    ctx.filter = `brightness(${100 + currentSettings.brightness}%) contrast(${
      100 + currentSettings.contrast
    }%) saturate(${100 + currentSettings.saturation}%)`;

    // Draw image
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
    setSettings(newSettings);
    hapticFeedback('light');
  };

  // Touch gesture handlers
  const getTouchDistance = (touches: any) => {
    // Accept React.TouchList or native TouchList
    if (!touches || touches.length < 2) return 0;
    const touch1 = touches[0] as any;
    const touch2 = touches[1] as any;
    return Math.sqrt(
      Math.pow(touch2.clientX - touch1.clientX, 2) +
        Math.pow(touch2.clientY - touch1.clientY, 2)
    );
  };

  const getTouchCenter = (touches: any) => {
    if (!touches || touches.length === 0) return { x: 0, y: 0 };
    if (touches.length === 1)
      return { x: (touches[0] as any).clientX, y: (touches[0] as any).clientY };

    const touch1 = touches[0] as any;
    const touch2 = touches[1] as any;
    return {
      x: (touch1.clientX + touch2.clientX) / 2,
      y: (touch1.clientY + touch2.clientY) / 2,
    };
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    e.preventDefault();
    const touches = e.touches;
    const touchState = touchStateRef.current;

    touchState.touchCount = touches.length;
    touchState.lastTouchTime = Date.now();

    if (touches.length === 2) {
      // Pinch gesture
      touchState.initialDistance = getTouchDistance(touches);
      touchState.initialZoom = settings.zoom;
      hapticFeedback('medium');
    } else if (touches.length === 1) {
      // Pan gesture
      touchState.initialPanX = settings.panX;
      touchState.initialPanY = settings.panY;
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    e.preventDefault();
    const touches = e.touches;
    const touchState = touchStateRef.current;

    if (touches.length === 2 && touchState.initialDistance > 0) {
      // Pinch to zoom
      const currentDistance = getTouchDistance(touches);
      const scale = currentDistance / touchState.initialDistance;
      const newZoom = Math.max(
        0.5,
        Math.min(5, touchState.initialZoom * scale)
      );

      if (Math.abs(newZoom - settings.zoom) > 0.01) {
        updateSetting('zoom', newZoom);
      }
    } else if (touches.length === 1 && editMode === 'view') {
      // Pan gesture
      const touch = touches[0];
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const deltaX = touch.clientX - rect.left - rect.width / 2;
        const deltaY = touch.clientY - rect.top - rect.height / 2;

        updateSetting('panX', touchState.initialPanX + deltaX * 0.5);
        updateSetting('panY', touchState.initialPanY + deltaY * 0.5);
      }
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const touchState = touchStateRef.current;
    const touchDuration = Date.now() - touchState.lastTouchTime;

    // Double tap to reset zoom
    if (
      e.touches.length === 0 &&
      touchDuration < 300 &&
      touchState.touchCount === 1
    ) {
      const now = Date.now();
      if (now - touchState.lastTouchTime < 300) {
        updateSetting('zoom', 1);
        updateSetting('panX', 0);
        updateSetting('panY', 0);
        hapticFeedback('heavy');
      }
    }

    touchState.touchCount = e.touches.length;
  };

  // Gesture-based adjustment handler
  const handleAdjustmentGesture = (
    info: PanInfo,
    adjustmentType: 'brightness' | 'contrast' | 'saturation'
  ) => {
    const sensitivity = 0.5;
    const delta = -info.delta.y * sensitivity;
    const currentValue = settings[adjustmentType];
    const newValue = Math.max(-100, Math.min(100, currentValue + delta));

    updateSetting(adjustmentType, Math.round(newValue));
  };

  const applyPreset = (preset: (typeof ADJUSTMENT_PRESETS)[0]) => {
    setSettings((prev) => ({
      ...prev,
      brightness: preset.brightness,
      contrast: preset.contrast,
      saturation: preset.saturation,
    }));
    hapticFeedback('medium');
  };

  const resetSettings = () => {
    setSettings({ ...DEFAULT_SETTINGS });
    setCropMode(false);
    setEditMode('view');
    hapticFeedback('heavy');
  };

  const saveEdit = async () => {
    if (!canvasRef.current) return;

    setIsProcessing(true);
    hapticFeedback('heavy');

    try {
      await api.savePhotoEdit(photoPath, settings as PhotoEdit);

      const blob = await new Promise<Blob>((resolve) => {
        canvasRef.current!.toBlob((blob) => resolve(blob!), 'image/jpeg', 0.95);
      });

      const editedImageUrl = URL.createObjectURL(blob);
      onSave(editedImageUrl);
    } catch (error) {
      console.error('Failed to save edit:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  const MobileControls = () => (
    <AnimatePresence>
      {showControls && (
        <motion.div
          initial={{ y: '100%' }}
          animate={{ y: 0 }}
          exit={{ y: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className={`fixed bottom-0 left-0 right-0 glass-surface border-t border-white/10 z-50`}
        >
          {/* Mode Selector */}
          <div className='flex items-center justify-center p-2 border-b border-white/10'>
            <div className='flex bg-white/5 rounded-lg p-1'>
              {(['view', 'adjust', 'transform', 'crop'] as const).map(
                (mode) => (
                  <button
                    key={mode}
                    onClick={() => setEditMode(mode)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                      editMode === mode
                        ? 'bg-blue-500/20 text-blue-400'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Mode-specific Controls */}
          <div className='p-4 max-h-64 overflow-y-auto'>
            {editMode === 'adjust' && (
              <div className='space-y-4'>
                {/* Presets */}
                <div>
                  <h4 className='text-sm font-medium mb-2'>Presets</h4>
                  <div className='flex gap-2 overflow-x-auto pb-2'>
                    {ADJUSTMENT_PRESETS.map((preset) => (
                      <button
                        key={preset.name}
                        onClick={() => applyPreset(preset)}
                        className='btn-glass btn-glass--muted text-xs px-3 py-2 whitespace-nowrap'
                      >
                        {preset.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Gesture Adjustments */}
                <div className='space-y-3'>
                  {(['brightness', 'contrast', 'saturation'] as const).map(
                    (adj) => (
                      <motion.div
                        key={adj}
                        drag='y'
                        dragConstraints={{ top: 0, bottom: 0 }}
                        onPan={(_, info) => handleAdjustmentGesture(info, adj)}
                        className='glass-surface rounded-lg p-3 cursor-grab active:cursor-grabbing'
                      >
                        <div className='flex items-center justify-between'>
                          <div className='flex items-center gap-2'>
                            {adj === 'brightness' && (
                              <Sun className='w-4 h-4' />
                            )}
                            {adj === 'contrast' && (
                              <Contrast className='w-4 h-4' />
                            )}
                            {adj === 'saturation' && (
                              <Droplet className='w-4 h-4' />
                            )}
                            <span className='text-sm font-medium capitalize'>
                              {adj}
                            </span>
                          </div>
                          <span className='text-sm text-gray-400'>
                            {settings[adj]}
                          </span>
                        </div>
                        <div className='text-xs text-gray-500 mt-1'>
                          Drag up/down to adjust
                        </div>
                      </motion.div>
                    )
                  )}
                </div>
              </div>
            )}

            {editMode === 'transform' && (
              <div className='grid grid-cols-2 gap-3'>
                <button
                  onClick={() =>
                    updateSetting('rotation', (settings.rotation - 90) % 360)
                  }
                  className='btn-glass btn-glass--muted flex items-center justify-center gap-2 py-3'
                >
                  <RotateCcw className='w-4 h-4' />
                  Rotate Left
                </button>
                <button
                  onClick={() =>
                    updateSetting('rotation', (settings.rotation + 90) % 360)
                  }
                  className='btn-glass btn-glass--muted flex items-center justify-center gap-2 py-3'
                >
                  <RotateCw className='w-4 h-4' />
                  Rotate Right
                </button>
                <button
                  onClick={() => updateSetting('flipH', !settings.flipH)}
                  className={`btn-glass btn-glass--muted flex items-center justify-center gap-2 py-3 ${
                    settings.flipH ? 'btn-glass--primary' : ''
                  }`}
                >
                  <FlipHorizontal className='w-4 h-4' />
                  Flip H
                </button>
                <button
                  onClick={() => updateSetting('flipV', !settings.flipV)}
                  className={`btn-glass btn-glass--muted flex items-center justify-center gap-2 py-3 ${
                    settings.flipV ? 'btn-glass--primary' : ''
                  }`}
                >
                  <FlipVertical className='w-4 h-4' />
                  Flip V
                </button>
              </div>
            )}

            {editMode === 'crop' && (
              <div className='space-y-3'>
                <button
                  onClick={() => setCropMode(!cropMode)}
                  className={`${glass.button} w-full py-3 ${
                    cropMode ? 'bg-blue-500/20 text-blue-400' : ''
                  }`}
                >
                  <Crop className='w-4 h-4 mr-2' />
                  {cropMode ? 'Exit Crop Mode' : 'Start Cropping'}
                </button>
                {settings.crop && (
                  <button
                    onClick={() => updateSetting('crop', null)}
                    className={`${glass.buttonDanger} w-full py-3`}
                  >
                    Clear Crop
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className='flex gap-3 p-4 border-t border-white/10'>
            <button
              onClick={resetSettings}
              className={`${glass.button} flex-1 py-3 flex items-center justify-center gap-2`}
            >
              <Undo className='w-4 h-4' />
              Reset
            </button>
            <button
              onClick={saveEdit}
              disabled={isProcessing}
              className={`${glass.buttonPrimary} flex-1 py-3 flex items-center justify-center gap-2`}
            >
              {isProcessing ? (
                <>
                  <div className='w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin' />
                  Saving...
                </>
              ) : (
                <>
                  <Check className='w-4 h-4' />
                  Save
                </>
              )}
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  const DesktopControls = () => (
    <div className='w-80 border-l border-white/10 p-4 space-y-6 overflow-y-auto'>
      {/* Device Mode Indicator */}
      <div className='flex items-center gap-2 text-sm text-gray-400'>
        <Monitor className='w-4 h-4' />
        Desktop Mode
      </div>

      {/* Quick Actions */}
      <div>
        <h4 className='text-sm font-medium mb-3'>Quick Actions</h4>
        <div className='grid grid-cols-2 gap-2'>
          <button
            onClick={() =>
              updateSetting('rotation', (settings.rotation - 90) % 360)
            }
            className={`${glass.button} text-xs px-3 py-2 justify-center`}
          >
            <RotateCcw size={14} className='mr-1' />
            Rotate Left
          </button>
          <button
            onClick={() =>
              updateSetting('rotation', (settings.rotation + 90) % 360)
            }
            className={`${glass.button} text-xs px-3 py-2 justify-center`}
          >
            <RotateCw size={14} className='mr-1' />
            Rotate Right
          </button>
          <button
            onClick={() => updateSetting('flipH', !settings.flipH)}
            className={`${glass.button} text-xs px-3 py-2 justify-center ${
              settings.flipH ? 'bg-blue-500/20 text-blue-400' : ''
            }`}
          >
            <FlipHorizontal size={14} className='mr-1' />
            Flip H
          </button>
          <button
            onClick={() => updateSetting('flipV', !settings.flipV)}
            className={`${glass.button} text-xs px-3 py-2 justify-center ${
              settings.flipV ? 'bg-blue-500/20 text-blue-400' : ''
            }`}
          >
            <FlipVertical size={14} className='mr-1' />
            Flip V
          </button>
        </div>
      </div>

      {/* Presets */}
      <div>
        <h4 className='text-sm font-medium mb-3'>Presets</h4>
        <div className='grid grid-cols-2 gap-2'>
          {ADJUSTMENT_PRESETS.map((preset) => (
            <button
              key={preset.name}
              onClick={() => applyPreset(preset)}
              className={`${glass.button} text-xs px-3 py-2`}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Adjustments */}
      <div>
        <h4 className='text-sm font-medium mb-3'>Adjustments</h4>
        <div className='space-y-4'>
          {(['brightness', 'contrast', 'saturation'] as const).map((adj) => (
            <div key={adj}>
              <div className='flex items-center justify-between mb-1'>
                <label className='text-xs text-gray-400 flex items-center gap-1 capitalize'>
                  {adj === 'brightness' && <Sun size={12} />}
                  {adj === 'contrast' && <Contrast size={12} />}
                  {adj === 'saturation' && <Droplet size={12} />}
                  {adj}
                </label>
                <span className='text-xs text-gray-400'>{settings[adj]}</span>
              </div>
              <input
                type='range'
                min='-100'
                max='100'
                value={settings[adj]}
                onChange={(e) => updateSetting(adj, parseInt(e.target.value))}
                className='w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer'
              />
            </div>
          ))}
        </div>
      </div>

      {/* Zoom Controls */}
      <div>
        <h4 className='text-sm font-medium mb-3'>Zoom & Pan</h4>
        <div className='space-y-2'>
          <div className='flex items-center gap-2'>
            <button
              onClick={() =>
                updateSetting('zoom', Math.max(0.5, settings.zoom - 0.1))
              }
              className={`${glass.button} p-2`}
            >
              <ZoomOut className='w-4 h-4' />
            </button>
            <span className='text-sm text-gray-400 flex-1 text-center'>
              {Math.round(settings.zoom * 100)}%
            </span>
            <button
              onClick={() =>
                updateSetting('zoom', Math.min(5, settings.zoom + 0.1))
              }
              className={`${glass.button} p-2`}
            >
              <ZoomIn className='w-4 h-4' />
            </button>
          </div>
          <button
            onClick={() => {
              updateSetting('zoom', 1);
              updateSetting('panX', 0);
              updateSetting('panY', 0);
            }}
            className={`${glass.button} w-full text-xs py-2`}
          >
            Reset View
          </button>
        </div>
      </div>

      {/* Save Button */}
      <div className='pt-4'>
        <button
          onClick={saveEdit}
          disabled={isProcessing}
          className={`${glass.buttonPrimary} text-sm px-4 py-3 w-full justify-center`}
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
  );

  return (
    <div className='fixed inset-0 z-[1300] flex items-center justify-center'>
      <div
        className='absolute inset-0 bg-black/90 backdrop-blur-sm'
        onClick={onClose}
      />

      <div
        className={`relative w-full h-full ${glass.surface} ${
          isMobile
            ? ''
            : 'max-w-7xl max-h-[90vh] rounded-2xl border border-white/10 shadow-2xl'
        } overflow-hidden flex flex-col`}
      >
        {/* Header */}
        <div className='flex items-center justify-between px-4 py-3 border-b border-white/10 bg-black/20'>
          <div className='flex items-center gap-3'>
            <h3 className='text-lg font-semibold'>Photo Editor</h3>
            {isMobile && (
              <div className='flex items-center gap-1 text-xs text-gray-400'>
                <Smartphone className='w-3 h-3' />
                Mobile
              </div>
            )}
          </div>

          <div className='flex items-center gap-2'>
            {isMobile && (
              <button
                onClick={() => setShowControls(!showControls)}
                className={`${glass.button} p-2`}
              >
                {showControls ? (
                  <ChevronDown className='w-4 h-4' />
                ) : (
                  <ChevronUp className='w-4 h-4' />
                )}
              </button>
            )}
            <button
              onClick={resetSettings}
              className={`${glass.button} text-sm px-3 py-2 ${
                isMobile ? 'hidden' : 'flex'
              } items-center gap-1`}
            >
              <Undo size={14} />
              Reset
            </button>
            <button onClick={onClose} className={`${glass.button} p-2`}>
              <X className='w-4 h-4' />
            </button>
          </div>
        </div>

        {/* Editor Content */}
        <div className='flex-1 flex overflow-hidden'>
          {/* Canvas Area */}
          <div
            ref={containerRef}
            className='flex-1 flex items-center justify-center bg-black/20 relative overflow-hidden'
          >
            <canvas
              ref={canvasRef}
              className={`max-w-full max-h-full object-contain ${
                cropMode
                  ? 'cursor-crosshair'
                  : isMobile
                  ? 'cursor-grab active:cursor-grabbing'
                  : ''
              }`}
              onTouchStart={isMobile ? handleTouchStart : undefined}
              onTouchMove={isMobile ? handleTouchMove : undefined}
              onTouchEnd={isMobile ? handleTouchEnd : undefined}
              style={{
                touchAction: 'none',
                userSelect: 'none',
              }}
            />

            {/* Mobile Zoom Indicator */}
            {isMobile && settings.zoom !== 1 && (
              <div className='absolute top-4 right-4 bg-black/50 text-white text-xs px-2 py-1 rounded'>
                {Math.round(settings.zoom * 100)}%
              </div>
            )}

            {/* Mobile Gesture Hints */}
            {isMobile && editMode === 'view' && (
              <div className='absolute bottom-4 left-4 right-4 text-center text-xs text-gray-400'>
                Pinch to zoom • Drag to pan • Double tap to reset
              </div>
            )}
          </div>

          {/* Desktop Controls */}
          {!isMobile && <DesktopControls />}
        </div>
      </div>

      {/* Mobile Controls */}
      {isMobile && <MobileControls />}
    </div>
  );
}

export default MobilePhotoEditor;
