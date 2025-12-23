
import { useState } from 'react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import { Shield, Trash2, AlertTriangle, Loader2, Check } from 'lucide-react';

export function PrivacyPanel() {
    const [confirmInput, setConfirmInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const handleDeleteAll = async () => {
        if (confirmInput !== 'DELETE') return;

        if (!window.confirm("FINAL WARNING: This will permanently delete all face data. Profiles, associations, and learned faces will be lost. Photos will remain.")) {
            return;
        }

        setLoading(true);
        setError(null);
        setSuccess(null);
        try {
            const res = await api.deleteAllFaceData();
            // Assuming res.deleted contains stats
            if (res.deleted) {
                setSuccess(`Deleted ${res.deleted.clusters || 0} people, ${res.deleted.associations || 0} face assignments.`);
            } else {
                setSuccess('All face data deleted successfully.');
            }
            setConfirmInput('');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to delete data');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-6`}>
                <h3 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2">
                    <Shield className="text-primary" />
                    Face Recognition Privacy
                </h3>

                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 space-y-4">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="text-red-400 shrink-0 mt-1" />
                        <div>
                            <h4 className="font-medium text-red-400">Delete All Face Data</h4>
                            <p className="text-sm text-red-400/80 mt-1">
                                This action is <strong>irreversible</strong>. It will:
                            </p>
                            <ul className="list-disc list-inside text-sm text-red-400/80 mt-2 space-y-1">
                                <li>Delete all identified people/clusters</li>
                                <li>Remove all face assignments from photos</li>
                                <li>Clear the face review queue and rejections</li>
                                <li>Delete all stored face embeddings and detections</li>
                            </ul>
                            <p className="text-sm text-red-400/80 mt-2">
                                Your photos and files will <strong>NOT</strong> be deleted.
                            </p>
                        </div>
                    </div>

                    <div className="space-y-3 pt-2">
                        <label className="block text-sm font-medium text-muted-foreground">
                            Type <strong>DELETE</strong> to confirm
                        </label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={confirmInput}
                                onChange={e => setConfirmInput(e.target.value)}
                                placeholder="DELETE"
                                className="bg-black/20 border border-red-500/30 rounded px-3 py-2 text-foreground w-full placeholder:text-muted-foreground/30 focus:border-red-500 focus:outline-none"
                            />
                            <button
                                onClick={handleDeleteAll}
                                disabled={confirmInput !== 'DELETE' || loading}
                                className="bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded font-medium transition-colors flex items-center gap-2 shrink-0"
                            >
                                {loading ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} />}
                                Delete Data
                            </button>
                        </div>
                    </div>
                </div>

                {error && (
                    <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded text-green-400 text-sm flex items-center gap-2">
                        <Check size={16} />
                        {success}
                    </div>
                )}
            </div>
        </div>
    );
}
