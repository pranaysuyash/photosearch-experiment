import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { Command } from 'cmdk';
import { Search, Zap, Moon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { type Photo, api } from '../../api';
import SecureLazyImage from '../gallery/SecureLazyImage';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../../utils/storage';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import { useNavigate } from 'react-router-dom';
import { glass } from '../../design/glass';
import { pickDirectory } from '../../utils/pickDirectory';

interface SpotlightProps {
  onPhotoSelect?: (photo: Photo) => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function Spotlight({
  onPhotoSelect,
  open: openProp,
  onOpenChange,
}: SpotlightProps) {
  const navigate = useNavigate();
  const isControlled = typeof openProp === 'boolean' && !!onOpenChange;
  const [internalOpen, setInternalOpen] = useState(false);
  const open = isControlled ? (openProp as boolean) : internalOpen;
  const setOpen = useCallback(
    (next: boolean | ((prev: boolean) => boolean)) => {
      if (isControlled) {
        const current = openProp as boolean;
        const resolved =
          typeof next === 'function'
            ? (next as (p: boolean) => boolean)(current)
            : next;
        onOpenChange?.(resolved);
        return;
      }

      setInternalOpen(next as boolean | ((prev: boolean) => boolean));
    },
    [isControlled, onOpenChange, openProp]
  );
  const [query, setQuery] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Use shared context for photo results
  const { photos: results, loading, setSearchQuery } = usePhotoSearchContext();

  const [status, setStatus] = useState<{
    message: string;
    type: 'success' | 'error' | 'info';
    details?: Record<string, unknown>;
  } | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const handleScan = useCallback(async () => {
    setStatus({ message: 'Choose a folder…', type: 'info' });
    const picked = await pickDirectory();
    if (!picked) {
      setStatus({
        message:
          'Local folder scanning is available in the desktop app. Connect cloud sources or open Settings → Sources.',
        type: 'info',
      });
      return;
    }

    setStatus({ message: 'Starting scan…', type: 'info' });

    try {
      const res = await api.addLocalFolderSource(picked);
      const jobId = res.job_id;

      // Record recent jobs for the Jobs page
      try {
        if (isLocalStorageAvailable()) {
          const raw = localGetItem('lm:recentJobs');
          const existing: string[] = raw ? JSON.parse(raw) : [];
          const next = [jobId, ...existing.filter((id) => id !== jobId)].slice(
            0,
            20
          );
          localSetItem('lm:recentJobs', JSON.stringify(next));
          window.dispatchEvent(new Event('lm:jobsChange'));
        }
      } catch {
        // ignore
      }

      setStatus({ message: 'Scan started. Processing...', type: 'info' });

      // Clear any existing poll
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }

      // Polling with ref tracking
      pollRef.current = setInterval(async () => {
        try {
          const job = await api.getJobStatus(jobId);
          if (job.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setStatus({ message: 'Scan Complete!', type: 'success' });
            setTimeout(() => {
              setOpen(false);
              setStatus(null);
            }, 2000);
            // Refresh results
            setSearchQuery(query);
          } else if (job.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setStatus({ message: `Failed: ${job.message}`, type: 'error' });
          } else {
            setStatus({
              message: job.message || 'Processing...',
              type: 'info',
            });
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setStatus({ message: 'Error tracking job', type: 'error' });
        }
      }, 1000);
    } catch {
      setStatus({ message: 'Failed to start scan', type: 'error' });
    }
  }, [query, setOpen, setSearchQuery, setStatus]);

  // Get system commands - use callback to stabilize reference
  // use handleScan directly as it is already memoized via useCallback
  const systemCommands = useMemo(
    () => [
      {
        id: 'open-library',
        name: 'Go to Library',
        icon: Search,
        action: () => {
          navigate('/');
          setOpen(false);
        },
      },
      {
        id: 'open-search',
        name: 'Go to Search',
        icon: Search,
        action: () => {
          navigate('/search');
          setOpen(false);
        },
      },
      {
        id: 'open-saved',
        name: 'Go to Saved Searches',
        icon: Search,
        action: () => {
          navigate('/saved-searches');
          setOpen(false);
        },
      },
      {
        id: 'open-tasks',
        name: 'Go to Jobs (background tasks)',
        icon: Zap,
        action: () => {
          navigate('/jobs');
          setOpen(false);
        },
      },
      {
        id: 'scan',
        name: 'Scan Library',
        icon: Zap,
        action: handleScan,
      },
      {
        id: 'toggle-theme',
        name: 'Toggle Dark/Light Mode',
        icon: Moon,
        action: () => {
          document.documentElement.classList.toggle('dark');
          setOpen(false);
        },
      },
    ],
    [handleScan, navigate, setOpen]
  );

  // Toggle with Cmd+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, [setOpen]);

  // Update search query only when user is actively searching in spotlight
  useEffect(() => {
    if (open && query.length > 0) {
      setSearchQuery(query);
    }
  }, [query, open, setSearchQuery]);

  return (
    <AnimatePresence>
      {open && (
        <div className='fixed inset-0 z-[100] flex items-start justify-center pt-[20vh] px-4'>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className='absolute inset-0 bg-background/80 backdrop-blur-sm'
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className={`relative w-full max-w-2xl ${glass.surface} rounded-xl shadow-2xl overflow-hidden`}
          >
            <Command className='w-full bg-transparent'>
              <div
                className='flex items-center border-b border-white/10 px-4'
                cmdk-input-wrapper=''
              >
                <Search className='w-5 h-5 text-muted-foreground mr-3' />
                <Command.Input
                  value={query}
                  onValueChange={setQuery}
                  placeholder="Search photos... try 'filename:sunset' or 'size:>5MB'"
                  className='w-full h-14 bg-transparent outline-none text-lg placeholder:text-muted-foreground/50'
                />
                {loading && (
                  <div className='animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full' />
                )}
                <div className='text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5 ml-2'>
                  ESC
                </div>
              </div>

              {/* Search Syntax Hints */}
              {!query && (
                <div className='px-4 py-2 border-b border-border bg-muted/30'>
                  <p className='text-xs text-muted-foreground mb-1.5 font-medium'>
                    Search Shortcuts:
                  </p>
                  <div className='flex flex-wrap gap-1.5'>
                    {[
                      { label: 'filename:', example: 'sunset' },
                      { label: 'size:', example: '>5MB' },
                      { label: 'date:', example: '2024' },
                      { label: 'camera:', example: 'Canon' },
                      { label: 'width:', example: '>1920' },
                    ].map((hint) => (
                      <button
                        key={hint.label}
                        onClick={() => setQuery(hint.label)}
                        className='px-2 py-0.5 text-xs bg-background border border-border rounded-md hover:bg-accent transition-colors font-mono'
                      >
                        <span className='text-primary'>{hint.label}</span>
                        <span className='text-muted-foreground'>
                          {hint.example}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {status && (
                <div
                  className={`px-4 py-2 text-sm border-b border-border flex items-center ${
                    status.type === 'error'
                      ? 'text-destructive bg-destructive/10'
                      : status.type === 'success'
                      ? 'text-green-500 bg-green-500/10'
                      : 'text-muted-foreground bg-muted/50'
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full mr-2 ${
                      status.type === 'error'
                        ? 'bg-destructive'
                        : status.type === 'success'
                        ? 'bg-green-500'
                        : 'animate-pulse bg-blue-500'
                    }`}
                  />
                  {status.message}
                </div>
              )}

              <Command.List className='max-h-[60vh] overflow-y-auto p-2 scrollbar-hide'>
                <Command.Empty className='py-6 text-center text-sm text-muted-foreground'>
                  No results found.
                </Command.Empty>

                {/* System Commands Group */}
                {!query && (
                  <Command.Group heading='Suggestions' className='mb-2'>
                    {/* eslint-disable-next-line react-hooks/refs */}
                    {systemCommands.map((cmd) => (
                      <Command.Item
                        key={cmd.id}
                        onSelect={cmd.action}
                        className='flex items-center px-2 py-2 rounded-lg cursor-pointer hover:bg-accent hover:text-accent-foreground aria-selected:bg-accent aria-selected:text-accent-foreground'
                      >
                        <cmd.icon className='w-4 h-4 mr-2' />
                        <span>{cmd.name}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {/* Photo Results Group */}
                {results.length > 0 && (
                  <Command.Group heading='Photos'>
                    {results.map((photo) => (
                      <Command.Item
                        key={photo.path}
                        onSelect={() => {
                          console.log('Selected:', photo.filename);
                          if (onPhotoSelect) {
                            onPhotoSelect(photo);
                          }
                          setOpen(false);
                        }}
                        className='flex items-center px-2 py-2 rounded-lg cursor-pointer hover:bg-accent hover:text-accent-foreground aria-selected:bg-accent aria-selected:text-accent-foreground'
                      >
                        <div className='w-8 h-8 rounded bg-secondary mr-3 overflow-hidden flex-shrink-0'>
                          <SecureLazyImage
                            path={photo.path}
                            size={120}
                            alt={photo.filename}
                            className='w-8 h-8'
                            showBadge={false}
                          />
                        </div>
                        <div className='flex flex-col overflow-hidden'>
                          <span className='truncate text-sm font-medium'>
                            {photo.filename}
                          </span>
                          <span className='truncate text-[10px] text-muted-foreground'>
                            {photo.path}
                          </span>
                        </div>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}
              </Command.List>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
