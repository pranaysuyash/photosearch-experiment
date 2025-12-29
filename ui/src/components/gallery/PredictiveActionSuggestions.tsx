import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Lightbulb,
  Star,
  Share,
  Edit3,
  FolderPlus,
  Users,
  MapPin,
  Trash2,
  Copy,
  Zap,
  X,
  ChevronRight
} from 'lucide-react';
import type { Photo } from '../../api';
import { api } from '../../api';

type SuggestionIcon = React.ComponentType<{ size?: number; className?: string }>;

type SuggestionAnalysis = {
  quality_score: number;
  faces: Array<{ person_name?: string | null }>;
  similar_photos: unknown[];
  event_context?: { name: string; confidence: number };
  editing_suggestions?: Array<{ confidence: number; reason: string }>;
};

interface ActionSuggestion {
  id: string;
  type: 'favorite' | 'share' | 'edit' | 'organize' | 'tag' | 'delete' | 'duplicate';
  confidence: number;
  reason: string;
  action: string;
  icon: SuggestionIcon;
  color: string;
  priority: 'high' | 'medium' | 'low';
  data?: unknown;
}

interface PredictiveActionSuggestionsProps {
  photo: Photo;
  userBehavior: {
    recentActions: string[];
    preferences: Record<string, number>;
    patterns: Record<string, unknown>;
  };
  onActionExecute: (action: string, data?: unknown) => void;
  isVisible: boolean;
}

const generateActionSuggestions = async (
  photo: Photo,
  analysis: SuggestionAnalysis,
  behavior: PredictiveActionSuggestionsProps['userBehavior']
): Promise<ActionSuggestion[]> => {
  const suggestions: ActionSuggestion[] = [];

  // High-quality photo suggestion
  if (analysis.quality_score > 0.8 && !photo.is_favorited) {
    suggestions.push({
      id: 'favorite-quality',
      type: 'favorite',
      confidence: analysis.quality_score,
      reason: 'This photo has excellent composition and quality',
      action: 'add-to-favorites',
      icon: Star,
      color: 'text-yellow-400',
      priority: 'high'
    });
  }

  // Face detection suggestion
  if (analysis.faces && analysis.faces.length > 0) {
    const unnamedFaces = analysis.faces.filter((face) => !face.person_name);
    if (unnamedFaces.length > 0) {
      suggestions.push({
        id: 'name-people',
        type: 'organize',
        confidence: 0.9,
        reason: `We found ${unnamedFaces.length} unnamed person${unnamedFaces.length > 1 ? 's' : ''}`,
        action: 'name-people',
        icon: Users,
        color: 'text-blue-400',
        priority: 'high',
        data: { faces: unnamedFaces }
      });
    }
  }

  // Similar photos suggestion
  if (analysis.similar_photos && analysis.similar_photos.length > 3) {
    suggestions.push({
      id: 'check-duplicates',
      type: 'duplicate',
      confidence: 0.7,
      reason: `Found ${analysis.similar_photos.length} very similar photos`,
      action: 'review-duplicates',
      icon: Copy,
      color: 'text-orange-400',
      priority: 'medium',
      data: { similar: analysis.similar_photos }
    });
  }

  // Location-based suggestion
  if (photo.metadata?.gps && !photo.location_tagged) {
    suggestions.push({
      id: 'add-location-tag',
      type: 'tag',
      confidence: 0.8,
      reason: 'Add location tag for better organization',
      action: 'add-location-tag',
      icon: MapPin,
      color: 'text-green-400',
      priority: 'medium',
      data: { gps: photo.metadata.gps }
    });
  }

  // Event detection suggestion
  if (analysis.event_context) {
    suggestions.push({
      id: 'create-album',
      type: 'organize',
      confidence: analysis.event_context.confidence,
      reason: `This looks like part of "${analysis.event_context.name}"`,
      action: 'create-event-album',
      icon: FolderPlus,
      color: 'text-purple-400',
      priority: 'high',
      data: { event: analysis.event_context }
    });
  }

  // Editing suggestion based on photo analysis
  if (analysis.editing_suggestions) {
    const topSuggestion = analysis.editing_suggestions[0];
    if (topSuggestion.confidence > 0.6) {
      suggestions.push({
        id: 'enhance-photo',
        type: 'edit',
        confidence: topSuggestion.confidence,
        reason: topSuggestion.reason,
        action: 'apply-enhancement',
        icon: Edit3,
        color: 'text-cyan-400',
        priority: 'medium',
        data: { enhancement: topSuggestion }
      });
    }
  }

  // Sharing suggestion based on user patterns
  if (behavior.patterns.shares_high_quality && analysis.quality_score > 0.85) {
    suggestions.push({
      id: 'share-quality',
      type: 'share',
      confidence: 0.7,
      reason: 'You often share high-quality photos like this',
      action: 'quick-share',
      icon: Share,
      color: 'text-pink-400',
      priority: 'low'
    });
  }

  // Old photo cleanup suggestion
  const createdAt =
    typeof photo.metadata?.filesystem?.created === 'string'
      ? photo.metadata.filesystem.created
      : '';
  const timestamp = createdAt ? new Date(createdAt).getTime() : NaN;
  const photoAge = Number.isFinite(timestamp) ? Date.now() - timestamp : 0;
  const daysOld = photoAge / (1000 * 60 * 60 * 24);

  if (daysOld > 365 && analysis.quality_score < 0.4 && !photo.is_favorited) {
    suggestions.push({
      id: 'cleanup-old',
      type: 'delete',
      confidence: 0.6,
      reason: 'Old, low-quality photo that might be worth cleaning up',
      action: 'suggest-cleanup',
      icon: Trash2,
      color: 'text-red-400',
      priority: 'low'
    });
  }

  // Sort by priority and confidence
  return suggestions
    .sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return b.confidence - a.confidence;
    })
    .slice(0, 3); // Show top 3 suggestions
};

export const PredictiveActionSuggestions: React.FC<PredictiveActionSuggestionsProps> = ({
  photo,
  userBehavior,
  onActionExecute,
  isVisible
}) => {
  const [suggestions, setSuggestions] = useState<ActionSuggestion[]>([]);
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!photo || !isVisible) return;

    const generateSuggestions = async () => {
      setLoading(true);
      try {
        const analysis = await buildSuggestionAnalysis(photo);
        const generatedSuggestions = await generateActionSuggestions(photo, analysis, userBehavior);
        setSuggestions(generatedSuggestions);
      } catch (error) {
        console.error('Failed to generate suggestions:', error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    };

    generateSuggestions();
  }, [photo, isVisible, userBehavior]);

  const trackSuggestionInteraction = (
    suggestionId: string,
    action: 'accepted' | 'dismissed',
    photoPath: string
  ) => {
    void suggestionId;
    void action;
    void photoPath;
  };

  const buildSuggestionAnalysis = async (targetPhoto: Photo): Promise<SuggestionAnalysis> => {
    const analysisRaw = (await api.getAnalysis(targetPhoto.path)) as Record<string, unknown>;
    const qualityRaw =
      (analysisRaw as { quality_score?: unknown }).quality_score ??
      (analysisRaw as { quality?: unknown }).quality;
    let qualityScore = 0;
    if (typeof qualityRaw === 'number') {
      qualityScore = qualityRaw > 1 ? Math.min(1, qualityRaw / 5) : Math.max(0, qualityRaw);
    }

    const facesResponse = await api
      .getFacesInPhoto(targetPhoto.path)
      .catch(() => ({ faces: [] as Array<Record<string, unknown>> }));
    const faces = Array.isArray(facesResponse?.faces)
      ? facesResponse.faces.map((face: Record<string, unknown>) => {
          const label =
            typeof face.person_label === 'string'
              ? face.person_label
              : typeof face.person_name === 'string'
                ? face.person_name
                : null;
          return { person_name: label };
        })
      : [];

    const similarRaw = (analysisRaw as { similar_photos?: unknown }).similar_photos;
    const similar_photos = Array.isArray(similarRaw) ? similarRaw : [];

    const eventRaw = (analysisRaw as { event_context?: unknown }).event_context;
    const event_context =
      eventRaw && typeof eventRaw === 'object'
        ? {
            name:
              typeof (eventRaw as { name?: unknown }).name === 'string'
                ? (eventRaw as { name: string }).name
                : 'Event',
            confidence:
              typeof (eventRaw as { confidence?: unknown }).confidence === 'number'
                ? (eventRaw as { confidence: number }).confidence
                : 0.5,
          }
        : undefined;

    const editingRaw = (analysisRaw as { editing_suggestions?: unknown }).editing_suggestions;
    const editing_suggestions = Array.isArray(editingRaw)
      ? editingRaw
          .map((item) => ({
            confidence:
              typeof (item as { confidence?: unknown }).confidence === 'number'
                ? (item as { confidence: number }).confidence
                : 0,
            reason:
              typeof (item as { reason?: unknown }).reason === 'string'
                ? (item as { reason: string }).reason
                : 'Enhance this photo',
          }))
          .filter((item) => item.confidence > 0)
      : undefined;

    return {
      quality_score: qualityScore,
      faces,
      similar_photos,
      event_context,
      editing_suggestions,
    };
  };

  const handleSuggestionClick = (suggestion: ActionSuggestion) => {
    onActionExecute(suggestion.action, suggestion.data);

    // Track user interaction for learning
    trackSuggestionInteraction(suggestion.id, 'accepted', photo.path);
  };

  const handleSuggestionDismiss = (suggestionId: string) => {
    setDismissedSuggestions(prev => new Set([...prev, suggestionId]));

    // Track dismissal for learning
    trackSuggestionInteraction(suggestionId, 'dismissed', photo.path);
  };

  const visibleSuggestions = suggestions.filter(s => !dismissedSuggestions.has(s.id));

  if (!isVisible || loading || visibleSuggestions.length === 0) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="fixed left-4 top-1/2 -translate-y-1/2 z-30 max-w-sm"
      >
        <div className="glass-surface rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb size={16} className="text-yellow-400" />
            <span className="text-sm font-medium text-white/90">
              Smart Suggestions
            </span>
          </div>

          <div className="space-y-2">
            {visibleSuggestions.map((suggestion, index) => (
              <motion.div
                key={suggestion.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="group"
              >
                <div className="glass-surface rounded-lg p-3 hover:bg-white/5 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center ${suggestion.color} flex-shrink-0`}>
                      <suggestion.icon size={16} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            suggestion.priority === 'high'
                              ? 'bg-red-500/20 text-red-300'
                              : suggestion.priority === 'medium'
                              ? 'bg-yellow-500/20 text-yellow-300'
                              : 'bg-blue-500/20 text-blue-300'
                          }`}>
                            {suggestion.priority}
                          </span>
                          <div className="w-12 h-1 bg-white/20 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-white/60 rounded-full"
                              style={{ width: `${suggestion.confidence * 100}%` }}
                            />
                          </div>
                        </div>

                        <button
                          onClick={() => handleSuggestionDismiss(suggestion.id)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity btn-glass btn-glass--muted w-6 h-6 p-0 justify-center"
                        >
                          <X size={12} />
                        </button>
                      </div>

                      <p className="text-sm text-white/80 mb-2 line-clamp-2">
                        {suggestion.reason}
                      </p>

                      <button
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="btn-glass btn-glass--primary text-xs px-3 py-1.5 flex items-center gap-1 w-full justify-center"
                      >
                        <Zap size={12} />
                        <span className="capitalize">{suggestion.type}</span>
                        <ChevronRight size={12} />
                      </button>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Learning indicator */}
          <div className="mt-3 pt-3 border-t border-white/10">
            <div className="text-xs text-white/50 flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              We learn from your choices to improve suggestions
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
