/**
 * Interactive Face Tagging Component
 * 
 * Provides visual face detection and tagging interface
 * Integrates with face detection API and clustering system
 */

import React, { useState, useEffect } from 'react';
import { X, User, Search, Check, Loader2, AlertTriangle } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import { FaceDetection, FaceDetectionResult, SimilarFacesResult } from '../../api';

interface InteractiveFaceTaggingProps {
  photoPath: string;
  imageUrl: string;
  onFacesDetected?: (faces: FaceDetection[]) => void;
  onFaceTagged?: (detectionId: string, personId: string) => void;
  showControls?: boolean;
}

export function InteractiveFaceTagging({
  photoPath,
  imageUrl,
  onFacesDetected,
  onFaceTagged,
  showControls = true
}: InteractiveFaceTaggingProps) {
  const [faces, setFaces] = useState<FaceDetection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFace, setSelectedFace] = useState<FaceDetection | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [similarFaces, setSimilarFaces] = useState<any[]>([]);
  const [tagging, setTagging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Detect faces when component mounts
  useEffect(() => {
    const detectFaces = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Detect faces in the photo
        const result: FaceDetectionResult = await api.detectFaces(photoPath);
        
        if (result.success && result.faces.length > 0) {
          setFaces(result.faces);
          if (onFacesDetected) {
            onFacesDetected(result.faces);
          }
        } else {
          setFaces([]);
        }
      } catch (err) {
        console.error('Face detection failed:', err);
        setError('Failed to detect faces in this photo');
      } finally {
        setLoading(false);
      }
    };

    detectFaces();
  }, [photoPath, onFacesDetected]);

  // Find similar faces when a face is selected
  useEffect(() => {
    const findSimilar = async () => {
      if (!selectedFace) {
        setSimilarFaces([]);
        return;
      }

      try {
        setTagging(true);
        
        // Find similar faces
        const result: SimilarFacesResult = await api.findSimilarFaces(
          selectedFace.detection_id, 
          0.7
        );
        
        if (result.success) {
          setSimilarFaces(result.similar_faces);
        }
      } catch (err) {
        console.error('Failed to find similar faces:', err);
      } finally {
        setTagging(false);
      }
    };

    findSimilar();
  }, [selectedFace]);

  // Search for people
  const searchPeople = async () => {
    if (!searchQuery.trim()) return;

    try {
      const result = await api.searchPeople(searchQuery);
      setSuggestions(result.people || []);
    } catch (err) {
      console.error('Search failed:', err);
      setError('Failed to search for people');
    }
  };

  // Tag a face with a person
  const tagFace = async (personId: string) => {
    if (!selectedFace) return;

    try {
      setTagging(true);
      
      // Add person to face
      const result = await api.addPersonToPhoto(photoPath, personId, selectedFace.detection_id);
      
      if (result.success && onFaceTagged) {
        onFaceTagged(selectedFace.detection_id, personId);
      }
      
      // Refresh faces
      const detectionResult = await api.detectFaces(photoPath);
      if (detectionResult.success) {
        setFaces(detectionResult.faces);
      }
      
      // Close tagging panel
      setSelectedFace(null);
    } catch (err) {
      console.error('Failed to tag face:', err);
      setError('Failed to tag face');
    } finally {
      setTagging(false);
    }
  };

  // Create a new person and tag the face
  const createAndTagPerson = async (name: string) => {
    if (!selectedFace || !name.trim()) return;

    try {
      setTagging(true);
      
      // Create new person cluster
      const clusterId = await api.addFaceCluster(name);
      
      // Tag the face with the new person
      await tagFace(clusterId);
    } catch (err) {
      console.error('Failed to create and tag person:', err);
      setError('Failed to create person');
    } finally {
      setTagging(false);
    }
  };

  // Calculate face bounding box style
  const getFaceBoxStyle = (face: FaceDetection) => ({
    left: `${face.bounding_box.x * 100}%`,
    top: `${face.bounding_box.y * 100}%`,
    width: `${face.bounding_box.width * 100}%`,
    height: `${face.bounding_box.height * 100}%`,
  });

  return (
    <div className="relative">
      {/* Photo with face overlays */}
      <div className="relative">
        <img
          src={imageUrl}
          alt="Photo"
          className="w-full h-auto max-h-[600px] object-contain"
        />

        {/* Loading state */}
        {loading && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
            <div className={`${glass.surface} p-4 rounded-lg flex items-center gap-2`}>
              <Loader2 className="animate-spin text-blue-400" size={20} />
              <span className="text-foreground">Detecting faces...</span>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
            <div className={`${glass.surface} p-4 rounded-lg flex items-center gap-2 text-yellow-400`}>
              <AlertTriangle size={20} />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Face bounding boxes */}
        {faces.map((face) => (
          <div
            key={face.detection_id}
            className="absolute border-2 border-blue-500 rounded-lg cursor-pointer hover:border-blue-400 transition-colors"
            style={getFaceBoxStyle(face)}
            onClick={() => setSelectedFace(face)}
          >
            {/* Show person label if available */}
            {face.person_id && (
              <div className="absolute -top-3 -left-1 bg-blue-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                <User size={12} />
                <span>{face.person_label || 'Person'}</span>
              </div>
            )}
          </div>
        ))}

        {/* No faces detected */}
        {!loading && faces.length === 0 && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
            <div className={`${glass.surface} p-4 rounded-lg text-center`}>
              <Search className="mx-auto text-muted-foreground mb-2" size={24} />
              <p className="text-muted-foreground text-sm">No faces detected</p>
            </div>
          </div>
        )}
      </div>

      {/* Face tagging panel */}
      {selectedFace && showControls && (
        <div className={`${glass.surfaceStrong} mt-4 p-4 rounded-lg`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-foreground">Tag This Face</h3>
            <button
              onClick={() => setSelectedFace(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X size={18} />
            </button>
          </div>

          {/* Face info */}
          <div className="mb-4 p-3 bg-white/5 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Detection ID: {selectedFace.detection_id}</p>
            <p className="text-sm text-muted-foreground mb-1">
              Quality: {(selectedFace.quality_score * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-muted-foreground">
              Location: {selectedFace.bounding_box.x.toFixed(2)}, {selectedFace.bounding_box.y.toFixed(2)}
            </p>
          </div>

          {/* Similar faces */}
          {similarFaces.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-1">
                <Search size={14} />
                Similar Faces Found
              </h4>
              <div className="flex flex-wrap gap-2">
                {similarFaces.slice(0, 3).map((similar) => (
                  <div
                    key={similar.detection_id}
                    className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm"
                  >
                    <img
                      src={api.getImageUrl(similar.photo_path, 40)}
                      alt="Similar face"
                      className="w-5 h-5 rounded-full object-cover"
                    />
                    <span>{(similar.similarity * 100).toFixed(0)}% match</span>
                    {similar.person_label && (
                      <span className="text-xs bg-blue-500/30 px-1 rounded">
                        {similar.person_label}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search for people */}
          <div className="mb-3">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search people..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-3 py-2 bg-white/10 rounded text-sm outline-none"
              />
              <button
                onClick={searchPeople}
                disabled={tagging}
                className={`btn-glass ${tagging ? 'btn-glass--muted' : 'btn-glass--primary'} px-3 py-2`}
              >
                <Search size={16} />
              </button>
            </div>
          </div>

          {/* Suggested people */}
          {suggestions.length > 0 && (
            <div className="mb-3">
              <h4 className="text-sm font-medium text-foreground mb-2">Suggested People</h4>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((person) => (
                  <button
                    key={person.cluster_id}
                    onClick={() => tagFace(person.cluster_id)}
                    disabled={tagging}
                    className="flex items-center gap-2 px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm hover:bg-green-500/30"
                  >
                    {person.thumbnail ? (
                      <img
                        src={person.thumbnail}
                        alt={person.label}
                        className="w-5 h-5 rounded-full object-cover"
                      />
                    ) : (
                      <User size={14} />
                    )}
                    <span>{person.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Create new person */}
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Or Create New Person</h4>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Person name"
                className="flex-1 px-3 py-2 bg-white/10 rounded text-sm outline-none"
              />
              <button
                className="btn-glass btn-glass--primary px-3 py-2"
                disabled={tagging}
              >
                <User size={16} />
                <span>Create</span>
              </button>
            </div>
          </div>

          {/* Tagging status */}
          {tagging && (
            <div className="mt-3 p-2 bg-white/5 rounded-lg flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="animate-spin" size={16} />
              <span>Tagging face...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Helper function to calculate face bounding box style
function faceBoundingBoxStyle(bbox: { x: number; y: number; width: number; height: number }) {
  return {
    left: `${bbox.x * 100}%`,
    top: `${bbox.y * 100}%`,
    width: `${bbox.width * 100}%`,
    height: `${bbox.height * 100}%`,
  };
}