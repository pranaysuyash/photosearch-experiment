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
  Loader2,
  AlertCircle,
  Settings,
  Download,
  Play,
  Eye,
  Highlighter,
  Languages,
  Camera,
  FolderOpen,
  Trash2,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '@/design/glass';

export interface TextRegion {
  id: string;
  photo_path: string;
  text_content: string;
  highlighted_text?: string;
  confidence_score: number;
  language_code: string;
  bbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  text_type?: string;
  reading_order?: number;
  created_at?: string;
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
  results?: Record<string, unknown>;
}

type TabId = 'search' | 'extract' | 'regions' | 'settings';
type OcrStats = {
  total_images_processed?: number;
  images_with_text?: number;
  images_without_text?: number;
  total_words_extracted?: number;
  avg_words_per_image?: number;
  language_distribution?: Record<string, number>;
  images_with_most_text?: Array<{ image_path: string; word_count: number }>;
  recent_ocr_processing?: Array<{ image_path: string; extracted_at: string; word_count: number }>;
  [key: string]: unknown;
};
type OcrStatsResponse = { stats?: OcrStats };
type OcrSearchResponse = {
  results?: {
    results?: Array<{
      image_path: string;
      text_content: string;
      language?: string;
      confidence?: number;
      extracted_at?: string;
    }>;
  };
};
type OcrExtractResponse = {
  results?: {
    status?: string;
    processed?: number;
    successful?: number;
    failed?: number;
    message?: string;
  };
};
type OcrImageStatsResponse = {
  stats?: {
    status?: string;
    text_content?: string;
    language?: string;
    confidence?: number;
    extracted_at?: string;
  };
};

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

const LANGUAGE_FLAG_MAP: Record<string, string> = {
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

const LANGUAGE_NORMALIZATION_MAP: Record<string, string> = {
  eng: 'en',
  spa: 'es',
  fra: 'fr',
  deu: 'de',
  ita: 'it',
  por: 'pt',
  rus: 'ru',
  jpn: 'ja',
  chi_sim: 'zh',
  chi_tra: 'zh',
  kor: 'ko',
  ara: 'ar',
  hin: 'hi',
};

const TESSERACT_LANGUAGE_MAP: Record<string, string> = {
  en: 'eng',
  es: 'spa',
  fr: 'fra',
  de: 'deu',
  it: 'ita',
  pt: 'por',
  ru: 'rus',
  ja: 'jpn',
  zh: 'chi_sim',
  ko: 'kor',
  ar: 'ara',
  hi: 'hin',
};

const normalizeLanguageCode = (langCode?: string) => {
  if (!langCode) return 'unknown';
  return LANGUAGE_NORMALIZATION_MAP[langCode] || langCode;
};

const toTesseractLanguage = (langCode: string) => {
  return TESSERACT_LANGUAGE_MAP[langCode] || langCode || 'eng';
};

const buildHighlightedText = (text: string, query: string) => {
  if (!query.trim()) return text;
  const safeQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(safeQuery, 'gi');
  return text.replace(regex, (match) => `<mark>${match}</mark>`);
};

const getLanguageFlag = (langCode: string) => {
  const normalized = normalizeLanguageCode(langCode);
  return LANGUAGE_FLAG_MAP[normalized] || '🌐';
};

export function OCRTextSearchPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<TextRegion[]>([]);
  const [selectedRegions, setSelectedRegions] = useState<TextRegion[]>([]);
  const [processingJobs, setProcessingJobs] = useState<
    Record<string, ProcessingJob>
  >({});
  const [loading, setLoading] = useState(false);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(['en']);
  const [minConfidence, setMinConfidence] = useState(0.5);
  const [enableHandwriting] = useState(false);
  const [showHighlighting, setShowHighlighting] = useState(true);
  const [batchProgress, setBatchProgress] = useState(0);
  const [stats, setStats] = useState<OcrStats>({});

  const loadStats = useCallback(async () => {
    try {
      const response = await api.get<OcrStatsResponse>('/ocr/stats');
      setStats(response?.stats ?? {});
    } catch (error) {
      console.error('Failed to load OCR stats:', error);
    }
  }, []);

  // Load stats on mount
  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  // "Clear OCR Data" — destructive: wipes all extracted text via DELETE /ocr/all
  const [clearingOcr, setClearingOcr] = useState(false);
  const [clearOcrError, setClearOcrError] = useState<string | null>(null);
  const handleClearOcrData = useCallback(async () => {
    if (
      !window.confirm(
        'Delete ALL extracted OCR text? This cannot be undone.'
      )
    ) {
      return;
    }
    setClearingOcr(true);
    setClearOcrError(null);
    try {
      await api.deleteOcrAll();
      await loadStats();
    } catch (err) {
      setClearOcrError(
        err instanceof Error ? err.message : 'Failed to clear OCR data'
      );
    } finally {
      setClearingOcr(false);
    }
  }, [loadStats]);

  const searchText = useCallback(
    async (query: string, language?: string) => {
      try {
        setLoading(true);
        const response = await api.get<OcrSearchResponse>('/ocr/search', {
          params: {
            query,
            limit: 100,
            offset: 0,
            ...(language ? { language } : {}),
          },
        });

        const matches = response?.results?.results ?? [];
        const normalized = matches.map((match, index) => {
          const normalizedLanguage = normalizeLanguageCode(match.language);
          return {
            id: `${match.image_path}-${index}`,
            photo_path: match.image_path,
            text_content: match.text_content,
            highlighted_text: buildHighlightedText(
              match.text_content,
              query
            ),
            confidence_score:
              typeof match.confidence === 'number' ? match.confidence : 0,
            language_code: normalizedLanguage,
            text_type: 'full',
            reading_order: index,
            created_at: match.extracted_at,
          } as TextRegion;
        });

        const filteredByLanguage =
          selectedLanguages.length > 0
            ? normalized.filter((result) =>
                selectedLanguages.includes(result.language_code)
              )
            : normalized;

        setSearchResults(
          filteredByLanguage.filter(
            (result) => result.confidence_score >= minConfidence
          )
        );
      } catch (error) {
        console.error('Failed to search text:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    },
    [minConfidence, selectedLanguages]
  );

  const extractTextBatch = useCallback(
    async (imagePaths: string[]) => {
      const jobId = `ocr-${Date.now()}`;
      const selectedLanguage = selectedLanguages[0] ?? 'en';
      const language = toTesseractLanguage(selectedLanguage);
      try {
        setLoading(true);
        setBatchProgress(0);
        setProcessingJobs((prev) => ({
          ...prev,
          [jobId]: {
            job_id: jobId,
            status: 'processing',
            message: 'Extracting text...',
            progress: 0,
            created_at: new Date().toISOString(),
          },
        }));

        const response = await api.post<OcrExtractResponse>('/ocr/extract', {
          image_paths: imagePaths,
          language,
        });

        const result = response?.results;
        const failed = result?.status === 'error';
        const message =
          result?.message ||
          (failed ? 'OCR extraction failed' : 'OCR extraction complete');

        setProcessingJobs((prev) => ({
          ...prev,
          [jobId]: {
            ...prev[jobId],
            status: failed ? 'failed' : 'completed',
            progress: 100,
            message,
          },
        }));
        setBatchProgress(100);
        loadStats();
      } catch (error) {
        console.error('Failed to extract text batch:', error);
        setProcessingJobs((prev) => ({
          ...prev,
          [jobId]: {
            ...prev[jobId],
            status: 'failed',
            progress: 0,
            message: 'OCR extraction failed',
          },
        }));
      } finally {
        setLoading(false);
      }
    },
    [selectedLanguages, loadStats]
  );

  const getTextRegions = useCallback(async (imagePath: string) => {
    try {
      const response = await api.get<OcrImageStatsResponse>(
        `/ocr/image/${encodeURIComponent(imagePath)}`
      );
      const stats = response?.stats;
      if (stats?.status !== 'processed') {
        setSelectedRegions([]);
        return;
      }
      const textContent = stats.text_content ?? '';
      const normalizedLanguage = normalizeLanguageCode(stats.language);
      setSelectedRegions([
        {
          id: `${imagePath}-full`,
          photo_path: imagePath,
          text_content: textContent,
          highlighted_text: buildHighlightedText(textContent, searchQuery),
          confidence_score:
            typeof stats.confidence === 'number' ? stats.confidence : 0,
          language_code: normalizedLanguage,
          text_type: 'full',
          reading_order: 0,
          created_at: stats.extracted_at,
        },
      ]);
    } catch (error) {
      console.error('Failed to get text regions:', error);
      setSelectedRegions([]);
    }
  }, [searchQuery]);

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

  const renderHighlightedText = (text: string, highlighted?: string) => {
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

  const hasRegionGeometry = selectedRegions.some((region) => region.bbox);

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
              {stats.total_images_processed || 0}
            </p>
            <p className='text-gray-400 text-sm'>Images processed</p>
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
                    className='h-full bg-blue-500 transition-[width] duration-300'
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
        {(['search', 'extract', 'regions', 'settings'] as TabId[]).map(
          (tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2 rounded-md capitalize transition ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {tab}
            </button>
          )
        )}
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
                  type='search'
                  placeholder='Search for text in images…'
                  aria-label='Search for text in images'
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
                  aria-label='Search text in images'
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
                    aria-label='OCR language filter'
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
                    aria-label='Minimum confidence'
                    aria-valuetext={`${(minConfidence * 100).toFixed(0)} percent`}
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
                  aria-pressed={showHighlighting}
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
              /* Result count is announced to assistive tech as results arrive */
              <div className={`${glass.card} p-6`} role='status' aria-live='polite'>
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
                            {region.text_type || 'text'}
                          </span>
                        </div>
                        <button
                          onClick={() => getTextRegions(region.photo_path)}
                          aria-label='View text regions on photo'
                          className='text-gray-400 hover:text-white'
                        >
                          <Eye className='w-4 h-4' />
                        </button>
                      </div>

                      <div className='mb-3'>
                        {renderHighlightedText(
                          region.text_content,
                          region.highlighted_text || region.text_content
                        )}
                      </div>

                      <div className='flex items-center justify-between'>
                        <span className='text-gray-400 text-sm'>
                          {region.photo_path.split('/').pop()}
                        </span>
                        <div className='flex items-center gap-2'>
                          {region.bbox ? (
                            <span className='text-gray-400 text-xs'>
                              Position: ({region.bbox!.x}, {region.bbox!.y})
                            </span>
                          ) : (
                            <span className='text-gray-400 text-xs'>
                              Full text
                            </span>
                          )}
                          <button
                            onClick={() =>
                              window.open(
                                api.getImageUrl(region.photo_path),
                                '_blank',
                                'noopener'
                              )
                            }
                            className='px-2 py-1 bg-white/10 text-gray-300 text-xs rounded hover:bg-white/20'
                          >
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
                  <p className='text-xs text-gray-500 mt-2'>
                    Only the first selected language is used for extraction.
                  </p>
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
                          Not available with the current OCR backend
                        </p>
                      </div>
                      <button
                        disabled
                        className={`w-12 h-6 ${
                          enableHandwriting ? 'bg-blue-600' : 'bg-gray-600'
                        } rounded-full relative opacity-50 cursor-not-allowed`}
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
                      <button
                        disabled
                        title='Not supported by the current OCR backend'
                        aria-label='Auto Language Detection (not supported by the current OCR backend)'
                        className='w-12 h-6 bg-blue-600 rounded-full relative opacity-50 cursor-not-allowed'
                      >
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
                        disabled
                        title='Not supported by the current OCR backend'
                        aria-label='Confidence threshold (not supported by the current OCR backend)'
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
                      Text extraction uses Tesseract OCR for printed text.
                      Handwriting recognition is not available in the current
                      backend. Processing time varies based on image complexity
                      and selected language.
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
              {!hasRegionGeometry && selectedRegions.length > 0 && (
                <p className='text-sm text-gray-400 mb-4'>
                  Region coordinates are not available in the current OCR backend.
                </p>
              )}

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
                        {hasRegionGeometry && (
                          <div className='absolute inset-0 pointer-events-none'>
                            {selectedRegions.map((region, index) =>
                              region.bbox ? (
                                <div
                                  key={region.id}
                                  className='absolute border-2 border-yellow-500 bg-yellow-500/10'
                                  style={{
                                    left: `${(region.bbox!.x / 1000) * 100}%`,
                                    top: `${(region.bbox!.y / 1000) * 100}%`,
                                    width: `${(region.bbox!.width / 1000) * 100}%`,
                                    height: `${(region.bbox!.height / 1000) * 100}%`,
                                  }}
                                >
                                  <span className='absolute -top-6 left-0 text-xs bg-yellow-500 text-black px-1 rounded'>
                                    {index + 1}
                                  </span>
                                </div>
                              ) : null
                            )}
                          </div>
                        )}
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
                              {region.bbox ? (
                                <>
                                  <span>
                                    Position: ({region.bbox!.x}, {region.bbox!.y})
                                  </span>
                                  <span>
                                    Size: {region.bbox!.width}×{region.bbox!.height}
                                  </span>
                                </>
                              ) : (
                                <span>Full text</span>
                              )}
                              <span className='capitalize'>
                                {region.text_type || 'text'}
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
                    <button
                      disabled
                      title='Not supported by the current OCR backend'
                      aria-label='GPU Acceleration (not supported by the current OCR backend)'
                      className='w-12 h-6 bg-blue-600 rounded-full relative opacity-50 cursor-not-allowed'
                    >
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
                    <button
                      disabled
                      title='Not supported by the current OCR backend'
                      aria-label='Parallel Processing (not supported by the current OCR backend)'
                      className='w-12 h-6 bg-blue-600 rounded-full relative opacity-50 cursor-not-allowed'
                    >
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
                    <button
                      disabled
                      title='Not supported by the current OCR backend'
                      aria-label='Auto-enhance Images (not supported by the current OCR backend)'
                      className='w-12 h-6 bg-blue-600 rounded-full relative opacity-50 cursor-not-allowed'
                    >
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
                    <label
                      htmlFor='ocr-threads'
                      className='block text-gray-300 text-sm mb-2'
                    >
                      Processing Threads
                    </label>
                    <select
                      id='ocr-threads'
                      disabled
                      title='Not supported by the current OCR backend'
                      className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500 opacity-50 cursor-not-allowed'
                    >
                      <option>Auto (Recommended)</option>
                      <option>1 Thread</option>
                      <option>2 Threads</option>
                      <option>4 Threads</option>
                      <option>8 Threads</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor='ocr-quality-threshold'
                      className='block text-gray-300 text-sm mb-2'
                    >
                      Image Quality Threshold
                    </label>
                    <input
                      id='ocr-quality-threshold'
                      type='range'
                      disabled
                      title='Not supported by the current OCR backend'
                      min='0'
                      max='100'
                      defaultValue='50'
                      className='w-full'
                    />
                  </div>

                  <div>
                    <label
                      htmlFor='ocr-cache-size'
                      className='block text-gray-300 text-sm mb-2'
                    >
                      Cache Size (MB)
                    </label>
                    <input
                      id='ocr-cache-size'
                      type='number'
                      disabled
                      title='Not supported by the current OCR backend'
                      defaultValue='512'
                      className='w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-500 opacity-50 cursor-not-allowed'
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className='pt-4 border-t border-white/10 space-y-2'>
              {clearOcrError && (
                <div
                  role='alert'
                  className='text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3'
                >
                  {clearOcrError}
                </div>
              )}
              <button
                disabled
                title='Not available yet'
                className='w-full px-4 py-2 bg-white/10 text-white rounded-lg flex items-center justify-center gap-2 opacity-50 cursor-not-allowed'
              >
                <Download className='w-4 h-4' />
                Export OCR Settings
              </button>
              <button
                onClick={handleClearOcrData}
                disabled={clearingOcr}
                className='w-full px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 flex items-center justify-center gap-2 disabled:opacity-50'
              >
                <Trash2 className='w-4 h-4' />
                {clearingOcr ? 'Clearing…' : 'Clear OCR Data'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(OCRTextSearchPanel);
