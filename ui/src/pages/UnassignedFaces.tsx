/**
 * Unassigned Faces Page - Trust & Review (Unknown bucket)
 *
 * Shows faces detected in photos that are not assigned to any person cluster.
 * Users can:
 * - Create a new person from a face (split into new cluster)
 * - Assign the face to an existing person (move)
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, UserPlus, Users } from 'lucide-react';
import { api } from '../api';
import { glass } from '@/design/glass';

type UnassignedFace = {
  detection_id: string;
  photo_path: string;
  bounding_box: unknown;
  quality_score?: number | null;
  created_at?: string | null;
};

type Cluster = { id: string; label?: string | null; face_count?: number };

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

const getThumbnailUrl = (photoPath: string) => {
  const encodedPath = encodeURIComponent(photoPath);
  return `/api/thumbnail/${encodedPath}?size=180`;
};

export default function UnassignedFaces() {
  const navigate = useNavigate();

  const [faces, setFaces] = useState<UnassignedFace[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [clusterFilter, setClusterFilter] = useState('');

  const [limit] = useState(30);
  const [offset, setOffset] = useState(0);

  const [selected, setSelected] = useState<UnassignedFace | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchFaces = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getUnassignedFaces(limit, offset);
      setFaces(Array.isArray(data?.faces) ? data.faces : []);
      setTotal(Number(data?.total ?? data?.count ?? 0));
    } catch (err) {
      console.error('Failed to load unassigned faces:', err);
      setError('Failed to load unassigned faces');
      setFaces([]);
      setTotal(0);
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
      console.error('Failed to load clusters:', err);
      setClusters([]);
    }
  };

  useEffect(() => {
    void Promise.all([fetchFaces(), fetchClusters()]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  const filteredClusters = useMemo(() => {
    const q = clusterFilter.trim().toLowerCase();
    if (!q) return clusters;
    return clusters.filter((c) => {
      const label = (c.label || '').toLowerCase();
      return label.includes(q) || c.id.toLowerCase().includes(q);
    });
  }, [clusterFilter, clusters]);

  const handleCreateNewPerson = async () => {
    if (!selected) return;
    const name = newPersonName.trim();
    if (!name) return;

    try {
      setSaving(true);
      await api.splitFaces([selected.detection_id], name);
      setShowModal(false);
      setSelected(null);
      setNewPersonName('');
      await fetchFaces();
      await fetchClusters();
    } catch (err) {
      console.error('Failed to create person from unassigned face:', err);
      setError('Failed to create person');
    } finally {
      setSaving(false);
    }
  };

  const handleAssignToExisting = async (clusterId: string) => {
    if (!selected) return;
    try {
      setSaving(true);
      await api.moveFace(selected.detection_id, clusterId);
      setShowModal(false);
      setSelected(null);
      await fetchFaces();
    } catch (err) {
      console.error('Failed to assign face:', err);
      setError('Failed to assign face');
    } finally {
      setSaving(false);
    }
  };

  const pageStart = offset + 1;
  const pageEnd = Math.min(offset + limit, total);

  return (
    <div className='min-h-screen'>
      <div className='border-b border-white/10'>
        <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
          <div className='flex items-center justify-between gap-4 flex-wrap'>
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
                <div className={`${glass.surface} p-3 rounded-xl border border-white/10`}>
                  <UserPlus size={24} className='text-orange-400' />
                </div>
                <div>
                  <h1 className='text-xl font-semibold text-foreground'>Unassigned Faces</h1>
                  <p className='text-sm text-muted-foreground tabular-nums'>
                    {total.toLocaleString()} faces not yet assigned to a person
                  </p>
                </div>
              </div>
            </div>

            <div className='flex items-center gap-2'>
              <button
                onClick={fetchFaces}
                className='btn-glass btn-glass--muted px-3 py-2 text-sm'
                disabled={loading}
                title='Refresh'
                aria-label='Refresh unassigned faces'
              >
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6'>
        {error && (
          <div role='alert' className='mb-4 text-sm text-red-400'>
            {error}
          </div>
        )}

        {loading ? (
          <div className='flex items-center justify-center py-20'>
            <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-primary' />
          </div>
        ) : faces.length === 0 ? (
          <div className={`${glass.surface} rounded-xl p-8 text-center border border-white/10`}>
            <Users className='mx-auto h-12 w-12 text-muted-foreground mb-4' />
            <h3 className='text-lg font-medium text-foreground mb-2'>All Assigned!</h3>
            <p className='text-muted-foreground'>No unassigned faces found.</p>
          </div>
        ) : (
          <>
            <div className='flex items-center justify-between gap-2 mb-3 flex-wrap'>
              <div className='text-xs text-muted-foreground'>
                Showing {pageStart}-{pageEnd} of {total}
              </div>
              <div className='flex gap-2'>
                <button
                  className='btn-glass btn-glass--muted text-sm px-3 py-2'
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                >
                  Previous
                </button>
                <button
                  className='btn-glass btn-glass--muted text-sm px-3 py-2'
                  disabled={offset + limit >= total}
                  onClick={() => setOffset(offset + limit)}
                >
                  Next
                </button>
              </div>
            </div>

            <div className='grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-6 gap-4'>
              {faces.map((face) => (
                <button
                  key={face.detection_id}
                  type='button'
                  className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden hover:border-primary/50 transition-colors text-left`}
                  onClick={() => {
                    setSelected(face);
                    setShowModal(true);
                    setNewPersonName('');
                    setClusterFilter('');
                  }}
                >
                  <div className='p-2 bg-black/20'>
                    <img
                      src={getThumbnailUrl(face.photo_path)}
                      alt='Unassigned face (photo thumbnail)'
                      className='w-full h-24 object-cover rounded'
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                  <div className='p-3'>
                    <div className='text-xs text-muted-foreground truncate'>
                      {face.photo_path.split('/').pop()}
                    </div>
                    {typeof face.quality_score === 'number' ? (
                      <div className='text-xs text-muted-foreground'>
                        Quality: {(face.quality_score * 100).toFixed(0)}%
                      </div>
                    ) : null}
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {showModal && selected && (
        <div
          className='fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4'
          onClick={() => setShowModal(false)}
        >
          <div
            className={`${glass.surface} border border-white/20 rounded-xl p-6 max-w-xl w-full shadow-2xl`}
            onClick={(e) => e.stopPropagation()}
          >
            <div className='flex items-center justify-between gap-3'>
              <h3 className='text-lg font-semibold text-foreground'>Assign this face</h3>
              <button
                className='btn-glass btn-glass--muted text-sm px-3 py-2'
                onClick={() => setShowModal(false)}
                disabled={saving}
              >
                Close
              </button>
            </div>

            <div className='mt-4 grid grid-cols-1 md:grid-cols-2 gap-4'>
              <div>
                <div className='text-sm text-muted-foreground mb-2'>Thumbnail</div>
                <img
                  src={getThumbnailUrl(selected.photo_path)}
                  alt='Selected face (photo thumbnail)'
                  className='w-full h-48 object-cover rounded-lg border border-white/10'
                />
                <div className='text-xs text-muted-foreground mt-2 break-all'>
                  {selected.photo_path}
                </div>
              </div>

              <div>
                <label htmlFor='unassigned-new-person-name' className='text-sm text-muted-foreground mb-2 block'>Create new person</label>
                <div className='flex gap-2'>
                  <input
                    id='unassigned-new-person-name'
                    value={newPersonName}
                    onChange={(e) => setNewPersonName(e.target.value)}
                    placeholder='Enter name…'
                    className='flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                  />
                  <button
                    className='btn-glass btn-glass--primary px-4 py-2 text-sm'
                    disabled={!newPersonName.trim() || saving}
                    onClick={handleCreateNewPerson}
                  >
                    Create
                  </button>
                </div>

                <div className='mt-4 text-sm text-muted-foreground mb-2'>Or assign to existing</div>
                <input
                  value={clusterFilter}
                  onChange={(e) => setClusterFilter(e.target.value)}
                  placeholder='Filter people…'
                  aria-label='Filter people'
                  className='w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50'
                />

                <div className='mt-2 max-h-56 overflow-y-auto space-y-2'>
                  {filteredClusters.length === 0 ? (
                    <div className='text-xs text-muted-foreground'>No matching people.</div>
                  ) : (
                    filteredClusters.map((c) => (
                      <button
                        key={c.id}
                        type='button'
                        className='w-full text-left px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors'
                        onClick={() => handleAssignToExisting(c.id)}
                        disabled={saving}
                      >
                        <div className='text-foreground text-sm'>
                          {c.label || `Person ${c.id}`}
                        </div>
                        {typeof c.face_count === 'number' ? (
                          <div className='text-xs text-muted-foreground'>
                            {c.face_count} faces
                          </div>
                        ) : null}
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className='mt-4 text-xs text-muted-foreground'>
              Creating a person uses the Split action (1 face → new cluster). Assigning uses Move.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
