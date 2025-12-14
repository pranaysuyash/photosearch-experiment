import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CalendarRange, ChevronUp, ChevronDown, X } from 'lucide-react';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import { isLocalStorageAvailable, localGetItem } from '../../utils/storage';

interface SonicTimelineProps {
  onDateClick?: (date: string) => void;
}

// Format YYYY-MM to readable format
function formatDate(dateStr: string): string {
  try {
    const [year, month] = dateStr.split('-');
    const monthNames = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
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
  const {
    timelineData: data,
    timelineLoading: loading,
    dateFrom,
    dateTo,
    setDateRange,
    clearDateRange,
  } = usePhotoSearchContext();
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [pinnedOpen, setPinnedOpen] = useState(false);
  const [hoverOpen, setHoverOpen] = useState(false);
  const [hidden, setHidden] = useState(false);
  const closeTimerRef = useRef<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const dragStartRef = useRef<number | null>(null);
  const dragEndRef = useRef<number | null>(null);
  const suppressNextClickRef = useRef(false);
  const [dragPreview, setDragPreview] = useState<{
    start: number | null;
    end: number | null;
  }>({ start: null, end: null });

  useEffect(() => {
    const sync = () => {
      try {
        if (!isLocalStorageAvailable()) {
          setHidden(false);
          return;
        }
        setHidden(localGetItem('lm:minimalMode') === '1');
      } catch {
        setHidden(false);
      }
    };
    sync();
    window.addEventListener('lm:prefChange', sync as EventListener);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('lm:prefChange', sync as EventListener);
      window.removeEventListener('storage', sync);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const onUp = () => finalizeDrag();
    window.addEventListener('pointerup', onUp, { passive: true });
    window.addEventListener('pointercancel', onUp, { passive: true });
    return () => {
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dragging]);

  // Early returns MUST come AFTER all hook definitions
  if (hidden) return null;

  if (loading)
    return (
      <div className='fixed bottom-6 left-4 right-4 sm:left-6 sm:right-auto sm:w-[520px] h-12 glass-surface rounded-2xl animate-pulse z-40' />
    );

  if (data.length === 0) return null;

  const maxCount = Math.max(...data.map((d) => d.count));
  const isOpen = pinnedOpen || hoverOpen;

  const selectedRange = (() => {
    if (!dateFrom && !dateTo) return null;
    const from = dateFrom ?? dateTo;
    const to = dateTo ?? dateFrom;
    if (!from || !to) return null;
    const a = data.findIndex((d) => d.date === from);
    const b = data.findIndex((d) => d.date === to);
    if (a < 0 || b < 0) return null;
    return { start: Math.min(a, b), end: Math.max(a, b) };
  })();

  const previewRange =
    dragging && dragPreview.start !== null && dragPreview.end !== null
      ? {
          start: Math.min(dragPreview.start, dragPreview.end),
          end: Math.max(dragPreview.start, dragPreview.end),
        }
      : null;

  const rangeToHighlight = previewRange ?? selectedRange;

  const finalizeDrag = () => {
    if (!dragging) return;
    const start = dragStartRef.current;
    const end = dragEndRef.current ?? start;
    setDragging(false);
    dragStartRef.current = null;
    dragEndRef.current = null;
    setDragPreview({ start: null, end: null });
    if (start === null || end === null) return;
    const a = Math.min(start, end);
    const b = Math.max(start, end);
    const from = data[a]?.date;
    const to = data[b]?.date;
    if (from && to) {
      suppressNextClickRef.current = true;
      setDateRange(from, to);
      onDateClick?.(from === to ? from : `${from}..${to}`);
    }
  };

  return (
    <motion.div
      className='fixed bottom-6 left-4 right-4 sm:left-6 sm:right-auto sm:w-[520px] glass-surface rounded-2xl shadow-2xl z-40'
      animate={{ height: isOpen ? '7.5rem' : '2.75rem' }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      onMouseEnter={() => {
        if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
        closeTimerRef.current = null;
        setHoverOpen(true);
      }}
      onMouseLeave={() => {
        if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current);
        closeTimerRef.current = window.setTimeout(
          () => setHoverOpen(false),
          900
        );
      }}
    >
      {/* Timeline Header with Minimize Button */}
      <div className='flex items-center justify-between px-3 py-2'>
        <div className='flex items-center gap-2 text-white/70 min-w-0'>
          <CalendarRange size={16} aria-hidden='true' />
          <span className='sr-only'>Timeline</span>
          {selectedRange && (
            <div className='text-[11px] text-white/70 truncate'>
              {formatDate(data[selectedRange.start].date)} –{' '}
              {formatDate(data[selectedRange.end].date)}
            </div>
          )}
        </div>
        <div className='flex items-center gap-2'>
          {selectedRange && (
            <button
              onClick={() => clearDateRange()}
              className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center text-white/80'
              aria-label='Clear date filter'
              title='Clear date filter'
            >
              <X size={14} />
            </button>
          )}
          <button
            onClick={() => setPinnedOpen((v) => !v)}
            className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center text-white/80'
            aria-label={pinnedOpen ? 'Auto-hide timeline' : 'Pin timeline open'}
            title={pinnedOpen ? 'Auto-hide timeline' : 'Pin timeline open'}
          >
            {pinnedOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            className='flex items-end gap-[3px] overflow-x-auto pb-3 px-4 scrollbar-hide h-[4.25rem]'
            initial={{ opacity: 0, scaleY: 0 }}
            animate={{ opacity: 1, scaleY: 1 }}
            exit={{ opacity: 0, scaleY: 0 }}
            transition={{ duration: 0.2 }}
            onPointerUp={() => finalizeDrag()}
            onPointerLeave={() => {
              if (dragging && !pinnedOpen) {
                // keep preview, but don't force hover state open
              }
            }}
          >
            {data.map((item, i) => {
              const isHovered = hoveredIndex === i;
              const inRange =
                rangeToHighlight &&
                i >= rangeToHighlight.start &&
                i <= rangeToHighlight.end;
              const heightPercent = (item.count / maxCount) * 100;
              const formattedDate = formatDate(item.date);

              return (
                <motion.div
                  key={item.date}
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.max(heightPercent, 8)}%` }}
                  transition={{
                    delay: i * 0.01,
                    type: 'spring',
                    stiffness: 100,
                  }}
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                  onPointerDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    try {
                      (e.currentTarget as HTMLElement).setPointerCapture(
                        e.pointerId
                      );
                    } catch {
                      // ignore
                    }
                    setPinnedOpen(true);
                    setDragging(true);
                    dragStartRef.current = i;
                    dragEndRef.current = i;
                    setDragPreview({ start: i, end: i });
                  }}
                  onPointerEnter={() => {
                    if (!dragging) return;
                    dragEndRef.current = i;
                    setDragPreview({ start: dragStartRef.current, end: i });
                  }}
                  onClick={() => {
                    if (dragging) return;
                    if (suppressNextClickRef.current) {
                      suppressNextClickRef.current = false;
                      return;
                    }
                    setDateRange(item.date, item.date);
                    onDateClick?.(item.date);
                  }}
                  className={`
                w-3 min-w-[12px] rounded-t-md cursor-pointer transition-all duration-200 relative
                ${
                  isHovered
                    ? 'bg-gradient-to-t from-blue-400 via-purple-400 to-pink-400 scale-110 shadow-lg shadow-purple-500/30'
                    : inRange
                    ? 'bg-gradient-to-t from-sky-400/60 via-purple-400/50 to-pink-400/40 shadow-lg shadow-sky-500/20'
                    : 'bg-gradient-to-t from-white/20 to-white/5 hover:from-white/40 hover:to-white/20'
                }
              `}
                  title={`${formattedDate}: ${item.count} photos`}
                >
                  {/* Hover tooltip */}
                  {isHovered && (
                    <div className='absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-white/10 backdrop-blur-xl text-white text-[11px] px-3 py-1.5 rounded-lg shadow-xl border border-white/10 whitespace-nowrap z-[60] pointer-events-none'>
                      <div className='font-semibold'>{formattedDate}</div>
                      <div className='text-white/60'>{item.count} photos</div>
                      {onDateClick && (
                        <div className='text-blue-300 text-[10px] mt-0.5'>
                          Click to filter
                        </div>
                      )}
                      {/* Tooltip arrow */}
                      <div className='absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-white/10'></div>
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
