/**
 * Low Confidence Page - Faces with low detection confidence
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';
import { glass } from '../design/glass';

interface LowConfidenceFace {
    id: number;
    image_path: string;
    bounding_box: number[];
    confidence: number;
    cluster_id: number | null;
}

export function LowConfidence() {
    const navigate = useNavigate();
    const [faces, setFaces] = useState<LowConfidenceFace[]>([]);
    const [loading, setLoading] = useState(true);
    const [count, setCount] = useState(0);

    useEffect(() => {
        fetchLowConfidence();
    }, []);

    const fetchLowConfidence = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/low-confidence`);
            const data = await response.json();
            setFaces(data.faces || []);
            setCount(data.count || 0);
        } catch (err) {
            console.error('Failed to fetch low confidence faces:', err);
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
                                <AlertCircle size={24} className="text-red-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold text-foreground">Review These Faces</h1>
                                <p className="text-sm text-muted-foreground">
                                    {count} faces we're not quite sure about
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
                ) : faces.length === 0 ? (
                    <div className={`${glass.surface} rounded-xl p-8 text-center border border-white/10`}>
                        <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">All Faces Look Good!</h3>
                        <p className="text-muted-foreground">
                            All detected faces have high confidence scores.
                        </p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                        {faces.map((face) => (
                            <div
                                key={face.id}
                                className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-red-500/50 transition-colors`}
                            >
                                <div className="p-3 bg-black/20">
                                    <img
                                        src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${face.id}/crop?size=150`}
                                        alt={`Face ${face.id}`}
                                        className="w-full h-24 object-cover rounded"
                                    />
                                </div>
                                <div className="p-3">
                                    <div className="text-sm font-medium text-foreground">
                                        {(face.confidence * 100).toFixed(0)}% confidence
                                    </div>
                                    <div className="text-xs text-muted-foreground truncate">
                                        {face.image_path.split('/').pop()}
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

export default LowConfidence;
