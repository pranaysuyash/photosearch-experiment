import { useEffect, useState } from 'react';
import { api, type TimelineData } from '../api';
import { cn } from '../lib/utils';
import { motion } from 'framer-motion';

export function SonicTimeline() {
  const [data, setData] = useState<TimelineData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTimeline()
      .then(setData)
      .catch(console.error) // TODO: Handle error better
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-16 w-full bg-secondary/20 animate-pulse" />;
  if (data.length === 0) return <div className="h-16 w-full flex items-center justify-center text-muted-foreground text-xs">No timeline data</div>;

  // Normalize data for visualization
  const maxCount = Math.max(...data.map(d => d.count));

  return (
    <div className="fixed bottom-0 left-0 right-0 h-24 bg-background/80 backdrop-blur-md border-t border-border z-50 px-4 py-2">
      <div className="flex h-full items-end gap-[2px] overflow-x-auto pb-2 scrollbar-hide">
        {data.map((item, i) => (
          <motion.div
            key={item.date}
            initial={{ height: 0 }}
            animate={{ height: `${(item.count / maxCount) * 100}%` }}
            transition={{ delay: i * 0.01 }}
            className={cn(
              "w-2 min-w-[8px] bg-primary/50 hover:bg-primary rounded-t-sm cursor-pointer transition-colors relative group"
            )}
            title={`${item.date}: ${item.count} photos`}
          >
             <div className="opacity-0 group-hover:opacity-100 absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-popover text-popover-foreground text-[10px] px-1 py-0.5 rounded shadow whitespace-nowrap z-50 pointer-events-none">
                {item.date}
             </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
