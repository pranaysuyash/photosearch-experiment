import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import { usePlatformDetect } from '../../hooks/usePlatformDetect';
import { useNotch } from '../../hooks/useNotch';
import { glass } from '../../design/glass';
import {
  Search,
  Sparkles,
  Pin,
  PinOff,
  ChevronDown,
  Image as ImageIcon,
  FileText,
  Video,
  X,
} from 'lucide-react';

/**
 * DynamicNotchSearch Component
 * 
 * Center-expansion design: The notch stays as a visual anchor in the center.
 * When expanded, the search bar expands LEFT and filter options expand RIGHT
 * from the central divider (like iPhone Dynamic Island).
 */
export function DynamicNotchSearch() {
  const {
    searchQuery,
    setSearchQuery,
    search,
    searchMode,
    setSearchMode,
    typeFilter,
    setTypeFilter,
  } = usePhotoSearchContext();

  const { isDesktopApp, isMobile } = usePlatformDetect();
  const { topInset } = useNotch();

  const initialMode = isMobile ? 'mobile' : isDesktopApp ? 'notch' : 'bubble';

  const [mode, setMode] = useState<'notch' | 'bubble' | 'mobile'>(initialMode);
  const [expanded, setExpanded] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isMobile) setMode('mobile');
    else if (isDesktopApp) setMode('notch');
    else setMode('bubble');
  }, [isMobile, isDesktopApp]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        if (!pinned && expanded) {
          setExpanded(false);
          setActiveGroup(null);
        }
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [expanded, pinned]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setExpanded(true);
        setPinned(true);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
      if (e.key === 'Escape' && expanded) {
        setExpanded(false);
        setPinned(false);
        setActiveGroup(null);
        inputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [expanded]);

  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    };
  }, []);

  const handleMouseEnter = () => {
    if (pinned || isMobile) return;
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    setExpanded(true);
  };

  const handleMouseLeave = () => {
    if (pinned || isMobile) return;
    hoverTimerRef.current = setTimeout(() => {
      setExpanded(false);
      setActiveGroup(null);
    }, 300);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    search(searchQuery);
  };

  const clearSearch = () => {
    setSearchQuery('');
    inputRef.current?.focus();
  };

  const collapsedHeight = mode === 'notch' && topInset > 0 ? Math.max(40, topInset + 8) : 44;

  return (
    <div
      ref={containerRef}
      className="fixed z-[9999] flex items-center justify-center"
      style={{
        top: mode === 'notch' ? 0 : 16,
        left: 0,
        right: 0,
        pointerEvents: 'none',
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Center-Expanding Container */}
      <motion.div
        className="flex items-center justify-center"
        style={{ pointerEvents: 'auto' }}
        initial={false}
        animate={{
          gap: expanded ? 8 : 0,
        }}
        transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      >
        {/* LEFT: Search Input (expands left from center) */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className={`${glass.surfaceStrong} rounded-full overflow-hidden flex items-center`}
              style={{ originX: 1, height: collapsedHeight }} // Expand from right edge (toward left), match height
            >
              <form onSubmit={handleSearchSubmit} className="flex items-center w-full h-full">
                <Search className="ml-4 text-muted-foreground w-4 h-4 flex-shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search photos..."
                  className="flex-1 bg-transparent border-none outline-none px-3 py-3 text-sm placeholder:text-muted-foreground/50"
                  autoFocus
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="p-1 mr-2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X size={14} />
                  </button>
                )}
              </form>
            </motion.div>
          )}
        </AnimatePresence>

        {/* CENTER: The Notch/Island (always visible) */}
        <motion.div
          onClick={() => !expanded && setExpanded(true)}
          className={`${glass.surfaceStrong} flex items-center justify-center cursor-pointer`}
          animate={{
            width: expanded ? 52 : 140,
            height: collapsedHeight,
            borderRadius: mode === 'notch' && !expanded ? '0 0 22px 22px' : 22,
          }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}
          whileHover={!expanded ? { scale: 1.02 } : {}}
          whileTap={!expanded ? { scale: 0.98 } : {}}
        >
          {!expanded ? (
            // Collapsed: Dynamic Island aesthetic
            <div className="flex items-center gap-2 px-2">
              <div className="w-2 h-2 rounded-full bg-gradient-to-br from-white/25 to-white/5" />
              <Search className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] text-muted-foreground font-medium tracking-wider">SEARCH</span>
              <div className="flex gap-1 ml-0.5">
                <div className="w-1 h-1 rounded-full bg-white/25 animate-pulse" />
                <div className="w-1 h-1 rounded-full bg-white/20 animate-pulse" style={{ animationDelay: '0.2s' }} />
                <div className="w-1 h-1 rounded-full bg-white/15 animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          ) : (
            // Expanded: Central divider with pin
            <button
              type="button"
              onClick={() => setPinned(!pinned)}
              className={`p-2 rounded-full transition-all ${pinned ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-white/10'}`}
              title={pinned ? "Unpin" : "Pin open"}
            >
              {pinned ? <Pin className="w-4 h-4" /> : <PinOff className="w-4 h-4" />}
            </button>
          )}
        </motion.div>

        {/* RIGHT: Filter Options (expand right from center) */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 'auto', opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className={`${glass.surfaceStrong} rounded-full flex items-center gap-1 px-2`}
              style={{ originX: 0, height: collapsedHeight, overflow: 'visible' }}
            >
              {/* Type Filter */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setActiveGroup(activeGroup === 'type' ? null : 'type')}
                  className={`px-3 py-2 rounded-full text-xs font-medium flex items-center gap-1 transition-all ${activeGroup === 'type' ? 'bg-white/15 text-foreground' : 'text-muted-foreground hover:bg-white/10'
                    }`}
                >
                  {typeFilter === 'all' ? 'All' : typeFilter}
                  <ChevronDown className={`w-3 h-3 transition-transform ${activeGroup === 'type' ? 'rotate-180' : ''}`} />
                </button>

                <AnimatePresence>
                  {activeGroup === 'type' && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className={`absolute top-full right-0 mt-2 w-32 rounded-xl p-1.5 z-[10000] ${glass.surfaceStrong}`}
                    >
                      {[
                        { id: 'all', label: 'All', icon: Sparkles },
                        { id: 'photo', label: 'Photos', icon: ImageIcon },
                        { id: 'video', label: 'Videos', icon: Video },
                      ].map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => { setTypeFilter(item.id); setActiveGroup(null); }}
                          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all ${typeFilter === item.id ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-white/10'
                            }`}
                        >
                          <item.icon className="w-3 h-3" />
                          {item.label}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Mode Filter */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setActiveGroup(activeGroup === 'mode' ? null : 'mode')}
                  className={`px-3 py-2 rounded-full text-xs font-medium flex items-center gap-1 transition-all ${activeGroup === 'mode' ? 'bg-white/15 text-foreground' : 'text-muted-foreground hover:bg-white/10'
                    }`}
                >
                  {searchMode === 'semantic' ? 'AI' : searchMode === 'metadata' ? 'Meta' : 'Visual'}
                  <ChevronDown className={`w-3 h-3 transition-transform ${activeGroup === 'mode' ? 'rotate-180' : ''}`} />
                </button>

                <AnimatePresence>
                  {activeGroup === 'mode' && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className={`absolute top-full right-0 mt-2 w-36 rounded-xl p-1.5 z-[10000] ${glass.surfaceStrong}`}
                    >
                      {[
                        { id: 'semantic', label: 'Semantic (AI)', icon: Sparkles },
                        { id: 'metadata', label: 'Metadata', icon: FileText },
                        { id: 'visual', label: 'Visual Match', icon: ImageIcon },
                      ].map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => { setSearchMode(item.id as any); setActiveGroup(null); }}
                          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all ${searchMode === item.id ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-white/10'
                            }`}
                        >
                          <item.icon className="w-3 h-3" />
                          {item.label}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
