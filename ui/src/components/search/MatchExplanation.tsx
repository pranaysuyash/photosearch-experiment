import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { 
  HelpCircle, 
  Camera, 
  MapPin, 
  Calendar, 
  Brain, 
  Zap, 
  Target,
  FileText,
  Eye,
  Database,
  X
} from 'lucide-react';

interface MatchReason {
  category: string;
  matched: string;
  confidence: number;
  badge: string;
  type: 'metadata' | 'semantic' | 'hybrid';
}

interface MatchBreakdown {
  metadata_score?: number;
  semantic_score?: number;
  filename_score?: number;
  content_score?: number;
}

interface MatchExplanation {
  type: 'metadata' | 'semantic' | 'hybrid';
  reasons: MatchReason[];
  overallConfidence: number;
  breakdown?: MatchBreakdown;
}

interface MatchExplanationProps {
  explanation: MatchExplanation;
  isCompact?: boolean;
}

const getCategoryIcon = (category: string) => {
  const categoryLower = category.toLowerCase();
  
  if (categoryLower.includes('camera') || categoryLower.includes('lens')) {
    return Camera;
  }
  if (categoryLower.includes('location') || categoryLower.includes('gps')) {
    return MapPin;
  }
  if (categoryLower.includes('date') || categoryLower.includes('time')) {
    return Calendar;
  }
  if (categoryLower.includes('visual') || categoryLower.includes('ai')) {
    return Brain;
  }
  if (categoryLower.includes('technical') || categoryLower.includes('exif')) {
    return Zap;
  }
  
  return Target;
};



const getScoreIcon = (label: string) => {
  switch (label) {
    case 'File': return FileText;
    case 'Content': return Eye;
    case 'Metadata': return Database;
    case 'Visual': return Brain;
    default: return Target;
  }
};

const getTypeColor = (type: string) => {
  switch (type) {
    case 'metadata': return 'bg-blue-500';
    case 'semantic': return 'bg-purple-500';
    case 'hybrid': return 'bg-gradient-to-r from-blue-500 to-purple-500';
    default: return 'bg-gray-500';
  }
};

export const MatchExplanation = ({ 
  explanation, 
  isCompact = false 
}: MatchExplanationProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Close modal on escape key and manage body scroll
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsExpanded(false);
      }
    };

    if (isExpanded) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
      console.log('Modal opened, body scroll disabled');
    } else {
      document.body.style.overflow = 'unset';
      console.log('Modal closed, body scroll restored');
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isExpanded]);

  if (isCompact) {
    const displayBreakdown = explanation.breakdown || {
      filename_score: Math.round(explanation.overallConfidence * 80),
      metadata_score: Math.round(explanation.overallConfidence * 90),
      semantic_score: Math.round(explanation.overallConfidence * 85),
      content_score: Math.round(explanation.overallConfidence * 85)
    };

    // Get top 2 contributing factors
    const topScores = [
      { label: 'File', score: displayBreakdown.filename_score, icon: FileText },
      { label: 'Content', score: displayBreakdown.content_score, icon: Eye },
      { label: 'Meta', score: displayBreakdown.metadata_score, icon: Database },
      { label: 'Visual', score: displayBreakdown.semantic_score, icon: Brain },
    ]
      .filter(item => item.score !== undefined && item.score > 0)
      .sort((a, b) => b.score! - a.score!)
      .slice(0, 2);

    const overallScore = Math.round(explanation.overallConfidence * 100);

    return (
      <div className="absolute bottom-0 left-0 right-0 p-3">
        <button 
          className="w-full glass-surface glass-surface--strong rounded-xl p-2.5 shadow-2xl hover:bg-white/5 transition-colors cursor-pointer text-left"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Match explanation clicked! Opening modal...');
            setIsExpanded(true);
          }}
          type="button"
        >
          <div className="flex items-center gap-3">
            {/* Overall Match Score */}
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${getTypeColor(explanation.type)}`} />
              <span className="text-sm font-bold text-white tabular-nums">
                {overallScore}%
              </span>
            </div>
            
            {/* Top Contributing Factors */}
            <div className="flex items-center gap-2 flex-1">
              {topScores.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div key={idx} className="flex items-center gap-1 text-white/70">
                    <Icon size={11} />
                    <span className="text-[10px] font-medium">{item.label}</span>
                  </div>
                );
              })}
            </div>
            
            {/* Why Icon */}
            <div className="flex items-center gap-1 text-white/80">
              <HelpCircle size={12} />
            </div>
          </div>
        </button>
        
        {isExpanded && createPortal(
          <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4" style={{ pointerEvents: 'auto' }}>
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/70 backdrop-blur-sm"
              onClick={() => setIsExpanded(false)}
            />
            {/* Modal */}
            <div
              className="relative w-full max-w-lg glass-surface glass-surface--strong rounded-2xl shadow-2xl p-6 max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${getTypeColor(explanation.type)}`} />
                  <h3 className="text-lg font-bold text-white/95">Why this matched</h3>
                </div>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="btn-glass p-2 rounded-lg hover:bg-white/20"
                >
                  <X size={14} className="text-white/80" />
                </button>
              </div>
              
              {explanation.breakdown && (
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2">
                    {[
                      { label: 'File', score: explanation.breakdown.filename_score },
                      { label: 'Content', score: explanation.breakdown.content_score },
                      { label: 'Metadata', score: explanation.breakdown.metadata_score },
                      { label: 'Visual', score: explanation.breakdown.semantic_score },
                    ].filter(item => item.score !== undefined && item.score > 0).map((item, idx) => {
                      const Icon = getScoreIcon(item.label);
                      return (
                        <div key={idx} className="glass-surface rounded-lg px-3 py-1.5">
                          <div className="flex items-center gap-1.5">
                            <Icon size={14} className="text-white/70" />
                            <span className="font-medium text-white/80 text-sm">{item.label}</span>
                            <span className="font-bold text-white/95 bg-white/20 px-2 py-0.5 rounded backdrop-blur-sm text-sm">
                              {Math.round(item.score!)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              
              <div className="space-y-2">
                {explanation.reasons && explanation.reasons.length > 0 ? (
                  explanation.reasons.map((reason, idx) => {
                    const Icon = getCategoryIcon(reason.category);
                    return (
                      <div
                        key={idx}
                        className="glass-surface rounded-lg p-3"
                      >
                        <div className="flex items-start gap-2">
                          <div className="flex-shrink-0 p-1.5 glass-surface rounded">
                            <Icon size={14} className="text-white/80" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-sm font-bold text-white/95">
                                {reason.category}
                              </span>
                              <span className="text-xs px-1.5 py-0.5 rounded bg-white/20 backdrop-blur-sm font-semibold text-white/90">
                                {Math.round(reason.confidence * 100)}%
                              </span>
                            </div>
                            <p className="text-sm text-white/80 leading-relaxed">
                              {reason.matched}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="glass-surface rounded-lg p-3 text-center">
                    <p className="text-white/70 text-sm">No detailed explanation available</p>
                  </div>
                )}
              </div>
            </div>
          </div>,
          document.body
        )}
      </div>
    );
  }

  // Non-compact view not used in current design
  return null;
};