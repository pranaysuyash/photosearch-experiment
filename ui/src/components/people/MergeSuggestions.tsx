/**
 * MergeSuggestions Component - Phase 5.4
 *
 * Displays conservative merge suggestions for face clusters.
 * Shows side-by-side comparison of representative faces with Merge/Dismiss actions.
 */
import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, AlertCircle, Check, X, Users, ArrowRight } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface MergeSuggestion {
    cluster_a_id: string;
    cluster_a_label: string;
    cluster_a_face_count: number;
    cluster_b_id: string;
    cluster_b_label: string;
    cluster_b_face_count: number;
    similarity: number;
    representative_a?: { photo_path: string; detection_id: string };
    representative_b?: { photo_path: string; detection_id: string };
}

interface MergeSuggestionsProps {
    onMerge?: (clusterA: string, clusterB: string) => Promise<void>;
}

export default function MergeSuggestions({ onMerge }: MergeSuggestionsProps) {
    const [suggestions, setSuggestions] = useState<MergeSuggestion[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [processingPair, setProcessingPair] = useState<string | null>(null);

    const fetchSuggestions = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await api.getMergeSuggestions(0.62, 10);
            setSuggestions(data.suggestions || []);
        } catch (err) {
            setError('Failed to load merge suggestions');
            console.error('Error fetching merge suggestions:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSuggestions();
    }, [fetchSuggestions]);

    const handleMerge = async (suggestion: MergeSuggestion) => {
        const pairKey = `${suggestion.cluster_a_id}-${suggestion.cluster_b_id}`;
        setProcessingPair(pairKey);
        try {
            if (onMerge) {
                await onMerge(suggestion.cluster_a_id, suggestion.cluster_b_id);
            } else {
                // Use default merge API
                await api.mergeClusters(suggestion.cluster_a_id, suggestion.cluster_b_id);
            }
            // Remove from local state
            setSuggestions((prev) =>
                prev.filter(
                    (s) =>
                        !(
                            s.cluster_a_id === suggestion.cluster_a_id &&
                            s.cluster_b_id === suggestion.cluster_b_id
                        )
                )
            );
        } catch (err) {
            console.error('Error merging clusters:', err);
            setError('Failed to merge clusters');
        } finally {
            setProcessingPair(null);
        }
    };

    const handleDismiss = async (suggestion: MergeSuggestion) => {
        const pairKey = `${suggestion.cluster_a_id}-${suggestion.cluster_b_id}`;
        setProcessingPair(pairKey);
        try {
            await api.dismissMergeSuggestion(suggestion.cluster_a_id, suggestion.cluster_b_id);
            // Remove from local state
            setSuggestions((prev) =>
                prev.filter(
                    (s) =>
                        !(
                            s.cluster_a_id === suggestion.cluster_a_id &&
                            s.cluster_b_id === suggestion.cluster_b_id
                        )
                )
            );
        } catch (err) {
            console.error('Error dismissing suggestion:', err);
            setError('Failed to dismiss suggestion');
        } finally {
            setProcessingPair(null);
        }
    };

    const getThumbnailUrl = (photoPath: string) => {
        const encodedPath = encodeURIComponent(photoPath);
        return `/api/thumbnail/${encodedPath}?size=120`;
    };

    if (loading && suggestions.length === 0) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 1rem' }} />
                <p>Finding potential duplicates...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <AlertCircle size={24} style={{ margin: '0 auto 1rem', color: 'var(--color-error)' }} />
                <p>{error}</p>
                <button
                    onClick={() => {
                        setError(null);
                        fetchSuggestions();
                    }}
                    className={glass.button}
                    style={{ marginTop: '1rem' }}
                >
                    Retry
                </button>
            </div>
        );
    }

    if (suggestions.length === 0) {
        return (
            <div className={glass.surface} style={{ padding: '2rem', textAlign: 'center' }}>
                <Users size={32} style={{ margin: '0 auto 1rem', color: 'var(--color-success)' }} />
                <h3 style={{ margin: '0 0 0.5rem' }}>No merge suggestions</h3>
                <p style={{ opacity: 0.7 }}>All clusters appear to be distinct people.</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>
                    Merge Suggestions <span style={{ opacity: 0.6 }}>({suggestions.length})</span>
                </h3>
                <button onClick={fetchSuggestions} className={glass.button} disabled={loading}>
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            <p style={{ fontSize: '0.875rem', opacity: 0.7, margin: 0 }}>
                These clusters have similar faces and never appear in the same photo. Review and merge if they're the same person.
            </p>

            {/* Suggestions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {suggestions.map((suggestion) => {
                    const pairKey = `${suggestion.cluster_a_id}-${suggestion.cluster_b_id}`;
                    const isProcessing = processingPair === pairKey;

                    return (
                        <div
                            key={pairKey}
                            className={glass.surface}
                            style={{
                                padding: '1rem',
                                opacity: isProcessing ? 0.5 : 1,
                                transition: 'opacity 0.2s',
                            }}
                        >
                            {/* Side-by-side comparison */}
                            <div
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr auto 1fr',
                                    gap: '1rem',
                                    alignItems: 'center',
                                }}
                            >
                                {/* Cluster A */}
                                <div style={{ textAlign: 'center' }}>
                                    <div
                                        style={{
                                            width: 80,
                                            height: 80,
                                            borderRadius: '50%',
                                            overflow: 'hidden',
                                            margin: '0 auto 0.5rem',
                                            background: 'var(--glass-bg)',
                                        }}
                                    >
                                        {suggestion.representative_a && (
                                            <img
                                                src={getThumbnailUrl(suggestion.representative_a.photo_path)}
                                                alt={suggestion.cluster_a_label}
                                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                        )}
                                    </div>
                                    <div style={{ fontWeight: 600 }}>{suggestion.cluster_a_label}</div>
                                    <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>
                                        {suggestion.cluster_a_face_count} faces
                                    </div>
                                </div>

                                {/* Similarity score */}
                                <div style={{ textAlign: 'center' }}>
                                    <ArrowRight size={24} style={{ opacity: 0.3, marginBottom: '0.25rem' }} />
                                    <div
                                        style={{
                                            fontSize: '1.25rem',
                                            fontWeight: 700,
                                            color:
                                                suggestion.similarity >= 0.7
                                                    ? 'var(--color-success)'
                                                    : 'var(--color-warning)',
                                        }}
                                    >
                                        {(suggestion.similarity * 100).toFixed(0)}%
                                    </div>
                                    <div style={{ fontSize: '0.7rem', opacity: 0.5 }}>similar</div>
                                </div>

                                {/* Cluster B */}
                                <div style={{ textAlign: 'center' }}>
                                    <div
                                        style={{
                                            width: 80,
                                            height: 80,
                                            borderRadius: '50%',
                                            overflow: 'hidden',
                                            margin: '0 auto 0.5rem',
                                            background: 'var(--glass-bg)',
                                        }}
                                    >
                                        {suggestion.representative_b && (
                                            <img
                                                src={getThumbnailUrl(suggestion.representative_b.photo_path)}
                                                alt={suggestion.cluster_b_label}
                                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).style.display = 'none';
                                                }}
                                            />
                                        )}
                                    </div>
                                    <div style={{ fontWeight: 600 }}>{suggestion.cluster_b_label}</div>
                                    <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>
                                        {suggestion.cluster_b_face_count} faces
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div
                                style={{
                                    display: 'flex',
                                    justifyContent: 'center',
                                    gap: '0.5rem',
                                    marginTop: '1rem',
                                }}
                            >
                                <button
                                    onClick={() => handleMerge(suggestion)}
                                    className={glass.button}
                                    disabled={isProcessing}
                                    style={{
                                        background: 'var(--color-success)',
                                        color: 'white',
                                        padding: '0.5rem 1rem',
                                    }}
                                >
                                    <Check size={16} /> Merge
                                </button>
                                <button
                                    onClick={() => handleDismiss(suggestion)}
                                    className={glass.button}
                                    disabled={isProcessing}
                                    style={{ padding: '0.5rem 1rem' }}
                                >
                                    <X size={16} /> Dismiss
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
