/**
 * Person Detail Page - Shows photos containing a specific person
 */
import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Camera, RefreshCw } from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';
import SecureLazyImage from '../components/gallery/SecureLazyImage';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import type { Photo } from '../api';

interface PersonPhoto {
    path: string;
    face_id: number;
    bounding_box: number[] | null;
    confidence: number;
}

interface ClusterInfo {
    id: string;
    label: string;
    face_count: number;
}

export default function PersonDetail() {
    const { clusterId } = useParams<{ clusterId: string }>();
    const navigate = useNavigate();
    const { openForPhoto } = usePhotoViewer();
    const [photos, setPhotos] = useState<PersonPhoto[]>([]);
    const [clusterInfo, setClusterInfo] = useState<ClusterInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!clusterId) return;

        const fetchPhotos = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(
                    `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/cluster/${clusterId}/photos`
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
        };

        fetchPhotos();
    }, [clusterId]);

    return (
        <div className="min-h-screen">
            {/* Header */}
            <div className="border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
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
                </div>
            </div>

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

                {/* Error */}
                {error && (
                    <div className="text-center py-20 text-red-400">
                        {error}
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
                        {photos.map((photo, index) => (
                            <div
                                key={`${photo.path}-${index}`}
                                className={`${glass.surface} rounded-xl overflow-hidden border border-white/10 hover:border-white/20 transition-colors cursor-pointer group`}
                                onClick={() => {
                                    // Convert to Photo type and open in modal
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

                                    {/* Confidence badge */}
                                    <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity">
                                        {Math.round(photo.confidence * 100)}% match
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
