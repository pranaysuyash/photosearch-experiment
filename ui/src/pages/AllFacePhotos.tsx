/**
 * All Face Photos Page - Shows all photos that contain detected faces
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Camera, RefreshCw } from 'lucide-react';
import { glass } from '../design/glass';
import SecureLazyImage from '../components/gallery/SecureLazyImage';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import type { Photo } from '../api';

interface FacePhoto {
    path: string;
    face_count: number;
}

export default function AllFacePhotos() {
    const navigate = useNavigate();
    const { openForPhoto } = usePhotoViewer();
    const [photos, setPhotos] = useState<FacePhoto[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchPhotos = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(
                    `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/photos-with-faces`
                );
                const data = await response.json();
                setPhotos(data.photos || []);
            } catch (err) {
                console.error('Failed to fetch photos with faces:', err);
                setError('Failed to load photos');
            } finally {
                setLoading(false);
            }
        };

        fetchPhotos();
    }, []);

    const handlePhotoClick = (photo: FacePhoto) => {
        const photoObj: Photo = {
            path: photo.path,
            filename: photo.path.split('/').pop() || '',
            score: 1,
            metadata: {}
        };
        const allPhotos: Photo[] = photos.map(p => ({
            path: p.path,
            filename: p.path.split('/').pop() || '',
            score: 1,
            metadata: {}
        }));
        openForPhoto(allPhotos, photoObj);
    };

    return (
        <div className="min-h-screen">
            {/* Header */}
            <div className="border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center gap-4">
                        <button onClick={() => navigate('/people')} className="btn-glass btn-glass--muted p-2">
                            <ArrowLeft size={20} />
                        </button>
                        <div className="flex items-center gap-3">
                            <div className={`${glass.surface} p-3 rounded-xl border border-white/10`}>
                                <Camera size={24} className="text-purple-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold text-foreground">Photos with Faces</h1>
                                <p className="text-sm text-muted-foreground">{photos.length} photos</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {loading && (
                    <div className="flex items-center justify-center py-20">
                        <RefreshCw size={20} className="animate-spin text-muted-foreground mr-3" />
                        <span className="text-muted-foreground">Loading photos...</span>
                    </div>
                )}

                {error && <div className="text-center py-20 text-red-400">{error}</div>}

                {!loading && !error && photos.length === 0 && (
                    <div className="text-center py-20">
                        <Camera size={48} className="mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">No Photos with Faces</h3>
                        <p className="text-muted-foreground">Scan your photos to detect faces.</p>
                    </div>
                )}

                {!loading && !error && photos.length > 0 && (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                        {photos.map((photo, index) => (
                            <div
                                key={`${photo.path}-${index}`}
                                className={`${glass.surface} rounded-xl overflow-hidden border border-white/10 hover:border-white/20 transition-colors cursor-pointer group`}
                                onClick={() => handlePhotoClick(photo)}
                            >
                                <div className="aspect-square relative">
                                    <SecureLazyImage
                                        path={photo.path}
                                        size={400}
                                        alt="Photo with faces"
                                        className="w-full h-full object-cover"
                                        showBadge={false}
                                    />
                                    {/* Face count badge */}
                                    <div className="absolute bottom-2 right-2 bg-black/60 backdrop-blur-sm rounded px-2 py-1 text-xs text-white">
                                        {photo.face_count} {photo.face_count === 1 ? 'face' : 'faces'}
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
