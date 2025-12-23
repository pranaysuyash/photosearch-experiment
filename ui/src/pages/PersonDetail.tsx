/**
 * Person Detail Page - Shows photos containing a specific person
 *
 * Phase 2 Features:
 * - Confirm/reject controls on each face
 * - Assignment state badges (auto/confirmed/rejected)
 * - Multi-select mode for split flow
 * - Move selected faces to another person
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    ArrowLeft, User, Camera, RefreshCw, Check, X,
    CheckCircle2, XCircle, AlertCircle, Move, UserPlus,
    Loader2, Undo2, AlertTriangle, ChevronDown, ChevronUp, Scissors, ToggleLeft, ToggleRight
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';
import SecureLazyImage from '../components/gallery/SecureLazyImage';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import type { Photo } from '../api';

interface PersonPhoto {
    path: string;
    face_id: number;
    detection_id?: string;
    bounding_box: number[] | null;
    confidence: number;
    assignment_state?: 'auto' | 'user_confirmed' | 'user_rejected';
}

interface ClusterInfo {
    id: string;
    label: string;
    face_count: number;
}

type AssignmentState = 'auto' | 'user_confirmed' | 'user_rejected';

export default function PersonDetail() {
    const { clusterId } = useParams<{ clusterId: string }>();
    const navigate = useNavigate();
    const { openForPhoto } = usePhotoViewer();
    const [photos, setPhotos] = useState<PersonPhoto[]>([]);
    const [clusterInfo, setClusterInfo] = useState<ClusterInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Phase 2 state
    const [selectedFaces, setSelectedFaces] = useState<Set<string>>(new Set());
    const [selectionMode, setSelectionMode] = useState(false);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [canUndo, setCanUndo] = useState(false);
    const [showSplitDialog, setShowSplitDialog] = useState(false);
    const [newPersonName, setNewPersonName] = useState('');

    // Phase 5.2: Mixed cluster warning state
    interface CoherenceData {
        coherence_score: number;
        variance: number;
        low_quality_ratio: number;
        is_mixed_suspected: boolean;
        face_count: number;
        avg_confidence: number;
    }
    const [coherence, setCoherence] = useState<CoherenceData | null>(null);
    const [showMixedDetails, setShowMixedDetails] = useState(false);

    // Phase 6: Privacy controls state
    const [indexingEnabled, setIndexingEnabled] = useState(true);
    const [indexingLoading, setIndexingLoading] = useState(false);

    const fetchPhotos = useCallback(async () => {
        if (!clusterId) return;

        setLoading(true);
        setError(null);
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/clusters/${clusterId}/photos`
            );
            const data = await response.json();
            setPhotos(data.results || []);

            // Also fetch cluster info
            const clustersRes = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/clusters`
            );
            const clustersData = await clustersRes.json();
            const cluster = clustersData.clusters?.find((c: any) => c.id === clusterId);
            if (cluster) {
                setClusterInfo({
                    id: cluster.id,
                    label: cluster.label || `Person ${cluster.id}`,
                    face_count: cluster.face_count
                });
            }
        } catch (err) {
            console.error('Failed to fetch person photos:', err);
            setError('Failed to load photos');
        } finally {
            setLoading(false);
        }
    }, [clusterId]);

    useEffect(() => {
        fetchPhotos();
    }, [fetchPhotos]);

    // Fetch coherence data for mixed cluster detection
    useEffect(() => {
        if (clusterId) {
            api.getClusterCoherence(clusterId)
                .then(setCoherence)
                .catch(console.error);
        }
    }, [clusterId]);

    // Fetch indexing status for privacy controls
    useEffect(() => {
        if (clusterId) {
            api.getPersonIndexingStatus(clusterId)
                .then((data) => setIndexingEnabled(data.enabled))
                .catch(console.error);
        }
    }, [clusterId]);

    // Toggle indexing enabled/disabled
    const handleToggleIndexing = async () => {
        if (!clusterId) return;
        setIndexingLoading(true);
        try {
            await api.setPersonIndexingEnabled(clusterId, !indexingEnabled);
            setIndexingEnabled(!indexingEnabled);
        } catch (err) {
            console.error('Failed to toggle indexing:', err);
        } finally {
            setIndexingLoading(false);
        }
    };

    // Clear success message after delay
    useEffect(() => {
        if (successMessage) {
            const timer = setTimeout(() => setSuccessMessage(null), 3000);
            return () => clearTimeout(timer);
        }
    }, [successMessage]);

    // Confirm a face assignment
    const handleConfirm = async (photo: PersonPhoto) => {
        if (!clusterId) return;
        const faceId = photo.detection_id || String(photo.face_id);

        try {
            setActionLoading(faceId);
            await api.confirmFace(faceId, clusterId);
            setSuccessMessage('Face confirmed');
            setCanUndo(true);

            // Update local state
            setPhotos(prev => prev.map(p =>
                (p.detection_id || String(p.face_id)) === faceId
                    ? { ...p, assignment_state: 'user_confirmed' as AssignmentState }
                    : p
            ));
        } catch (err) {
            console.error('Failed to confirm face:', err);
            setError('Failed to confirm face');
        } finally {
            setActionLoading(null);
        }
    };

    // Reject a face from this cluster
    const handleReject = async (photo: PersonPhoto) => {
        if (!clusterId) return;
        const faceId = photo.detection_id || String(photo.face_id);

        try {
            setActionLoading(faceId);
            await api.rejectFace(faceId, clusterId);
            setSuccessMessage('Face rejected - moved to Unknown');
            setCanUndo(true);

            // Remove from local state
            setPhotos(prev => prev.filter(p =>
                (p.detection_id || String(p.face_id)) !== faceId
            ));
        } catch (err) {
            console.error('Failed to reject face:', err);
            setError('Failed to reject face');
        } finally {
            setActionLoading(null);
        }
    };

    // Toggle face selection
    const toggleFaceSelection = (photo: PersonPhoto) => {
        const faceId = photo.detection_id || String(photo.face_id);
        setSelectedFaces(prev => {
            const next = new Set(prev);
            if (next.has(faceId)) {
                next.delete(faceId);
            } else {
                next.add(faceId);
            }
            return next;
        });
    };

    // Split selected faces to new person
    const handleSplit = async () => {
        if (selectedFaces.size === 0) return;

        try {
            setActionLoading('split');
            const detectionIds = Array.from(selectedFaces);
            const result = await api.splitFaces(detectionIds, newPersonName || undefined);

            setSuccessMessage(`Created new person with ${result.faces_moved} faces`);
            setCanUndo(true);
            setSelectedFaces(new Set());
            setSelectionMode(false);
            setShowSplitDialog(false);
            setNewPersonName('');

            // Refresh photos
            await fetchPhotos();
        } catch (err) {
            console.error('Failed to split faces:', err);
            setError('Failed to split faces');
        } finally {
            setActionLoading(null);
        }
    };

    // Undo last operation
    const handleUndo = async () => {
        try {
            setActionLoading('undo');
            const result = await api.undoLastOperation();
            if (result.success) {
                setSuccessMessage(`Undid ${result.operation_type}`);
                setCanUndo(false);
                await fetchPhotos();
            }
        } catch (err) {
            console.error('Undo failed:', err);
            setError('Failed to undo');
        } finally {
            setActionLoading(null);
        }
    };

    // Get assignment state badge
    const getStateBadge = (state?: AssignmentState) => {
        switch (state) {
            case 'user_confirmed':
                return (
                    <div className="absolute top-2 left-2 bg-green-500/80 backdrop-blur-sm rounded-full p-1" title="Confirmed">
                        <CheckCircle2 size={14} className="text-white" />
                    </div>
                );
            case 'user_rejected':
                return (
                    <div className="absolute top-2 left-2 bg-red-500/80 backdrop-blur-sm rounded-full p-1" title="Rejected">
                        <XCircle size={14} className="text-white" />
                    </div>
                );
            case 'auto':
            default:
                return (
                    <div className="absolute top-2 left-2 bg-blue-500/80 backdrop-blur-sm rounded-full p-1" title="Auto-detected">
                        <AlertCircle size={14} className="text-white" />
                    </div>
                );
        }
    };

    return (
        <div className="min-h-screen">
            {/* Header */}
            <div className="border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => navigate('/people')}
                                className="btn-glass btn-glass--muted p-2"
                            >
                                <ArrowLeft size={20} />
                            </button>

                            <div className="flex items-center gap-3">
                                <div className={`${glass.surface} p-3 rounded-xl border border-white/10`}>
                                    <User size={24} className="text-primary" />
                                </div>
                                <div>
                                    <h1 className="text-xl font-semibold text-foreground">
                                        {clusterInfo?.label || `Person ${clusterId}`}
                                    </h1>
                                    <p className="text-sm text-muted-foreground">
                                        {photos.length} photos • {clusterInfo?.face_count || 0} appearances
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-2">
                            {/* Indexing toggle - Phase 6 */}
                            <button
                                onClick={handleToggleIndexing}
                                disabled={indexingLoading}
                                className={`btn-glass px-3 py-2 flex items-center gap-1 ${indexingEnabled
                                        ? 'btn-glass--muted'
                                        : 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400'
                                    }`}
                                title={indexingEnabled ? 'Auto-assignment enabled' : 'Auto-assignment disabled'}
                            >
                                {indexingLoading ? (
                                    <Loader2 className="animate-spin" size={16} />
                                ) : indexingEnabled ? (
                                    <ToggleRight size={16} className="text-green-400" />
                                ) : (
                                    <ToggleLeft size={16} />
                                )}
                                <span className="hidden sm:inline">
                                    {indexingEnabled ? 'Auto-assign ON' : 'Auto-assign OFF'}
                                </span>
                            </button>

                            {/* Undo button */}
                            {canUndo && (
                                <button
                                    onClick={handleUndo}
                                    disabled={actionLoading === 'undo'}
                                    className="btn-glass btn-glass--muted px-3 py-2 flex items-center gap-1"
                                >
                                    {actionLoading === 'undo' ? (
                                        <Loader2 className="animate-spin" size={16} />
                                    ) : (
                                        <Undo2 size={16} />
                                    )}
                                    <span>Undo</span>
                                </button>
                            )}

                            {/* Selection mode toggle */}
                            <button
                                onClick={() => {
                                    setSelectionMode(!selectionMode);
                                    if (selectionMode) {
                                        setSelectedFaces(new Set());
                                    }
                                }}
                                className={`btn-glass px-3 py-2 flex items-center gap-1 ${selectionMode ? 'btn-glass--primary' : 'btn-glass--muted'
                                    }`}
                            >
                                <Move size={16} />
                                <span>{selectionMode ? `${selectedFaces.size} selected` : 'Select'}</span>
                            </button>

                            {/* Split button (when faces selected) */}
                            {selectionMode && selectedFaces.size > 0 && (
                                <button
                                    onClick={() => setShowSplitDialog(true)}
                                    className="btn-glass btn-glass--primary px-3 py-2 flex items-center gap-1"
                                >
                                    <UserPlus size={16} />
                                    <span>Move to New Person</span>
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Success message */}
            {successMessage && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                    <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-lg text-green-400 flex items-center gap-2">
                        <Check size={16} />
                        <span>{successMessage}</span>
                    </div>
                </div>
            )}

            {/* Error message */}
            {error && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                    <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 flex items-center justify-between">
                        <span>{error}</span>
                        <button onClick={() => setError(null)}>
                            <X size={16} />
                        </button>
                    </div>
                </div>
            )}

            {/* Mixed Cluster Warning Panel - Phase 5.2 */}
            {coherence?.is_mixed_suspected && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                    <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                        <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3">
                                <AlertTriangle size={20} className="text-yellow-500 mt-0.5" />
                                <div>
                                    <h3 className="font-semibold text-yellow-400">
                                        This cluster may contain multiple people
                                    </h3>
                                    <p className="text-sm text-yellow-400/80 mt-1">
                                        Our analysis detected higher than normal variance in face embeddings.
                                        Review the faces below and use Split mode to separate different people.
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowMixedDetails(!showMixedDetails)}
                                className="text-yellow-400 hover:text-yellow-300 p-1"
                            >
                                {showMixedDetails ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            </button>
                        </div>

                        {/* Expandable stats */}
                        {showMixedDetails && (
                            <div className="mt-4 pt-4 border-t border-yellow-500/20 grid grid-cols-2 sm:grid-cols-4 gap-4">
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-yellow-400">
                                        {(coherence.coherence_score * 100).toFixed(0)}%
                                    </div>
                                    <div className="text-xs text-yellow-400/60">Coherence</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-yellow-400">
                                        {coherence.variance.toFixed(3)}
                                    </div>
                                    <div className="text-xs text-yellow-400/60">Variance</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-yellow-400">
                                        {(coherence.low_quality_ratio * 100).toFixed(0)}%
                                    </div>
                                    <div className="text-xs text-yellow-400/60">Low Quality</div>
                                </div>
                                <div className="text-center">
                                    <div className="text-2xl font-bold text-yellow-400">
                                        {(coherence.avg_confidence * 100).toFixed(0)}%
                                    </div>
                                    <div className="text-xs text-yellow-400/60">Avg Confidence</div>
                                </div>
                            </div>
                        )}

                        {/* Split Mode CTA */}
                        <div className="mt-4 flex gap-3">
                            <button
                                onClick={() => setSelectionMode(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-400 text-black font-medium rounded-lg transition-colors"
                            >
                                <Scissors size={16} />
                                Enter Split Mode
                            </button>
                            <button
                                onClick={() => setShowMixedDetails(!showMixedDetails)}
                                className="text-yellow-400/70 hover:text-yellow-400 text-sm"
                            >
                                {showMixedDetails ? 'Hide' : 'Show'} Details
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Loading */}
                {loading && (
                    <div className="flex items-center justify-center py-20">
                        <div className="flex items-center gap-3">
                            <RefreshCw size={20} className="animate-spin text-muted-foreground" />
                            <span className="text-muted-foreground">Loading photos...</span>
                        </div>
                    </div>
                )}

                {/* No Photos */}
                {!loading && !error && photos.length === 0 && (
                    <div className="text-center py-20">
                        <Camera size={48} className="mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">No Photos Found</h3>
                        <p className="text-muted-foreground">
                            This person doesn't appear in any photos yet.
                        </p>
                    </div>
                )}

                {/* Photo Grid */}
                {!loading && !error && photos.length > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                        {photos.map((photo, index) => {
                            const faceId = photo.detection_id || String(photo.face_id);
                            const isSelected = selectedFaces.has(faceId);
                            const isLoading = actionLoading === faceId;

                            return (
                                <div
                                    key={`${photo.path}-${index}`}
                                    className={`${glass.surface} rounded-xl overflow-hidden border transition-all relative group ${isSelected
                                        ? 'border-blue-400 ring-2 ring-blue-400/50'
                                        : 'border-white/10 hover:border-white/20'
                                        } ${selectionMode ? 'cursor-pointer' : ''}`}
                                    onClick={() => {
                                        if (selectionMode) {
                                            toggleFaceSelection(photo);
                                        } else {
                                            // Open in photo viewer
                                            const photoAsPhotoType: Photo = {
                                                path: photo.path,
                                                filename: photo.path.split('/').pop() || '',
                                                score: photo.confidence,
                                                metadata: {}
                                            };
                                            const allPhotosAsPhotoType: Photo[] = photos.map(p => ({
                                                path: p.path,
                                                filename: p.path.split('/').pop() || '',
                                                score: p.confidence,
                                                metadata: {}
                                            }));
                                            openForPhoto(allPhotosAsPhotoType, photoAsPhotoType);
                                        }
                                    }}
                                >
                                    <div className="aspect-square relative">
                                        <SecureLazyImage
                                            path={photo.path}
                                            size={400}
                                            alt={`Photo containing ${clusterInfo?.label || 'person'}`}
                                            className="w-full h-full object-cover"
                                            showBadge={false}
                                        />

                                        {/* Assignment state badge */}
                                        {getStateBadge(photo.assignment_state)}

                                        {/* Selection checkbox */}
                                        {selectionMode && (
                                            <div className={`absolute top-2 right-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${isSelected
                                                ? 'bg-blue-500 border-blue-500'
                                                : 'bg-black/40 border-white/50'
                                                }`}>
                                                {isSelected && <Check size={14} className="text-white" />}
                                            </div>
                                        )}

                                        {/* Confidence badge */}
                                        <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                            {Math.round(photo.confidence * 100)}% match
                                        </div>

                                        {/* Loading overlay */}
                                        {isLoading && (
                                            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                                                <Loader2 className="animate-spin text-white" size={24} />
                                            </div>
                                        )}
                                    </div>

                                    {/* Confirm/Reject controls (shown on hover, not in selection mode) */}
                                    {!selectionMode && !isLoading && (
                                        <div className="absolute bottom-0 left-0 right-0 p-2 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                                            <div className="flex gap-2 justify-center">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleConfirm(photo);
                                                    }}
                                                    className="px-3 py-1.5 bg-green-500/80 hover:bg-green-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors"
                                                    title="Confirm: This is the right person"
                                                >
                                                    <CheckCircle2 size={14} />
                                                    <span>Confirm</span>
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleReject(photo);
                                                    }}
                                                    className="px-3 py-1.5 bg-red-500/80 hover:bg-red-500 rounded-lg text-xs text-white flex items-center gap-1 transition-colors"
                                                    title="Reject: Not this person"
                                                >
                                                    <XCircle size={14} />
                                                    <span>Not them</span>
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Split Dialog */}
            {showSplitDialog && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className={`${glass.surfaceStrong} rounded-xl p-6 max-w-md w-full mx-4 border border-white/10`}>
                        <h2 className="text-lg font-semibold text-foreground mb-4">
                            Move {selectedFaces.size} Faces to New Person
                        </h2>

                        <div className="mb-4">
                            <label className="block text-sm text-muted-foreground mb-2">
                                New Person Name (optional)
                            </label>
                            <input
                                type="text"
                                value={newPersonName}
                                onChange={(e) => setNewPersonName(e.target.value)}
                                placeholder="Enter name..."
                                className="w-full px-4 py-2 bg-white/10 rounded-lg outline-none border border-white/10 focus:border-blue-400"
                            />
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => {
                                    setShowSplitDialog(false);
                                    setNewPersonName('');
                                }}
                                className="btn-glass btn-glass--muted flex-1"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSplit}
                                disabled={actionLoading === 'split'}
                                className="btn-glass btn-glass--primary flex-1 flex items-center justify-center gap-2"
                            >
                                {actionLoading === 'split' ? (
                                    <Loader2 className="animate-spin" size={16} />
                                ) : (
                                    <UserPlus size={16} />
                                )}
                                <span>Create Person</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
