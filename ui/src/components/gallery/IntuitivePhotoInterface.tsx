import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Settings } from 'lucide-react';
import type { Photo } from '../../api';

// Import all our innovative UI components
import { AmbientContextActions } from './AmbientContextActions';
import { SmartSelectionCanvas } from './SmartSelectionCanvas';
import { PhotoRelationshipGraph, type PhotoRelationship } from './PhotoRelationshipGraph';
import { PredictiveActionSuggestions } from './PredictiveActionSuggestions';

interface IntuitivePhotoInterfaceProps {
  photos: Photo[];
  selectedPhoto?: Photo | null;
  onPhotoSelect: (photo: Photo) => void;
  onPhotoAction: (action: string, photo: Photo, data?: unknown) => void;
  userBehavior: {
    recentActions: string[];
    preferences: Record<string, number>;
    patterns: Record<string, unknown>;
  };
  children: React.ReactNode;
}

interface InterfaceSettings {
  showHoverZones: boolean;
  showFaceOverlays: boolean;
  enableGestures: boolean;
  showContextActions: boolean;
  enableInlineEdit: boolean;
  showRelationships: boolean;
  showSuggestions: boolean;
  smartSelectionEnabled: boolean;
}

const DEFAULT_SETTINGS: InterfaceSettings = {
  showHoverZones: true,
  showFaceOverlays: true,
  enableGestures: true,
  showContextActions: true,
  enableInlineEdit: true,
  showRelationships: true,
  showSuggestions: true,
  smartSelectionEnabled: false
};

export const IntuitivePhotoInterface: React.FC<IntuitivePhotoInterfaceProps> = ({
  photos,
  selectedPhoto,
  onPhotoSelect,
  onPhotoAction,
  userBehavior,
  children
}) => {
  const [settings, setSettings] = useState<InterfaceSettings>(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);
  const [photoPositions] = useState<Map<string, { x: number; y: number; width: number; height: number }>>(new Map());
  const containerRef = useRef<HTMLDivElement>(null);

  const handlePhotoAction = useCallback((action: string, data?: unknown) => {
    if (!selectedPhoto) return;
    onPhotoAction(action, selectedPhoto, data);
  }, [selectedPhoto, onPhotoAction]);

  const handleSelectionChange = useCallback((selectedPhotos: Photo[]) => {
    onPhotoAction('bulk-select', selectedPhotos[0], { photos: selectedPhotos });
  }, [onPhotoAction]);

  const handleRelationshipExplore = useCallback((relationship: PhotoRelationship) => {
    if (!selectedPhoto) return;
    onPhotoAction('explore-relationship', selectedPhoto, relationship);
  }, [selectedPhoto, onPhotoAction]);

  const updateSetting = (key: keyof InterfaceSettings, value: boolean) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div ref={containerRef} className="relative">
      {/* Main content with smart selection overlay */}
      <div className="relative">
        {settings.smartSelectionEnabled && (
          <SmartSelectionCanvas
            photos={photos}
            photoPositions={photoPositions}
            onSelectionChange={handleSelectionChange}
            isActive={settings.smartSelectionEnabled}
            onToggle={() => updateSetting('smartSelectionEnabled', !settings.smartSelectionEnabled)}
          />
        )}

        {children}
      </div>

      {/* Ambient context actions */}
      {settings.showContextActions && selectedPhoto && (
        <AmbientContextActions
          photo={selectedPhoto}
          onAction={handlePhotoAction}
          isVisible={true}
        />
      )}

      {/* Photo relationship graph */}
      {settings.showRelationships && (
        <PhotoRelationshipGraph
          photos={photos}
          selectedPhoto={selectedPhoto}
          onPhotoSelect={onPhotoSelect}
          onRelationshipExplore={handleRelationshipExplore}
        />
      )}

      {/* Predictive action suggestions */}
      {settings.showSuggestions && selectedPhoto && (
        <PredictiveActionSuggestions
          photo={selectedPhoto}
          userBehavior={userBehavior}
          onActionExecute={handlePhotoAction}
          isVisible={true}
        />
      )}

      {/* Interface controls */}
      <div className="fixed top-4 right-4 z-50">
        <div className="flex items-center gap-2">
          {/* Smart selection toggle */}
          <button
            onClick={() => updateSetting('smartSelectionEnabled', !settings.smartSelectionEnabled)}
            className={`btn-glass ${settings.smartSelectionEnabled ? 'btn-glass--primary' : 'btn-glass--muted'} w-10 h-10 p-0 justify-center`}
            title="Smart selection"
            aria-label="Smart selection"
            aria-pressed={settings.smartSelectionEnabled}
          >
            <Zap size={16} />
          </button>

          {/* Settings toggle */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="btn-glass btn-glass--muted w-10 h-10 p-0 justify-center"
            title="Interface settings"
            aria-label="Interface settings"
            aria-expanded={showSettings}
          >
            <Settings size={16} />
          </button>
        </div>

        {/* Settings panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              className="absolute top-full right-0 mt-2 glass-surface rounded-2xl p-4 w-64"
            >
              <h3 className="text-white/90 font-semibold text-sm mb-3">
                Interface Features
              </h3>

              <div className="space-y-3">
                {Object.entries(settings).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <label htmlFor={`interface-setting-${key}`} className="text-white/70 text-sm capitalize">
                      {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                    </label>
                    <button
                      id={`interface-setting-${key}`}
                      onClick={() => updateSetting(key as keyof InterfaceSettings, !value)}
                      role="switch"
                      aria-checked={value}
                      aria-label={key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                      className={`w-10 h-6 rounded-full transition-colors ${
                        value ? 'bg-blue-500' : 'bg-white/20'
                      } relative`}
                    >
                      <div
                        className={`w-4 h-4 rounded-full bg-white transition-transform ${
                          value ? 'translate-x-5' : 'translate-x-1'
                        } absolute top-1`}
                      />
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-3 border-t border-white/10">
                <p className="text-xs text-white/50">
                  Customize your photo browsing experience with these intelligent features.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
