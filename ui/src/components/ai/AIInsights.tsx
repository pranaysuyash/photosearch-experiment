/**
 * Insights Component
 *
 * Displays generated insights and recommendations for photos.
 */
import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Lightbulb,
  Trophy,
  Tag,
  Eye,
  ThumbsUp,
  ChartBar,
  Wrench,
  X,
  Check,
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface PhotoInsight {
  id: string;
  photo_path: string;
  insight_type: string;
  insight_data: any;
  confidence: number;
  generated_at: string;
  is_applied: boolean;
}

interface PhotographerPatterns {
  photo_paths_count: number;
  common_subjects: string[];
  preferred_times: string[];
  composition_tendencies: string[];
  suggested_improvements: string[];
}

export function AIInsights({ photoPath }: { photoPath?: string }) {
  const [insights, setInsights] = useState<PhotoInsight[]>([]);
  const [patterns, setPatterns] = useState<PhotographerPatterns | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    'insights' | 'patterns' | 'recommendations'
  >('insights');
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);

  // Load insights for the specific photo
  useEffect(() => {
    loadInsights();
  }, [photoPath]);

  const loadInsights = async () => {
    if (!photoPath) return;

    try {
      setLoading(true);
      setError(null);

      const response = await api.get(
        `/ai/insights/photo/${encodeURIComponent(photoPath)}`
      );
      setInsights(response.insights || []);
    } catch (err) {
      console.error('Failed to load insights:', err);
      setError('Failed to load photo insights');
    } finally {
      setLoading(false);
    }
  };

  const loadPatterns = async () => {
    try {
      setLoading(true);
      setError(null);

      // In a real implementation, we would analyze multiple photos
      // For demonstration, we'll use a mock implementation
      const mockPatterns: PhotographerPatterns = {
        photo_paths_count: selectedPaths.length || 100,
        common_subjects: ['Landscapes', 'Portraits', 'Architecture'],
        preferred_times: ['Morning (8-10 AM)', 'Evening (6-8 PM)'],
        composition_tendencies: ['Rule of Thirds', 'Leading Lines'],
        suggested_improvements: [
          'Try shooting during golden hour for better lighting',
          'Experiment with different angles for portraits',
          'Explore macro photography for small details',
        ],
      };

      setPatterns(mockPatterns);
    } catch (err) {
      console.error('Failed to load patterns:', err);
      setError('Failed to analyze photographer patterns');
    } finally {
      setLoading(false);
    }
  };

  const toggleInsightApplied = async (insightId: string, applied: boolean) => {
    try {
      await api.put(`/ai/insights/${insightId}`, {
        is_applied: applied,
      });

      // Update local state
      setInsights(
        insights.map((insight) =>
          insight.id === insightId
            ? { ...insight, is_applied: applied }
            : insight
        )
      );
    } catch (err) {
      console.error('Failed to update insight status:', err);
      setError('Failed to update insight status');
    }
  };

  const getInsightIcon = (type: string) => {
    const icons: Record<string, any> = {
      best_shot: Trophy,
      tag_suggestion: Tag,
      pattern: ChartBar,
      organization: Wrench,
    };

    const Icon = icons[type] || Lightbulb;
    return <Icon size={16} />;
  };

  const getInsightDescription = (insight: PhotoInsight) => {
    switch (insight.insight_type) {
      case 'best_shot':
        return 'This photo captures excellent composition and timing';
      case 'tag_suggestion':
        return `Suggested tag: ${insight.insight_data.suggested_tag || 'N/A'}`;
      case 'pattern':
        return `Pattern detected: ${
          insight.insight_data.pattern_type || 'N/A'
        }`;
      case 'organization':
        return `Suggestion: ${insight.insight_data.reason || 'N/A'}`;
      default:
        return insight.insight_data.description || 'Generated insight';
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className='flex items-center justify-center h-32'>
          <div className='w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin' />
        </div>
      </div>
    );
  }

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-semibold text-foreground flex items-center gap-2'>
          <Sparkles className='text-primary' size={24} />
          Insights
        </h2>

        <div className='flex items-center gap-2'>
          <button
            onClick={loadInsights}
            className='btn-glass btn-glass--muted text-xs px-3 py-1.5 flex items-center gap-1'
          >
            <Lightbulb size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className='flex border-b border-white/10'>
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            activeTab === 'insights'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('insights')}
        >
          <div className='flex items-center gap-2'>
            <Lightbulb size={16} />
            Photo Insights
          </div>
        </button>
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            activeTab === 'patterns'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('patterns')}
        >
          <div className='flex items-center gap-2'>
            <ChartBar size={16} />
            Patterns
          </div>
        </button>
        <button
          className={`pb-2 px-4 text-sm font-medium ${
            activeTab === 'recommendations'
              ? 'text-foreground border-b-2 border-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('recommendations')}
        >
          <div className='flex items-center gap-2'>
            <Wrench size={16} />
            Recommendations
          </div>
        </button>
      </div>

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div className='space-y-4'>
          {insights.length === 0 ? (
            <div
              className={`${glass.surface} rounded-xl border border-white/10 p-8 text-center`}
            >
              <Lightbulb
                size={48}
                className='mx-auto text-muted-foreground mb-4 opacity-50'
              />
              <h3 className='font-medium text-foreground mb-2'>
                No Insights Yet
              </h3>
              <p className='text-sm text-muted-foreground max-w-md mx-auto'>
                We’ll analyze your photo and provide helpful insights and
                recommendations shortly.
              </p>
            </div>
          ) : (
            <div className='space-y-3'>
              {insights.map((insight) => (
                <div
                  key={insight.id}
                  className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
                >
                  <div className='flex items-start justify-between'>
                    <div className='flex items-start gap-3 flex-1'>
                      <div
                        className={`p-2 rounded-lg ${
                          insight.insight_type === 'best_shot'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : insight.insight_type === 'tag_suggestion'
                            ? 'bg-blue-500/20 text-blue-400'
                            : insight.insight_type === 'pattern'
                            ? 'bg-green-500/20 text-green-400'
                            : insight.insight_type === 'organization'
                            ? 'bg-purple-500/20 text-purple-400'
                            : 'bg-white/10 text-foreground'
                        }`}
                      >
                        {getInsightIcon(insight.insight_type)}
                      </div>
                      <div className='flex-1'>
                        <div className='flex items-center gap-2 mb-1'>
                          <h4 className='font-medium text-foreground capitalize'>
                            {insight.insight_type.replace('_', ' ')}
                          </h4>
                          <span className='text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary'>
                            {Math.round(insight.confidence * 100)}% confidence
                          </span>
                        </div>
                        <p className='text-sm text-muted-foreground'>
                          {getInsightDescription(insight)}
                        </p>
                      </div>
                    </div>
                    <div className='flex items-center gap-2'>
                      <button
                        onClick={() =>
                          toggleInsightApplied(insight.id, !insight.is_applied)
                        }
                        className={`btn-glass ${
                          insight.is_applied
                            ? 'btn-glass--primary'
                            : 'btn-glass--muted'
                        } p-1.5`}
                        title={
                          insight.is_applied
                            ? 'Mark as not applied'
                            : 'Mark as applied'
                        }
                      >
                        {insight.is_applied ? (
                          <Check size={14} />
                        ) : (
                          <ThumbsUp size={14} />
                        )}
                      </button>
                      <button
                        onClick={() => {}}
                        className='btn-glass btn-glass--muted p-1.5'
                        title='More options'
                      >
                        <Eye size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Patterns Tab */}
      {activeTab === 'patterns' && (
        <div className='space-y-4'>
          {patterns ? (
            <div className='space-y-6'>
              <div
                className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
              >
                <h3 className='font-medium text-foreground mb-3 flex items-center gap-2'>
                  <ChartBar size={16} />
                  Shooting Patterns
                </h3>
                <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
                  <div>
                    <h4 className='text-sm font-medium text-foreground mb-2'>
                      Common Subjects
                    </h4>
                    <div className='flex flex-wrap gap-2'>
                      {patterns.common_subjects.map((subject, idx) => (
                        <span
                          key={idx}
                          className='px-2 py-1 rounded-full bg-primary/10 text-primary text-xs'
                        >
                          {subject}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className='text-sm font-medium text-foreground mb-2'>
                      Preferred Times
                    </h4>
                    <div className='flex flex-wrap gap-2'>
                      {patterns.preferred_times.map((time, idx) => (
                        <span
                          key={idx}
                          className='px-2 py-1 rounded-full bg-green-500/10 text-green-400 text-xs'
                        >
                          {time}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div
                className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
              >
                <h3 className='font-medium text-foreground mb-3 flex items-center gap-2'>
                  <Wrench size={16} />
                  Recommended Improvements
                </h3>
                <ul className='space-y-2'>
                  {patterns.suggested_improvements.map((suggestion, idx) => (
                    <li key={idx} className='flex items-start gap-2'>
                      <div className='w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5'>
                        <Lightbulb size={10} className='text-primary' />
                      </div>
                      <span className='text-sm text-foreground'>
                        {suggestion}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div
              className={`${glass.surface} rounded-xl border border-white/10 p-8 text-center`}
            >
              <ChartBar
                size={48}
                className='mx-auto text-muted-foreground mb-4 opacity-50'
              />
              <h3 className='font-medium text-foreground mb-2'>
                Analyze Your Patterns
              </h3>
              <p className='text-sm text-muted-foreground mb-4 max-w-md mx-auto'>
                Select photos to analyze your photography patterns and receive
                personalized recommendations.
              </p>
              <button
                onClick={loadPatterns}
                className='btn-glass btn-glass--primary px-4 py-2'
              >
                Analyze Patterns
              </button>
            </div>
          )}
        </div>
      )}

      {/* Recommendations Tab */}
      {activeTab === 'recommendations' && (
        <div className='space-y-4'>
          <div
            className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4`}
          >
            <h3 className='font-medium text-foreground mb-3 flex items-center gap-2'>
              <Wrench size={16} />
              Personalized Recommendations
            </h3>

            <div className='space-y-4'>
              <div className='p-4 rounded-lg bg-gradient-to-r from-primary/10 to-purple-500/10'>
                <h4 className='font-medium text-foreground mb-1'>
                  Best Shot Identification
                </h4>
                <p className='text-sm text-muted-foreground mb-2'>
                  We found high-quality shots based on composition, lighting,
                  and technical quality.
                </p>
                <div className='flex gap-2'>
                  <button className='btn-glass btn-glass--primary text-xs px-3 py-1.5'>
                    View Best Shots
                  </button>
                  <button className='btn-glass btn-glass--muted text-xs px-3 py-1.5'>
                    Settings
                  </button>
                </div>
              </div>

              <div className='p-4 rounded-lg bg-gradient-to-r from-green-500/10 to-emerald-500/10'>
                <h4 className='font-medium text-foreground mb-1'>
                  Smart Tagging
                </h4>
                <p className='text-sm text-muted-foreground mb-2'>
                  Automatically tag your photos with relevant labels to improve
                  searchability.
                </p>
                <div className='flex gap-2'>
                  <button className='btn-glass btn-glass--primary text-xs px-3 py-1.5'>
                    Apply Suggestions
                  </button>
                  <button className='btn-glass btn-glass--muted text-xs px-3 py-1.5'>
                    Review Tags
                  </button>
                </div>
              </div>

              <div className='p-4 rounded-lg bg-gradient-to-r from-blue-500/10 to-cyan-500/10'>
                <h4 className='font-medium text-foreground mb-1'>
                  Organization Tips
                </h4>
                <p className='text-sm text-muted-foreground mb-2'>
                  Recommendations for organizing your photo library based on our
                  analysis.
                </p>
                <button className='btn-glass btn-glass--primary text-xs px-3 py-1.5'>
                  View Organization Plan
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className='text-sm text-destructive bg-destructive/10 rounded-lg p-3'>
          {error}
          <button className='ml-2' onClick={() => setError(null)}>
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
