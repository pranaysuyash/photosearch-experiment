/**
 * Singletons Page - People appearing only once in library
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, ArrowLeft } from 'lucide-react';
import { glass } from '../design/glass';

interface SingletonCluster {
    cluster_id: string;
    label: string;
    face_id: number;
    image_path: string;
    confidence: number;
}

export function Singletons() {
    const navigate = useNavigate();
    const [clusters, setClusters] = useState<SingletonCluster[]>([]);
    const [loading, setLoading] = useState(true);
    const [count, setCount] = useState(0);

    useEffect(() => {
        fetchSingletons();
    }, []);

    const fetchSingletons = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/singletons`);
            const data = await response.json();
            setClusters(data.singletons || []);
            setCount(data.count || 0);
        } catch (err) {
            console.error('Failed to fetch singletons:', err);
        } finally {
            setLoading(false);
        }
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
                                <User size={24} className="text-yellow-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold text-foreground">Seen Just Once</h1>
                                <p className="text-sm text-muted-foreground">
                                    {count} people who appeared in only one photo
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                ) : clusters.length === 0 ? (
                    <div className={`${glass.surface} rounded-xl p-8 text-center border border-white/10`}>
                        <User className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">Everyone's Been Seen Twice!</h3>
                        <p className="text-muted-foreground">
                            All detected people appear in multiple photos.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                        {clusters.map((cluster) => (
                            <div
                                key={cluster.cluster_id}
                                className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-yellow-500/50 cursor-pointer transition-colors`}
                                onClick={() => navigate(`/people/${cluster.cluster_id}`)}
                            >
                                <div className="p-3 bg-black/20">
                                    {cluster.face_id && (
                                        <img
                                            src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${cluster.face_id}/crop?size=150`}
                                            alt={cluster.label}
                                            className="w-full h-24 object-cover rounded"
                                        />
                                    )}
                                </div>
                                <div className="p-3">
                                    <div className="text-sm font-medium text-foreground truncate">{cluster.label}</div>
                                    <div className="text-xs text-muted-foreground">1 appearance</div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

export default Singletons;
