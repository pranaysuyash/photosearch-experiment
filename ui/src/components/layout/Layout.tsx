/**
 * Layout Component
 *
 * Provides modern floating navigation layout
 */

import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  // Settings,
  // Info,
  Eye,
  // EyeOff,
  // EyeOff, // Removed as per instruction
  ArrowUp,
  Menu,
  X,
  // Clock,
} from 'lucide-react';
import { ModeRail } from './ModeRail';
// import { Spotlight } from '../search/Spotlight';
import { DynamicNotchSearch } from './DynamicNotchSearch';
import { ActionsPod } from './ActionsPod'; // Kept as ActionsPod, assuming instruction's 'ActionPod' was a typo
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
// import { useJobMonitor } from '../../hooks/useJobMonitor'; // Removed as per instruction
// import { usePhotoViewer } from '../../contexts/PhotoViewerContext';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../../utils/storage';
import { api } from '../../api';
import './Layout.css';
// import { NotchBar, useNotchAware } from './NotchBar';


interface LayoutProps {
  children?: React.ReactNode;
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const lastScrollYRef = useRef(0);
  // const { hasNotch } = useNotchAware();

  const [searchExpanded, setSearchExpanded] = useState(false);

  const { photos, resultCount } = usePhotoSearchContext();
  const resultsNumber = resultCount ?? photos.length;



  const [minimalMode, setMinimalMode] = useState(false);
  const [headerHidden, setHeaderHidden] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [hasRecentJobs, setHasRecentJobs] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
    setMobileMenuOpen(false);
  }, [location.pathname, searchExpanded]);

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

  // Search moved to page content - don't show in header
  // const showHeaderSearch = false;

  // const resultsNumber = resultCount ?? photos.length; // Now from context

  const toggleMinimalMode = () => {
    const next = !minimalMode;
    setMinimalMode(next);
    if (isLocalStorageAvailable()) {
      localSetItem('lm:minimalMode', next ? '1' : '0');
      window.dispatchEvent(new Event('lm:prefChange'));
    }
  };

  const headerMotionTarget = headerHidden
    ? { opacity: 0, y: -140 }
    : { opacity: 1, y: 0 };

  const headerMotionTransition = {
    duration: 0.28,
    ease: [0.25, 0.46, 0.45, 0.94] as const,
  };

  return (
    <div className='min-h-screen bg-background text-foreground selection:bg-primary/30 selection:text-primary-foreground font-sans'>
      {/* Background gradients */}
      <div className='fixed inset-0 z-0 pointer-events-none'>
        <div className='absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/5 blur-[120px] opacity-50 mix-blend-screen animate-pulse-slow' />
        <div className='absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-secondary/5 blur-[120px] opacity-50 mix-blend-screen animate-pulse-slow delay-1000' />
      </div>

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
        <div className='fixed top-0 left-0 right-0 z-[1000] pointer-events-none'>
          <div className='lm-header-grid w-full max-w-[1600px] mx-auto grid grid-cols-[auto_1fr_auto] items-start px-2 sm:px-4 md:px-6 pt-3 sm:pt-4 gap-2 sm:gap-4'>
            {/* Left rail: modes */}
            <motion.div
              className='lm-header-left pointer-events-auto z-20'
              initial={{ opacity: 0, y: -10 }}
              animate={headerMotionTarget}
              transition={headerMotionTransition}
            >
              <ModeRail variant='standalone' />
            </motion.div>

            {/* Center: Dynamic Notch Search */}
            <motion.div
              className='lm-header-center flex justify-center pointer-events-auto z-10'
              initial={{ opacity: 0, y: -10 }}
              animate={headerMotionTarget}
              transition={headerMotionTransition}
            >
              <DynamicNotchSearch onExpandedChange={setSearchExpanded} />
            </motion.div>

            {/* Right rail: actions */}
            <div className="lm-header-right relative z-20 h-11 flex items-center justify-end">
              <AnimatePresence>
                {!searchExpanded && (
                  <>
                    {/* Desktop: Static Grid Item */}
                    <motion.div
                      layout
                      className='pointer-events-auto hidden md:block'
                      initial={{ opacity: 0, x: 20, scale: 0.9 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      exit={{ opacity: 0, x: 20, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ActionsPod
                        hasRecentJobs={hasRecentJobs}
                        toggleMinimalMode={toggleMinimalMode}
                      />
                    </motion.div>

                    {/* Mobile: More menu */}
                    <motion.button
                      type='button'
                      className='pointer-events-auto md:hidden btn-glass btn-glass--muted w-10 h-10 p-0 justify-center'
                      onClick={() => setMobileMenuOpen((v) => !v)}
                      aria-expanded={mobileMenuOpen}
                      aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
                      initial={{ opacity: 0, y: -10 }}
                      animate={headerMotionTarget}
                      transition={headerMotionTransition}
                    >
                      {mobileMenuOpen ? <X size={16} /> : <Menu size={16} />}
                    </motion.button>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>

          {mobileMenuOpen && !searchExpanded && (
            <>
              <div
                className='lm-mobile-menu-backdrop'
                onClick={() => setMobileMenuOpen(false)}
              />
              <div className='lm-mobile-menu pointer-events-auto'>
                <div className='lm-mobile-menu-section'>
                  <ModeRail variant='standalone' />
                </div>
                <ActionsPod
                  hasRecentJobs={hasRecentJobs}
                  toggleMinimalMode={toggleMinimalMode}
                />
              </div>
            </>
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
                      // setSpotlightOpen(true);
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
      )}

      {/* Main Content Area */}
      <main className='lm-main flex-1 w-full max-w-[1600px] mx-auto pt-20 px-4 md:px-6 pb-32'>
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {children}
        </motion.div>
      </main >

      {/* Back to Top */}
      {
        !minimalMode && showBackToTop && (
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className='fixed bottom-6 right-6 z-[1000] btn-glass btn-glass--muted w-11 h-11 p-0 justify-center'
            title='Back to top'
            aria-label='Back to top'
          >
            <ArrowUp size={18} />
          </button>
        )
      }
    </div >
  );
};

export default Layout;
