import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UserCircle2,
  RotateCw,
  Search,
  MoreHorizontal,
  Eye,
  EyeOff,
  Users,
  Edit3,
} from 'lucide-react';
import { api } from '../../api';
import type { SimilarFace, SimilarFacesResult } from '../../api';
import { useToast } from '../ui/useToast';

interface FaceCluster {
  id: string;
  label?: string;
  cluster_label?: string;
  face_count?: number;
  face_ids?: string[];
  confidence?: number;
  representative_face?: {
    detection_id: string;
    photo_path: string;
    quality_score?: number;
  };
}

interface PhotoFacePanelProps {
  faceClusters: FaceCluster[];
  onRefresh: () => void;
  isLoading: boolean;
  onNavigateToPeople?: () => void;
}

interface ContextMenuState {
  isOpen: boolean;
  x: number;
  y: number;
  cluster: FaceCluster | null;
}

export const PhotoFacePanel: React.FC<PhotoFacePanelProps> = ({
  faceClusters,
  onRefresh,
  isLoading,
  onNavigateToPeople
}) => {
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    isOpen: false,
    x: 0,
    y: 0,
    cluster: null
  });
  const [similarFacesModal, setSimilarFacesModal] = useState<{
    isOpen: boolean;
    cluster: FaceCluster | null;
  }>({ isOpen: false, cluster: null });
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { showToast } = useToast();

  const handleContextMenu = useCallback((e: React.MouseEvent, cluster: FaceCluster) => {
    e.preventDefault();
    e.stopPropagation();

    setContextMenu({
      isOpen: true,
      x: e.clientX,
      y: e.clientY,
      cluster
    });
  }, []);

  const closeContextMenu = useCallback(() => {
    setContextMenu({ isOpen: false, x: 0, y: 0, cluster: null });
  }, []);

  const handleFindSimilar = useCallback(async (cluster: FaceCluster) => {
    if (!cluster.face_ids?.[0]) return;

    setSimilarFacesModal({ isOpen: true, cluster });
    closeContextMenu();
  }, [closeContextMenu]);

  const handleHidePerson = useCallback(async (cluster: FaceCluster) => {
    setActionLoading(`hide-${cluster.id}`);
    try {
      await api.hideCluster(cluster.id);
      showToast('Person hidden successfully', 'success');
      onRefresh();
    } catch (err) {
      console.error('Failed to hide person:', err);
      showToast('Failed to hide person', 'error');
    } finally {
      setActionLoading(null);
    }
    closeContextMenu();
  }, [closeContextMenu, onRefresh, showToast]);

  const handleRenamePerson = useCallback(async (cluster: FaceCluster) => {
    const newName = prompt('Enter new name:', cluster.label || '');
    if (!newName) return;

    setActionLoading(`rename-${cluster.id}`);
    try {
      await api.renameCluster(cluster.id, newName);
      showToast('Person renamed successfully', 'success');
      onRefresh();
    } catch (err) {
      console.error('Failed to rename person:', err);
      showToast('Failed to rename person', 'error');
    } finally {
      setActionLoading(null);
    }
    closeContextMenu();
  }, [closeContextMenu, onRefresh, showToast]);

  const handleViewAllPhotos = useCallback(() => {
    // Navigate to people page with this person selected
    if (onNavigateToPeople) {
      onNavigateToPeople();
      // Could also pass cluster ID to pre-select
    }
    closeContextMenu();
  }, [closeContextMenu, onNavigateToPeople]);

  const getFaceImageUrl = useCallback((cluster: FaceCluster) => {
    if (cluster.face_ids?.[0]) {
      return `/api/faces/crop/${cluster.face_ids[0]}?size=40`;
    }
    return null;
  }, []);

  const getQualityColor = useCallback((confidence?: number) => {
    if (!confidence) return 'text-white/60';
    if (confidence >= 0.9) return 'text-green-400';
    if (confidence >= 0.7) return 'text-yellow-400';
    return 'text-orange-400';
  }, []);

  // Close context menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => closeContextMenu();
    if (contextMenu.isOpen) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu.isOpen, closeContextMenu]);

  if (faceClusters.length === 0) {
    return null;
  }

  return (
    <>
      <div className='glass-surface rounded-xl p-3'>
        <div className='flex items-center justify-between gap-2 mb-3'>
          <div className='text-xs uppercase tracking-wider text-white/60 flex items-center gap-2'>
            <UserCircle2 size={12} />
            People ({faceClusters.length})
          </div>
          <div className='flex items-center gap-1'>
            {onNavigateToPeople && (
              <button
                className='btn-glass btn-glass--muted w-7 h-7 p-0 justify-center'
                onClick={onNavigateToPeople}
                title='View all people'
              >
                <Users size={12} />
              </button>
            )}
            <button
              className='btn-glass btn-glass--muted w-7 h-7 p-0 justify-center'
              onClick={onRefresh}
              disabled={isLoading}
              title='Refresh faces'
            >
              <RotateCw size={12} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        <div className='space-y-2'>
          {faceClusters.map((cluster, idx) => {
            const faceImageUrl = getFaceImageUrl(cluster);
            const displayName = cluster.label || cluster.cluster_label || `Person ${cluster.id || idx + 1}`;
            const isLoading = actionLoading?.includes(cluster.id);

            return (
              <motion.div
                key={cluster.id || idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className='flex items-center gap-3 p-2 rounded-lg glass-surface hover:bg-white/5 transition-colors group'
                onContextMenu={(e) => handleContextMenu(e, cluster)}
              >
                {/* Face thumbnail */}
                <div className='relative w-8 h-8 rounded-full overflow-hidden bg-white/10 flex-shrink-0'>
                  {faceImageUrl ? (
                    <img
                      src={faceImageUrl}
                      alt={displayName}
                      className='w-full h-full object-cover'
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className='w-full h-full flex items-center justify-center'>
                      <UserCircle2 size={16} className='text-white/40' />
                    </div>
                  )}

                  {/* Quality indicator */}
                  {cluster.confidence && (
                    <div className='absolute -top-1 -right-1 w-3 h-3 rounded-full bg-black/50 flex items-center justify-center'>
                      <div
                        className={`w-1.5 h-1.5 rounded-full ${getQualityColor(cluster.confidence)}`}
                        title={`Confidence: ${Math.round(cluster.confidence * 100)}%`}
                      />
                    </div>
                  )}
                </div>

                {/* Person info */}
                <div className='flex-1 min-w-0'>
                  <div className='text-sm text-white/90 font-medium truncate'>
                    {displayName}
                  </div>
                  {cluster.face_count && (
                    <div className='text-xs text-white/60'>
                      {cluster.face_count} face{cluster.face_count === 1 ? '' : 's'}
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className='flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity'>
                  <button
                    className='btn-glass btn-glass--muted w-6 h-6 p-0 justify-center'
                    onClick={() => handleFindSimilar(cluster)}
                    title='Find similar faces'
                    disabled={isLoading}
                  >
                    <Search size={10} />
                  </button>
                  <button
                    className='btn-glass btn-glass--muted w-6 h-6 p-0 justify-center'
                    onClick={(e) => handleContextMenu(e, cluster)}
                    title='More actions'
                    disabled={isLoading}
                  >
                    <MoreHorizontal size={10} />
                  </button>
                </div>

                {/* Loading indicator */}
                {isLoading && (
                  <div className='w-4 h-4 border border-white/20 border-t-white/60 rounded-full animate-spin' />
                )}
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Context Menu */}
      <AnimatePresence>
        {contextMenu.isOpen && contextMenu.cluster && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.1 }}
            className='fixed z-50 glass-surface glass-surface--strong rounded-lg shadow-xl border border-white/10 py-1 min-w-[160px]'
            style={{
              left: Math.min(contextMenu.x, window.innerWidth - 180),
              top: Math.min(contextMenu.y, window.innerHeight - 200)
            }}
          >
            <button
              className='w-full px-3 py-2 text-left text-sm text-white/90 hover:bg-white/10 flex items-center gap-2'
              onClick={handleViewAllPhotos}
            >
              <Eye size={14} />
              View all photos
            </button>

            <button
              className='w-full px-3 py-2 text-left text-sm text-white/90 hover:bg-white/10 flex items-center gap-2'
              onClick={() => handleFindSimilar(contextMenu.cluster!)}
            >
              <Search size={14} />
              Find similar faces
            </button>

            <div className='h-px bg-white/10 my-1' />

            <button
              className='w-full px-3 py-2 text-left text-sm text-white/90 hover:bg-white/10 flex items-center gap-2'
              onClick={() => handleRenamePerson(contextMenu.cluster!)}
            >
              <Edit3 size={14} />
              Rename person
            </button>

            <button
              className='w-full px-3 py-2 text-left text-sm text-white/90 hover:bg-white/10 flex items-center gap-2'
              onClick={() => handleHidePerson(contextMenu.cluster!)}
            >
              <EyeOff size={14} />
              Hide person
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Similar Faces Modal */}
      <AnimatePresence>
        {similarFacesModal.isOpen && similarFacesModal.cluster && (
          <SimilarFacesModal
            cluster={similarFacesModal.cluster}
            onClose={() => setSimilarFacesModal({ isOpen: false, cluster: null })}
          />
        )}
      </AnimatePresence>
    </>
  );
};

interface SimilarFacesModalProps {
  cluster: FaceCluster;
  onClose: () => void;
}

const SimilarFacesModal: React.FC<SimilarFacesModalProps> = ({ cluster, onClose }) => {
  const [similarFaces, setSimilarFaces] = useState<SimilarFace[]>([]);
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState(0.7);

  const { showToast } = useToast();

  const loadSimilarFaces = useCallback(async () => {
    if (!cluster.face_ids?.[0]) return;

    setLoading(true);
    try {
      const response: SimilarFacesResult = await api.findSimilarFaces(
        cluster.face_ids[0],
        threshold,
        20,
        false
      );
      setSimilarFaces(response.similar_faces || []);
    } catch (err) {
      console.error('Failed to find similar faces:', err);
      showToast('Failed to find similar faces', 'error');
      setSimilarFaces([]);
    } finally {
      setLoading(false);
    }
  }, [cluster.face_ids, threshold, showToast]);

  React.useEffect(() => {
    loadSimilarFaces();
  }, [loadSimilarFaces]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className='fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm'
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className='glass-surface glass-surface--strong rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col'
        onClick={(e) => e.stopPropagation()}
      >
        <div className='flex items-center justify-between mb-4'>
          <h3 className='text-lg font-semibold text-white'>
            Similar to {cluster.label || `Person ${cluster.id}`}
          </h3>
          <button
            onClick={onClose}
            className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center'
          >
            ×
          </button>
        </div>

        <div className='flex items-center gap-4 mb-4'>
          <label className='text-sm text-white/70'>Similarity threshold:</label>
          <input
            type='range'
            min='0.3'
            max='0.9'
            step='0.05'
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className='flex-1'
          />
          <span className='text-sm text-white/90 min-w-[3rem]'>
            {Math.round(threshold * 100)}%
          </span>
        </div>

        <div className='flex-1 overflow-y-auto'>
          {loading ? (
            <div className='flex items-center justify-center py-8'>
              <div className='w-6 h-6 border border-white/20 border-t-white/60 rounded-full animate-spin' />
            </div>
          ) : similarFaces.length > 0 ? (
            <div className='grid grid-cols-4 gap-3'>
              {similarFaces.map((face, idx) => (
                <div key={idx} className='glass-surface rounded-lg p-2 text-center'>
                  <img
                    src={`/api/faces/crop/${face.detection_id}?size=80`}
                    alt='Similar face'
                    className='w-full aspect-square object-cover rounded mb-2'
                  />
                  <div className='text-xs text-white/70'>
                    {Math.round(face.similarity * 100)}% match
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className='text-center py-8 text-white/60'>
              No similar faces found at this threshold
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};
