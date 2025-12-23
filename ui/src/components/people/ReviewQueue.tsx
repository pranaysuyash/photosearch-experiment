/**
 * ReviewQueue Component - Phase 5.1: Needs Review UI
 *
 * Displays faces that need human review (gray zone assignments).
 * Allows confirm, reject, or skip actions with undo support.
 */
import { useState, useEffect, useCallback } from 'react';
import { Check, X, SkipForward, RefreshCw, AlertCircle, User } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface ReviewItem {
    id: number;
    detection_id: string;
    candidate_cluster_id: string;
    similarity: number;
    reason: string;
    status: string;
    created_at: string;
    photo_path: string;
    bounding_box: { x: number; y: number; w: number; h: number };
    quality_score: number | null;
    candidate_label: string | null;
    candidate_face_count: number | null;
}

interface ReviewQueueProps {
    onCountChange?: (count: number) => void;
}

const REASON_LABELS: Record<string, string> = {
    gray_zone: 'Below auto-assign threshold',
    low_confidence: 'Low confidence match',
    ambiguous: 'Multiple possible matches',
};

export default function ReviewQueue({ onCountChange }: ReviewQueueProps) {
    const [items, setItems] = useState<ReviewItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [processingId, setProcessingId] = useState<string | null>(null);
    const [offset, setOffset] = useState(0);
    const limit = 10;

    const fetchQueue = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await api.getReviewQueue(limit, offset);
            setItems(data.items || []);
            setTotal(data.total || 0);
            onCountChange?.(data.total || 0);
        } catch (err) {
            setError('Failed to load review queue');
            console.error('Error fetching review queue:', err);
        } finally {
            setLoading(false);
        }
    }, [offset, onCountChange]);

    useEffect(() => {
        fetchQueue();
    }, [fetchQueue]);

    const handleResolve = async (
        detectionId: string,
        action: 'confirm' | 'reject' | 'skip',
        clusterId?: string
    ) => {
        try {
            setProcessingId(detectionId);
            await api.resolveReviewItem(detectionId, action, clusterId);
            // Remove from local state immediately for responsive UI
            setItems((prev) => prev.filter((item) => item.detection_id !== detectionId));
            setTotal((prev) => Math.max(0, prev - 1));
            onCountChange?.(Math.max(0, total - 1));
        } catch (err) {
            console.error(`Error ${action}ing review item:`, err);
            setError(`Failed to ${action} item`);
        } finally {
            setProcessingId(null);
        }
    };

    const getFaceCropUrl = (photoPath: string, bbox: ReviewItem['bounding_box']) => {
        // Use the face crop endpoint if available, otherwise use photo thumbnail
        const encodedPath = encodeURIComponent(photoPath);
        return `/api/thumbnail/${encodedPath}?size=150`;
    };

    if (loading && items.length === 0) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 1rem' }} />
                <p>Loading review queue...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <AlertCircle size={24} style={{ margin: '0 auto 1rem', color: 'var(--color-error)' }} />
                <p>{error}</p>
                <button onClick={fetchQueue} className={glass.button} style={{ marginTop: '1rem' }}>
                    Retry
                </button>
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <Check size={32} style={{ margin: '0 auto 1rem', color: 'var(--color-success)' }} />
                <h3 style={{ margin: '0 0 0.5rem' }}>All caught up!</h3>
                <p style={{ opacity: 0.7 }}>No faces need review right now.</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>
                    Needs Review <span style={{ opacity: 0.6 }}>({total})</span>
                </h3>
                <button onClick={fetchQueue} className={glass.button} disabled={loading}>
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            {/* Queue Items */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {items.map((item) => (
                    <div
                        key={item.detection_id}
                        className={glass.surface}
                        style={{
                            padding: '1rem',
                            display: 'grid',
                            gridTemplateColumns: '80px 1fr auto',
                            gap: '1rem',
                            alignItems: 'center',
                            opacity: processingId === item.detection_id ? 0.5 : 1,
                            transition: 'opacity 0.2s',
                        }}
                    >
                        {/* Face Thumbnail */}
                        <div
                            style={{
                                width: 80,
                                height: 80,
                                borderRadius: '8px',
                                overflow: 'hidden',
                                background: 'var(--glass-bg)',
                            }}
                        >
                            <img
                                src={getFaceCropUrl(item.photo_path, item.bounding_box)}
                                alt="Face to review"
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = 'none';
                                }}
                            />
                        </div>

                        {/* Details */}
                        <div>
                            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                                {item.candidate_label ? (
                                    <>
                                        Might be: <strong>{item.candidate_label}</strong>
                                    </>
                                ) : (
                                    <>
                                        <User size={14} style={{ display: 'inline', marginRight: 4 }} />
                                        Unknown Person
                                    </>
                                )}
                            </div>
                            <div style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                                Similarity: {(item.similarity * 100).toFixed(0)}%
                            </div>
                            <div style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '0.25rem' }}>
                                {REASON_LABELS[item.reason] || item.reason}
                            </div>
                        </div>

                        {/* Actions */}
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                                onClick={() =>
                                    handleResolve(item.detection_id, 'confirm', item.candidate_cluster_id)
                                }
                                className={glass.button}
                                disabled={processingId === item.detection_id}
                                title="Confirm this match"
                                style={{
                                    background: 'var(--color-success)',
                                    color: 'white',
                                    padding: '0.5rem',
                                }}
                            >
                                <Check size={18} />
                            </button>
                            <button
                                onClick={() =>
                                    handleResolve(item.detection_id, 'reject', item.candidate_cluster_id)
                                }
                                className={glass.button}
                                disabled={processingId === item.detection_id}
                                title="Not this person"
                                style={{
                                    background: 'var(--color-error)',
                                    color: 'white',
                                    padding: '0.5rem',
                                }}
                            >
                                <X size={18} />
                            </button>
                            <button
                                onClick={() => handleResolve(item.detection_id, 'skip')}
                                className={glass.button}
                                disabled={processingId === item.detection_id}
                                title="Skip for now"
                                style={{ padding: '0.5rem' }}
                            >
                                <SkipForward size={18} />
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {/* Pagination */}
            {total > limit && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                    <button
                        onClick={() => setOffset(Math.max(0, offset - limit))}
                        disabled={offset === 0}
                        className={glass.button}
                    >
                        Previous
                    </button>
                    <span style={{ padding: '0.5rem', opacity: 0.7 }}>
                        {offset + 1}-{Math.min(offset + limit, total)} of {total}
                    </span>
                    <button
                        onClick={() => setOffset(offset + limit)}
                        disabled={offset + limit >= total}
                        className={glass.button}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
