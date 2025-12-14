import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import {
  Search,
  Mic,
  Pin,
  PinOff,
  ChevronRight,
  Image as ImageIcon,
  FileText,
  Video,
  Clock,
  Cloud,
  HardDrive,
  Shield,
  Sparkles,
  X,
} from 'lucide-react';

export function DynamicNotchSearch() {
  const {
    searchQuery,
    setSearchQuery,
    search,
    searchMode,
    setSearchMode,
    typeFilter,
    setTypeFilter,
    // dateFrom, setDateRange
  } = usePhotoSearchContext();

  const [expanded, setExpanded] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const [mode, setMode] = useState<'notch' | 'bubble' | 'camera'>('camera');
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hoverTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Handle outside clicks
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        if (!pinned && expanded) {
          setExpanded(false);
          setActiveGroup(null);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [expanded, pinned]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setExpanded(true);
        setPinned(true);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
      if (e.key === 'Escape') {
        if (expanded) {
          setExpanded(false);
          setPinned(false);
          setActiveGroup(null);
          inputRef.current?.blur();
        }
      }
      // Mode switching for demo purposes
      if (e.altKey) {
        if (e.key === '1') setMode('bubble');
        if (e.key === '2') setMode('notch');
        if (e.key === '3') setMode('camera');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [expanded]);

  const handleMouseEnter = () => {
    if (pinned) return;
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
    setExpanded(true);
  };

  const handleMouseLeave = () => {
    if (pinned) return;
    hoverTimerRef.current = setTimeout(() => {
      setExpanded(false);
      setActiveGroup(null);
    }, 300);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    search(searchQuery);
    // Optional: collapse on search?
    // setExpanded(false);
  };

  // Animation variants
  const containerVariants = {
    collapsed: {
      width: mode === 'camera' ? 160 : 46,
      height: mode === 'camera' ? 44 : 46,
      borderRadius: mode === 'camera' ? '0 0 22px 22px' : 999,
      transition: { type: 'spring', stiffness: 300, damping: 30 },
    },
    expanded: {
      width: 'min(600px, 94vw)',
      height: 54, // Slightly taller when expanded
      borderRadius: 27, // Rounded rect
      transition: { type: 'spring', stiffness: 300, damping: 30 },
    },
  };

  return (
    <motion.div
      ref={containerRef}
      className={`fixed z-[9999] bg-[#141824] shadow-2xl text-[#e6e8ef] overflow-visible flex items-center
        ${mode === 'camera' ? 'top-0 left-1/2 -translate-x-1/2' : ''}
        ${mode === 'notch' ? 'top-2 left-1/2 -translate-x-1/2' : ''}
        ${mode === 'bubble' ? 'top-4 right-4' : ''}
      `}
      initial='collapsed'
      animate={expanded ? 'expanded' : 'collapsed'}
      variants={containerVariants}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        // Safe area support
        marginTop: 'env(safe-area-inset-top)',
      }}
    >
      {/* Handle / Icon (Visible when collapsed) */}
      <div
        className={`absolute inset-0 flex items-center justify-center cursor-pointer ${
          expanded ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}
        onClick={() => setPinned(!pinned)}
      >
        {mode === 'camera' ? (
          <div className='w-16 h-4 bg-black/50 rounded-full shadow-inner' />
        ) : (
          <Search className='w-5 h-5 opacity-80' />
        )}
      </div>

      {/* Expanded Content */}
      <motion.div
        className='flex items-center w-full h-full px-2 opacity-0'
        animate={{ opacity: expanded ? 1 : 0 }}
        transition={{ duration: 0.2 }}
      >
        {/* Left: Search Input */}
        <form
          onSubmit={handleSearchSubmit}
          className='flex-1 flex items-center gap-2 min-w-0'
        >
          <div className='relative flex-1 flex items-center'>
            <Search className='absolute left-3 w-4 h-4 text-gray-400' />
            <input
              ref={inputRef}
              type='text'
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder='Search photos...'
              className='w-full h-9 pl-9 pr-3 bg-[#101420] border border-white/10 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50 transition-colors'
            />
          </div>

          <button
            type='button'
            onClick={() => setPinned(!pinned)}
            className={`p-2 rounded-full hover:bg-white/10 transition-colors ${
              pinned ? 'text-blue-400' : 'text-gray-400'
            }`}
          >
            {pinned ? (
              <Pin className='w-4 h-4' />
            ) : (
              <PinOff className='w-4 h-4' />
            )}
          </button>
        </form>

        <div className='w-px h-6 bg-white/10 mx-2' />

        {/* Right: Filters */}
        <div className='flex items-center gap-1'>
          {/* Type Filter Group */}
          <div className='relative group'>
            <button
              className={`px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-white/10 transition-colors flex items-center gap-1 ${
                activeGroup === 'type'
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400'
              }`}
              onClick={() =>
                setActiveGroup(activeGroup === 'type' ? null : 'type')
              }
            >
              Type <ChevronRight className='w-3 h-3 opacity-50' />
            </button>

            <AnimatePresence>
              {activeGroup === 'type' && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className='absolute top-full right-0 mt-2 w-48 bg-[#141824] border border-white/10 rounded-xl shadow-xl p-2 flex flex-col gap-1 overflow-hidden'
                >
                  <div className='text-[10px] uppercase tracking-wider text-gray-500 px-2 py-1 font-semibold'>
                    File Type
                  </div>
                  {[
                    { id: 'all', label: 'All', icon: Sparkles },
                    { id: 'photo', label: 'Photos', icon: ImageIcon },
                    { id: 'video', label: 'Videos', icon: Video },
                  ].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setTypeFilter(t.id);
                        setActiveGroup(null);
                      }}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs w-full text-left transition-colors ${
                        typeFilter === t.id
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'hover:bg-white/5 text-gray-300'
                      }`}
                    >
                      <t.icon className='w-3 h-3' />
                      {t.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Mode Filter Group */}
          <div className='relative group'>
            <button
              className={`px-3 py-1.5 rounded-lg text-xs font-medium hover:bg-white/10 transition-colors flex items-center gap-1 ${
                activeGroup === 'mode'
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400'
              }`}
              onClick={() =>
                setActiveGroup(activeGroup === 'mode' ? null : 'mode')
              }
            >
              Mode <ChevronRight className='w-3 h-3 opacity-50' />
            </button>

            <AnimatePresence>
              {activeGroup === 'mode' && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className='absolute top-full right-0 mt-2 w-48 bg-[#141824] border border-white/10 rounded-xl shadow-xl p-2 flex flex-col gap-1 overflow-hidden'
                >
                  <div className='text-[10px] uppercase tracking-wider text-gray-500 px-2 py-1 font-semibold'>
                    Search Mode
                  </div>
                  {[
                    { id: 'semantic', label: 'Semantic (AI)', icon: Sparkles },
                    { id: 'metadata', label: 'Metadata', icon: FileText },
                    { id: 'visual', label: 'Visual Match', icon: ImageIcon },
                  ].map((m) => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setSearchMode(m.id as any);
                        setActiveGroup(null);
                      }}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs w-full text-left transition-colors ${
                        searchMode === m.id
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'hover:bg-white/5 text-gray-300'
                      }`}
                    >
                      <m.icon className='w-3 h-3' />
                      {m.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
