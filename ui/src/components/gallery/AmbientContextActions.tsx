import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MapPin,
  Calendar,
  Camera,
  Users,
  Tag,
  Palette,
  Sun,
  Moon,
  Car,
  Home,
  Plane,
  Coffee,
  Music,
  Book,
  Flower
} from 'lucide-react';
import { api, type Photo } from '../../api';

type ActionIcon = React.ComponentType<{ size?: number; className?: string }>;

type PhotoAnalysis = {
  concepts?: Array<{ name: string; confidence: number }>;
  dominant_colors?: string[];
};

interface ContextAction {
  id: string;
  type: 'location' | 'time' | 'object' | 'person' | 'event' | 'mood';
  icon: ActionIcon;
  label: string;
  description: string;
  action: string;
  confidence: number;
  data?: unknown;
}

interface AmbientContextActionsProps {
  photo: Photo;
  onAction: (action: string, data?: unknown) => void;
  isVisible: boolean;
}

export const AmbientContextActions: React.FC<AmbientContextActionsProps> = ({
  photo,
  onAction,
  isVisible
}) => {
  const [contextActions, setContextActions] = useState<ContextAction[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!photo || !isVisible) return;

    const analyzeContext = async () => {
      setLoading(true);
      try {
        // Get AI analysis for the photo
        const analysis = (await api.getAnalysis(photo.path)) as PhotoAnalysis;
        const actions = generateContextActions(photo, analysis);
        setContextActions(actions);
      } catch (error) {
        console.error('Failed to analyze photo context:', error);
        setContextActions([]);
      } finally {
        setLoading(false);
      }
    };

    analyzeContext();
  }, [photo, isVisible]);

  const generateContextActions = (
    photo: Photo,
    analysis: PhotoAnalysis | null
  ): ContextAction[] => {
    const actions: ContextAction[] = [];

    // Location-based actions
    if (photo.metadata?.gps?.latitude) {
      actions.push({
        id: 'nearby-photos',
        type: 'location',
        icon: MapPin,
        label: 'Photos nearby',
        description: 'Find photos taken in this area',
        action: 'find-nearby-photos',
        confidence: 0.9,
        data: { lat: photo.metadata.gps.latitude, lng: photo.metadata.gps.longitude }
      });
    }

    // Time-based actions
    const createdDate = photo.metadata?.filesystem?.created;
    const photoDate =
      createdDate && typeof createdDate === 'string'
        ? new Date(createdDate)
        : null;
    if (photoDate && photoDate.getFullYear() > 1970) {
      actions.push({
        id: 'same-day-photos',
        type: 'time',
        icon: Calendar,
        label: 'Same day photos',
        description: `Other photos from ${photoDate.toLocaleDateString()}`,
        action: 'find-same-day-photos',
        confidence: 0.8,
        data: { date: photoDate.toISOString().split('T')[0] }
      });
    }

    // Camera/equipment actions
    if (photo.metadata?.exif?.image?.Make) {
      actions.push({
        id: 'same-camera-photos',
        type: 'object',
        icon: Camera,
        label: 'Same camera',
        description: `Photos from ${photo.metadata.exif.image.Make}`,
        action: 'find-same-camera-photos',
        confidence: 0.7,
        data: { camera: photo.metadata.exif.image.Make }
      });
    }

    // AI-detected objects and scenes
    if (analysis?.concepts) {
      analysis.concepts.forEach((concept) => {
        if (concept.confidence > 0.7) {
          const iconMap: Record<string, ActionIcon> = {
            car: Car,
            home: Home,
            travel: Plane,
            food: Coffee,
            music: Music,
            book: Book,
            flower: Flower,
            sunset: Sun,
            night: Moon,
            people: Users,
          };

          const icon = iconMap[concept.name.toLowerCase()] || Tag;

          actions.push({
            id: `concept-${concept.name}`,
            type: 'object',
            icon,
            label: `More ${concept.name}`,
            description: `Find similar ${concept.name} photos`,
            action: 'find-concept-photos',
            confidence: concept.confidence,
            data: { concept: concept.name }
          });
        }
      });
    }

    // Color-based actions
    if (analysis?.dominant_colors && analysis.dominant_colors.length > 0) {
      const dominantColor = analysis.dominant_colors[0];
      actions.push({
        id: 'similar-colors',
        type: 'mood',
        icon: Palette,
        label: 'Similar colors',
        description: `Photos with similar color palette`,
        action: 'find-similar-colors',
        confidence: 0.6,
        data: { color: dominantColor }
      });
    }

    // Sort by confidence and return top 4
    return actions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 4);
  };

  const handleActionClick = (action: ContextAction) => {
    onAction(action.action, action.data);
  };

  if (!isVisible || loading || contextActions.length === 0) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        className="absolute bottom-4 left-4 right-4 z-20"
      >
        <div className="glass-surface rounded-2xl p-4">
          <div className="text-xs text-white/60 mb-3 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            We discovered these connections
          </div>

          <div className="grid grid-cols-2 gap-2">
            {contextActions.map((action, index) => (
              <motion.button
                key={action.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                onClick={() => handleActionClick(action)}
                className="glass-surface hover:bg-white/10 rounded-lg p-3 text-left transition group"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center flex-shrink-0 group-hover:bg-white/20 transition-colors">
                    <action.icon size={16} className="text-white/80" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white/90 mb-1">
                      {action.label}
                    </div>
                    <div className="text-xs text-white/60 line-clamp-2">
                      {action.description}
                    </div>

                    {/* Confidence indicator */}
                    <div className="mt-2 flex items-center gap-1">
                      <div className="w-12 h-1 bg-white/20 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-400 rounded-full transition-[width]"
                          style={{ width: `${action.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-white/50">
                        {Math.round(action.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
