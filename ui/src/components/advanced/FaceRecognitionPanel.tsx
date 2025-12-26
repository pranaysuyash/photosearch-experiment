/**
 * Face Recognition Panel
 *
 * Advanced face recognition UI with:
 * - Face clustering and person labeling
 * - Privacy controls and consent management
 * - Face tagging and search capabilities
 * - Training data collection for improved recognition
 * - Progress tracking for large operations
 */

import { useState, useEffect, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Search,
  Shield,
  Download,
  Play,
  AlertCircle,
  Loader2,
  Camera,
  Lock,
  Trash2,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

export interface FaceCluster {
  id: string;
  cluster_label: string | null;
  representative_face_id: string | null;
  face_count: number;
  confidence_score: number;
  privacy_level: string;
  is_protected: boolean;
  created_at: string;
  updated_at: string;
}

export interface FaceDetection {
  id: string;
  photo_path: string;
  bbox_x: number;
  bbox_y: number;
  bbox_width: number;
  bbox_height: number;
  confidence: number;
  quality_score: number;
  pose_angles: Record<string, number>;
  age_estimate?: number;
  gender?: string;
  created_at: string;
}

interface ProcessingJob {
  job_id: string;
  status: string;
  message: string;
  progress: number;
  created_at: string;
  updated_at?: string;
  results?: Record<string, unknown>;
}

type TabId = 'clusters' | 'scan' | 'settings' | 'privacy';
type FaceClustersResponse = { clusters: FaceCluster[] };
type FaceSearchResponse = { matches?: string[] };
type JobStartResponse = { job_id: string; message?: string };
type JobStatusResponse = ProcessingJob | { job_status: ProcessingJob };

export function FaceRecognitionPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('clusters');
  const [clusters, setClusters] = useState<FaceCluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<FaceCluster | null>(
    null
  );
  const [clusterFaces, setClusterFaces] = useState<FaceDetection[]>([]);
  const [processingJobs, setProcessingJobs] = useState<
    Record<string, ProcessingJob>
  >({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(false);
  const [newPersonName, setNewPersonName] = useState('');

  const loadFaceClusters = useCallback(async () => {
    try {
      const response = await api.get<FaceClustersResponse>(
        '/api/face/clusters?min_faces=2'
      );
      setClusters(response?.clusters ?? []);
    } catch (error) {
      console.error('Failed to load face clusters:', error);
    }
  }, []);

  // Load face clusters on mount
  useEffect(() => {
    let cancelled = false;

    const rafId = window.requestAnimationFrame(() => {
      if (!cancelled) void loadFaceClusters();
    });

    const interval = window.setInterval(() => {
      if (!cancelled) void loadFaceClusters();
    }, 30000); // Refresh every 30 seconds

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(rafId);
      clearInterval(interval);
    };
  }, [loadFaceClusters]);

  const startDirectoryProcessing = useCallback(
    async (directoryPath: string) => {
      try {
        setLoading(true);
        const response = await api.post<JobStartResponse>(
          '/api/face/process-directory',
          {
            directory_path: directoryPath,
          },
          {
            params: { show_progress: true },
          }
        );

        const jobId = response?.job_id;
        if (!jobId) {
          setLoading(false);
          return;
        }
        setProcessingJobs((prev) => ({
          ...prev,
          [jobId]: {
            job_id: jobId,
            status: 'queued',
            message: response?.message ?? '',
            progress: 0,
            created_at: new Date().toISOString(),
          },
        }));

        // Start polling for job status
        const pollInterval = window.setInterval(async () => {
          try {
            const jobResponse = await api.get<JobStatusResponse>(
              `/api/jobs/${jobId}`
            );
            const jobStatus =
              'job_status' in jobResponse
                ? jobResponse.job_status
                : jobResponse;

            if (jobStatus?.job_id) {
              setProcessingJobs((prev) => ({
                ...prev,
                [jobId]: jobStatus,
              }));
            }

            if (jobStatus?.status === 'completed') {
              clearInterval(pollInterval);
              setLoading(false);
              loadFaceClusters(); // Refresh clusters
            } else if (jobStatus?.status === 'failed') {
              clearInterval(pollInterval);
              setLoading(false);
            }
          } catch (pollError) {
            console.error('Failed to poll job status:', pollError);
            clearInterval(pollInterval);
            setLoading(false);
          }
        }, 2000);
      } catch (error) {
        console.error('Failed to start face processing:', error);
        setLoading(false);
      }
    },
    [loadFaceClusters]
  );

  const labelCluster = useCallback(
    async (
      clusterId: string,
      personName: string,
      privacyLevel: string = 'standard'
    ) => {
      try {
        await api.post('/api/face/label', {
          cluster_id: clusterId,
          person_name: personName,
          privacy_level: privacyLevel,
        });

        // Update local state
        setClusters((prev) =>
          prev.map((cluster) =>
            cluster.id === clusterId
              ? {
                  ...cluster,
                  cluster_label: personName,
                  privacy_level: privacyLevel,
                }
              : cluster
          )
        );

        setNewPersonName('');
      } catch (error) {
        console.error('Failed to label cluster:', error);
      }
    },
    []
  );

  const searchByPerson = useCallback(async (personName: string) => {
    try {
      const response = await api.get<FaceSearchResponse>(
        `/api/face/search/${encodeURIComponent(personName)}`
      );
      setSearchResults(response?.matches ?? []);
    } catch (error) {
      console.error('Failed to search by person:', error);
      setSearchResults([]);
    }
  }, []);

  const loadClusterFaces = useCallback(
    async (clusterId: string) => {
      try {
        // This would need a dedicated endpoint to get faces in a cluster
        // For now, we'll use the existing data structure
        const cluster = clusters.find((c) => c.id === clusterId);
        if (cluster) {
          // Load sample faces for demonstration
          setClusterFaces([]);
        }
      } catch (error) {
        console.error('Failed to load cluster faces:', error);
      }
    },
    [clusters]
  );

  const handleDirectorySelect = () => {
    // This would integrate with Tauri or browser file selection
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        const directoryPath = files[0].webkitRelativePath.split('/')[0];
        startDirectoryProcessing(directoryPath);
      }
    };
    input.click();
  };

  const getPrivacyIcon = (level: string) => {
    switch (level) {
      case 'private':
        return Lock;
      case 'sensitive':
        return Shield;
      default:
        return Users;
    }
  };

  const getPrivacyColor = (level: string) => {
    switch (level) {
      case 'private':
        return 'text-red-500';
      case 'sensitive':
        return 'text-yellow-500';
      default:
        return 'text-green-500';
    }
  };

  const tabs: TabId[] = ['clusters', 'scan', 'settings', 'privacy'];

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white mb-2'>
            Face Recognition
          </h2>
          <p className='text-gray-400'>
            Organize photos by people with smart face detection
          </p>
        </div>
        <button
          onClick={handleDirectorySelect}
          disabled={loading}
          className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2'
        >
          {loading ? (
            <Loader2 className='w-4 h-4 animate-spin' />
          ) : (
            <Camera className='w-4 h-4' />
          )}
          Scan Directory
        </button>
      </div>

      {/* Processing Jobs */}
      {Object.keys(processingJobs).length > 0 && (
        <div className={`${glass.card} p-4 space-y-2`}>
          <h3 className='text-white font-semibold flex items-center gap-2'>
            <Play className='w-4 h-4' />
            Active Operations
          </h3>
          {Object.entries(processingJobs).map(([jobId, job]) => (
            <div
              key={jobId}
              className='flex items-center justify-between p-2 bg-black/20 rounded'
            >
              <div className='flex items-center gap-3'>
                <div
                  className={`w-2 h-2 rounded-full ${
                    job.status === 'completed'
                      ? 'bg-green-500'
                      : job.status === 'failed'
                      ? 'bg-red-500'
                      : 'bg-yellow-500 animate-pulse'
                  }`}
                />
                <span className='text-gray-300 text-sm'>{job.message}</span>
              </div>
              <div className='flex items-center gap-2'>
                <span className='text-gray-400 text-xs'>
                  {job.progress.toFixed(1)}%
                </span>
                <div className='w-20 h-2 bg-black/30 rounded-full overflow-hidden'>
                  <div
                    className='h-full bg-blue-500 transition-all duration-300'
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className='flex space-x-1 p-1 bg-black/20 rounded-lg'>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-2 rounded-md capitalize transition-all ${
              activeTab === tab
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <AnimatePresence mode='wait'>
        {/* Clusters Tab */}
        {activeTab === 'clusters' && (
          <motion.div
            key='clusters'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='grid grid-cols-1 lg:grid-cols-3 gap-6'
          >
            {/* Clusters List */}
            <div className='lg:col-span-2 space-y-4'>
              <div className='flex items-center justify-between'>
                <h3 className='text-xl font-semibold text-white'>
                  Face Clusters
                </h3>
                <span className='text-gray-400 text-sm'>
                  {clusters.length} groups
                </span>
              </div>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                {clusters.map((cluster) => (
                  <motion.div
                    key={cluster.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setSelectedCluster(cluster);
                      loadClusterFaces(cluster.id);
                    }}
                    className={`${
                      glass.card
                    } p-4 cursor-pointer border-2 transition-colors ${
                      selectedCluster?.id === cluster.id
                        ? 'border-blue-500'
                        : 'border-transparent hover:border-white/20'
                    }`}
                  >
                    <div className='flex items-start justify-between'>
                      <div className='flex-1'>
                        <div className='flex items-center gap-2 mb-2'>
                          {(() => {
                            const PrivacyIcon = getPrivacyIcon(
                              cluster.privacy_level
                            );
                            return (
                              <PrivacyIcon
                                className={`w-4 h-4 ${getPrivacyColor(
                                  cluster.privacy_level
                                )}`}
                              />
                            );
                          })()}
                          <span className='text-white font-medium'>
                            {cluster.cluster_label || 'Unnamed Person'}
                          </span>
                        </div>
                        <div className='flex items-center gap-4 text-sm text-gray-400'>
                          <span>{cluster.face_count} photos</span>
                          <span>
                            {(cluster.confidence_score * 100).toFixed(1)}%
                            confidence
                          </span>
                        </div>
                      </div>
                      <div className='text-right'>
                        <div className='text-xs text-gray-500'>
                          {new Date(cluster.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Cluster Details */}
            <div className={`${glass.card} p-4`}>
              {selectedCluster ? (
                <div className='space-y-4'>
                  <div>
                    <h4 className='text-white font-semibold mb-1'>
                      {selectedCluster.cluster_label || 'Unnamed Person'}
                    </h4>
                    <p className='text-gray-400 text-sm'>Cluster Details</p>
                  </div>

                  {!selectedCluster.cluster_label && (
                    <div className='space-y-2'>
                      <input
                        type='text'
                        placeholder='Enter person name'
                        value={newPersonName}
                        onChange={(e) => setNewPersonName(e.target.value)}
                        className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500'
                      />
                      <button
                        onClick={() =>
                          labelCluster(selectedCluster.id, newPersonName)
                        }
                        disabled={!newPersonName.trim()}
                        className='w-full px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
                      >
                        Label Person
                      </button>
                    </div>
                  )}

                  <div className='space-y-3'>
                    <div className='flex justify-between text-sm'>
                      <span className='text-gray-400'>Photos:</span>
                      <span className='text-white'>
                        {selectedCluster.face_count}
                      </span>
                    </div>
                    <div className='flex justify-between text-sm'>
                      <span className='text-gray-400'>
                        Face samples loaded:
                      </span>
                      <span className='text-white'>{clusterFaces.length}</span>
                    </div>
                    <div className='flex justify-between text-sm'>
                      <span className='text-gray-400'>Confidence:</span>
                      <span className='text-white'>
                        {(selectedCluster.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className='flex justify-between text-sm'>
                      <span className='text-gray-400'>Privacy:</span>
                      <span
                        className={`capitalize ${getPrivacyColor(
                          selectedCluster.privacy_level
                        )}`}
                      >
                        {selectedCluster.privacy_level}
                      </span>
                    </div>
                    <div className='flex justify-between text-sm'>
                      <span className='text-gray-400'>Protected:</span>
                      <span className='text-white'>
                        {selectedCluster.is_protected ? 'Yes' : 'No'}
                      </span>
                    </div>
                  </div>

                  <div className='pt-3 border-t border-white/10 space-y-2'>
                    <button className='w-full px-3 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20'>
                      View All Photos
                    </button>
                    <button className='w-full px-3 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30'>
                      Delete Cluster
                    </button>
                  </div>
                </div>
              ) : (
                <div className='text-center py-8'>
                  <Users className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400'>
                    Select a cluster to view details
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Search Tab */}
        {activeTab === 'scan' && (
          <motion.div
            key='scan'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Search by Person
              </h3>

              <div className='flex gap-2'>
                <input
                  type='text'
                  placeholder="Enter person's name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && searchQuery.trim()) {
                      searchByPerson(searchQuery);
                    }
                  }}
                  className='flex-1 px-4 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500'
                />
                <button
                  onClick={() =>
                    searchQuery.trim() && searchByPerson(searchQuery)
                  }
                  disabled={!searchQuery.trim()}
                  className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  <Search className='w-4 h-4' />
                </button>
              </div>

              {searchResults.length > 0 && (
                <div className='mt-4'>
                  <h4 className='text-white font-medium mb-2'>
                    Found {searchResults.length} photos of "{searchQuery}"
                  </h4>
                  <div className='grid grid-cols-3 md:grid-cols-6 lg:grid-cols-8 gap-2'>
                    {searchResults.slice(0, 24).map((photoPath, index) => (
                      <div
                        key={index}
                        className='aspect-square bg-black/20 rounded-lg overflow-hidden'
                      >
                        <img
                          src={`/api/image/${encodeURIComponent(photoPath)}`}
                          alt={`Photo ${index + 1}`}
                          className='w-full h-full object-cover hover:scale-110 transition-transform cursor-pointer'
                        />
                      </div>
                    ))}
                  </div>
                  {searchResults.length > 24 && (
                    <p className='text-gray-400 text-sm mt-2'>
                      Showing 24 of {searchResults.length} results
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Directory Processing
              </h3>
              <p className='text-gray-400 mb-4'>
                Scan a directory to detect and cluster faces in your photo
                collection.
              </p>

              <button
                onClick={handleDirectorySelect}
                disabled={loading}
                className='w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
              >
                {loading ? (
                  <>
                    <Loader2 className='w-4 h-4 animate-spin' />
                    Processing...
                  </>
                ) : (
                  <>
                    <Camera className='w-4 h-4' />
                    Select Directory to Scan
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <motion.div
            key='settings'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6 space-y-6`}
          >
            <h3 className='text-xl font-semibold text-white'>
              Face Recognition Settings
            </h3>

            <div className='space-y-4'>
              <div className='flex items-center justify-between'>
                <div>
                  <h4 className='text-white font-medium'>GPU Acceleration</h4>
                  <p className='text-gray-400 text-sm'>
                    Use GPU for faster face processing when available
                  </p>
                </div>
                <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                  <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full transition-transform' />
                </button>
              </div>

              <div className='flex items-center justify-between'>
                <div>
                  <h4 className='text-white font-medium'>
                    Auto-cluster New Faces
                  </h4>
                  <p className='text-gray-400 text-sm'>
                    Automatically group similar faces as they're detected
                  </p>
                </div>
                <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                  <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full transition-transform' />
                </button>
              </div>

              <div className='flex items-center justify-between'>
                <div>
                  <h4 className='text-white font-medium'>
                    Face Quality Threshold
                  </h4>
                  <p className='text-gray-400 text-sm'>
                    Minimum quality score for face detection
                  </p>
                </div>
                <input
                  type='range'
                  min='0'
                  max='100'
                  defaultValue='50'
                  className='w-32'
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* Privacy Tab */}
        {activeTab === 'privacy' && (
          <motion.div
            key='privacy'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6 space-y-6`}
          >
            <div className='flex items-center gap-3 mb-4'>
              <Shield className='w-6 h-6 text-yellow-500' />
              <h3 className='text-xl font-semibold text-white'>
                Privacy & Security
              </h3>
            </div>

            <div className='bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4'>
              <div className='flex items-start gap-3'>
                <AlertCircle className='w-5 h-5 text-yellow-500 mt-0.5' />
                <div>
                  <h4 className='text-yellow-400 font-medium mb-1'>
                    Privacy Notice
                  </h4>
                  <p className='text-gray-300 text-sm'>
                    Face recognition data is processed locally on your device
                    and encrypted when stored. You have full control over face
                    data and can delete it at any time.
                  </p>
                </div>
              </div>
            </div>

            <div className='space-y-4'>
              <div className='flex items-center justify-between'>
                <div>
                  <h4 className='text-white font-medium'>Encrypt Face Data</h4>
                  <p className='text-gray-400 text-sm'>
                    Encrypt all face embeddings for privacy
                  </p>
                </div>
                <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                  <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full transition-transform' />
                </button>
              </div>

              <div className='flex items-center justify-between'>
                <div>
                  <h4 className='text-white font-medium'>Privacy Mode</h4>
                  <p className='text-gray-400 text-sm'>
                    Hide face detection results until explicitly enabled
                  </p>
                </div>
                <button
                  onClick={() => setPrivacyMode(!privacyMode)}
                  className={`w-12 h-6 ${
                    privacyMode ? 'bg-blue-600' : 'bg-gray-600'
                  } rounded-full relative`}
                >
                  <div
                    className={`absolute ${
                      privacyMode ? 'right-1' : 'left-1'
                    } top-1 w-4 h-4 bg-white rounded-full transition-transform`}
                  />
                </button>
              </div>

              <div className='pt-4 border-t border-white/10 space-y-2'>
                <button className='w-full px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20'>
                  <Download className='w-4 h-4 inline mr-2' />
                  Export Face Data
                </button>
                <button className='w-full px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30'>
                  <Trash2 className='w-4 h-4 inline mr-2' />
                  Delete All Face Data
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(FaceRecognitionPanel);
