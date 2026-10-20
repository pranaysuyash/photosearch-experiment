import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  MapPin,
  Calendar,
  Camera,
  Palette,
  Link,
  EyeOff,
  Filter
} from 'lucide-react';
import { api, type Photo } from '../../api';

type RelationshipIcon = React.ComponentType<{ size?: number; className?: string }>;

export interface PhotoRelationship {
  id: string;
  type: 'person' | 'location' | 'time' | 'camera' | 'color' | 'event';
  strength: number; // 0-1
  photos: Photo[];
  metadata: {
    label: string;
    description: string;
    icon: RelationshipIcon;
    color: string;
  };
}

interface PhotoRelationshipGraphProps {
  photos: Photo[];
  selectedPhoto?: Photo | null;
  onPhotoSelect: (photo: Photo) => void;
  onRelationshipExplore: (relationship: PhotoRelationship) => void;
}

const extractDateKey = (photo: Photo): string | null => {
  const created =
    typeof photo.metadata?.filesystem?.created === 'string'
      ? photo.metadata.filesystem.created
      : null;
  if (!created) return null;
  const date = new Date(created);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().split('T')[0];
};

const extractCameraMake = (photo: Photo): string | null => {
  const make =
    photo.metadata?.exif?.image?.Make ||
    (photo.metadata?.exif as Record<string, unknown> | undefined)?.Make;
  return typeof make === 'string' && make.trim() ? make : null;
};

const extractLocationKey = (photo: Photo): string | null => {
  const lat = photo.metadata?.gps?.latitude;
  const lng = photo.metadata?.gps?.longitude;
  if (typeof lat !== 'number' || typeof lng !== 'number') return null;
  return `${lat.toFixed(2)},${lng.toFixed(2)}`;
};

const buildRelationships = (
  selected: Photo,
  allPhotos: Photo[]
): PhotoRelationship[] => {
  const relationships: PhotoRelationship[] = [];
  const selectedDate = extractDateKey(selected);
  const selectedCamera = extractCameraMake(selected);
  const selectedLocation = extractLocationKey(selected);

  if (selectedDate) {
    const related = allPhotos.filter(
      (photo) => photo.path !== selected.path && extractDateKey(photo) === selectedDate
    );
    if (related.length > 0) {
      relationships.push({
        id: `time-${selectedDate}`,
        type: 'time',
        strength: Math.min(1, related.length / Math.max(1, allPhotos.length)),
        photos: [selected, ...related],
        metadata: {
          label: `Photos from ${selectedDate}`,
          description: `${related.length + 1} photo${related.length === 0 ? '' : 's'} captured that day`,
          icon: Calendar,
          color: 'text-purple-400',
        },
      });
    }
  }

  if (selectedLocation) {
    const related = allPhotos.filter(
      (photo) => photo.path !== selected.path && extractLocationKey(photo) === selectedLocation
    );
    if (related.length > 0) {
      relationships.push({
        id: `location-${selectedLocation}`,
        type: 'location',
        strength: Math.min(1, related.length / Math.max(1, allPhotos.length)),
        photos: [selected, ...related],
        metadata: {
          label: 'Nearby location',
          description: `${related.length + 1} photo${related.length === 0 ? '' : 's'} from this area`,
          icon: MapPin,
          color: 'text-green-400',
        },
      });
    }
  }

  if (selectedCamera) {
    const related = allPhotos.filter(
      (photo) => photo.path !== selected.path && extractCameraMake(photo) === selectedCamera
    );
    if (related.length > 0) {
      relationships.push({
        id: `camera-${selectedCamera}`,
        type: 'camera',
        strength: Math.min(1, related.length / Math.max(1, allPhotos.length)),
        photos: [selected, ...related],
        metadata: {
          label: `Shot on ${selectedCamera}`,
          description: `${related.length + 1} photo${related.length === 0 ? '' : 's'} with the same camera`,
          icon: Camera,
          color: 'text-orange-400',
        },
      });
    }
  }

  return relationships;
};

export const PhotoRelationshipGraph: React.FC<PhotoRelationshipGraphProps> = ({
  photos,
  selectedPhoto,
  onPhotoSelect,
  onRelationshipExplore
}) => {
  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(new Set(['person', 'location', 'time']));
  const [isExpanded, setIsExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const relationships = useMemo(() => {
    if (!selectedPhoto) return [];
    return buildRelationships(selectedPhoto, photos);
  }, [selectedPhoto, photos]);
  const loading = false;

  const getRelationshipIcon = (type: string) => {
    const icons = {
      person: Users,
      location: MapPin,
      time: Calendar,
      camera: Camera,
      color: Palette,
      event: Link
    };
    return icons[type as keyof typeof icons] || Link;
  };

  const getRelationshipColor = (type: string) => {
    const colors = {
      person: 'text-blue-400',
      location: 'text-green-400',
      time: 'text-purple-400',
      camera: 'text-orange-400',
      color: 'text-pink-400',
      event: 'text-cyan-400'
    };
    return colors[type as keyof typeof colors] || 'text-gray-400';
  };

  const toggleRelationshipType = (type: string) => {
    setVisibleTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  };

  const visibleRelationships = relationships.filter(rel => visibleTypes.has(rel.type));

  if (!selectedPhoto || relationships.length === 0) {
    return null;
  }

  return (
    <div className="fixed right-4 top-1/2 -translate-y-1/2 z-30">
      <AnimatePresence>
        {!isExpanded ? (
          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            onClick={() => setIsExpanded(true)}
            className="glass-surface rounded-full w-12 h-12 flex items-center justify-center hover:bg-white/10 transition-colors"
            title="Show photo connections"
            aria-label="Show photo connections"
          >
            <Link size={20} className="text-white/80" />
            {relationships.length > 0 && (
              <div className="absolute -top-1 -right-1 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-xs text-white font-bold">
                  {relationships.length}
                </span>
              </div>
            )}
          </motion.button>
        ) : (
          <motion.div
            ref={containerRef}
            initial={{ opacity: 0, x: 20, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.9 }}
            className="glass-surface rounded-2xl p-4 w-80 max-h-[70vh] overflow-y-auto"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-white/90 font-semibold text-sm">
                  Photo Connections
                </h3>
                <p className="text-white/60 text-xs">
                  We found {relationships.length} relationships
                </p>
              </div>
              <button
                onClick={() => setIsExpanded(false)}
                className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                title="Hide photo connections"
                aria-label="Hide photo connections"
              >
                <EyeOff size={14} />
              </button>
            </div>

            {/* Relationship type filters */}
            <div className="flex flex-wrap gap-1 mb-4">
              {['person', 'location', 'time', 'camera', 'color', 'event'].map(type => {
                const Icon = getRelationshipIcon(type);
                const isVisible = visibleTypes.has(type);
                const count = relationships.filter(r => r.type === type).length;

                if (count === 0) return null;

                return (
                  <button
                    key={type}
                    onClick={() => toggleRelationshipType(type)}
                    className={`btn-glass ${isVisible ? 'btn-glass--primary' : 'btn-glass--muted'} text-xs px-2 py-1 flex items-center gap-1`}
                  >
                    <Icon size={12} />
                    <span className="capitalize">{type}</span>
                    <span className="text-xs opacity-60">({count})</span>
                  </button>
                );
              })}
            </div>

            {/* Relationships list */}
            <div className="space-y-3">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                </div>
              ) : (
                visibleRelationships.map((relationship, index) => {
                  const Icon = getRelationshipIcon(relationship.type);
                  const colorClass = getRelationshipColor(relationship.type);

                  return (
                    <motion.div
                      key={relationship.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="glass-surface rounded-lg p-3 hover:bg-white/5 transition-colors cursor-pointer"
                      role="button"
                      tabIndex={0}
                      onClick={() => onRelationshipExplore(relationship)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onRelationshipExplore(relationship);
                        }
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center ${colorClass}`}>
                          <Icon size={16} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="text-white/90 font-medium text-sm truncate">
                              {relationship.metadata.label}
                            </h4>
                            <div className="flex items-center gap-1">
                              <div className="w-12 h-1 bg-white/20 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-white/60 rounded-full transition-[width]"
                                  style={{ width: `${relationship.strength * 100}%` }}
                                />
                              </div>
                              <span className="text-xs text-white/50">
                                {Math.round(relationship.strength * 100)}%
                              </span>
                            </div>
                          </div>

                          <p className="text-white/60 text-xs mb-2 line-clamp-2">
                            {relationship.metadata.description}
                          </p>

                          {/* Related photos preview */}
                          <div className="flex items-center gap-1">
                            <div className="flex -space-x-1">
                              {relationship.photos.slice(0, 4).map((photo, idx) => (
                                <button
                                  key={photo.path}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onPhotoSelect(photo);
                                  }}
                                  className="w-6 h-6 rounded border-2 border-white/20 overflow-hidden hover:border-white/40 transition-colors"
                                  style={{ zIndex: 4 - idx }}
                                >
                                  <img
                                    src={api.getImageUrl(photo.path, 64)}
                                    alt={photo.filename}
                                    className="w-full h-full object-cover"
                                  />
                                </button>
                              ))}
                            </div>

                            {relationship.photos.length > 4 && (
                              <span className="text-xs text-white/50 ml-1">
                                +{relationship.photos.length - 4} more
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  );
                })
              )}
            </div>

            {visibleRelationships.length === 0 && !loading && (
              <div className="text-center py-8">
                <Filter size={24} className="text-white/40 mx-auto mb-2" />
                <p className="text-white/60 text-sm">
                  No relationships match your filters
                </p>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
