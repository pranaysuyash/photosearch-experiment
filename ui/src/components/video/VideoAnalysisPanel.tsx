/**
 * Video Analysis Panel
 *
 * Comprehensive video content analysis interface with:
 * - Video processing and keyframe extraction
 * - Scene detection and navigation
 * - OCR text search within videos
 * - Video thumbnail generation
 * - Batch video processing
 */

import React, { useState, useEffect, useCallback, memo } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Video,
  Image as ImageIcon,
  FileText,
  Target,
  BarChart3,
  X,
  AlertCircle,
  Loader2,
  Sparkles,
  RefreshCw,
  Film,
  Scissors,
  Type,
  Grid3X3,
  Eye,
  Trash2,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../design/glass';

interface VideoMetadata {
  duration: number;
  fps: number;
  width: number;
  height: number;
  codec: string;
  bitrate: number;
  file_size: number;
}

interface VideoKeyframe {
  id: number;
  frame_number: number;
  timestamp: number;
  frame_path: string;
  scene_id: number;
  is_scene_boundary: boolean;
  visual_hash: string;
}

interface VideoScene {
  id: number;
  scene_number: number;
  start_timestamp: number;
  end_timestamp: number;
  duration: number;
  keyframe_count: number;
  scene_description?: string;
}

interface VideoOCRResult {
  id: number;
  frame_number: number;
  timestamp: number;
  detected_text: string;
  confidence: number;
  language: string;
}

interface VideoAnalysisResult {
  video_path: string;
  metadata: VideoMetadata;
  keyframes: VideoKeyframe[];
  scenes: VideoScene[];
  ocr_results: VideoOCRResult[];
  summary: {
    keyframes_count: number;
    scenes_count: number;
    text_detections: number;
    duration: number;
  };
}

interface VideoAnalysisPanelProps {
  onClose?: () => void;
}

export const VideoAnalysisPanel: React.FC<VideoAnalysisPanelProps> = memo(({ onClose }) => {
  
  // State management
  const [selectedVideoPath, setSelectedVideoPath] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<VideoAnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedScene, setSelectedScene] = useState<number | null>(null);
  const [selectedKeyframe, setSelectedKeyframe] = useState<VideoKeyframe | null>(null);
  const [showOCRResults, setShowOCRResults] = useState(false);
  const [minConfidence, setMinConfidence] = useState(0.5);
  const [videoStats, setVideoStats] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'analyze' | 'search' | 'stats'>('analyze');

  // Load video statistics on mount
  useEffect(() => {
    loadVideoStats();
  }, []);

  const loadVideoStats = useCallback(async () => {
    try {
      const response = await api.get('/video/stats');
      setVideoStats(response.data.stats);
    } catch (error) {
      console.error('Failed to load video stats:', error);
    }
  }, []);

  const analyzeVideo = useCallback(async (videoPath: string, forceReprocess = false) => {
    if (!videoPath.trim()) {
      setError('Please enter a video path');
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    
    try {
      // Start analysis
      await api.post('/video/analyze', {
        video_path: videoPath,
        force_reprocess: forceReprocess
      });

      // Poll for results (in a real app, you might use WebSockets)
      let attempts = 0;
      const maxAttempts = 30; // 30 seconds timeout
      
      const pollResults = async (): Promise<void> => {
        try {
          const response = await api.get(`/video/analysis/${encodeURIComponent(videoPath)}`);
          setAnalysisResult(response.data);
          setIsAnalyzing(false);
          await loadVideoStats(); // Refresh stats
        } catch (error: any) {
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(pollResults, 1000); // Poll every second
          } else {
            setError('Analysis timeout - please check the video file and try again');
            setIsAnalyzing(false);
          }
        }
      };

      // Start polling after a short delay
      setTimeout(pollResults, 2000);
      
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to start video analysis');
      setIsAnalyzing(false);
    }
  }, [loadVideoStats]);

  const searchVideoContent = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await api.post('/video/search', {
        query: query,
        limit: 50,
        offset: 0
      });
      setSearchResults(response.data.results);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to search video content');
    }
  }, []);

  const loadVideoAnalysis = useCallback(async (videoPath: string) => {
    try {
      const response = await api.get(`/video/analysis/${encodeURIComponent(videoPath)}`);
      setAnalysisResult(response.data);
      setSelectedVideoPath(videoPath);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to load video analysis');
    }
  }, []);

  const deleteVideoAnalysis = useCallback(async (videoPath: string) => {
    if (!confirm('Are you sure you want to delete the analysis data for this video?')) {
      return;
    }

    try {
      await api.delete(`/video/analysis/${encodeURIComponent(videoPath)}`);
      if (analysisResult?.video_path === videoPath) {
        setAnalysisResult(null);
      }
      await loadVideoStats();
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to delete video analysis');
    }
  }, [analysisResult, loadVideoStats]);

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const renderAnalysisTab = () => (
    <div className="space-y-6">
      {/* Video Input */}
      <div className={`${glass.surface} p-6 rounded-lg`}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Video className="w-5 h-5" />
          Video Analysis
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Video Path</label>
            <input
              type="text"
              value={selectedVideoPath}
              onChange={(e) => setSelectedVideoPath(e.target.value)}
              placeholder="/path/to/video.mp4"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isAnalyzing}
            />
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={() => analyzeVideo(selectedVideoPath, false)}
              disabled={isAnalyzing || !selectedVideoPath.trim()}
              className={`${glass.buttonPrimary} flex items-center gap-2 px-4 py-2 rounded-md`}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Analyze Video
                </>
              )}
            </button>
            
            <button
              onClick={() => analyzeVideo(selectedVideoPath, true)}
              disabled={isAnalyzing || !selectedVideoPath.trim()}
              className={`${glass.button} flex items-center gap-2 px-4 py-2 rounded-md`}
            >
              <RefreshCw className="w-4 h-4" />
              Force Reprocess
            </button>
          </div>
        </div>
      </div>

      {/* Analysis Results */}
      {analysisResult && (
        <div className="space-y-6">
          {/* Video Metadata */}
          <div className={`${glass.surface} p-6 rounded-lg`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Video Information
              </h3>
              <button
                onClick={() => deleteVideoAnalysis(analysisResult.video_path)}
                className={`${glass.buttonDanger} text-sm flex items-center gap-2 px-3 py-1 rounded-md`}
              >
                <Trash2 className="w-4 h-4" />
                Delete Analysis
              </button>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="text-sm text-gray-400">Duration</div>
                <div className="text-lg font-semibold">
                  {formatDuration(analysisResult.metadata.duration)}
                </div>
              </div>
              
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="text-sm text-gray-400">Resolution</div>
                <div className="text-lg font-semibold">
                  {analysisResult.metadata.width}×{analysisResult.metadata.height}
                </div>
              </div>
              
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="text-sm text-gray-400">Frame Rate</div>
                <div className="text-lg font-semibold">
                  {analysisResult.metadata.fps.toFixed(1)} fps
                </div>
              </div>
              
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="text-sm text-gray-400">File Size</div>
                <div className="text-lg font-semibold">
                  {formatFileSize(analysisResult.metadata.file_size)}
                </div>
              </div>
            </div>
          </div>

          {/* Analysis Summary */}
          <div className={`${glass.surface} p-6 rounded-lg`}>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5" />
              Analysis Summary
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="flex items-center gap-3">
                  <Grid3X3 className="w-8 h-8 text-blue-400" />
                  <div>
                    <div className="text-2xl font-bold">{analysisResult.summary.keyframes_count}</div>
                    <div className="text-sm text-gray-400">Keyframes Extracted</div>
                  </div>
                </div>
              </div>
              
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="flex items-center gap-3">
                  <Scissors className="w-8 h-8 text-green-400" />
                  <div>
                    <div className="text-2xl font-bold">{analysisResult.summary.scenes_count}</div>
                    <div className="text-sm text-gray-400">Scenes Detected</div>
                  </div>
                </div>
              </div>
              
              <div className={`${glass.card} p-4 rounded-md`}>
                <div className="flex items-center gap-3">
                  <Type className="w-8 h-8 text-purple-400" />
                  <div>
                    <div className="text-2xl font-bold">{analysisResult.summary.text_detections}</div>
                    <div className="text-sm text-gray-400">Text Detections</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Scenes */}
          {analysisResult.scenes.length > 0 && (
            <div className={`${glass.surface} p-6 rounded-lg`}>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Film className="w-5 h-5" />
                Detected Scenes
              </h3>
              
              <div className="space-y-2">
                {analysisResult.scenes.map((scene) => (
                  <div
                    key={scene.id}
                    className={`${glass.card} p-4 rounded-md cursor-pointer transition-all ${
                      selectedScene === scene.scene_number ? 'ring-2 ring-blue-400' : ''
                    }`}
                    onClick={() => setSelectedScene(
                      selectedScene === scene.scene_number ? null : scene.scene_number
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Scene {scene.scene_number + 1}</div>
                        <div className="text-sm text-gray-400">
                          {formatDuration(scene.start_timestamp)} - {formatDuration(scene.end_timestamp)}
                          {' '}({formatDuration(scene.duration)})
                        </div>
                      </div>
                      <div className="text-sm text-gray-400">
                        {scene.keyframe_count} keyframes
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Keyframes */}
          {analysisResult.keyframes.length > 0 && (
            <div className={`${glass.surface} p-6 rounded-lg`}>
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <ImageIcon className="w-5 h-5" />
                Keyframes
                {selectedScene !== null && (
                  <span className="text-sm text-gray-400 ml-2">
                    (Scene {selectedScene + 1})
                  </span>
                )}
              </h3>
              
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {analysisResult.keyframes
                  .filter(kf => selectedScene === null || kf.scene_id === selectedScene)
                  .map((keyframe) => (
                    <div
                      key={keyframe.id}
                      className={`${glass.card} p-2 rounded-md cursor-pointer transition-all ${
                        selectedKeyframe?.id === keyframe.id ? 'ring-2 ring-blue-400' : ''
                      }`}
                      onClick={() => setSelectedKeyframe(keyframe)}
                    >
                      <div className="aspect-video bg-gray-800 rounded mb-2 flex items-center justify-center">
                        <ImageIcon className="w-8 h-8 text-gray-600" />
                      </div>
                      <div className="text-xs text-center">
                        <div className="font-medium">{formatDuration(keyframe.timestamp)}</div>
                        <div className="text-gray-400">Frame {keyframe.frame_number}</div>
                        {keyframe.is_scene_boundary && (
                          <div className="text-yellow-400 text-xs mt-1">Scene Boundary</div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* OCR Results */}
          {analysisResult.ocr_results.length > 0 && (
            <div className={`${glass.surface} p-6 rounded-lg`}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Text Detections
                </h3>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Min Confidence:</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={minConfidence}
                      onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                      className="w-20"
                    />
                    <span className="text-sm w-8">{minConfidence.toFixed(1)}</span>
                  </div>
                  <button
                    onClick={() => setShowOCRResults(!showOCRResults)}
                    className={`${glass.button} flex items-center gap-2 px-3 py-1 rounded-md`}
                  >
                    {showOCRResults ? <Eye className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    {showOCRResults ? 'Hide' : 'Show'} Details
                  </button>
                </div>
              </div>
              
              {showOCRResults && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {analysisResult.ocr_results
                    .filter(ocr => ocr.confidence >= minConfidence)
                    .map((ocr) => (
                      <div key={ocr.id} className={`${glass.card} p-3 rounded-md`}>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="font-medium">{ocr.detected_text}</div>
                            <div className="text-sm text-gray-400">
                              {formatDuration(ocr.timestamp)} • Confidence: {(ocr.confidence * 100).toFixed(1)}%
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 ml-4">
                            {ocr.language}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderSearchTab = () => (
    <div className="space-y-6">
      {/* Search Input */}
      <div className={`${glass.surface} p-6 rounded-lg`}>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Search className="w-5 h-5" />
          Search Video Content
        </h3>
        
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for text in videos..."
            className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && searchVideoContent(searchQuery)}
          />
          <button
            onClick={() => searchVideoContent(searchQuery)}
            className={`${glass.buttonPrimary} flex items-center gap-2 px-4 py-2 rounded-md`}
          >
            <Search className="w-4 h-4" />
            Search
          </button>
        </div>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className={`${glass.surface} p-6 rounded-lg`}>
          <h3 className="text-lg font-semibold mb-4">
            Search Results ({searchResults.length})
          </h3>
          
          <div className="space-y-3">
            {searchResults.map((result, index) => (
              <div key={index} className={`${glass.card} p-4 rounded-md`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-blue-400 cursor-pointer hover:text-blue-300"
                         onClick={() => loadVideoAnalysis(result.video_path)}>
                      {result.video_path.split('/').pop()}
                    </div>
                    <div className="text-sm text-gray-300 mt-1">
                      "{result.matched_text}"
                    </div>
                    <div className="text-xs text-gray-400 mt-2">
                      At {formatDuration(result.timestamp)} • 
                      Confidence: {(result.confidence * 100).toFixed(1)}% • 
                      {result.resolution}
                    </div>
                  </div>
                  <div className="ml-4">
                    <button
                      onClick={() => loadVideoAnalysis(result.video_path)}
                      className={`${glass.button} text-sm flex items-center gap-2 px-3 py-1 rounded-md`}
                    >
                      <Eye className="w-4 h-4" />
                      View
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderStatsTab = () => (
    <div className="space-y-6">
      {videoStats && (
        <div className={`${glass.surface} p-6 rounded-lg`}>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Video Analysis Statistics
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="flex items-center gap-3">
                <Video className="w-8 h-8 text-blue-400" />
                <div>
                  <div className="text-2xl font-bold">{videoStats.total_videos}</div>
                  <div className="text-sm text-gray-400">Videos Processed</div>
                </div>
              </div>
            </div>
            
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="flex items-center gap-3">
                <ImageIcon className="w-8 h-8 text-green-400" />
                <div>
                  <div className="text-2xl font-bold">{videoStats.total_keyframes}</div>
                  <div className="text-sm text-gray-400">Keyframes Extracted</div>
                </div>
              </div>
            </div>
            
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="flex items-center gap-3">
                <Scissors className="w-8 h-8 text-purple-400" />
                <div>
                  <div className="text-2xl font-bold">{videoStats.total_scenes}</div>
                  <div className="text-sm text-gray-400">Scenes Detected</div>
                </div>
              </div>
            </div>
            
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="flex items-center gap-3">
                <FileText className="w-8 h-8 text-yellow-400" />
                <div>
                  <div className="text-2xl font-bold">{videoStats.total_ocr_detections}</div>
                  <div className="text-sm text-gray-400">Text Detections</div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="text-sm text-gray-400">Total Duration Processed</div>
              <div className="text-xl font-semibold">{videoStats.total_duration_hours}h</div>
            </div>
            
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="text-sm text-gray-400">Avg Keyframes/Video</div>
              <div className="text-xl font-semibold">{videoStats.average_keyframes_per_video}</div>
            </div>
            
            <div className={`${glass.card} p-4 rounded-md`}>
              <div className="text-sm text-gray-400">Avg Scenes/Video</div>
              <div className="text-xl font-semibold">{videoStats.average_scenes_per_video}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className={`${glass.surface} w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col rounded-lg`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Video className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold">Video Content Analysis</h2>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Tab Navigation */}
            <div className="flex bg-white/5 rounded-lg p-1">
              <button
                onClick={() => setActiveTab('analyze')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'analyze'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Analyze
              </button>
              <button
                onClick={() => setActiveTab('search')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'search'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Search
              </button>
              <button
                onClick={() => setActiveTab('stats')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === 'stats'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Statistics
              </button>
            </div>
            
            {onClose && (
              <button
                onClick={onClose}
                className={`${glass.button} p-2 rounded-md`}
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {activeTab === 'analyze' && renderAnalysisTab()}
          {activeTab === 'search' && renderSearchTab()}
          {activeTab === 'stats' && renderStatsTab()}
        </div>
      </motion.div>
    </div>
  );
});

VideoAnalysisPanel.displayName = 'VideoAnalysisPanel';

export default VideoAnalysisPanel;