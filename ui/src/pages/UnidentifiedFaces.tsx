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
import { api } from '../api';

interface UnidentifiedFace {
  detection_id: string;
  photo_path: string;
  bounding_box: unknown;
  quality_score?: number | null;
}

interface Cluster {
  id: string;
  label?: string | null;
  face_count?: number;
}

type RawCluster = {
  id?: string | number;
  cluster_id?: string | number;
  label?: string | null;
  face_count?: number;
};

const normalizeCluster = (value: unknown): Cluster | null => {
  if (!value || typeof value !== 'object') return null;
  const v = value as RawCluster;
  const idRaw = v.id ?? v.cluster_id;
  if (idRaw === undefined || idRaw === null) return null;

  return {
    id: String(idRaw),
    label: v.label ?? null,
    face_count: typeof v.face_count === 'number' ? v.face_count : undefined,
  };
};

export default function UnidentifiedFaces() {
  const navigate = useNavigate();
  const [faces, setFaces] = useState<UnidentifiedFace[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFace, setSelectedFace] = useState<UnidentifiedFace | null>(
    null
  );
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');

  useEffect(() => {
    fetchUnidentifiedFaces();
    fetchClusters();
  }, []);

  const fetchUnidentifiedFaces = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getUnassignedFaces(100, 0);
      setFaces(Array.isArray(data?.faces) ? data.faces : []);
    } catch (err) {
      console.error('Failed to fetch unidentified faces:', err);
      setError('Failed to load unidentified faces');
      setFaces([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchClusters = async () => {
    try {
      const data = await api.getFaceClusters();
      const raw: unknown[] = Array.isArray(data?.clusters) ? data.clusters : [];
      setClusters(
        raw
          .map(normalizeCluster)
          .filter((c): c is Cluster => c !== null)
      );
    } catch (err) {
      console.error('Failed to fetch clusters:', err);
      setClusters([]);
    }
  };

  const assignToPerson = async (detectionId: string, clusterId: string) => {
    try {
      await api.moveFace(detectionId, clusterId);
      setFaces(faces.filter((f) => f.detection_id !== detectionId));
      setShowAssignModal(false);
      setSelectedFace(null);
    } catch (err) {
      console.error('Failed to assign face:', err);
    }
  };

  const createNewPerson = async (detectionId: string, name: string) => {
    try {
      await api.splitFaces([detectionId], name);
      setFaces(faces.filter((f) => f.detection_id !== detectionId));
      setShowAssignModal(false);
      setSelectedFace(null);
      setNewPersonName('');
      void fetchClusters();
    } catch (err) {
      console.error('Failed to create person:', err);
    }
  };

  const getThumbnailUrl = (photoPath: string) => {
    const encodedPath = encodeURIComponent(photoPath);
    return `/api/thumbnail/${encodedPath}?size=180`;
  };

  return (
    <div className='min-h-screen'>
      {/* Header */}
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <div className='flex items-center gap-4'>
            <button
              onClick={() => navigate('/people')}
              className='btn-glass btn-glass--muted p-2'
              aria-label='Back to People'
              title='Back to People'
            >
              <ArrowLeft size={20} />
            </button>
            <div className='flex items-center gap-3'>
              <div
                className={`${glass.surface} p-3 rounded-xl border border-white/10`}
              >
                <User size={24} className='text-orange-400' />
              </div>
              <div>
                <h1 className='text-xl font-semibold text-foreground'>
                  Name These
                </h1>
                <p className='text-sm text-muted-foreground tabular-nums'>
                  {faces.length} faces waiting to be identified
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'>
        {loading && (
          <div className='flex items-center justify-center py-20'>
            <RefreshCw
              size={20}
              className='animate-spin text-muted-foreground mr-3'
            />
            <span className='text-muted-foreground'>Loading faces…</span>
          </div>
        )}

        {error && (
          <div role='alert' className='text-center py-20 text-red-400'>
            {error}
          </div>
        )}

        {!loading && !error && faces.length === 0 && (
          <div className='text-center py-20'>
            <Camera size={48} className='mx-auto text-muted-foreground mb-4' />
            <h3 className='text-lg font-medium text-foreground mb-2'>
              All Faces Identified!
            </h3>
            <p className='text-muted-foreground'>
              There are no unidentified faces in your library.
            </p>
          </div>
        )}

        {!loading && !error && faces.length > 0 && (
          <div className='grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4'>
            {faces.map((face) => (
              <div
                key={face.detection_id}
                className={`${glass.surface} rounded-xl overflow-hidden border border-white/10 hover:border-primary/50 transition-colors cursor-pointer group`}
                role='button'
                tabIndex={0}
                onClick={() => {
                  setSelectedFace(face);
                  setShowAssignModal(true);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedFace(face);
                    setShowAssignModal(true);
                  }
                }}
              >
                <div className='aspect-square relative'>
                  <img
                    src={getThumbnailUrl(face.photo_path)}
                    alt='Unidentified face'
                    className='w-full h-full object-cover'
                  />
                  <div className='absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity flex items-center justify-center'>
                    <UserPlus size={24} className='text-white' />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assign Modal */}
      {showAssignModal && selectedFace && (
        <div
          className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'
          onClick={() => setShowAssignModal(false)}
        >
          <div
            className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-md w-full shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className='text-lg font-semibold text-foreground mb-4'>
              Identify This Face
            </h3>

            <div className='mb-4 flex justify-center'>
              <img
                src={getThumbnailUrl(selectedFace.photo_path)}
                alt='Face'
                className='w-32 h-32 object-cover rounded-lg'
              />
            </div>

            {/* Create New Person */}
            <div className='mb-4'>
              <label
                htmlFor='unif-new-person-name'
                className='text-sm text-muted-foreground mb-2 block'
              >
                Create New Person
              </label>
              <div className='flex gap-2'>
                <input
                  id='unif-new-person-name'
                  type='text'
                  value={newPersonName}
                  onChange={(e) => setNewPersonName(e.target.value)}
                  placeholder='Enter name…'
                  className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                />
                <button
                  onClick={() =>
                    newPersonName.trim() &&
                    createNewPerson(selectedFace.detection_id, newPersonName.trim())
                  }
                  className='btn-glass btn-glass--primary px-4 py-2'
                  disabled={!newPersonName.trim()}
                >
                  Create
                </button>
              </div>
            </div>

            {/* Assign to Existing */}
            {clusters.length > 0 && (
              <div>
                <p className='text-sm text-muted-foreground mb-2 block'>
                  Or Assign to Existing Person
                </p>
                <div className='max-h-40 overflow-y-auto space-y-2'>
                  {clusters.map((cluster) => (
                    <button
                      key={cluster.id}
                      onClick={() =>
                        assignToPerson(selectedFace.detection_id, cluster.id)
                      }
                      className='w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors'
                    >
                      <span className='text-foreground'>
                        {cluster.label || `Person ${cluster.id}`}
                      </span>
                      <span className='text-muted-foreground text-xs ml-2'>
                        ({cluster.face_count ?? 0} faces)
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className='mt-4 flex justify-end'>
              <button
                onClick={() => setShowAssignModal(false)}
                className='btn-glass btn-glass--muted px-4 py-2'
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
