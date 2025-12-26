/**
 * Duplicate Management Panel
 *
 * Advanced duplicate detection and management UI with:
 * - Visual comparison of duplicate images
 * - Smart resolution suggestions
 * - Batch operations for multiple duplicate groups
 * - Quality assessment and space savings calculations
 * - Progress tracking for large duplicate scans
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Copy,
  Search,
  Image as ImageIcon,
  FolderOpen,
  Layers,
  Target,
  BarChart3,
  X,
  AlertCircle,
  Loader2,
  ZoomIn,
  Sparkles,
  HardDrive,
  ChevronLeft,
  ChevronRight,
  Archive,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';

export interface DuplicateGroup {
  id: string;
  group_type: string;
  similarity_threshold: number;
  photos: Array<{
    path: string;
    similarity_score: number;
    is_primary: boolean;
    resolution_action: string;
  }>;
  total_size_mb: number;
  primary_photo_id: string | null;
  resolution_strategy: string | null;
  auto_resolvable: boolean;
  created_at: string;
  updated_at: string;
}

export interface ResolutionSuggestion {
  type: string;
  description: string;
  action: string;
  target_photo?: string;
  space_saved_mb: number;
  confidence: number;
  reasoning: string;
  originals?: string[];
  edited?: string[];
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

type TabId = 'groups' | 'scan' | 'suggestions' | 'analytics';
type DuplicateGroupsResponse = { groups: DuplicateGroup[] };
type ScanDuplicatesResponse = { job_id: string; message?: string };
type JobStatusResponse = ProcessingJob | { job_status: ProcessingJob };
type ResolutionSuggestionsResponse =
  | { suggestions?: { suggestions?: ResolutionSuggestion[] } }
  | { suggestions?: ResolutionSuggestion[] }
  | undefined;

export function DuplicateManagementPanel() {
  const { isDark } = useAmbientThemeContext();
  const surfaceClass = isDark ? 'bg-black/20' : 'bg-white/40';
  const [activeTab, setActiveTab] = useState<TabId>('groups');
  const [duplicateGroups, setDuplicateGroups] = useState<DuplicateGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<DuplicateGroup | null>(
    null
  );
  const [resolutionSuggestions, setResolutionSuggestions] = useState<
    ResolutionSuggestion[]
  >([]);
  const [processingJobs, setProcessingJobs] = useState<
    Record<string, ProcessingJob>
  >({});
  const [loading, setLoading] = useState(false);
  const [showComparison, setShowComparison] = useState(false);
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [scanProgress, setScanProgress] = useState(0);
  const [totalSpaceSaved, setTotalSpaceSaved] = useState(0);

  const loadDuplicateGroups = useCallback(async () => {
    try {
      const response =
        (await api.getDuplicateGroups()) as DuplicateGroupsResponse;
      const groups = response?.groups ?? [];
      setDuplicateGroups(groups);

      // Calculate total space that could be saved
      const totalSaved = groups.reduce((sum: number, group: DuplicateGroup) => {
        return sum + (group.photos.length > 1 ? group.total_size_mb * 0.7 : 0); // Assume 70% savings
      }, 0);
      setTotalSpaceSaved(totalSaved);
    } catch (error) {
      console.error('Failed to load duplicate groups:', error);
    }
  }, []);

  // Load duplicate groups on mount
  useEffect(() => {
    const rafId = window.requestAnimationFrame(() => {
      void loadDuplicateGroups();
    });

    return () => {
      window.cancelAnimationFrame(rafId);
    };
  }, [loadDuplicateGroups]);

  const startDuplicateScan = useCallback(
    async (directoryPath: string, similarityThreshold: number = 5.0) => {
      try {
        setLoading(true);
        setScanProgress(0);

        const response = (await api.scanDuplicatesWithPath(
          directoryPath,
          similarityThreshold
        )) as ScanDuplicatesResponse;

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
              jobResponse && 'job_status' in jobResponse
                ? jobResponse.job_status
                : jobResponse;

            if (jobStatus) {
              setProcessingJobs((prev) => ({
                ...prev,
                [jobId]: jobStatus,
              }));
            }

            setScanProgress(jobStatus?.progress ?? 0);

            if (jobStatus?.status === 'completed') {
              clearInterval(pollInterval);
              setLoading(false);
              loadDuplicateGroups();
            } else if (jobStatus?.status === 'failed') {
              clearInterval(pollInterval);
              setLoading(false);
            }
          } catch (pollError) {
            console.error('Failed to poll duplicate scan:', pollError);
            clearInterval(pollInterval);
            setLoading(false);
          }
        }, 2000);
      } catch (error) {
        console.error('Failed to start duplicate scan:', error);
        setLoading(false);
      }
    },
    [loadDuplicateGroups]
  );

  const getResolutionSuggestions = useCallback(async (groupId: string) => {
    try {
      const response = await api.get<ResolutionSuggestionsResponse>(
        `/api/duplicates/suggestions/${groupId}`
      );

      const suggestions = Array.isArray(response?.suggestions)
        ? response?.suggestions
        : response?.suggestions?.suggestions;

      setResolutionSuggestions(suggestions ?? []);
    } catch (error) {
      console.error('Failed to get resolution suggestions:', error);
      setResolutionSuggestions([]);
    }
  }, []);

  const resolveDuplicate = useCallback(
    async (groupId: string, action: string, targetPhotos: string[]) => {
      try {
        await api.post('/api/duplicates/resolve', {
          group_id: groupId,
          resolution_action: action,
          target_photos: targetPhotos,
        });

        // Refresh groups
        loadDuplicateGroups();
        setSelectedGroup(null);
        setResolutionSuggestions([]);
      } catch (error) {
        console.error('Failed to resolve duplicates:', error);
      }
    },
    [loadDuplicateGroups]
  );

  const handleDirectorySelect = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        const directoryPath = files[0].webkitRelativePath.split('/')[0];
        startDuplicateScan(directoryPath, 5.0);
      }
    };
    input.click();
  };

  const getGroupTypeColor = (type: string) => {
    switch (type) {
      case 'exact':
        return 'text-red-500';
      case 'near':
        return 'text-orange-500';
      case 'similar':
        return 'text-yellow-500';
      default:
        return 'text-blue-500';
    }
  };

  const getGroupTypeIcon = (type: string) => {
    switch (type) {
      case 'exact':
        return Copy;
      case 'near':
        return Layers;
      case 'similar':
        return ImageIcon;
      default:
        return Target;
    }
  };

  const formatFileSize = (mb: number) => {
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(1)} GB`;
  };

  const tabs: TabId[] = ['groups', 'scan', 'suggestions', 'analytics'];

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white mb-2'>
            Duplicate Management
          </h2>
          <p className='text-gray-400'>
            Find and manage duplicate images to save storage space
          </p>
          <p className='text-gray-500 text-xs'>
            Active jobs: {Object.keys(processingJobs).length} • Selected:{' '}
            {selectedPhotos.size}
          </p>
        </div>
        <div className='flex items-center gap-3'>
          <div className='text-right'>
            <p className='text-white font-semibold'>
              {formatFileSize(totalSpaceSaved)}
            </p>
            <p className='text-gray-400 text-sm'>Potential savings</p>
          </div>
          <button
            onClick={handleDirectorySelect}
            disabled={loading}
            className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2'
          >
            {loading ? (
              <Loader2 className='w-4 h-4 animate-spin' />
            ) : (
              <Search className='w-4 h-4' />
            )}
            Scan for Duplicates
          </button>
        </div>
      </div>

      {/* Scan Progress */}
      {loading && (
        <div className={`${glass.card} p-4`}>
          <div className='flex items-center justify-between mb-2'>
            <h3 className='text-white font-semibold flex items-center gap-2'>
              <Loader2 className='w-4 h-4 animate-spin' />
              Scanning for Duplicates
            </h3>
            <span className='text-gray-400 text-sm'>
              {scanProgress.toFixed(1)}%
            </span>
          </div>
          <div className='w-full h-2 bg-black/30 rounded-full overflow-hidden'>
            <div
              className='h-full bg-blue-500 transition-all duration-300'
              style={{ width: `${scanProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className={`flex space-x-1 p-1 ${surfaceClass} rounded-lg`}>
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
        {/* Groups Tab */}
        {activeTab === 'groups' && (
          <motion.div
            key='groups'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='grid grid-cols-1 lg:grid-cols-3 gap-6'
          >
            {/* Duplicate Groups List */}
            <div className='lg:col-span-2 space-y-4'>
              <div className='flex items-center justify-between'>
                <h3 className='text-xl font-semibold text-white'>
                  Duplicate Groups
                </h3>
                <span className='text-gray-400 text-sm'>
                  {duplicateGroups.length} groups
                </span>
              </div>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                {duplicateGroups.map((group) => (
                  <motion.div
                    key={group.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => {
                      setSelectedGroup(group);
                      setSelectedPhotos(
                        new Set(group.photos.map((p) => p.path))
                      );
                      getResolutionSuggestions(group.id);
                    }}
                    className={`${
                      glass.card
                    } p-4 cursor-pointer border-2 transition-colors ${
                      selectedGroup?.id === group.id
                        ? 'border-blue-500'
                        : 'border-transparent hover:border-white/20'
                    }`}
                  >
                    <div className='flex items-start justify-between mb-3'>
                      <div className='flex items-center gap-2'>
                        {React.createElement(
                          getGroupTypeIcon(group.group_type),
                          {
                            className: `w-4 h-4 ${getGroupTypeColor(
                              group.group_type
                            )}`,
                          }
                        )}
                        <span
                          className={`capitalize ${getGroupTypeColor(
                            group.group_type
                          )} font-medium`}
                        >
                          {group.group_type}
                        </span>
                      </div>
                      <span className='text-gray-400 text-xs'>
                        {group.photos.length} photos
                      </span>
                    </div>

                    {/* Photo thumbnails */}
                    <div className='grid grid-cols-3 gap-1 mb-3'>
                      {group.photos.slice(0, 6).map((photo, index) => (
                        <div
                          key={index}
                          className='aspect-square bg-black/20 rounded overflow-hidden'
                        >
                          <img
                            src={`/api/image/${encodeURIComponent(photo.path)}`}
                            alt={`Photo ${index + 1}`}
                            className='w-full h-full object-cover hover:scale-110 transition-transform'
                          />
                        </div>
                      ))}
                      {group.photos.length > 6 && (
                        <div className='aspect-square bg-black/20 rounded flex items-center justify-center'>
                          <span className='text-gray-400 text-xs'>
                            +{group.photos.length - 6}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className='flex items-center justify-between text-sm'>
                      <span className='text-gray-400'>
                        {formatFileSize(group.total_size_mb)}
                      </span>
                      <span className='text-green-400'>
                        ~{formatFileSize(group.total_size_mb * 0.7)} saved
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Group Details and Actions */}
            <div className='space-y-4'>
              {selectedGroup ? (
                <>
                  <div className={`${glass.card} p-4`}>
                    <h4 className='text-white font-semibold mb-3 flex items-center gap-2'>
                      {React.createElement(
                        getGroupTypeIcon(selectedGroup.group_type),
                        {
                          className: `w-4 h-4 ${getGroupTypeColor(
                            selectedGroup.group_type
                          )}`,
                        }
                      )}
                      {selectedGroup.group_type.charAt(0).toUpperCase() +
                        selectedGroup.group_type.slice(1)}{' '}
                      Duplicates
                    </h4>

                    <div className='space-y-2 mb-4'>
                      <div className='flex justify-between text-sm'>
                        <span className='text-gray-400'>Photos:</span>
                        <span className='text-white'>
                          {selectedGroup.photos.length}
                        </span>
                      </div>
                      <div className='flex justify-between text-sm'>
                        <span className='text-gray-400'>Total Size:</span>
                        <span className='text-white'>
                          {formatFileSize(selectedGroup.total_size_mb)}
                        </span>
                      </div>
                      <div className='flex justify-between text-sm'>
                        <span className='text-gray-400'>Similarity:</span>
                        <span className='text-white'>
                          {selectedGroup.similarity_threshold}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => setShowComparison(true)}
                      className='w-full px-3 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 flex items-center justify-center gap-2'
                    >
                      <ZoomIn className='w-4 h-4' />
                      Compare Images
                    </button>
                  </div>

                  {resolutionSuggestions.length > 0 && (
                    <div className={`${glass.card} p-4`}>
                      <h4 className='text-white font-semibold mb-3 flex items-center gap-2'>
                        <Sparkles className='w-4 h-4 text-yellow-500' />
                        Smart Suggestions
                      </h4>

                      <div className='space-y-2'>
                        {resolutionSuggestions.map((suggestion, index) => (
                          <div
                            key={index}
                            className='p-2 bg-black/20 rounded-lg'
                          >
                            <p className='text-white text-sm mb-1'>
                              {suggestion.description}
                            </p>
                            <div className='flex items-center justify-between'>
                              <p className='text-green-400 text-xs'>
                                {suggestion.reasoning}
                              </p>
                              <span className='text-gray-400 text-xs'>
                                {formatFileSize(suggestion.space_saved_mb)}
                              </span>
                            </div>
                            <button
                              onClick={() => {
                                const targetPhotos = suggestion.target_photo
                                  ? [suggestion.target_photo]
                                  : [];
                                resolveDuplicate(
                                  selectedGroup.id,
                                  suggestion.action,
                                  targetPhotos
                                );
                              }}
                              className='mt-2 w-full px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700'
                            >
                              Apply
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className={`${glass.card} p-4`}>
                    <h4 className='text-white font-semibold mb-3'>
                      Quick Actions
                    </h4>
                    <div className='space-y-2'>
                      <button
                        onClick={() =>
                          resolveDuplicate(
                            selectedGroup.id,
                            'keep_best',
                            selectedGroup.photos.map((p) => p.path)
                          )
                        }
                        className='w-full px-3 py-2 bg-green-600/20 text-green-400 rounded-lg hover:bg-green-600/30'
                      >
                        Keep Best Quality
                      </button>
                      <button
                        onClick={() =>
                          resolveDuplicate(
                            selectedGroup.id,
                            'keep_largest',
                            selectedGroup.photos.map((p) => p.path)
                          )
                        }
                        className='w-full px-3 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30'
                      >
                        Keep Largest Files
                      </button>
                      <button
                        onClick={() =>
                          resolveDuplicate(
                            selectedGroup.id,
                            'move_edited',
                            selectedGroup.photos.map((p) => p.path)
                          )
                        }
                        className='w-full px-3 py-2 bg-yellow-600/20 text-yellow-400 rounded-lg hover:bg-yellow-600/30'
                      >
                        Archive Duplicates
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className={`${glass.card} p-6 text-center`}>
                  <Copy className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400'>
                    Select a duplicate group to view details and actions
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Scan Tab */}
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
                Configure Duplicate Scan
              </h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                <div>
                  <label className='block text-gray-300 text-sm mb-2'>
                    Directory to Scan
                  </label>
                  <button
                    onClick={handleDirectorySelect}
                    disabled={loading}
                    className='w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
                  >
                    <FolderOpen className='w-4 h-4' />
                    {loading ? 'Scanning...' : 'Select Directory'}
                  </button>
                </div>

                <div>
                  <label className='block text-gray-300 text-sm mb-2'>
                    Similarity Threshold
                  </label>
                  <select className='w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'>
                    <option value='0'>Exact Duplicates Only</option>
                    <option value='2' selected>
                      Near Duplicates (5% difference)
                    </option>
                    <option value='5'>Similar Images (15% difference)</option>
                    <option value='10'>
                      Visually Similar (30% difference)
                    </option>
                  </select>
                </div>
              </div>

              <div className='mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
                <div className='flex items-start gap-3'>
                  <AlertCircle className='w-5 h-5 text-blue-500 mt-0.5' />
                  <div>
                    <h4 className='text-blue-400 font-medium mb-1'>
                      Scan Information
                    </h4>
                    <p className='text-gray-300 text-sm'>
                      The scan will compare images using multiple algorithms
                      including MD5 hashing, perceptual hashing (PHash), and
                      color histogram analysis. This process may take several
                      minutes for large collections.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Advanced Options
              </h3>

              <div className='space-y-4'>
                <div className='flex items-center justify-between'>
                  <div>
                    <h4 className='text-white font-medium'>
                      Include Subdirectories
                    </h4>
                    <p className='text-gray-400 text-sm'>
                      Scan all subdirectories recursively
                    </p>
                  </div>
                  <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                    <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                  </button>
                </div>

                <div className='flex items-center justify-between'>
                  <div>
                    <h4 className='text-white font-medium'>
                      Ignore Small Files
                    </h4>
                    <p className='text-gray-400 text-sm'>
                      Skip files smaller than 50KB
                    </p>
                  </div>
                  <button className='w-12 h-6 bg-gray-600 rounded-full relative'>
                    <div className='absolute left-1 top-1 w-4 h-4 bg-white rounded-full' />
                  </button>
                </div>

                <div className='flex items-center justify-between'>
                  <div>
                    <h4 className='text-white font-medium'>
                      Parallel Processing
                    </h4>
                    <p className='text-gray-400 text-sm'>
                      Use multiple CPU cores for faster scanning
                    </p>
                  </div>
                  <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                    <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Suggestions Tab */}
        {activeTab === 'suggestions' && (
          <motion.div
            key='suggestions'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Smart Suggestions
            </h3>
            <p className='text-gray-400 mb-6'>
              Get smart suggestions for managing duplicates based on image
              quality, metadata, and common user patterns.
            </p>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
              <div className='p-4 bg-black/20 rounded-lg'>
                <Sparkles className='w-8 h-8 text-yellow-500 mb-3' />
                <h4 className='text-white font-medium mb-2'>
                  Quality-Based Resolution
                </h4>
                <p className='text-gray-400 text-sm'>
                  Automatically keep the highest quality image in each duplicate
                  group
                </p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <HardDrive className='w-8 h-8 text-blue-500 mb-3' />
                <h4 className='text-white font-medium mb-2'>
                  Storage Optimization
                </h4>
                <p className='text-gray-400 text-sm'>
                  Prioritize actions that maximize storage space savings
                </p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <Archive className='w-8 h-8 text-green-500 mb-3' />
                <h4 className='text-white font-medium mb-2'>Smart Archiving</h4>
                <p className='text-gray-400 text-sm'>
                  Move duplicates to archive folders instead of deleting
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <motion.div
            key='analytics'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`${glass.card} p-6`}
          >
            <h3 className='text-xl font-semibold text-white mb-4'>
              Duplicate Analytics
            </h3>

            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6'>
              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <Copy className='w-5 h-5 text-red-500' />
                  <span className='text-gray-400 text-xs'>Total</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {duplicateGroups.length}
                </p>
                <p className='text-gray-400 text-sm'>Duplicate Groups</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <ImageIcon className='w-5 h-5 text-blue-500' />
                  <span className='text-gray-400 text-xs'>Total</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {duplicateGroups.reduce(
                    (sum, group) => sum + group.photos.length,
                    0
                  )}
                </p>
                <p className='text-gray-400 text-sm'>Duplicate Photos</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <HardDrive className='w-5 h-5 text-green-500' />
                  <span className='text-gray-400 text-xs'>Saved</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {formatFileSize(totalSpaceSaved)}
                </p>
                <p className='text-gray-400 text-sm'>Potential Space</p>
              </div>

              <div className='p-4 bg-black/20 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <BarChart3 className='w-5 h-5 text-yellow-500' />
                  <span className='text-gray-400 text-xs'>Average</span>
                </div>
                <p className='text-2xl font-bold text-white'>
                  {duplicateGroups.length > 0
                    ? (
                        duplicateGroups.reduce(
                          (sum, group) => sum + group.photos.length,
                          0
                        ) / duplicateGroups.length
                      ).toFixed(1)
                    : '0'}
                </p>
                <p className='text-gray-400 text-sm'>Photos per Group</p>
              </div>
            </div>

            <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
              <div>
                <h4 className='text-white font-medium mb-3'>
                  Duplicate Types Distribution
                </h4>
                <div className='space-y-2'>
                  {['exact', 'near', 'similar'].map((type) => {
                    const count = duplicateGroups.filter(
                      (g) => g.group_type === type
                    ).length;
                    const percentage =
                      duplicateGroups.length > 0
                        ? (count / duplicateGroups.length) * 100
                        : 0;
                    return (
                      <div
                        key={type}
                        className='flex items-center justify-between'
                      >
                        <span className='text-gray-300 capitalize'>{type}</span>
                        <div className='flex items-center gap-2'>
                          <div className='w-24 h-2 bg-black/30 rounded-full overflow-hidden'>
                            <div
                              className={`h-full ${
                                type === 'exact'
                                  ? 'bg-red-500'
                                  : type === 'near'
                                  ? 'bg-orange-500'
                                  : 'bg-yellow-500'
                              }`}
                              style={{ width: `${percentage}%` }}
                            />
                          </div>
                          <span className='text-gray-400 text-sm w-12 text-right'>
                            {count}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <h4 className='text-white font-medium mb-3'>
                  Space Savings by Type
                </h4>
                <div className='space-y-2'>
                  {['exact', 'near', 'similar'].map((type) => {
                    const spaceSaved = duplicateGroups
                      .filter((g) => g.group_type === type)
                      .reduce(
                        (sum, group) => sum + group.total_size_mb * 0.7,
                        0
                      );
                    return (
                      <div
                        key={type}
                        className='flex items-center justify-between'
                      >
                        <span className='text-gray-300 capitalize'>{type}</span>
                        <span className='text-green-400'>
                          {formatFileSize(spaceSaved)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Comparison Modal */}
      <AnimatePresence>
        {showComparison && selectedGroup && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className='fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4'
            onClick={() => setShowComparison(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className={`${glass.card} max-w-6xl w-full max-h-[90vh] overflow-hidden`}
              onClick={(e) => e.stopPropagation()}
            >
              <div className='p-6 border-b border-white/10'>
                <div className='flex items-center justify-between'>
                  <h3 className='text-xl font-semibold text-white'>
                    Compare Duplicate Images
                  </h3>
                  <button
                    onClick={() => setShowComparison(false)}
                    className='text-gray-400 hover:text-white'
                  >
                    <X className='w-5 h-5' />
                  </button>
                </div>
              </div>

              <div className='p-6'>
                <div className='flex items-center justify-between mb-4'>
                  <button
                    onClick={() =>
                      setCurrentImageIndex(Math.max(0, currentImageIndex - 1))
                    }
                    disabled={currentImageIndex === 0}
                    className='p-2 bg-white/10 rounded-lg hover:bg-white/20 disabled:opacity-50'
                  >
                    <ChevronLeft className='w-4 h-4' />
                  </button>

                  <div className='flex-1 mx-4 text-center'>
                    <p className='text-gray-400 text-sm'>
                      Image {currentImageIndex + 1} of{' '}
                      {selectedGroup.photos.length}
                    </p>
                  </div>

                  <button
                    onClick={() =>
                      setCurrentImageIndex(
                        Math.min(
                          selectedGroup.photos.length - 1,
                          currentImageIndex + 1
                        )
                      )
                    }
                    disabled={
                      currentImageIndex === selectedGroup.photos.length - 1
                    }
                    className='p-2 bg-white/10 rounded-lg hover:bg-white/20 disabled:opacity-50'
                  >
                    <ChevronRight className='w-4 h-4' />
                  </button>
                </div>

                <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
                  {currentImageIndex > 0 && (
                    <div>
                      <h4 className='text-white font-medium mb-2'>
                        Previous Image
                      </h4>
                      <div className='aspect-square bg-black/20 rounded-lg overflow-hidden'>
                        <img
                          src={`/api/image/${encodeURIComponent(
                            selectedGroup.photos[currentImageIndex - 1].path
                          )}`}
                          alt='Previous'
                          className='w-full h-full object-contain'
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <h4 className='text-white font-medium mb-2'>
                      Current Image
                    </h4>
                    <div className='aspect-square bg-black/20 rounded-lg overflow-hidden'>
                      <img
                        src={`/api/image/${encodeURIComponent(
                          selectedGroup.photos[currentImageIndex].path
                        )}`}
                        alt='Current'
                        className='w-full h-full object-contain'
                      />
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(DuplicateManagementPanel);
