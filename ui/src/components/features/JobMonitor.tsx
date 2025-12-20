/**
 * Job Monitor Component
 *
 * Displays active jobs and their status with real-time updates
 */

import { useEffect, useMemo, useState } from 'react';
import { Clock, RefreshCw, Trash2, X } from 'lucide-react';
import { api, type Job } from '../../api';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../../utils/storage';

const JobMonitor = () => {
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [jobsById, setJobsById] = useState<Record<string, Job | null>>({});
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [manualId, setManualId] = useState('');

  const readRecentJobIds = () => {
    try {
      if (!isLocalStorageAvailable()) {
        setJobIds([]);
        return;
      }
      const raw = localGetItem('lm:recentJobs');
      const list: string[] = raw ? JSON.parse(raw) : [];
      setJobIds(Array.isArray(list) ? list : []);
    } catch {
      setJobIds([]);
    }
  };

  const writeRecentJobIds = (next: string[]) => {
    setJobIds(next);
    try {
      if (isLocalStorageAvailable()) {
        localSetItem('lm:recentJobs', JSON.stringify(next));
        window.dispatchEvent(new Event('lm:jobsChange'));
      }
    } catch {
      // ignore
    }
  };

  const refreshOne = async (jobId: string) => {
    setLoadingIds((prev) => new Set(prev).add(jobId));
    try {
      const job = await api.getJobStatus(jobId);
      setJobsById((prev) => ({ ...prev, [jobId]: job }));
    } catch {
      setJobsById((prev) => ({ ...prev, [jobId]: null }));
    } finally {
      setLoadingIds((prev) => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
    }
  };

  const refreshAll = async () => {
    await Promise.all(jobIds.map((id) => refreshOne(id)));
  };

  useEffect(() => {
    readRecentJobIds();
    const onJobsChange = () => readRecentJobIds();
    window.addEventListener('lm:jobsChange', onJobsChange as EventListener);
    return () =>
      window.removeEventListener(
        'lm:jobsChange',
        onJobsChange as EventListener
      );
  }, []);

  useEffect(() => {
    if (jobIds.length === 0) return;
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobIds.join('|')]);

  useEffect(() => {
    if (!autoRefresh || jobIds.length === 0) return;
    const interval = setInterval(() => refreshAll(), 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, jobIds.join('|')]);

  const addManualId = () => {
    const trimmed = manualId.trim();
    if (!trimmed) return;
    writeRecentJobIds(
      [trimmed, ...jobIds.filter((id) => id !== trimmed)].slice(0, 20)
    );
    setManualId('');
  };

  const statusBadge = useMemo(() => {
    return (status?: string) => {
      switch (status) {
        case 'completed':
          return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20';
        case 'failed':
          return 'bg-red-500/15 text-red-300 border-red-500/20';
        case 'processing':
          return 'bg-sky-500/15 text-sky-300 border-sky-500/20';
        case 'pending':
          return 'bg-amber-500/15 text-amber-300 border-amber-500/20';
        case 'cancelled':
          return 'bg-white/10 text-white/70 border-white/10';
        default:
          return 'bg-white/10 text-white/70 border-white/10';
      }
    };
  }, []);

  return (
    <div className='mx-auto w-full max-w-6xl px-1 sm:px-0'>
      <div className='mb-6'>
        <h1 className='text-2xl font-semibold tracking-tight text-foreground'>
          Jobs
        </h1>
        <p className='text-sm text-muted-foreground'>
          Background work (indexing, analysis, and scans) that runs
          asynchronously.
        </p>
      </div>

      <div className='glass-surface rounded-2xl p-4 sm:p-6 mb-4'>
        <div className='text-sm font-medium text-foreground mb-2'>
          What is a “job”?
        </div>
        <ul className='text-sm text-muted-foreground space-y-1'>
          <li>
            Created when you run actions like{' '}
            <span className='text-foreground'>Spotlight → Scan Library</span>.
          </li>
          <li>
            Tracks progress for long-running steps (metadata extraction,
            embeddings, clustering).
          </li>
          <li>
            Stored locally in{' '}
            <span className='text-foreground'>Recent Jobs</span> so you can
            revisit status later.
          </li>
        </ul>
      </div>

      <div className='glass-surface rounded-2xl p-4 sm:p-6 space-y-4'>
        {/* Controls row - stacks on mobile */}
        <div className='flex flex-col sm:flex-row sm:items-center gap-3'>
          <div className='flex items-center gap-2 flex-wrap'>
            <button
              onClick={() => refreshAll()}
              className='btn-glass btn-glass--muted text-xs px-3 py-2 min-h-[44px]'
              title='Refresh all'
              aria-label='Refresh all jobs'
            >
              <RefreshCw size={14} />
              Refresh
            </button>

            <button
              onClick={() => writeRecentJobIds([])}
              className='btn-glass btn-glass--danger text-xs px-3 py-2 min-h-[44px]'
              title='Clear recent jobs'
              aria-label='Clear all recent jobs'
            >
              <Trash2 size={14} />
              Clear
            </button>
          </div>

          <div className='sm:ml-auto flex items-center gap-2'>
            <label className='flex items-center gap-2 text-xs text-muted-foreground cursor-pointer min-h-[44px]'>
              <input
                type='checkbox'
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className='w-4 h-4'
              />
              Auto-refresh
            </label>
          </div>
        </div>

        {/* Job ID input - responsive width */}
        <div className='flex flex-col sm:flex-row items-stretch sm:items-center gap-2'>
          <input
            value={manualId}
            onChange={(e) => setManualId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addManualId()}
            placeholder='Paste a job ID…'
            className='flex-1 min-w-0 sm:min-w-[240px] glass-surface rounded-full px-4 py-3 text-sm bg-transparent outline-none focus:ring-2 focus:ring-primary/30'
            aria-label='Job ID input'
          />
          <button
            onClick={addManualId}
            className='btn-glass btn-glass--primary text-sm px-4 py-3 min-h-[44px]'
            aria-label='Track job'
          >
            Track
          </button>
        </div>

        {jobIds.length === 0 ? (
          <div className='text-center text-muted-foreground py-10'>
            <Clock className='mx-auto mb-3 opacity-60' size={22} />
            <div className='text-sm'>No tracked jobs yet.</div>
            <div className='text-xs opacity-70 mt-1'>
              Start a scan from Spotlight (⌘/Ctrl+K) and it will appear here.
            </div>
          </div>
        ) : (
          <div className='grid grid-cols-1 gap-3'>
            {jobIds.map((id) => {
              const job = jobsById[id];
              const isLoading = loadingIds.has(id);
              return (
                <div key={id} className='glass-surface rounded-2xl p-4'>
                  <div className='flex items-start gap-3'>
                    <div className='min-w-0 flex-1'>
                      <div className='flex items-center gap-2'>
                        <div className='text-sm font-semibold text-foreground truncate'>
                          {job?.type ?? 'Unknown job'}
                        </div>
                        <span
                          className={`text-[11px] px-2 py-0.5 rounded-full border ${statusBadge(
                            job?.status
                          )}`}
                        >
                          {isLoading ? 'loading' : job?.status ?? 'unknown'}
                        </span>
                      </div>
                      <div className='text-xs text-muted-foreground mt-1 break-all'>
                        {id}
                      </div>

                      {job?.message && (
                        <div className='text-xs text-muted-foreground mt-2'>
                          {job.message}
                        </div>
                      )}

                      {typeof job?.progress === 'number' && (
                        <div className='mt-3'>
                          <div className='h-1.5 w-full bg-white/10 rounded-full overflow-hidden'>
                            <div
                              className={`h-full bg-sky-400/70 score-fill-${Math.round(
                                Math.round(
                                  Math.max(0, Math.min(100, job.progress))
                                ) / 10
                              ) * 10
                                }`}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action buttons - larger touch targets */}
                    <div className='flex items-center gap-2 flex-shrink-0'>
                      <button
                        onClick={() => refreshOne(id)}
                        className='btn-glass btn-glass--muted w-10 h-10 sm:w-9 sm:h-9 p-0 justify-center min-w-[44px] min-h-[44px]'
                        title='Refresh job status'
                        aria-label='Refresh job status'
                      >
                        <RefreshCw size={16} />
                      </button>
                      <button
                        onClick={() =>
                          writeRecentJobIds(jobIds.filter((x) => x !== id))
                        }
                        className='btn-glass btn-glass--danger w-10 h-10 sm:w-9 sm:h-9 p-0 justify-center min-w-[44px] min-h-[44px]'
                        title='Stop tracking this job'
                        aria-label='Stop tracking job'
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default JobMonitor;
