/**
 * Image Analysis Component
 *
 * Provides an intelligent analysis of photos including objects, scenes, and descriptions
 */

import { useState, useEffect } from 'react';
import type { Photo } from '../../api';
import { api } from '../../api';
import { Copy, RotateCcw } from 'lucide-react';

interface ImageAnalysis {
  caption?: string;
  tags?: string[];
  objects?: string[];
  scene?: string;
  colors?: string[];
  quality?: number;
  analysis_date?: string;
}

interface ImageAnalysisProps {
  photo: Photo;
  isOpen: boolean;
}

const ImageAnalysis: React.FC<ImageAnalysisProps> = ({ photo, isOpen }) => {
  const [analysis, setAnalysis] = useState<ImageAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load image analysis when viewer opens
  useEffect(() => {
    if (isOpen && photo) {
      loadAnalysis();
    }
  }, [isOpen, photo]);

  const loadAnalysis = async () => {
    if (!photo) return;

    setLoading(true);
    setError(null);

    try {
      // Try to get existing analysis for this photo
      const response = await api.getAnalysis(photo.path);
      if (response && Object.keys(response).length > 0) {
        setAnalysis(response);
      } else {
        // If no analysis exists yet, show a message prompting user to analyze
        setAnalysis(null);
      }
    } catch (err) {
      // If the analysis isn't available yet, this is expected - don't show error
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    if (!photo) return;

    setLoading(true);
    setError(null);

    try {
      // Run analysis on the photo
      const response = await api.analyzeImage(photo.path);

      // Update the analysis with the response
      setAnalysis(response);
    } catch (err) {
      setError("Couldn't analyze the image right now. Try again later.");
      console.error('Analysis error:', err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="mb-4 p-4 bg-gray-800/50 rounded-lg border border-gray-700">
      <div className="flex justify-between items-center mb-3">
        <h4 className="font-bold text-white/90 text-sm flex items-center gap-2">
          <span className="bg-gradient-to-r from-purple-500 to-blue-500 w-6 h-6 rounded flex items-center justify-center text-xs">
            🔍
          </span>
          Image Insights
        </h4>
        <div className="text-xs text-gray-400">The app looked over this photo and found the items and characteristics below.</div>
        <div className="flex gap-2">
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="text-xs px-2 py-1 bg-blue-600/30 hover:bg-blue-600/50 rounded text-blue-200 disabled:opacity-50 flex items-center gap-1"
          >
            {loading ? (
              <span>Detecting...</span>
            ) : (
              <>
                <RotateCcw size={12} />
                Detect
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-red-400 text-xs mb-2">{error}</div>
      )}

      {loading && !analysis && (
        <div className="text-gray-400 text-xs">Detecting features in the image…</div>
      )}

      {analysis && !loading && (
        <div className="space-y-3">
          {analysis.caption && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Caption</div>
              <div className="text-sm text-white/90 flex items-start justify-between gap-2">
                <span>{analysis.caption}</span>
                <button
                  onClick={() => copyToClipboard(analysis.caption || '')}
                  className="text-gray-400 hover:text-white/80 ml-2 flex-shrink-0"
                  title="Copy caption"
                >
                  <Copy size={12} />
                </button>
              </div>
            </div>
          )}

          {analysis.scene && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Scene</div>
              <div className="text-sm text-white/90">{analysis.scene}</div>
            </div>
          )}

          {analysis.tags && analysis.tags.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Tags</div>
              <div className="flex flex-wrap gap-1">
                {analysis.tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 bg-blue-600/20 rounded-full text-blue-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.objects && analysis.objects.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Objects Detected</div>
              <div className="flex flex-wrap gap-1">
                {analysis.objects.map((obj, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2 py-1 bg-green-600/20 rounded-full text-green-200"
                  >
                    {obj}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.colors && analysis.colors.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Colors</div>
              <div className="flex items-center gap-1 flex-wrap">
                {analysis.colors.map((color, idx) => {
                  // Convert color name to hex or use a default palette
                  const colorMap: Record<string, string> = {
                    'red': '#EF4444',
                    'blue': '#3B82F6',
                    'green': '#10B981',
                    'yellow': '#FBBF24',
                    'purple': '#A855F7',
                    'orange': '#F97316',
                    'pink': '#EC4899',
                    'white': '#F9FAFB',
                    'black': '#111827',
                    'gray': '#6B7280',
                    'brown': '#92400E',
                  };
                  const hexColor = colorMap[color.toLowerCase()] || '#6B7280';

                  return (
                    <div key={idx} className="flex items-center gap-1">
                      <div
                        className="w-4 h-4 rounded border border-white/20"
                        style={{ backgroundColor: hexColor }}
                        title={color}
                      />
                      <span className="text-xs text-white/80">{color}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {analysis.quality !== undefined && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Quality Score</div>
              <div className="flex items-center gap-2">
                <div className="w-full bg-gray-700 rounded-full h-1.5">
                  <div
                    className="bg-green-500 h-1.5 rounded-full"
                    style={{ width: `${(analysis.quality / 5) * 100}%` }}
                  ></div>
                </div>
                <span className="text-xs text-white/80">{analysis.quality}/5</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageAnalysis;
