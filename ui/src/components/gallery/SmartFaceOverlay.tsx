import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Search, UserPlus } from 'lucide-react';
import { api } from '../../api';

interface FaceDetection {
  id: string;
  bbox: [number, number, number, number]; // x, y, width, height (normalized 0-1)
  confidence: number;
  cluster_id?: string;
  person_name?: string;
}

interface SmartFaceOverlayProps {
  photoPath: string;
  imageElement: HTMLImageElement | null;
  onFaceAction: (action: string, faceData: FaceDetection) => void;
}

export const SmartFaceOverlay: React.FC<SmartFaceOverlayProps> = ({
  photoPath,
  imageElement,
  onFaceAction
}) => {
  const [faces, setFaces] = useState<FaceDetection[]>([]);
  const [hoveredFace, setHoveredFace] = useState<string | null>(null);
  const [showOverlay, setShowOverlay] = useState(false);
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!imageElement) return;

    const updateImageSize = () => {
      setImageSize({
        width: imageElement.clientWidth,
        height: imageElement.clientHeight
      });
    };

    updateImageSize();
    window.addEventListener('resize', updateImageSize);

    return () => window.removeEventListener('resize', updateImageSize);
  }, [imageElement]);

  useEffect(() => {
    const loadFaces = async () => {
      try {
        const response = await api.getFacesInPhoto(photoPath);
        const rawFaces = Array.isArray(response?.faces) ? response.faces : [];
        const mappedFaces: FaceDetection[] = rawFaces.map((face: Record<string, unknown>) => {
          const id =
            typeof face.detection_id === 'string'
              ? face.detection_id
              : typeof face.id === 'string'
                ? face.id
                : `${face.detection_id || face.id || ''}`;
          const bboxCandidate =
            (Array.isArray(face.bounding_box) && face.bounding_box) ||
            (Array.isArray(face.bbox) && face.bbox) ||
            [0, 0, 0, 0];
          const confidence =
            typeof face.overall_quality === 'number'
              ? face.overall_quality
              : typeof face.quality_score === 'number'
                ? face.quality_score
                : typeof face.confidence === 'number'
                  ? face.confidence
                  : 0;
          const clusterId =
            typeof face.person_id === 'string'
              ? face.person_id
              : typeof face.cluster_id === 'string'
                ? face.cluster_id
                : undefined;
          const personName =
            typeof face.person_label === 'string'
              ? face.person_label
              : typeof face.person_name === 'string'
                ? face.person_name
                : undefined;

          return {
            id,
            bbox: bboxCandidate as [number, number, number, number],
            confidence,
            cluster_id: clusterId,
            person_name: personName,
          };
        });
        setFaces(mappedFaces);
      } catch (error) {
        console.error('Failed to load face detections:', error);
        setFaces([]);
      }
    };

    if (photoPath) {
      loadFaces();
    }
  }, [photoPath]);

  const handleFaceClick = (face: FaceDetection, action: string) => {
    onFaceAction(action, face);
  };

  if (!imageElement || faces.length === 0) return null;

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      onMouseEnter={() => setShowOverlay(true)}
      onMouseLeave={() => {
        setShowOverlay(false);
        setHoveredFace(null);
      }}
    >
      <AnimatePresence>
        {showOverlay && faces.map((face) => {
          const isNormalized = face.bbox.every(
            (value) => typeof value === 'number' && value >= 0 && value <= 1
          );
          const x = isNormalized ? face.bbox[0] * imageSize.width : face.bbox[0];
          const y = isNormalized ? face.bbox[1] * imageSize.height : face.bbox[1];
          const width = isNormalized ? face.bbox[2] * imageSize.width : face.bbox[2];
          const height = isNormalized ? face.bbox[3] * imageSize.height : face.bbox[3];

          return (
            <motion.div
              key={face.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="absolute pointer-events-auto"
              style={{
                left: x,
                top: y,
                width,
                height
              }}
              onMouseEnter={() => setHoveredFace(face.id)}
              onMouseLeave={() => setHoveredFace(null)}
            >
              {/* Face bounding box */}
              <div className="absolute inset-0 border-2 border-blue-400/60 rounded-lg backdrop-blur-sm bg-blue-400/10" />

              {/* Face actions - appear on hover */}
              <AnimatePresence>
                {hoveredFace === face.id && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute -bottom-12 left-1/2 -translate-x-1/2 flex gap-1"
                  >
                    <button
                      onClick={() => handleFaceClick(face, 'view-all-photos')}
                      className="btn-glass btn-glass--primary w-8 h-8 p-0 justify-center"
                      title="View all photos of this person"
                    >
                      <Users size={14} />
                    </button>

                    <button
                      onClick={() => handleFaceClick(face, 'find-similar')}
                      className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                      title="Find similar faces"
                    >
                      <Search size={14} />
                    </button>

                    {!face.person_name && (
                      <button
                        onClick={() => handleFaceClick(face, 'name-person')}
                        className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
                        title="Name this person"
                      >
                        <UserPlus size={14} />
                      </button>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Person name label */}
              {face.person_name && (
                <div className="absolute -top-6 left-1/2 -translate-x-1/2 glass-surface rounded px-2 py-1">
                  <span className="text-xs text-white/90 font-medium">
                    {face.person_name}
                  </span>
                </div>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};
