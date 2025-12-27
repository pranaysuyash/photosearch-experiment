/**
 * Image Analysis Component
 *
 * Provides intelligent analysis of photos including objects, scenes, and descriptions
 */

import { useState, useEffect, useCallback } from 'react';
import type { Photo } from '../../api';
import { api } from '../../api';
import { Copy, RotateCcw, Eye, ChevronDown } from 'lucide-react';

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
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Load image analysis when viewer opens
  const loadAnalysis = useCallback(async () => {
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
    } catch {
      // If the analysis isn't available yet, this is expected - don't show error
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }, [photo]);

  useEffect(() => {
    if (isOpen && photo) {
      void loadAnalysis();
    }
  }, [isOpen, photo, loadAnalysis]);

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
    <div className='mb-4 glass-surface rounded-xl overflow-hidden'>
      <div
        className='flex justify-between items-center p-4 cursor-pointer hover:bg-white/5 transition-colors'
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className='flex items-center gap-3'>
          <div className='glass-surface rounded-lg p-2'>
            <Eye size={16} className='text-primary/70' />
          </div>
          <div>
            <h4 className='font-semibold text-white/90 text-sm'>
              Image Insights
            </h4>
            <p className='text-xs text-white/50'>
              We looked over this photo and found the items and characteristics
              below.
            </p>
          </div>
        </div>
        <div className='flex items-center gap-2'>
          <button
            onClick={(e) => {
              e.stopPropagation();
              runAnalysis();
            }}
            disabled={loading}
            className='btn-glass btn-glass--muted text-xs px-3 py-2'
            title='Analyze image'
          >
            {loading ? (
              <span>Analyzing...</span>
            ) : (
              <>
                <RotateCcw size={12} />
                Detect
              </>
            )}
          </button>
          <div
            className='transition-transform duration-200'
            style={{
              transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)',
            }}
          >
            <ChevronDown size={16} className='text-white/50' />
          </div>
        </div>
      </div>

      {!isCollapsed && (
        <div className='px-4 pb-4 border-t border-white/5'>
          {error && (
            <div className='mt-3 p-3 glass-surface rounded-lg border border-red-500/20 bg-red-500/10'>
              <p className='text-red-400 text-xs'>{error}</p>
            </div>
          )}

          {loading && !analysis && (
            <div className='mt-3 p-3 glass-surface rounded-lg'>
              <p className='text-white/60 text-xs'>
                We're analyzing the image features…
              </p>
            </div>
          )}

          {!analysis && !loading && !error && (
            <div className='mt-3 p-3 glass-surface rounded-lg'>
              <p className='text-white/60 text-xs'>
                Click "Detect" to analyze this image and discover its contents.
              </p>
            </div>
          )}

          {analysis && !loading && (
            <div className='mt-3 space-y-3'>
              {analysis.caption && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Caption
                  </div>
                  <div className='text-sm text-white/90 flex items-start justify-between gap-2'>
                    <span className='leading-relaxed'>{analysis.caption}</span>
                    <button
                      onClick={() => copyToClipboard(analysis.caption || '')}
                      className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center flex-shrink-0'
                      title='Copy caption'
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                </div>
              )}

              {analysis.scene && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Scene
                  </div>
                  <div className='text-sm text-white/90'>{analysis.scene}</div>
                </div>
              )}

              {analysis.tags && analysis.tags.length > 0 && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Tags
                  </div>
                  <div className='flex flex-wrap gap-2'>
                    {analysis.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className='text-xs px-2 py-1 glass-surface rounded-full text-blue-200 border border-blue-500/20'
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {analysis.objects && analysis.objects.length > 0 && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Objects We Found
                  </div>
                  <div className='flex flex-wrap gap-2'>
                    {analysis.objects.map((obj, idx) => (
                      <span
                        key={idx}
                        className='text-xs px-2 py-1 glass-surface rounded-full text-green-200 border border-green-500/20'
                      >
                        {obj}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {analysis.colors && analysis.colors.length > 0 && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Colors
                  </div>
                  <div className='flex items-center gap-2 flex-wrap'>
                    {analysis.colors.map((color, idx) => {
                      // Convert color name to hex or use a default palette
                      const colorMap: Record<string, string> = {
                        red: '#EF4444',
                        blue: '#3B82F6',
                        green: '#10B981',
                        yellow: '#FBBF24',
                        purple: '#A855F7',
                        orange: '#F97316',
                        pink: '#EC4899',
                        white: '#F9FAFB',
                        black: '#111827',
                        gray: '#6B7280',
                        brown: '#92400E',
                      };
                      const hexColor =
                        colorMap[color.toLowerCase()] || '#6B7280';

                      return (
                        <div
                          key={idx}
                          className='flex items-center gap-2 glass-surface rounded-full px-2 py-1'
                        >
                          <div
                            className='w-3 h-3 rounded-full border border-white/20'
                            style={{ backgroundColor: hexColor }}
                            title={color}
                          />
                          <span className='text-xs text-white/80'>{color}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {analysis.quality !== undefined && (
                <div className='glass-surface rounded-lg p-3'>
                  <div className='text-xs text-white/50 mb-2 uppercase tracking-wider'>
                    Quality Score
                  </div>
                  <div className='flex items-center gap-3'>
                    <div className='flex-1 glass-surface rounded-full h-2 overflow-hidden'>
                      <div
                        className='bg-gradient-to-r from-primary/60 to-primary h-full rounded-full transition-all duration-300'
                        style={{ width: `${(analysis.quality / 5) * 100}%` }}
                      />
                    </div>
                    <span className='text-xs text-white/80 font-mono'>
                      {analysis.quality}/5
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ImageAnalysis;
