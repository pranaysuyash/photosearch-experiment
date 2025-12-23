/**
 * Advanced Features Page
 *
 * Main page that provides access to all 5 advanced features:
 * - Face Recognition & People Clustering
 * - Enhanced Duplicate Management
 * - OCR Text Search with Highlighting
 * - Smart Albums Rule Builder
 * - Analytics Dashboard
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Copy,
  FileText,
  Settings,
  BarChart3,
  FolderOpen,
  Sparkles,
  Shield,
  Zap,
  TrendingUp,
  Eye,
  Lock,
  Play,
  RefreshCw,
  Check,
  AlertCircle,
  Info,
} from 'lucide-react';
import { glass } from '../design/glass';
import { useAmbientThemeContext } from '../contexts/AmbientThemeContext';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';

// Import advanced features components
import {
  FaceRecognitionPanel,
  DuplicateManagementPanel,
  OCRTextSearchPanel,
  SmartAlbumsBuilder,
  AnalyticsDashboard,
} from '../components/advanced';

type FeatureType =
  | 'face-recognition'
  | 'duplicate-management'
  | 'ocr-search'
  | 'smart-albums'
  | 'analytics';

interface Feature {
  id: FeatureType;
  name: string;
  description: string;
  icon: React.ElementType;
  color: string;
  status: 'available' | 'initializing' | 'unavailable';
  capabilities: string[];
}

export function AdvancedFeaturesPage() {
  const { isDark } = useAmbientThemeContext();
  const navigate = useNavigate();
  const [selectedFeature, setSelectedFeature] =
    useState<FeatureType>('face-recognition');
  const [features, setFeatures] = useState<Feature[]>([]);
  const [systemStatus, setSystemStatus] = useState<
    'loading' | 'ready' | 'error'
  >('loading');

  // Hidden Genius: expose /api/advanced/scan-directory
  const [scanDirectoryPath, setScanDirectoryPath] = useState('');
  const [scanFaces, setScanFaces] = useState(true);
  const [scanDuplicates, setScanDuplicates] = useState(true);
  const [scanOcr, setScanOcr] = useState(true);
  const [scanSubmitting, setScanSubmitting] = useState(false);
  const [scanResult, setScanResult] = useState<null | {
    job_ids: string[];
    message?: string;
  }>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  // Hidden Genius: expose /api/advanced/comprehensive-stats
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [comprehensiveStats, setComprehensiveStats] = useState<any>(null);

  // Load system status and feature availability
  useEffect(() => {
    loadSystemStatus();
    const interval = setInterval(loadSystemStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      const data = await api.get('/api/advanced/status');

      setSystemStatus('ready');

      const featureData: Feature[] = [
        {
          id: 'face-recognition',
          name: 'Face Recognition',
          description: 'Detect, cluster, and organize photos by people',
          icon: Users,
          color: 'text-purple-500',
          status: data.features?.face_recognition?.available
            ? 'available'
            : 'unavailable',
          capabilities: [
            'Face detection and clustering',
            'Person labeling and search',
            'Privacy-first processing',
            'GPU acceleration support',
            'Encrypted face data storage',
          ],
        },
        {
          id: 'duplicate-management',
          name: 'Duplicate Management',
          description: 'Find and manage duplicate and similar images',
          icon: Copy,
          color: 'text-red-500',
          status: data.features?.duplicate_detection?.available
            ? 'available'
            : 'unavailable',
          capabilities: [
            'Multiple hash algorithms',
            'Visual comparison tools',
            'Smart resolution suggestions',
            'Batch duplicate operations',
            'Space savings calculation',
          ],
        },
        {
          id: 'ocr-search',
          name: 'OCR Text Search',
          description: 'Search for text within images using OCR technology',
          icon: FileText,
          color: 'text-blue-500',
          status: data.features?.ocr_search?.available
            ? 'available'
            : 'unavailable',
          capabilities: [
            'Multi-language text extraction',
            'Text highlighting in results',
            'Handwriting recognition',
            'Confidence scoring',
            'Batch text processing',
          ],
        },
        {
          id: 'smart-albums',
          name: 'Smart Albums',
          description: 'Create intelligent albums with custom rules',
          icon: FolderOpen,
          color: 'text-green-500',
          status: 'available', // Always available
          capabilities: [
            'Visual rule builder',
            'Suggested albums',
            'Template system',
            'Complex boolean logic',
            'Real-time preview',
          ],
        },
        {
          id: 'analytics',
          name: 'Analytics Dashboard',
          description: 'Get insights and analytics about your photo library',
          icon: BarChart3,
          color: 'text-yellow-500',
          status: 'available', // Always available
          capabilities: [
            'Library usage analytics',
            'Search pattern analysis',
            'Performance monitoring',
            'Storage optimization insights',
            'User behavior tracking',
          ],
        },
      ];

      setFeatures(featureData);
    } catch (error) {
      console.error('Failed to load system status:', error);
      setSystemStatus('error');
    }
  };

  const startComprehensiveScan = async () => {
    const directory_path = scanDirectoryPath.trim();
    if (!directory_path) {
      setScanError('Please enter a directory path to scan.');
      return;
    }

    setScanSubmitting(true);
    setScanError(null);
    setScanResult(null);

    try {
      const res = await api.post('/api/advanced/scan-directory', {
        directory_path,
        scan_faces: scanFaces,
        scan_duplicates: scanDuplicates,
        scan_ocr: scanOcr,
      });

      setScanResult({
        job_ids: Array.isArray(res?.job_ids) ? res.job_ids : [],
        message: res?.message,
      });
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to start scan';
      setScanError(String(detail));
    } finally {
      setScanSubmitting(false);
    }
  };

  const loadComprehensiveStats = async () => {
    setStatsLoading(true);
    setStatsError(null);

    try {
      const data = await api.get('/api/advanced/comprehensive-stats');
      setComprehensiveStats(data);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to load comprehensive stats';
      setStatsError(String(detail));
    } finally {
      setStatsLoading(false);
    }
  };

  const renderFeaturePanel = () => {
    switch (selectedFeature) {
      case 'face-recognition':
        return <FaceRecognitionPanel />;
      case 'duplicate-management':
        return <DuplicateManagementPanel />;
      case 'ocr-search':
        return <OCRTextSearchPanel />;
      case 'smart-albums':
        return <SmartAlbumsBuilder />;
      case 'analytics':
        return <AnalyticsDashboard />;
      default:
        return null;
    }
  };

  const getFeatureIcon = (feature: Feature) => {
    const Icon = feature.icon;
    const iconColor =
      feature.status === 'available' ? feature.color : 'text-gray-500';

    return (
      <div
        className={`w-12 h-12 rounded-lg bg-black/30 flex items-center justify-center mb-3 ${iconColor}`}
      >
        {React.createElement(
          Icon as React.ElementType<{ className?: string }>,
          { className: 'w-6 h-6' }
        )}
      </div>
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'available':
        return (
          <div className='flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full'>
            <div className='w-1.5 h-1.5 bg-green-400 rounded-full' />
            Available
          </div>
        );
      case 'initializing':
        return (
          <div className='flex items-center gap-1 px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full'>
            <div className='w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse' />
            Initializing
          </div>
        );
      case 'unavailable':
        return (
          <div className='flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full'>
            <div className='w-1.5 h-1.5 bg-red-400 rounded-full' />
            Unavailable
          </div>
        );
      default:
        return null;
    }
  };

  if (systemStatus === 'loading') {
    return (
      <div className='min-h-screen bg-black flex items-center justify-center'>
        <div className={`${glass.card} p-8 text-center`}>
          <div className='w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4' />
          <p className='text-gray-300'>Loading advanced features...</p>
        </div>
      </div>
    );
  }

  if (systemStatus === 'error') {
    return (
      <div className='min-h-screen bg-black flex items-center justify-center'>
        <div className={`${glass.card} p-8 text-center max-w-md`}>
          <AlertCircle className='w-12 h-12 text-red-500 mx-auto mb-4' />
          <h2 className='text-xl font-semibold text-white mb-2'>
            Service Unavailable
          </h2>
          <p className='text-gray-400'>
            Unable to load advanced features. Please check your connection and
            try again.
          </p>
          <button
            onClick={() => window.location.reload()}
            className='mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700'
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className='min-h-screen bg-black'>
      {/* Header */}
      <div className='p-6 border-b border-white/10'>
        <div className='max-w-7xl mx-auto'>
          <div className='flex items-center justify-between mb-4'>
            <div>
              <h1 className='text-3xl font-bold text-white mb-2'>
                Advanced Features
              </h1>
              <p className='text-gray-400'>
                Powerful smart tools for your photo library
              </p>
            </div>
            <div className='flex items-center gap-4'>
              <div className='text-right'>
                <p className='text-sm text-gray-400'>System Status</p>
                <p className='text-lg font-semibold text-green-400'>Ready</p>
              </div>
              <button
                className='p-2 bg-white/10 rounded-lg hover:bg-white/20 text-gray-400 hover:text-white'
                aria-label='Advanced settings'
                title='Advanced settings'
              >
                <Settings className='w-5 h-5' />
              </button>
            </div>
          </div>

          {/* Comprehensive scan quick action (high leverage) */}
          <div className={`${glass.card} p-4 border border-white/10 mb-4`}>
            <div className='flex items-start justify-between gap-4'>
              <div>
                <h2 className='text-white font-semibold flex items-center gap-2'>
                  <Zap className='w-4 h-4 text-yellow-500' />
                  Comprehensive directory scan
                </h2>
                <p className='text-gray-400 text-sm mt-1'>
                  Starts face clustering, duplicate detection, and OCR scans for
                  a directory (runs as background jobs).
                </p>
              </div>
              <button
                onClick={() => navigate('/jobs')}
                className='px-3 py-2 bg-white/10 rounded-lg hover:bg-white/20 text-gray-200 text-sm'
                title='Open job monitor'
              >
                View Jobs
              </button>
            </div>

            <div className='mt-3 grid grid-cols-1 md:grid-cols-3 gap-3'>
              <div className='md:col-span-2'>
                <label className='block text-xs text-gray-400 mb-1'>
                  Directory path
                </label>
                <input
                  value={scanDirectoryPath}
                  onChange={(e) => setScanDirectoryPath(e.target.value)}
                  placeholder='/path/to/photos'
                  className='w-full px-3 py-2 bg-black/40 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50'
                />
              </div>
              <div className='flex items-end'>
                <button
                  onClick={startComprehensiveScan}
                  disabled={scanSubmitting}
                  className='w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2'
                >
                  {scanSubmitting ? (
                    <>
                      <RefreshCw className='w-4 h-4 animate-spin' />
                      Starting…
                    </>
                  ) : (
                    <>
                      <Play className='w-4 h-4' />
                      Start scan
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className='mt-3 flex flex-wrap gap-4'>
              <label className='flex items-center gap-2 text-sm text-gray-300'>
                <input
                  type='checkbox'
                  checked={scanFaces}
                  onChange={(e) => setScanFaces(e.target.checked)}
                />
                Faces
              </label>
              <label className='flex items-center gap-2 text-sm text-gray-300'>
                <input
                  type='checkbox'
                  checked={scanDuplicates}
                  onChange={(e) => setScanDuplicates(e.target.checked)}
                />
                Duplicates
              </label>
              <label className='flex items-center gap-2 text-sm text-gray-300'>
                <input
                  type='checkbox'
                  checked={scanOcr}
                  onChange={(e) => setScanOcr(e.target.checked)}
                />
                OCR
              </label>
            </div>

            {scanError && (
              <div className='mt-3 text-sm text-red-400 flex items-center gap-2'>
                <AlertCircle className='w-4 h-4' />
                {scanError}
              </div>
            )}

            {scanResult && (
              <div className='mt-3 text-sm text-green-400'>
                <div className='flex items-center gap-2'>
                  <Check className='w-4 h-4' />
                  {scanResult.message || 'Scan started'}
                </div>
                {scanResult.job_ids.length > 0 && (
                  <div className='mt-2 text-gray-300'>
                    Job IDs: {scanResult.job_ids.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Comprehensive stats quick action (high leverage) */}
          <div className={`${glass.card} p-4 border border-white/10 mb-4`}>
            <div className='flex items-start justify-between gap-4'>
              <div>
                <h2 className='text-white font-semibold flex items-center gap-2'>
                  <TrendingUp className='w-4 h-4 text-green-400' />
                  Comprehensive stats
                </h2>
                <p className='text-gray-400 text-sm mt-1'>
                  Loads deep library and pipeline statistics (faces, duplicates,
                  OCR, and active jobs).
                </p>
              </div>
              <div className='flex items-center gap-2'>
                <button
                  onClick={loadComprehensiveStats}
                  disabled={statsLoading}
                  className='px-3 py-2 bg-white/10 rounded-lg hover:bg-white/20 text-gray-200 text-sm disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2'
                  title='Load comprehensive stats'
                >
                  {statsLoading ? (
                    <>
                      <RefreshCw className='w-4 h-4 animate-spin' />
                      Loading…
                    </>
                  ) : (
                    <>
                      <RefreshCw className='w-4 h-4' />
                      Load stats
                    </>
                  )}
                </button>
              </div>
            </div>

            {statsError && (
              <div className='mt-3 text-sm text-red-400 flex items-center gap-2'>
                <AlertCircle className='w-4 h-4' />
                {statsError}
              </div>
            )}

            {comprehensiveStats && (
              <div className='mt-3 grid grid-cols-1 md:grid-cols-3 gap-3'>
                <div className='bg-black/30 border border-white/10 rounded-lg p-3'>
                  <div className='text-xs text-gray-400'>Total photos</div>
                  <div className='text-lg text-white font-semibold'>
                    {comprehensiveStats?.library_stats?.total_photos ?? '—'}
                  </div>
                </div>
                <div className='bg-black/30 border border-white/10 rounded-lg p-3'>
                  <div className='text-xs text-gray-400'>Total size (GB)</div>
                  <div className='text-lg text-white font-semibold'>
                    {typeof comprehensiveStats?.library_stats?.total_size_gb ===
                    'number'
                      ? comprehensiveStats.library_stats.total_size_gb.toFixed(2)
                      : '—'}
                  </div>
                </div>
                <div className='bg-black/30 border border-white/10 rounded-lg p-3'>
                  <div className='text-xs text-gray-400'>Active jobs</div>
                  <div className='text-lg text-white font-semibold'>
                    {comprehensiveStats?.active_jobs ?? '—'}
                  </div>
                </div>

                <div className='md:col-span-3'>
                  <div className='flex items-center gap-2 text-xs text-gray-400 mb-1'>
                    <Info className='w-3.5 h-3.5' />
                    Raw payload (for debugging / trust)
                  </div>
                  <pre className='max-h-64 overflow-auto text-xs text-gray-200 bg-black/40 border border-white/10 rounded-lg p-3 whitespace-pre-wrap'>
                    {JSON.stringify(comprehensiveStats, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Feature Navigation */}
          <div className='flex space-x-4 overflow-x-auto pb-2'>
            {features.map((feature) => (
              <motion.button
                key={feature.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedFeature(feature.id)}
                className={`flex-shrink-0 p-4 rounded-lg border-2 transition-all ${
                  selectedFeature === feature.id
                    ? 'bg-blue-600/20 border-blue-500'
                    : 'bg-white/5 border-white/20 hover:border-white/30'
                }`}
              >
                <div className='flex items-center gap-3'>
                  {getFeatureIcon(feature)}
                  <div className='text-left'>
                    <h3 className='text-white font-medium'>{feature.name}</h3>
                    <p className='text-gray-400 text-sm'>
                      {feature.description}
                    </p>
                  </div>
                  {getStatusBadge(feature.status)}
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      </div>

      {/* Feature Panel */}
      <div className='max-w-7xl mx-auto p-6'>
        <AnimatePresence mode='wait'>
          <motion.div
            key={selectedFeature}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {renderFeaturePanel()}
          </motion.div>
        </AnimatePresence>

        {/* Feature Capabilities */}
        {selectedFeature && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className={`${glass.card} p-6 mt-6`}
          >
            <div className='flex items-center gap-3 mb-4'>
              <Sparkles className='w-5 h-5 text-yellow-500' />
              <h3 className='text-lg font-semibold text-white'>Capabilities</h3>
            </div>
            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3'>
              {features
                .find((f) => f.id === selectedFeature)
                ?.capabilities.map((capability, index) => (
                  <div key={index} className='flex items-center gap-2'>
                    <Check className='w-4 h-4 text-green-500 flex-shrink-0' />
                    <span className='text-gray-300 text-sm'>{capability}</span>
                  </div>
                ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
