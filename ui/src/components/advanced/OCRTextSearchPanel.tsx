/**
 * OCR Text Search Panel
 *
 * Advanced OCR and text search UI with:
 * - Multi-language text extraction and search
 * - Text region highlighting in search results
 * - Confidence indicators and quality assessment
 * - Handwriting recognition support
 * - Batch processing and progress tracking
 * - Language auto-detection
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  FileText,
  Globe,
  PenTool,
  Loader2,
  Check,
  X,
  AlertCircle,
  Settings,
  Download,
  Upload,
  Play,
  Pause,
  Eye,
  EyeOff,
  Highlighter,
  Type,
  Languages,
  Zap,
  Camera,
  FolderOpen,
  BarChart3,
  Filter,
  Trash2,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';
import { useAmbientThemeContext } from '../../contexts/AmbientThemeContext';

export interface TextRegion {
  id: string;
  photo_path: string;
  text_content: string;
  highlighted_text: string;
  confidence_score: number;
  language_code: string;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  text_type: string;
  reading_order: number;
  created_at: string;
}

export interface OCRResult {
  photo_path: string;
  text_regions: TextRegion[];
  full_text: string;
  languages_detected: string[];
  processing_time_ms: number;
  confidence_average: number;
  created_at: string;
}

interface LanguageInfo {
  code: string;
  name: string;
  supported: boolean;
}

interface ProcessingJob {
  job_id: string;
  status: string;
  message: string;
  progress: number;
  created_at: string;
  updated_at?: string;
  results?: any;
}

const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: 'en', name: 'English', supported: true },
  { code: 'es', name: 'Spanish', supported: true },
  { code: 'fr', name: 'French', supported: true },
  { code: 'de', name: 'German', supported: true },
  { code: 'it', name: 'Italian', supported: true },
  { code: 'pt', name: 'Portuguese', supported: true },
  { code: 'ru', name: 'Russian', supported: false },
  { code: 'ja', name: 'Japanese', supported: false },
  { code: 'zh', name: 'Chinese', supported: false },
  { code: 'ko', name: 'Korean', supported: false },
  { code: 'ar', name: 'Arabic', supported: false },
  { code: 'hi', name: 'Hindi', supported: false },
];

export function OCRTextSearchPanel() {
  const { isDark } = useAmbientThemeContext();
  const [activeTab, setActiveTab] = useState<
    'search' | 'extract' | 'regions' | 'settings'
  >('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<TextRegion[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<TextRegion[]>([]);
  const [processingJobs, setProcessingJobs] = useState<
    Record<string, ProcessingJob>
  >({});
  const [loading, setLoading] = useState(false);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(['en']);
  const [minConfidence, setMinConfidence] = useState(0.5);
  const [enableHandwriting, setEnableHandwriting] = useState(true);
  const [showHighlighting, setShowHighlighting] = useState(true);
  const [batchProgress, setBatchProgress] = useState(0);
  const [stats, setStats] = useState<any>({});

  // Load stats on mount
  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const response = await api.get('/api/analytics/library', {
        params: { metric_types: ['ocr_processing'] },
      });
      setStats(response.data.analytics.ocr_processing || {});
    } catch (error) {
      console.error('Failed to load OCR stats:', error);
    }
  }, []);

  const searchText = useCallback(
    async (query: string, language?: string) => {
      try {
        setLoading(true);
        const response = await api.post('/api/ocr/search', {
          query,
          language,
          min_confidence: minConfidence,
          limit: 100,
        });

        setSearchResults(response.data.matches);
      } catch (error) {
        console.error('Failed to search text:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    },
    [minConfidence]
  );

  const extractTextBatch = useCallback(
    async (imagePaths: string[]) => {
      try {
        setLoading(true);

        const response = await api.post('/api/ocr/extract-batch', {
          image_paths: imagePaths,
          languages: selectedLanguages,
          enable_handwriting: enableHandwriting,
        });

        const jobId = response.data.job_id;
        setProcessingJobs((prev) => ({
          ...prev,
          [jobId]: {
            job_id: jobId,
            status: 'queued',
            message: response.data.message,
            progress: 0,
            created_at: new Date().toISOString(),
          },
        }));

        // Start polling for job status
        const pollInterval = setInterval(async () => {
          try {
            const jobResponse = await api.get(`/api/jobs/${jobId}`);
            const jobStatus = jobResponse.data.job_status;

            setProcessingJobs((prev) => ({
              ...prev,
              [jobId]: jobStatus,
            }));

            setBatchProgress(jobStatus.progress || 0);

            if (jobStatus.status === 'completed') {
              clearInterval(pollInterval);
              setLoading(false);
              loadStats();
            } else if (jobStatus.status === 'failed') {
              clearInterval(pollInterval);
              setLoading(false);
            }
          } catch (error) {
            clearInterval(pollInterval);
            setLoading(false);
          }
        }, 2000);
      } catch (error) {
        console.error('Failed to extract text batch:', error);
        setLoading(false);
      }
    },
    [selectedLanguages, enableHandwriting, loadStats]
  );

  const getTextRegions = useCallback(async (imagePath: string) => {
    try {
      const response = await api.get(
        `/api/ocr/regions/${encodeURIComponent(imagePath)}`
      );
      setSelectedRegions(response.data.regions);
    } catch (error) {
      console.error('Failed to get text regions:', error);
      setSelectedRegions([]);
    }
  }, []);

  const handleDirectorySelect = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.multiple = true;
    input.accept = 'image/*';
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        const imagePaths = Array.from(files).map(
          (file) => file.webkitRelativePath
        );
        extractTextBatch(imagePaths);
      }
    };
    input.click();
  };

  const toggleLanguage = useCallback((langCode: string) => {
    setSelectedLanguages((prev) => {
      if (prev.includes(langCode)) {
        return prev.filter((code) => code !== langCode);
      } else {
        return [...prev, langCode];
      }
    });
  }, []);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-500';
    if (confidence >= 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getLanguageFlag = (langCode: string) => {
    const flags: Record<string, string> = {
      en: '🇺🇸',
      es: '🇪🇸',
      fr: '🇫🇷',
      de: '🇩🇪',
      it: '🇮🇹',
      pt: '🇵🇹',
      ru: '🇷🇺',
      ja: '🇯🇵',
      zh: '🇨🇳',
      ko: '🇰🇷',
      ar: '🇸🇦',
      hi: '🇮🇳',
    };
    return flags[langCode] || '🌐';
  };

  const renderHighlightedText = (text: string, highlighted: string) => {
    if (!showHighlighting || !highlighted || !text) {
      return <span className='text-gray-300'>{text}</span>;
    }

    // Safe highlighting: split by highlight markers and style accordingly
    // Expected format: "normal text<mark>highlighted text</mark>normal text"
    const parts = highlighted.split(/<mark>|<\/mark>/);
    const elements: React.ReactNode[] = [];

    parts.forEach((part, index) => {
      // Even indices (0, 2, 4...) are normal text, odd indices (1, 3, 5...) are highlighted
      if (index % 2 === 0) {
        // Normal text
        if (part) {
          elements.push(<span key={index}>{part}</span>);
        }
      } else {
        // Highlighted text - use CSS styling instead of HTML
        if (part) {
          elements.push(
            <span key={index} className='bg-yellow-400 text-black px-1 rounded'>
              {part}
            </span>
          );
        }
      }
    });

    return <span className='text-gray-300'>{elements}</span>;
  };

  return (
    <div className='p-6 space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h2 className='text-2xl font-bold text-white mb-2'>
            OCR Text Search
          </h2>
          <p className='text-gray-400'>
            Search text within images using advanced OCR technology
          </p>
        </div>
        <div className='flex items-center gap-3'>
          <div className='text-right'>
            <p className='text-white font-semibold'>
              {stats.total_text_regions_in_db || 0}
            </p>
            <p className='text-gray-400 text-sm'>Text regions found</p>
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
            Extract Text
          </button>
        </div>
      </div>

      {/* Batch Processing Progress */}
      {Object.keys(processingJobs).length > 0 && (
        <div className={`${glass.card} p-4 space-y-2`}>
          <h3 className='text-white font-semibold flex items-center gap-2'>
            <Play className='w-4 h-4' />
            Active OCR Processing
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
        {['search', 'extract', 'regions', 'settings'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
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
        {/* Search Tab */}
        {activeTab === 'search' && (
          <motion.div
            key='search'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            {/* Search Interface */}
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Search Text in Images
              </h3>

              <div className='flex gap-2 mb-4'>
                <input
                  type='text'
                  placeholder='Search for text in images...'
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && searchQuery.trim()) {
                      searchText(searchQuery);
                    }
                  }}
                  className='flex-1 px-4 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500'
                />
                <button
                  onClick={() => searchQuery.trim() && searchText(searchQuery)}
                  disabled={!searchQuery.trim() || loading}
                  className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  {loading ? (
                    <Loader2 className='w-4 h-4 animate-spin' />
                  ) : (
                    <Search className='w-4 h-4' />
                  )}
                </button>
              </div>

              {/* Search Filters */}
              <div className='flex items-center gap-4 text-sm'>
                <div className='flex items-center gap-2'>
                  <span className='text-gray-400'>Language:</span>
                  <select
                    value=''
                    onChange={(e) =>
                      e.target.value && searchText(searchQuery, e.target.value)
                    }
                    className='px-2 py-1 bg-black/30 border border-white/20 rounded text-white text-sm'
                  >
                    <option value=''>All Languages</option>
                    {SUPPORTED_LANGUAGES.filter((lang) =>
                      selectedLanguages.includes(lang.code)
                    ).map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {getLanguageFlag(lang.code)} {lang.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className='flex items-center gap-2'>
                  <span className='text-gray-400'>Min Confidence:</span>
                  <input
                    type='range'
                    min='0'
                    max='1'
                    step='0.1'
                    value={minConfidence}
                    onChange={(e) =>
                      setMinConfidence(parseFloat(e.target.value))
                    }
                    className='w-24'
                  />
                  <span className='text-gray-400 text-xs w-8'>
                    {(minConfidence * 100).toFixed(0)}%
                  </span>
                </div>

                <button
                  onClick={() => setShowHighlighting(!showHighlighting)}
                  className={`flex items-center gap-1 px-2 py-1 rounded ${
                    showHighlighting
                      ? 'bg-blue-600 text-white'
                      : 'bg-white/10 text-gray-400'
                  }`}
                >
                  <Highlighter className='w-3 h-3' />
                  Highlight
                </button>
              </div>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className={`${glass.card} p-6`}>
                <h3 className='text-xl font-semibold text-white mb-4'>
                  Found {searchResults.length} results for "{searchQuery}"
                </h3>

                <div className='space-y-4'>
                  {searchResults.map((region, index) => (
                    <motion.div
                      key={region.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className='p-4 bg-black/20 rounded-lg border border-white/10 hover:border-white/20 transition-colors'
                    >
                      <div className='flex items-start justify-between mb-2'>
                        <div className='flex items-center gap-3'>
                          <span className='text-lg'>
                            {getLanguageFlag(region.language_code)}
                          </span>
                          <span className='text-white font-medium capitalize'>
                            {SUPPORTED_LANGUAGES.find(
                              (l) => l.code === region.language_code
                            )?.name || region.language_code}
                          </span>
                          <span
                            className={`text-sm ${getConfidenceColor(
                              region.confidence_score
                            )}`}
                          >
                            {(region.confidence_score * 100).toFixed(1)}%
                          </span>
                          <span className='px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded'>
                            {region.text_type}
                          </span>
                        </div>
                        <button
                          onClick={() => getTextRegions(region.photo_path)}
                          className='text-gray-400 hover:text-white'
                        >
                          <Eye className='w-4 h-4' />
                        </button>
                      </div>

                      <div className='mb-3'>
                        {renderHighlightedText(
                          region.text_content,
                          region.highlighted_text
                        )}
                      </div>

                      <div className='flex items-center justify-between'>
                        <span className='text-gray-400 text-sm'>
                          {region.photo_path.split('/').pop()}
                        </span>
                        <div className='flex items-center gap-2'>
                          <span className='text-gray-400 text-xs'>
                            Position: ({region.bbox.x}, {region.bbox.y})
                          </span>
                          <button className='px-2 py-1 bg-white/10 text-gray-300 text-xs rounded hover:bg-white/20'>
                            View Image
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Extract Tab */}
        {activeTab === 'extract' && (
          <motion.div
            key='extract'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Text Extraction
              </h3>

              <div className='grid grid-cols-1 md:grid-cols-2 gap-6 mb-6'>
                <div>
                  <h4 className='text-white font-medium mb-3 flex items-center gap-2'>
                    <Languages className='w-4 h-4' />
                    Select Languages
                  </h4>
                  <div className='space-y-2'>
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <label
                        key={lang.code}
                        className='flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 cursor-pointer'
                      >
                        <input
                          type='checkbox'
                          checked={selectedLanguages.includes(lang.code)}
                          onChange={() => toggleLanguage(lang.code)}
                          disabled={!lang.supported}
                          className='w-4 h-4 rounded border-white/20 bg-black/30 text-blue-600 focus:ring-blue-500'
                        />
                        <span className='text-lg'>
                          {getLanguageFlag(lang.code)}
                        </span>
                        <span
                          className={`flex-1 ${
                            lang.supported ? 'text-white' : 'text-gray-500'
                          }`}
                        >
                          {lang.name}
                        </span>
                        {!lang.supported && (
                          <span className='text-xs text-gray-500'>
                            Not available
                          </span>
                        )}
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className='text-white font-medium mb-3 flex items-center gap-2'>
                    <Settings className='w-4 h-4' />
                    Extraction Options
                  </h4>
                  <div className='space-y-4'>
                    <div className='flex items-center justify-between'>
                      <div>
                        <h5 className='text-white font-medium'>
                          Handwriting Recognition
                        </h5>
                        <p className='text-gray-400 text-sm'>
                          Extract handwritten text using EasyOCR
                        </p>
                      </div>
                      <button
                        onClick={() => setEnableHandwriting(!enableHandwriting)}
                        className={`w-12 h-6 ${
                          enableHandwriting ? 'bg-blue-600' : 'bg-gray-600'
                        } rounded-full relative`}
                      >
                        <div
                          className={`absolute ${
                            enableHandwriting ? 'right-1' : 'left-1'
                          } top-1 w-4 h-4 bg-white rounded-full transition-transform`}
                        />
                      </button>
                    </div>

                    <div className='flex items-center justify-between'>
                      <div>
                        <h5 className='text-white font-medium'>
                          Auto Language Detection
                        </h5>
                        <p className='text-gray-400 text-sm'>
                          Automatically detect text languages
                        </p>
                      </div>
                      <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                        <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                      </button>
                    </div>

                    <div className='flex items-center justify-between'>
                      <div>
                        <h5 className='text-white font-medium'>
                          Confidence Threshold
                        </h5>
                        <p className='text-gray-400 text-sm'>
                          Minimum confidence for text extraction
                        </p>
                      </div>
                      <input
                        type='range'
                        min='0'
                        max='1'
                        step='0.1'
                        defaultValue='0.5'
                        className='w-32'
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className='p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg'>
                <div className='flex items-start gap-3'>
                  <AlertCircle className='w-5 h-5 text-blue-500 mt-0.5' />
                  <div>
                    <h4 className='text-blue-400 font-medium mb-1'>
                      Extraction Information
                    </h4>
                    <p className='text-gray-300 text-sm'>
                      Text extraction uses Tesseract OCR for printed text and
                      EasyOCR for handwritten text. Processing time varies based
                      on image complexity and selected languages.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Directory Processing
              </h3>

              <button
                onClick={handleDirectorySelect}
                disabled={loading}
                className='w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
              >
                {loading ? (
                  <>
                    <Loader2 className='w-4 h-4 animate-spin' />
                    Processing... ({batchProgress.toFixed(1)}%)
                  </>
                ) : (
                  <>
                    <FolderOpen className='w-4 h-4' />
                    Select Directory for Text Extraction
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}

        {/* Regions Tab */}
        {activeTab === 'regions' && (
          <motion.div
            key='regions'
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className='space-y-6'
          >
            <div className={`${glass.card} p-6`}>
              <h3 className='text-xl font-semibold text-white mb-4'>
                Text Regions
              </h3>

              {selectedRegions.length > 0 ? (
                <div className='space-y-4'>
                  <div className='grid grid-cols-1 lg:grid-cols-2 gap-6'>
                    <div>
                      <h4 className='text-white font-medium mb-3'>
                        Image with Text Regions
                      </h4>
                      <div className='relative bg-black/20 rounded-lg overflow-hidden'>
                        <img
                          src={`/api/image/${encodeURIComponent(
                            selectedRegions[0].photo_path
                          )}`}
                          alt='Text regions'
                          className='w-full h-auto'
                        />
                        {/* Overlay text regions - simplified for demo */}
                        <div className='absolute inset-0 pointer-events-none'>
                          {selectedRegions.map((region, index) => (
                            <div
                              key={region.id}
                              className='absolute border-2 border-yellow-500 bg-yellow-500/10'
                              style={{
                                left: `${(region.bbox.x / 1000) * 100}%`,
                                top: `${(region.bbox.y / 1000) * 100}%`,
                                width: `${(region.bbox.width / 1000) * 100}%`,
                                height: `${(region.bbox.height / 1000) * 100}%`,
                              }}
                            >
                              <span className='absolute -top-6 left-0 text-xs bg-yellow-500 text-black px-1 rounded'>
                                {index + 1}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className='text-white font-medium mb-3'>
                        Extracted Text
                      </h4>
                      <div className='space-y-3 max-h-96 overflow-y-auto'>
                        {selectedRegions.map((region, index) => (
                          <div
                            key={region.id}
                            className='p-3 bg-black/20 rounded-lg'
                          >
                            <div className='flex items-center justify-between mb-2'>
                              <span className='text-white font-medium'>
                                Region {index + 1}
                              </span>
                              <div className='flex items-center gap-2'>
                                <span
                                  className={`text-sm ${getConfidenceColor(
                                    region.confidence_score
                                  )}`}
                                >
                                  {(region.confidence_score * 100).toFixed(1)}%
                                </span>
                                <span className='text-xs text-gray-400'>
                                  {getLanguageFlag(region.language_code)}
                                </span>
                              </div>
                            </div>
                            <p className='text-gray-300 text-sm mb-2'>
                              {region.text_content}
                            </p>
                            <div className='flex items-center gap-4 text-xs text-gray-500'>
                              <span>
                                Position: ({region.bbox.x}, {region.bbox.y})
                              </span>
                              <span>
                                Size: {region.bbox.width}×{region.bbox.height}
                              </span>
                              <span className='capitalize'>
                                {region.text_type}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className='pt-4 border-t border-white/10'>
                    <h4 className='text-white font-medium mb-3'>Full Text</h4>
                    <div className='p-4 bg-black/20 rounded-lg'>
                      <p className='text-gray-300 whitespace-pre-wrap'>
                        {selectedRegions
                          .map((region) => region.text_content)
                          .join('\n')}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className='text-center py-8'>
                  <FileText className='w-12 h-12 text-gray-600 mx-auto mb-3' />
                  <p className='text-gray-400'>
                    Search for text or extract from images to see text regions
                  </p>
                </div>
              )}
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
            <h3 className='text-xl font-semibold text-white'>OCR Settings</h3>

            <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
              <div>
                <h4 className='text-white font-medium mb-4'>
                  Processing Preferences
                </h4>
                <div className='space-y-4'>
                  <div className='flex items-center justify-between'>
                    <div>
                      <h5 className='text-white font-medium'>
                        GPU Acceleration
                      </h5>
                      <p className='text-gray-400 text-sm'>
                        Use GPU for faster text processing
                      </p>
                    </div>
                    <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                      <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                    </button>
                  </div>

                  <div className='flex items-center justify-between'>
                    <div>
                      <h5 className='text-white font-medium'>
                        Parallel Processing
                      </h5>
                      <p className='text-gray-400 text-sm'>
                        Process multiple images simultaneously
                      </p>
                    </div>
                    <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                      <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                    </button>
                  </div>

                  <div className='flex items-center justify-between'>
                    <div>
                      <h5 className='text-white font-medium'>
                        Auto-enhance Images
                      </h5>
                      <p className='text-gray-400 text-sm'>
                        Improve image quality before OCR
                      </p>
                    </div>
                    <button className='w-12 h-6 bg-blue-600 rounded-full relative'>
                      <div className='absolute right-1 top-1 w-4 h-4 bg-white rounded-full' />
                    </button>
                  </div>
                </div>
              </div>

              <div>
                <h4 className='text-white font-medium mb-4'>
                  Quality & Performance
                </h4>
                <div className='space-y-4'>
                  <div>
                    <label className='block text-gray-300 text-sm mb-2'>
                      Processing Threads
                    </label>
                    <select className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'>
                      <option>Auto (Recommended)</option>
                      <option>1 Thread</option>
                      <option>2 Threads</option>
                      <option>4 Threads</option>
                      <option>8 Threads</option>
                    </select>
                  </div>

                  <div>
                    <label className='block text-gray-300 text-sm mb-2'>
                      Image Quality Threshold
                    </label>
                    <input
                      type='range'
                      min='0'
                      max='100'
                      defaultValue='50'
                      className='w-full'
                    />
                  </div>

                  <div>
                    <label className='block text-gray-300 text-sm mb-2'>
                      Cache Size (MB)
                    </label>
                    <input
                      type='number'
                      defaultValue='512'
                      className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500'
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className='pt-4 border-t border-white/10 space-y-2'>
              <button className='w-full px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 flex items-center justify-center gap-2'>
                <Download className='w-4 h-4' />
                Export OCR Settings
              </button>
              <button className='w-full px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 flex items-center justify-center gap-2'>
                <Trash2 className='w-4 h-4' />
                Clear OCR Cache
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(OCRTextSearchPanel);
