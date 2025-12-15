import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  HelpCircle, 
  Camera, 
  MapPin, 
  Calendar, 
  Brain, 
  Zap, 
  Target,
  ChevronDown,
  ChevronUp
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

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
  if (confidence >= 0.6) return 'text-blue-600 bg-blue-50 border-blue-200';
  if (confidence >= 0.4) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-gray-600 bg-gray-50 border-gray-200';
};

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-green-700 bg-green-100';
  if (score >= 60) return 'text-blue-700 bg-blue-100';
  if (score >= 40) return 'text-yellow-700 bg-yellow-100';
  return 'text-red-700 bg-red-100';
};

const ScoreBreakdown = ({ breakdown }: { breakdown: MatchBreakdown }) => {
  const scores = [
    { label: 'File', score: breakdown.filename_score, icon: '📄' },
    { label: 'Content', score: breakdown.content_score, icon: '🤖' },
    { label: 'Metadata', score: breakdown.metadata_score, icon: '📊' },
    { label: 'Semantic', score: breakdown.semantic_score, icon: '🧠' },
  ].filter(item => item.score !== undefined && item.score > 0);

  if (scores.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {scores.map((item, idx) => (
        <div
          key={idx}
          className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(item.score!)}`}
        >
          <span>{item.icon}</span>
          <span>{item.label}: {Math.round(item.score!)}%</span>
        </div>
      ))}
    </div>
  );
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

  if (isCompact) {
    return (
      <div className="relative">
        <div className="bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md border border-gray-200">
          {/* Score Breakdown */}
          {explanation.breakdown && (
            <ScoreBreakdown breakdown={explanation.breakdown} />
          )}
          
          {/* Main Match Info */}
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${getTypeColor(explanation.type)}`} />
            <span className="text-sm font-semibold text-gray-800">
              {Math.round(explanation.overallConfidence * 100)}% match
            </span>
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setIsExpanded(!isExpanded);
              }}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1 font-semibold hover:bg-blue-50 px-2 py-1 rounded-full transition-colors z-20 relative"
            >
              <HelpCircle size={14} />
              Why?
            </button>
          </div>
        </div>
        
        <AnimatePresence>
          {isExpanded && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 z-[9998]"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setIsExpanded(false);
                }}
              />
              {/* Modal */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: -10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 bg-white border border-gray-200 rounded-lg shadow-2xl z-[9999] p-4 max-h-[80vh] overflow-y-auto"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
              >
              <div className="text-sm font-medium text-gray-900 mb-2">
                Why this photo matched:
              </div>
              <div className="space-y-2">
                {explanation.reasons.map((reason, idx) => {
                  const Icon = getCategoryIcon(reason.category);
                  return (
                    <div key={idx} className="flex items-center gap-2 text-sm">
                      <Icon size={14} className="text-gray-500" />
                      <span className="text-gray-700">{reason.matched}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded border ${getConfidenceColor(reason.confidence)}`}>
                        {Math.round(reason.confidence * 100)}%
                      </span>
                    </div>
                  );
                })}
              </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/95 backdrop-blur-sm border border-gray-200 rounded-lg p-4 shadow-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${getTypeColor(explanation.type)}`} />
          <h4 className="text-sm font-semibold text-gray-900">
            Match Explanation
          </h4>
          <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getConfidenceColor(explanation.overallConfidence)}`}>
            {Math.round(explanation.overallConfidence * 100)}% confidence
          </div>
        </div>
        
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp size={16} />
              Hide details
            </>
          ) : (
            <>
              <ChevronDown size={16} />
              Show details
            </>
          )}
        </button>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3"
          >
            {explanation.reasons.map((reason, idx) => {
              const Icon = getCategoryIcon(reason.category);
              return (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className="flex items-start gap-3 p-3 bg-gray-50/50 rounded-lg"
                >
                  <div className="flex-shrink-0 p-2 bg-white rounded-md shadow-sm">
                    <Icon size={16} className="text-gray-600" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-gray-900">
                        {reason.category}
                      </span>
                      <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded border">
                        {reason.type}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-700 mb-2">
                      {reason.matched}
                    </p>
                    
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all duration-300 ${
                            reason.confidence >= 0.8 ? 'bg-green-500' :
                            reason.confidence >= 0.6 ? 'bg-blue-500' :
                            reason.confidence >= 0.4 ? 'bg-yellow-500' : 'bg-gray-400'
                          }`}
                          style={{ width: `${reason.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-600">
                        {Math.round(reason.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-lg">
                    {reason.badge}
                  </div>
                </motion.div>
              );
            })}
            
            <div className="pt-3 border-t border-gray-200">
              <div className="text-xs text-gray-500">
                <strong>Search Type:</strong> {explanation.type.charAt(0).toUpperCase() + explanation.type.slice(1)} search
                {explanation.type === 'metadata' && ' - Exact metadata matching'}
                {explanation.type === 'semantic' && ' - We understand your content visually'}
                {explanation.type === 'hybrid' && ' - We combined file details with visual understanding'}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};