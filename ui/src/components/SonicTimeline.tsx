import { useState } from 'react';
import { type TimelineData } from '../api';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';

interface SonicTimelineProps {
  onDateClick?: (date: string) => void;
}

// Format YYYY-MM to readable format
function formatDate(dateStr: string): string {
  try {
    const [year, month] = dateStr.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthIndex = parseInt(month, 10) - 1;
    if (monthIndex >= 0 && monthIndex < 12) {
      return `${monthNames[monthIndex]} ${year}`;
    }
    return dateStr;
  } catch {
    return dateStr;
  }
}

export function SonicTimeline({ onDateClick }: SonicTimelineProps) {
  const { timelineData: data, timelineLoading: loading } = usePhotoSearchContext();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [isMinimized, setIsMinimized] = useState(false);

  if (loading) return (
    <div className="fixed bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-slate-900/80 to-transparent backdrop-blur-xl animate-pulse z-40" />
  );
  
  if (data.length === 0) return (
    <div className="fixed bottom-0 left-0 right-0 h-20 flex items-center justify-center text-white/40 text-xs bg-gradient-to-t from-slate-900/80 to-transparent backdrop-blur-xl z-40">
      No timeline data
    </div>
  );

  const maxCount = Math.max(...data.map(d => d.count));

  return (
    <motion.div 
      className="fixed bottom-0 left-0 right-0 bg-gradient-to-t from-slate-900/95 via-slate-900/80 to-transparent backdrop-blur-xl border-t border-white/5 z-40"
      animate={{ height: isMinimized ? '2.5rem' : '6rem' }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Timeline Header with Minimize Button */}
      <div className="flex items-center justify-between px-6 py-2">
        <div className="text-white/30 text-[10px] uppercase tracking-widest">
          Timeline
        </div>
        <button
          onClick={() => setIsMinimized(!isMinimized)}
          className="text-white/40 hover:text-white/70 transition-colors p-1 rounded"
          aria-label={isMinimized ? 'Expand timeline' : 'Minimize timeline'}
        >
          {isMinimized ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>
      
      <AnimatePresence>
        {!isMinimized && (
          <motion.div 
            className="flex items-end gap-[3px] overflow-x-auto pb-3 px-6 scrollbar-hide"
            style={{ height: '3.5rem' }}
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            exit={{ opacity: 0, scaleY: 0 }}
            transition={{ duration: 0.2 }}
          >
        {data.map((item, i) => {
          const isHovered = hoveredIndex === i;
          const heightPercent = (item.count / maxCount) * 100;
          const formattedDate = formatDate(item.date);
          
          return (
            <motion.div
              key={item.date}
              initial={{ height: 0 }}
              animate={{ height: `${Math.max(heightPercent, 8)}%` }}
              transition={{ delay: i * 0.01, type: 'spring', stiffness: 100 }}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              onClick={() => onDateClick?.(item.date)}
              className={`
                w-3 min-w-[12px] rounded-t-md cursor-pointer transition-all duration-200 relative
                ${isHovered 
                  ? 'bg-gradient-to-t from-blue-400 via-purple-400 to-pink-400 scale-110 shadow-lg shadow-purple-500/30' 
                  : 'bg-gradient-to-t from-white/20 to-white/5 hover:from-white/40 hover:to-white/20'
                }
              `}
              title={`${formattedDate}: ${item.count} photos`}
            >
              {/* Hover tooltip */}
              {isHovered && (
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-xl text-white text-[11px] px-3 py-1.5 rounded-lg shadow-xl border border-white/10 whitespace-nowrap z-[60] pointer-events-none">
                  <div className="font-semibold">{formattedDate}</div>
                  <div className="text-white/60">{item.count} photos</div>
                  {onDateClick && <div className="text-blue-300 text-[10px] mt-0.5">Click to filter</div>}
                  {/* Tooltip arrow */}
                  <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-white/10"></div>
                </div>
              )}
            </motion.div>
          );
        })}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
