/**
 * Split Cluster Modal - Advanced Face Management
 *
 * Allows users to select faces from a mixed cluster and create a new person.
 * Uses the glass design system and follows living language guidelines.
 */
import { useState, useEffect } from 'react';
import { X, User, Users, CheckCircle, RefreshCw } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface Face {
  id: string;
  detection_id: string;
  photo_path: string;
  quality_score?: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  faces?: Face[];
}

interface SplitClusterModalProps {
  cluster: FaceCluster;
  isOpen: boolean;
  onClose: () => void;
  onSplit: () => void;
}

export function SplitClusterModal({ cluster, isOpen, onClose, onSplit }: SplitClusterModalProps) {
  const [faces, setFaces] = useState<Face[]>([]);
  const [selectedFaces, setSelectedFaces] = useState<Set<string>>(new Set());
  const [newPersonName, setNewPersonName] = useState('');
  const [loading, setLoading] = useState(false);
  const [splitting, setSplitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && cluster.id) {
      fetchClusterFaces();
    }
  }, [isOpen, cluster.id]);

  const fetchClusterFaces = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch detailed face information for this cluster
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/clusters/${cluster.id}/photos`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch cluster faces');
      }

      const data = await response.json();

      // Extract faces from the response
      const clusterFaces: Face[] = [];
      if (data.photos) {
        data.photos.forEach((photo: any) => {
          if (photo.faces) {
            photo.faces.forEach((face: any) => {
              clusterFaces.push({
                id: face.detection_id || face.id,
                detection_id: face.detection_id || face.id,
                photo_path: photo.photo_path || photo.path,
                quality_score: face.quality_score,
                bounding_box: face.bounding_box
              });
            });
          }
        });
      }

      setFaces(clusterFaces);
    } catch (err) {
      console.error('Failed to fetch cluster faces:', err);
      setError('Failed to load faces for this person');
    } finally {
      setLoading(false);
    }
  };

  const toggleFaceSelection = (faceId: string) => {
    const newSelection = new Set(selectedFaces);
    if (newSelection.has(faceId)) {
      newSelection.delete(faceId);
    } else {
      newSelection.add(faceId);
    }
    setSelectedFaces(newSelection);
  };

  const handleSplit = async () => {
    if (selectedFaces.size === 0) {
      setError('Please select at least one face to move');
      return;
    }

    try {
      setSplitting(true);
      setError(null);

      // Call the split API endpoint
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/split`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            detection_ids: Array.from(selectedFaces),
            label: newPersonName.trim() || undefined
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to split cluster');
      }

      const result = await response.json();

      // Success - close modal and refresh parent
      onSplit();
      onClose();

      // Reset state
      setSelectedFaces(new Set());
      setNewPersonName('');

    } catch (err: any) {
      console.error('Failed to split cluster:', err);
      setError(err.message || 'Failed to split cluster');
    } finally {
      setSplitting(false);
    }
  };

  const handleClose = () => {
    setSelectedFaces(new Set());
    setNewPersonName('');
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`${glass.surface} border border-white/20 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Users className="text-primary" size={24} />
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Split "{cluster.label || `Person ${cluster.id}`}"
              </h2>
              <p className="text-sm text-muted-foreground">
                Select faces to move to a new person
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="btn-glass btn-glass--muted w-10 h-10 p-0 justify-center"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center gap-3">
                <RefreshCw size={20} className="animate-spin text-muted-foreground" />
                <span className="text-muted-foreground">Loading faces...</span>
              </div>
            </div>
          ) : (
            <>
              {/* Selection Info */}
              <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                <div className="flex items-center gap-2 text-blue-400 text-sm">
                  <CheckCircle size={16} />
                  <span>
                    {selectedFaces.size} of {faces.length} faces selected
                    {selectedFaces.size > 0 && ` • Will create new person with ${selectedFaces.size} face${selectedFaces.size === 1 ? '' : 's'}`}
                  </span>
                </div>
              </div>

              {/* New Person Name Input */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Name for new person (optional)
                </label>
                <input
                  type="text"
                  value={newPersonName}
                  onChange={(e) => setNewPersonName(e.target.value)}
                  placeholder="Enter person name (optional)..."
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                />
              </div>

              {/* Face Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {faces.map((face) => {
                  const isSelected = selectedFaces.has(face.id);
                  return (
                    <div
                      key={face.id}
                      className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                        isSelected
                          ? 'border-primary shadow-lg shadow-primary/20'
                          : 'border-white/10 hover:border-white/20'
                      }`}
                      onClick={() => toggleFaceSelection(face.id)}
                    >
                      {/* Face Image */}
                      <div className="aspect-square bg-black/20">
                        <img
                          src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/crop/${face.detection_id}?size=150`}
                          alt="Face"
                          className="w-full h-full object-cover"
                          loading="lazy"
                          onError={(e) => {
                            // Fallback to full image if crop fails
                            const img = e.target as HTMLImageElement;
                            img.src = api.getImageUrl(face.photo_path, 150);
                          }}
                        />
                      </div>

                      {/* Selection Indicator */}
                      {isSelected && (
                        <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                          <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                            <CheckCircle size={16} className="text-white" />
                          </div>
                        </div>
                      )}

                      {/* Quality Score */}
                      {face.quality_score && (
                        <div className="absolute top-1 right-1 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
                          {Math.round(face.quality_score * 100)}%
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {faces.length === 0 && !loading && (
                <div className="text-center py-12">
                  <User size={48} className="mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium text-foreground mb-2">
                    No Faces Found
                  </h3>
                  <p className="text-muted-foreground">
                    Unable to load faces for this person
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-white/10">
          <div className="text-sm text-muted-foreground">
            {selectedFaces.size > 0 && (
              <span>
                {faces.length - selectedFaces.size} faces will remain with "{cluster.label || `Person ${cluster.id}`}"
              </span>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="btn-glass btn-glass--muted px-4 py-2"
              disabled={splitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSplit}
              className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
              disabled={splitting || selectedFaces.size === 0 || !newPersonName.trim()}
            >
              {splitting && <RefreshCw size={14} className="animate-spin" />}
              {splitting ? 'Splitting...' : `Split ${selectedFaces.size} Face${selectedFaces.size === 1 ? '' : 's'}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SplitClusterModal;
