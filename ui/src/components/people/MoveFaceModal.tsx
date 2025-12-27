/**
 * Move Face Modal - Advanced Face Management
 *
 * Allows users to move a single face from one person to another.
 * Uses the glass design system and follows living language guidelines.
 */
import { useState, useEffect, useCallback } from 'react';
import { X, ArrowRight, RefreshCw, Search } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface Face {
  id: string;
  detection_id: string;
  photo_path: string;
  quality_score?: number;
  cluster_id: string;
  cluster_label?: string;
}

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
}

interface MoveFaceModalProps {
  face: Face;
  isOpen: boolean;
  onClose: () => void;
  onMove: () => void;
}

export function MoveFaceModal({ face, isOpen, onClose, onMove }: MoveFaceModalProps) {
  const [availableClusters, setAvailableClusters] = useState<FaceCluster[]>([]);
  const [targetClusterId, setTargetClusterId] = useState('');
  const [createNewPerson, setCreateNewPerson] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');
  const [loading, setLoading] = useState(false);
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchAvailableClusters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.getFaceClusters();
      const clusters = response.clusters || [];

      // Filter out the current cluster
      const availableClusters = clusters.filter(
        (cluster: FaceCluster) => cluster.id !== face.cluster_id
      );

      setAvailableClusters(availableClusters);
    } catch (err) {
      console.error('Failed to fetch available clusters:', err);
      setError('Failed to load available people');
    } finally {
      setLoading(false);
    }
  }, [face.cluster_id]);

  useEffect(() => {
    if (isOpen) {
      fetchAvailableClusters();
    }
  }, [fetchAvailableClusters, isOpen]);

  const handleMove = async () => {
    if (!createNewPerson && !targetClusterId) {
      setError('Please select a person or choose to create a new one');
      return;
    }

    if (createNewPerson && !newPersonName.trim()) {
      setError('Please enter a name for the new person');
      return;
    }

    try {
      setMoving(true);
      setError(null);

      if (createNewPerson) {
        // Create new person and move face
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${face.detection_id}/create-person`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              person_name: newPersonName.trim()
            })
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create new person');
        }
      } else {
        // Move face to existing cluster
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/move`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              face_id: face.detection_id,
              from_cluster_id: face.cluster_id,
              to_cluster_id: targetClusterId
            })
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to move face');
        }
      }

      // Success - close modal and refresh parent
      onMove();
      onClose();

      // Reset state
      setTargetClusterId('');
      setCreateNewPerson(false);
      setNewPersonName('');

    } catch (err: unknown) {
      console.error('Failed to move face:', err);
      setError(err instanceof Error ? err.message : 'Failed to move face');
    } finally {
      setMoving(false);
    }
  };

  const handleClose = () => {
    setTargetClusterId('');
    setCreateNewPerson(false);
    setNewPersonName('');
    setError(null);
    setSearchTerm('');
    onClose();
  };

  const filteredClusters = availableClusters.filter(cluster =>
    cluster.label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    cluster.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`${glass.surface} border border-white/20 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <ArrowRight className="text-primary" size={24} />
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Move Face
              </h2>
              <p className="text-sm text-muted-foreground">
                Move this face to a different person or create a new one
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

          {/* Face Preview */}
          <div className="mb-6 p-4 bg-white/5 border border-white/10 rounded-lg">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 bg-black/20 rounded-lg overflow-hidden">
                <img
                  src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/crop/${face.detection_id}?size=150`}
                  alt="Face to move"
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const img = e.target as HTMLImageElement;
                    img.src = api.getImageUrl(face.photo_path, 150);
                  }}
                />
              </div>
              <div>
                <div className="text-sm font-medium text-foreground">
                  Moving from: {face.cluster_label || `Person ${face.cluster_id}`}
                </div>
                <div className="text-xs text-muted-foreground">
                  {face.photo_path.split('/').pop()}
                </div>
                {face.quality_score && (
                  <div className="text-xs text-muted-foreground">
                    Quality: {Math.round(face.quality_score * 100)}%
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Move Options */}
          <div className="space-y-4">
            {/* Option 1: Move to existing person */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  id="existing-person"
                  name="move-option"
                  checked={!createNewPerson}
                  onChange={() => setCreateNewPerson(false)}
                  className="w-4 h-4 text-primary"
                />
                <label htmlFor="existing-person" className="text-sm font-medium text-foreground">
                  Move to existing person
                </label>
              </div>

              {!createNewPerson && (
                <div className="ml-6 space-y-3">
                  {/* Search */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={16} />
                    <input
                      type="text"
                      placeholder="Search people..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                    />
                  </div>

                  {/* Person List */}
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw size={20} className="animate-spin text-muted-foreground" />
                    </div>
                  ) : (
                    <div className="max-h-60 overflow-y-auto space-y-2">
                      {filteredClusters.map((cluster) => (
                        <div
                          key={cluster.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            targetClusterId === cluster.id
                              ? 'border-primary bg-primary/10'
                              : 'border-white/10 hover:border-white/20 bg-white/5'
                          }`}
                          onClick={() => setTargetClusterId(cluster.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-sm font-medium text-foreground">
                                {cluster.label || `Person ${cluster.id}`}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {cluster.face_count} faces • {cluster.image_count} photos
                              </div>
                            </div>
                            {targetClusterId === cluster.id && (
                              <div className="w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                                <div className="w-2 h-2 bg-white rounded-full" />
                              </div>
                            )}
                          </div>
                        </div>
                      ))}

                      {filteredClusters.length === 0 && !loading && (
                        <div className="text-center py-8 text-muted-foreground">
                          {searchTerm ? 'No people found matching your search' : 'No other people available'}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Option 2: Create new person */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  id="new-person"
                  name="move-option"
                  checked={createNewPerson}
                  onChange={() => setCreateNewPerson(true)}
                  className="w-4 h-4 text-primary"
                />
                <label htmlFor="new-person" className="text-sm font-medium text-foreground">
                  Create new person
                </label>
              </div>

              {createNewPerson && (
                <div className="ml-6">
                  <input
                    type="text"
                    placeholder="Enter person name..."
                    value={newPersonName}
                    onChange={(e) => setNewPersonName(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-white/10 gap-3">
          <button
            onClick={handleClose}
            className="btn-glass btn-glass--muted px-4 py-2"
            disabled={moving}
          >
            Cancel
          </button>
          <button
            onClick={handleMove}
            className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
            disabled={
              moving ||
              (!createNewPerson && !targetClusterId) ||
              (createNewPerson && !newPersonName.trim())
            }
          >
            {moving && <RefreshCw size={14} className="animate-spin" />}
            {moving ? 'Moving...' : 'Move Face'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default MoveFaceModal;
