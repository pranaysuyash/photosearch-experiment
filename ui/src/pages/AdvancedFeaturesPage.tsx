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
  Check,
  AlertCircle,
  Info,
} from 'lucide-react';
import { glass } from '../design/glass';
import { useAmbientThemeContext } from '../contexts/AmbientThemeContext';

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
  const [selectedFeature, setSelectedFeature] =
    useState<FeatureType>('face-recognition');
  const [features, setFeatures] = useState<Feature[]>([]);
  const [systemStatus, setSystemStatus] = useState<
    'loading' | 'ready' | 'error'
  >('loading');

  // Load system status and feature availability
  useEffect(() => {
    loadSystemStatus();
    const interval = setInterval(loadSystemStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      const response = await fetch('/api/advanced/status');
      const data = await response.json();

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
        {React.createElement(Icon as React.ElementType<{ className?: string }>, { className: "w-6 h-6" })}
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
              <button className='p-2 bg-white/10 rounded-lg hover:bg-white/20 text-gray-400 hover:text-white'>
                <Settings className='w-5 h-5' />
              </button>
            </div>
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
