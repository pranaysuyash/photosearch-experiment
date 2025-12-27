/**
 * Similar Face Search Component
 *
 * Allows users to find faces similar to a selected face.
 * Uses the glass design system and follows living language guidelines.
 */
import { useState } from 'react';
import { Search, X, RefreshCw, User, Camera } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface Face {
  id: string;
  detection_id: string;
  photo_path: string;
  similarity_score?: number;
  quality_score?: number;
  cluster_id?: string;
  cluster_label?: string;
}

interface SimilarFaceSearchProps {
  faceId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function SimilarFaceSearch({ faceId, isOpen, onClose }: SimilarFaceSearchProps) {
  const [similarFaces, setSimilarFaces] = useState<Face[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threshold, setThreshold] = useState(0.7);

  const findSimilarFaces = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${faceId}/similar?threshold=${threshold}`
      );

      if (!response.ok) {
        throw new Error('Failed to find similar faces');
      }

      const data = await response.json();
      setSimilarFaces(data.similar_faces || []);

    } catch (err: unknown) {
      console.error('Failed to find similar faces:', err);
      setError(err instanceof Error ? err.message : 'Failed to find similar faces');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setSimilarFaces([]);
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
            <Search className="text-primary" size={24} />
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Find Similar Faces
              </h2>
              <p className="text-sm text-muted-foreground">
                We'll search for faces that look similar to the selected one
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
          {/* Search Controls */}
          <div className="mb-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Similarity Threshold
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm text-muted-foreground w-12">
                  {Math.round(threshold * 100)}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Higher values find more similar faces, lower values find more matches
              </p>
            </div>

            <button
              onClick={findSimilarFaces}
              disabled={loading}
              className="btn-glass btn-glass--primary flex items-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search size={16} />
                  Find Similar Faces
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Results */}
          {similarFaces.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Camera size={16} />
                <span>Found {similarFaces.length} similar face{similarFaces.length === 1 ? '' : 's'}</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {similarFaces.map((face, index) => (
                  <div
                    key={face.id || index}
                    className="bg-white/5 border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors"
                  >
                    {/* Face Image */}
                    <div className="aspect-square bg-black/20 relative">
                      <img
                        src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/crop/${face.detection_id}?size=150`}
                        alt="Similar face"
                        className="w-full h-full object-cover"
                        loading="lazy"
                        onError={(e) => {
                          // Fallback to full image if crop fails
                          const img = e.target as HTMLImageElement;
                          img.src = api.getImageUrl(face.photo_path, 150);
                        }}
                      />

                      {/* Similarity Score */}
                      {face.similarity_score && (
                        <div className="absolute top-2 right-2 bg-primary/80 text-white text-xs px-2 py-1 rounded">
                          {Math.round(face.similarity_score * 100)}%
                        </div>
                      )}
                    </div>

                    {/* Face Info */}
                    <div className="p-3">
                      <div className="text-xs text-muted-foreground mb-1">
                        {face.cluster_label || 'Unknown Person'}
                      </div>

                      {face.quality_score && (
                        <div className="text-xs text-muted-foreground">
                          Quality: {Math.round(face.quality_score * 100)}%
                        </div>
                      )}

                      <div className="text-xs text-muted-foreground truncate mt-1" title={face.photo_path}>
                        {face.photo_path.split('/').pop()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {similarFaces.length === 0 && !loading && !error && (
            <div className="text-center py-12">
              <Search size={48} className="mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">
                Ready to Search
              </h3>
              <p className="text-muted-foreground">
                Click "Find Similar Faces" to search for faces that look like this one
              </p>
            </div>
          )}

          {similarFaces.length === 0 && !loading && !error && findSimilarFaces.length > 0 && (
            <div className="text-center py-12">
              <User size={48} className="mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">
                No Similar Faces Found
              </h3>
              <p className="text-muted-foreground">
                Try lowering the similarity threshold to find more matches
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end p-6 border-t border-white/10">
          <button
            onClick={handleClose}
            className="btn-glass btn-glass--muted px-4 py-2"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default SimilarFaceSearch;
