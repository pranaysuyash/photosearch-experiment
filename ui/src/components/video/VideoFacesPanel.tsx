/**
 * VideoFacesPanel - Shows people appearing in a video
 *
 * Phase 7.5 Feature: "People in this video" panel with timestamp jump
 */
import { useState, useEffect } from 'react';
import { Users, Clock, Play, ChevronDown, ChevronUp, User } from 'lucide-react';
import { api } from '../../api';

interface VideoPersonAppearance {
    cluster_id: string;
    person_name: string | null;
    track_count: number;
    total_screen_time_ms: number;
    first_appearance_ms: number;
    last_appearance_ms: number;
}

interface VideoFacesPanelProps {
    videoPath: string;
    videoId?: string;
    onSeek?: (timestampMs: number) => void;
    isCollapsed?: boolean;
}

type ApiError = {
    response?: {
        status?: number;
        data?: {
            detail?: string;
        };
    };
    message?: string;
};

function formatTime(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function formatDuration(ms: number): string {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) {
        return `${seconds}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) {
        return `${minutes}m`;
    }
    return `${minutes}m ${remainingSeconds}s`;
}

export function VideoFacesPanel({
    videoPath,
    videoId,
    onSeek,
    isCollapsed: initialCollapsed = false
}: VideoFacesPanelProps) {
    const [people, setPeople] = useState<VideoPersonAppearance[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);
    const [processingStatus, setProcessingStatus] = useState<string | null>(null);

    const getApiErrorMessage = (err: unknown, fallback: string) => {
        return (err as ApiError)?.response?.data?.detail || (err as ApiError)?.message || fallback;
    };

    // Generate video ID from path if not provided
    const effectiveVideoId = videoId || `video_${btoa(videoPath).slice(0, 16)}`;

    useEffect(() => {
        async function loadPeople() {
            setLoading(true);
            setError(null);

            try {
                // First check if video has been processed
                const status = await api.getVideoFaceStatus(effectiveVideoId);

                if (status.status === 'not_found') {
                    setProcessingStatus('not_processed');
                    setPeople([]);
                } else if (status.status === 'processing') {
                    setProcessingStatus('processing');
                    setPeople([]);
                } else {
                    // Get people appearing in video
                    const response = await api.getVideoPeople(effectiveVideoId);
                    setPeople(response.people || []);
                    setProcessingStatus('completed');
                }
            } catch (err: unknown) {
                // 404 means video hasn't been processed
                const apiError = err as ApiError;
                if (apiError.response?.status === 404 || apiError.response?.data?.detail?.includes('not found')) {
                    setProcessingStatus('not_processed');
                    setPeople([]);
                } else {
                    setError(getApiErrorMessage(err, 'Failed to load video faces'));
                }
            } finally {
                setLoading(false);
            }
        }

        if (videoPath) {
            loadPeople();
        }
    }, [videoPath, effectiveVideoId]);

    const handleProcessVideo = async () => {
        setProcessingStatus('processing');
        try {
            await api.processVideoFaces(videoPath);
            setProcessingStatus('processing');

            // Poll for completion
            const pollInterval = setInterval(async () => {
                try {
                    const status = await api.getVideoFaceStatus(effectiveVideoId);
                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        const response = await api.getVideoPeople(effectiveVideoId);
                        setPeople(response.people || []);
                        setProcessingStatus('completed');
                    }
                } catch {
                    // Continue polling
                }
            }, 3000);

            // Stop polling after 5 minutes
            setTimeout(() => clearInterval(pollInterval), 300000);
        } catch (err: unknown) {
            setError(getApiErrorMessage(err, 'Failed to process video'));
            setProcessingStatus('not_processed');
        }
    };

    const handleJumpToTime = (ms: number) => {
        if (onSeek) {
            onSeek(ms);
        }
    };

    // Don't render if no video path
    if (!videoPath) return null;

    // Loading state
    if (loading) {
        return (
            <div className="glass-surface rounded-xl p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm">Loading faces...</span>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="glass-surface rounded-xl p-4 border border-red-500/20">
                <p className="text-sm text-red-400">{error}</p>
            </div>
        );
    }

    // Not processed state
    if (processingStatus === 'not_processed') {
        return (
            <div className="glass-surface rounded-xl p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-muted-foreground">
                        <Users size={16} />
                        <span className="text-sm">People in this video</span>
                    </div>
                    <button
                        onClick={handleProcessVideo}
                        className="btn-glass btn-glass--primary text-xs px-3 py-1.5"
                    >
                        Scan for Faces
                    </button>
                </div>
            </div>
        );
    }

    // Processing state
    if (processingStatus === 'processing') {
        return (
            <div className="glass-surface rounded-xl p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                    <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm">Scanning for faces...</span>
                </div>
                <p className="text-xs text-muted-foreground/70 mt-2">
                    This may take a few minutes for longer videos
                </p>
            </div>
        );
    }

    // No people found
    if (people.length === 0) {
        return (
            <div className="glass-surface rounded-xl p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                    <Users size={16} />
                    <span className="text-sm">No people detected in this video</span>
                </div>
            </div>
        );
    }

    // People found - render panel
    return (
        <div className="glass-surface rounded-xl overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Users size={16} className="text-primary" />
                    <span className="font-medium">People in this video</span>
                    <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                        {people.length}
                    </span>
                </div>
                {isCollapsed ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
            </button>

            {/* People list */}
            {!isCollapsed && (
                <div className="border-t border-white/10 divide-y divide-white/5">
                    {people.map((person) => (
                        <div
                            key={person.cluster_id}
                            className="p-3 hover:bg-white/5 transition-colors"
                        >
                            <div className="flex items-start gap-3">
                                {/* Person avatar placeholder */}
                                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
                                    <User size={20} className="text-white/50" />
                                </div>

                                <div className="flex-1 min-w-0">
                                    {/* Name and screen time */}
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium truncate">
                                            {person.person_name || `Person ${person.cluster_id.slice(-4)}`}
                                        </span>
                                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                                            <Clock size={12} />
                                            {formatDuration(person.total_screen_time_ms)}
                                        </span>
                                    </div>

                                    {/* Track count and time range */}
                                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                        <span>{person.track_count} appearance{person.track_count !== 1 ? 's' : ''}</span>
                                        <span>•</span>
                                        <span>
                                            {formatTime(person.first_appearance_ms)} - {formatTime(person.last_appearance_ms)}
                                        </span>
                                    </div>

                                    {/* Jump to timestamp buttons */}
                                    {onSeek && (
                                        <div className="flex items-center gap-2 mt-2">
                                            <button
                                                onClick={() => handleJumpToTime(person.first_appearance_ms)}
                                                className="btn-glass text-xs px-2 py-1 flex items-center gap-1"
                                                title="Jump to first appearance"
                                            >
                                                <Play size={10} />
                                                First
                                            </button>
                                            {person.first_appearance_ms !== person.last_appearance_ms && (
                                                <button
                                                    onClick={() => handleJumpToTime(person.last_appearance_ms)}
                                                    className="btn-glass text-xs px-2 py-1 flex items-center gap-1"
                                                    title="Jump to last appearance"
                                                >
                                                    <Play size={10} />
                                                    Last
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default VideoFacesPanel;
