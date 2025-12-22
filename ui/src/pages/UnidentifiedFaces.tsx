/**
 * Unidentified Faces Page - Manage faces not yet assigned to a person
 * 
 * This page shows all detected faces that haven't been clustered/identified,
 * allowing users to assign them to existing people or create new person entries.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Camera, RefreshCw, UserPlus } from 'lucide-react';
import { glass } from '../design/glass';

interface UnidentifiedFace {
    id: number;
    image_path: string;
    bounding_box: number[];
    confidence: number;
}

interface Cluster {
    id: string;
    label: string;
    face_count: number;
}

export default function UnidentifiedFaces() {
    const navigate = useNavigate();
    const [faces, setFaces] = useState<UnidentifiedFace[]>([]);
    const [clusters, setClusters] = useState<Cluster[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedFace, setSelectedFace] = useState<UnidentifiedFace | null>(null);
    const [showAssignModal, setShowAssignModal] = useState(false);
    const [newPersonName, setNewPersonName] = useState('');

    useEffect(() => {
        fetchUnidentifiedFaces();
        fetchClusters();
    }, []);

    const fetchUnidentifiedFaces = async () => {
        try {
            setLoading(true);
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/unidentified`
            );
            const data = await response.json();
            // API now returns clusters (unlabeled ones)
            // Convert to face-like format for display
            const clusterData = data.clusters || [];
            const facesFromClusters: UnidentifiedFace[] = [];
            for (const cluster of clusterData) {
                for (let i = 0; i < (cluster.face_ids || []).length; i++) {
                    facesFromClusters.push({
                        id: cluster.face_ids[i],
                        image_path: cluster.images?.[i] || '',
                        bounding_box: [],
                        confidence: 1.0
                    });
                }
            }
            setFaces(facesFromClusters);
        } catch (err) {
            console.error('Failed to fetch unidentified faces:', err);
            setError('Failed to load unidentified faces');
        } finally {
            setLoading(false);
        }
    };

    const fetchClusters = async () => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/clusters`
            );
            const data = await response.json();
            setClusters(data.clusters || []);
        } catch (err) {
            console.error('Failed to fetch clusters:', err);
        }
    };

    const assignToPerson = async (faceId: number, clusterId: string) => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${faceId}/assign`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cluster_id: clusterId })
                }
            );
            if (response.ok) {
                setFaces(faces.filter(f => f.id !== faceId));
                setShowAssignModal(false);
                setSelectedFace(null);
            }
        } catch (err) {
            console.error('Failed to assign face:', err);
        }
    };

    const createNewPerson = async (faceId: number, name: string) => {
        try {
            const response = await fetch(
                `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${faceId}/create-person`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ label: name })
                }
            );
            if (response.ok) {
                setFaces(faces.filter(f => f.id !== faceId));
                setShowAssignModal(false);
                setSelectedFace(null);
                setNewPersonName('');
                fetchClusters();
            }
        } catch (err) {
            console.error('Failed to create person:', err);
        }
    };

    const getFaceCropUrl = (faceId: number) => {
        return `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/faces/${faceId}/crop?size=200`;
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
                                <User size={24} className="text-orange-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold text-foreground">Name These</h1>
                                <p className="text-sm text-muted-foreground">
                                    {faces.length} faces waiting to be identified
                                </p>
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
                        <span className="text-muted-foreground">Loading faces...</span>
                    </div>
                )}

                {error && <div className="text-center py-20 text-red-400">{error}</div>}

                {!loading && !error && faces.length === 0 && (
                    <div className="text-center py-20">
                        <Camera size={48} className="mx-auto text-muted-foreground mb-4" />
                        <h3 className="text-lg font-medium text-foreground mb-2">All Faces Identified!</h3>
                        <p className="text-muted-foreground">There are no unidentified faces in your library.</p>
                    </div>
                )}

                {!loading && !error && faces.length > 0 && (
                    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4">
                        {faces.map((face) => (
                            <div
                                key={face.id}
                                className={`${glass.surface} rounded-xl overflow-hidden border border-white/10 hover:border-primary/50 transition-colors cursor-pointer group`}
                                onClick={() => {
                                    setSelectedFace(face);
                                    setShowAssignModal(true);
                                }}
                            >
                                <div className="aspect-square relative">
                                    <img
                                        src={getFaceCropUrl(face.id)}
                                        alt="Unidentified face"
                                        className="w-full h-full object-cover"
                                    />
                                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                        <UserPlus size={24} className="text-white" />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Assign Modal */}
            {showAssignModal && selectedFace && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowAssignModal(false)}>
                    <div className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`} onClick={e => e.stopPropagation()}>
                        <h3 className="text-lg font-semibold text-foreground mb-4">Identify This Face</h3>

                        <div className="mb-4 flex justify-center">
                            <img src={getFaceCropUrl(selectedFace.id)} alt="Face" className="w-32 h-32 object-cover rounded-lg" />
                        </div>

                        {/* Create New Person */}
                        <div className="mb-4">
                            <label className="text-sm text-muted-foreground mb-2 block">Create New Person</label>
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={newPersonName}
                                    onChange={(e) => setNewPersonName(e.target.value)}
                                    placeholder="Enter name..."
                                    className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                                />
                                <button
                                    onClick={() => newPersonName.trim() && createNewPerson(selectedFace.id, newPersonName.trim())}
                                    className="btn-glass btn-glass--primary px-4 py-2"
                                    disabled={!newPersonName.trim()}
                                >
                                    Create
                                </button>
                            </div>
                        </div>

                        {/* Assign to Existing */}
                        {clusters.length > 0 && (
                            <div>
                                <label className="text-sm text-muted-foreground mb-2 block">Or Assign to Existing Person</label>
                                <div className="max-h-40 overflow-y-auto space-y-2">
                                    {clusters.map(cluster => (
                                        <button
                                            key={cluster.id}
                                            onClick={() => assignToPerson(selectedFace.id, cluster.id)}
                                            className="w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                                        >
                                            <span className="text-foreground">{cluster.label || `Person ${cluster.id}`}</span>
                                            <span className="text-muted-foreground text-xs ml-2">({cluster.face_count} faces)</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="mt-4 flex justify-end">
                            <button onClick={() => setShowAssignModal(false)} className="btn-glass btn-glass--muted px-4 py-2">
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
