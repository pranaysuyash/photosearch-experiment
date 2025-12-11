import { useEffect, useState } from 'react';
import { api, type TimelineData } from '../api';
import { motion } from 'framer-motion';

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
  const [data, setData] = useState<TimelineData[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    api.getTimeline()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-20 w-full bg-gradient-to-t from-slate-900/80 to-transparent backdrop-blur-xl animate-pulse" />;
  if (data.length === 0) return <div className="h-20 w-full flex items-center justify-center text-white/40 text-xs bg-gradient-to-t from-slate-900/80 to-transparent backdrop-blur-xl">No timeline data</div>;

  const maxCount = Math.max(...data.map(d => d.count));

  return (
    <div className="fixed bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-slate-900/95 via-slate-900/80 to-transparent backdrop-blur-xl border-t border-white/5 z-50 px-6">
      {/* Timeline Label */}
      <div className="absolute top-1 left-6 text-white/30 text-[10px] uppercase tracking-widest">
        Timeline
      </div>
      
      <div className="flex h-full items-end gap-[3px] overflow-x-auto pb-3 pt-5 scrollbar-hide">
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
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-xl text-white text-[11px] px-3 py-1.5 rounded-lg shadow-xl border border-white/10 whitespace-nowrap z-50 pointer-events-none">
                  <div className="font-semibold">{formattedDate}</div>
                  <div className="text-white/60">{item.count} photos</div>
                  {onDateClick && <div className="text-blue-300 text-[10px] mt-0.5">Click to filter</div>}
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
