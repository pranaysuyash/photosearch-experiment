/**
 * Layout Component
 *
 * Provides modern floating navigation layout
 */

import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search,
  Settings,
  Info,
  Eye,
  EyeOff,
  ArrowUp,
  Clock,
} from 'lucide-react';
import { ModeRail } from './ModeRail';
import { Spotlight } from './Spotlight';
import { EnhancedSearchUI } from './EnhancedSearchUI';
import { usePhotoSearchContext } from '../contexts/PhotoSearchContext';
import { usePhotoViewer } from '../contexts/PhotoViewerContext';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../utils/storage';
import { api } from '../api';
import './Layout.css';

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const lastScrollYRef = useRef(0);
  const {
    photos,
    loading,
    resultCount,
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    sortBy,
    setSortBy,
    typeFilter,
    setTypeFilter,
    favoritesFilter,
    setFavoritesFilter,
    search,
  } = usePhotoSearchContext();
  const { openForPhoto } = usePhotoViewer();

  const [minimalMode, setMinimalMode] = useState(false);
  const [searchExpanded, setSearchExpanded] = useState(false);

  const [headerHidden, setHeaderHidden] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [spotlightOpen, setSpotlightOpen] = useState(false);
  const [hasRecentJobs, setHasRecentJobs] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [stats, setStats] = useState<{
    active_files?: number;
    deleted_files?: number;
  } | null>(null);

  useEffect(() => {
    const syncFromStorage = () => {
      try {
        if (!isLocalStorageAvailable()) return;
        setMinimalMode(localGetItem('lm:minimalMode') === '1');
      } catch {
        // ignore
      }
    };

    window.addEventListener('storage', syncFromStorage);
    window.addEventListener('lm:prefChange', syncFromStorage as EventListener);
    return () => {
      window.removeEventListener('storage', syncFromStorage);
      window.removeEventListener(
        'lm:prefChange',
        syncFromStorage as EventListener
      );
    };
  }, []);

  useEffect(() => {
    const syncRecentJobs = () => {
      try {
        const raw = localGetItem('lm:recentJobs');
        const list: unknown = raw ? JSON.parse(raw) : [];
        setHasRecentJobs(Array.isArray(list) && list.length > 0);
      } catch {
        setHasRecentJobs(false);
      }
    };

    syncRecentJobs();
    window.addEventListener('lm:jobsChange', syncRecentJobs as EventListener);
    window.addEventListener('storage', syncRecentJobs);
    return () => {
      window.removeEventListener(
        'lm:jobsChange',
        syncRecentJobs as EventListener
      );
      window.removeEventListener('storage', syncRecentJobs);
    };
  }, []);

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  useEffect(() => {
    const onScroll = () => {
      if (minimalMode) return;
      const y = window.scrollY || 0;
      const prev = lastScrollYRef.current;
      lastScrollYRef.current = y;

      setShowBackToTop(y > 900);

      if (y < 40) {
        setHeaderHidden(false);
        return;
      }

      const scrollingDown = y > prev;
      if (scrollingDown && y > 120) setHeaderHidden(true);
      if (!scrollingDown) setHeaderHidden(false);
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [minimalMode]);

  const showHeaderSearch =
    !(location.pathname === '/' && photos.length === 0) &&
    !location.pathname.startsWith('/globe');

  const resultsNumber = resultCount ?? photos.length;

  const toggleMinimalMode = () => {
    const next = !minimalMode;
    setMinimalMode(next);
    if (isLocalStorageAvailable()) {
      localSetItem('lm:minimalMode', next ? '1' : '0');
      window.dispatchEvent(new Event('lm:prefChange'));
    }
  };

  return (
    <div className='modern-layout'>
      {minimalMode && (
        <button
          onClick={toggleMinimalMode}
          className='fixed top-4 left-4 z-[1100] btn-glass btn-glass--muted text-xs px-3 py-2'
          title='Exit focus mode'
          aria-label='Exit focus mode'
        >
          <Eye size={14} />
          Exit focus
        </button>
      )}

      {/* Floating Top Bar */}
      {!minimalMode && (
        <>
          {/* Left rail: modes */}
          <motion.div
            className={`floating-pod floating-pod--left ${
              headerHidden ? 'floating-pod--hidden' : ''
            }`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
          >
            <ModeRail variant='inline' />
          </motion.div>

          {/* Center rail: search + status */}
          {showHeaderSearch && (
            <motion.div
              className={`floating-pod floating-pod--center ${
                headerHidden ? 'floating-pod--hidden' : ''
              }`}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              <div 
                className='floating-center-row'
                onMouseEnter={() => setSearchExpanded(true)}
                onMouseLeave={() => setSearchExpanded(false)}
              >
                {searchExpanded ? (
                  <div className='floating-search expanded'>
                    <EnhancedSearchUI
                      searchQuery={searchQuery}
                      setSearchQuery={setSearchQuery}
                      searchMode={searchMode}
                      setSearchMode={setSearchMode}
                      sortBy={sortBy}
                      setSortBy={setSortBy}
                      typeFilter={typeFilter}
                      setTypeFilter={setTypeFilter}
                      favoritesFilter={favoritesFilter}
                      setFavoritesFilter={setFavoritesFilter}
                      onSearch={() => search(searchQuery)}
                      isCompact={true}
                      heroTitle={null}
                    />
                  </div>
                ) : (
                  <button
                    className='btn-glass btn-glass--muted w-10 h-10 p-0 justify-center'
                    onClick={() => setSearchExpanded(true)}
                    title='Search'
                    aria-label='Search'
                  >
                    <Search size={18} />
                  </button>
                )}

                {(resultsNumber > 0 || stats?.active_files !== undefined) && (
                  <div className='floating-status'>
                    {loading && (
                      <div
                        className='w-4 h-4 border-2 border-white/15 border-t-white/70 rounded-full animate-spin'
                        aria-label='Searching'
                        title='Searching...'
                      />
                    )}
                    {resultsNumber > 0 && (
                      <button
                        type='button'
                        className='status-chip'
                        onClick={() => setStatusOpen((v) => !v)}
                        aria-label='Search results and library status'
                        title='Results + Library status'
                      >
                        {resultsNumber.toLocaleString()} results
                      </button>
                    )}
                    {stats?.active_files !== undefined && (
                      <button
                        type='button'
                        className='status-chip'
                        onClick={() => setStatusOpen((v) => !v)}
                        aria-label='Library indexing status'
                        title='Library indexing status'
                      >
                        Indexed {stats.active_files.toLocaleString()}
                      </button>
                    )}
                  </div>
                )}

                {statusOpen && (
                  <div className='status-popover-root'>
                    <div
                      className='status-popover-backdrop'
                      onClick={() => setStatusOpen(false)}
                    />
                    <div className='status-popover glass-surface glass-surface--strong rounded-2xl p-4'>
                      <div className='text-sm font-semibold text-foreground mb-2'>
                        Library status
                      </div>
                      <div className='text-sm text-muted-foreground space-y-1'>
                        <div>
                          Results:{' '}
                          <span className='text-foreground font-semibold'>
                            {resultsNumber.toLocaleString()}
                          </span>
                        </div>
                        {stats?.active_files !== undefined && (
                          <div>
                            Indexed:{' '}
                            <span className='text-foreground font-semibold'>
                              {stats.active_files.toLocaleString()}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className='mt-3 flex flex-wrap gap-2'>
                        <button
                          type='button'
                          className='btn-glass btn-glass--muted text-xs px-3 py-2'
                          onClick={() => {
                            setStatusOpen(false);
                            setSpotlightOpen(true);
                          }}
                        >
                          Scan a folder…
                        </button>
                        <Link
                          to='/settings#library'
                          className='btn-glass btn-glass--primary text-xs px-3 py-2'
                          onClick={() => setStatusOpen(false)}
                        >
                          Manage library
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Right rail: actions */}
          <motion.div
            className={`floating-pod floating-pod--right ${
              headerHidden ? 'floating-pod--hidden' : ''
            }`}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
          >
            <div className='glass-surface rounded-full p-1 header-actions'>
              {!showHeaderSearch && (
                <button
                  onClick={() => setSpotlightOpen(true)}
                  className='icon-btn'
                  data-tooltip='Search'
                  title='Search (⌘/Ctrl+K)'
                  aria-label='Search'
                >
                  <Search size={18} />
                </button>
              )}
              <Link
                to='/jobs'
                className='icon-btn relative'
                data-tooltip='Jobs'
                title='Jobs (background scans/indexing)'
                aria-label='Jobs'
              >
                <Clock size={18} />
                {hasRecentJobs && (
                  <span className='absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.65)]' />
                )}
              </Link>
              <button
                onClick={toggleMinimalMode}
                className='icon-btn'
                data-tooltip='Focus'
                title='Focus mode (hide chrome)'
                aria-label='Toggle focus mode'
              >
                <EyeOff size={18} />
              </button>
              <Link
                to='/settings'
                className='icon-btn'
                data-tooltip='Settings'
                title='Settings'
                aria-label='Settings'
              >
                <Settings size={18} />
              </Link>
              <Link
                to='/about'
                className='icon-btn'
                data-tooltip='About'
                title='About'
                aria-label='About'
              >
                <Info size={18} />
              </Link>
            </div>
          </motion.div>
        </>
      )}

      {/* Main Content Area */}
      <main className='content-area'>
        <Spotlight
          open={spotlightOpen}
          onOpenChange={setSpotlightOpen}
          onPhotoSelect={(photo) => openForPhoto(photos, photo)}
        />
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {children}
        </motion.div>
      </main>

      {/* Back to Top */}
      {!minimalMode && showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          className='fixed bottom-6 right-6 z-[1000] btn-glass btn-glass--muted w-11 h-11 p-0 justify-center'
          title='Back to top'
          aria-label='Back to top'
        >
          <ArrowUp size={18} />
        </button>
      )}
    </div>
  );
};

export default Layout;
