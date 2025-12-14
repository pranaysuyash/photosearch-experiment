/**
 * Settings Page
 *
 * Application settings and configuration
 */

import { useState } from 'react';
import {
  isLocalStorageAvailable,
  localGetItem,
  localSetItem,
} from '../utils/storage';
import { api } from '../api';

const Settings = () => {
  const [focusMode, setFocusMode] = useState(() => {
    if (!isLocalStorageAvailable()) return false;
    return localGetItem('lm:minimalMode') === '1';
  });
  const [folders, setFolders] = useState<string[]>(() => {
    try {
      if (!isLocalStorageAvailable()) return [];
      const raw = localGetItem('lm:libraryFolders');
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed)
        ? parsed.filter((v) => typeof v === 'string')
        : [];
    } catch {
      return [];
    }
  });
  const [folderInput, setFolderInput] = useState('');
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [scanBusy, setScanBusy] = useState(false);

  const toggleFocusMode = () => {
    const next = !focusMode;
    setFocusMode(next);
    if (isLocalStorageAvailable()) {
      localSetItem('lm:minimalMode', next ? '1' : '0');
      window.dispatchEvent(new Event('lm:prefChange'));
    }
  };

  const writeFolders = (next: string[]) => {
    setFolders(next);
    try {
      if (isLocalStorageAvailable()) {
        localSetItem('lm:libraryFolders', JSON.stringify(next));
      }
    } catch {
      // ignore
    }
  };

  const recordRecentJob = (jobId: string) => {
    try {
      if (!isLocalStorageAvailable()) return;
      const raw = localGetItem('lm:recentJobs');
      const existing: string[] = raw ? JSON.parse(raw) : [];
      const next = [jobId, ...existing.filter((id) => id !== jobId)].slice(
        0,
        20
      );
      localSetItem('lm:recentJobs', JSON.stringify(next));
      window.dispatchEvent(new Event('lm:jobsChange'));
    } catch {
      // ignore
    }
  };

  const scanFolder = async (path: string) => {
    const trimmed = path.trim();
    if (!trimmed) return;
    setScanBusy(true);
    setScanMessage('Starting scan…');
    try {
      const res = await api.scan(trimmed, true);
      if (res?.job_id) recordRecentJob(res.job_id);
      setScanMessage('Scan started in background. Check Jobs for progress.');
    } catch (e) {
      setScanMessage(`Scan failed: ${String(e)}`);
    } finally {
      setScanBusy(false);
    }
  };

  const addFolder = async () => {
    const trimmed = folderInput.trim();
    if (!trimmed) return;
    const next = [trimmed, ...folders.filter((f) => f !== trimmed)].slice(
      0,
      20
    );
    writeFolders(next);
    setFolderInput('');
    await scanFolder(trimmed);
  };

  return (
    <div className='mx-auto w-full max-w-3xl'>
      <div className='mb-6'>
        <h1 className='text-2xl font-semibold tracking-tight text-foreground'>
          Settings
        </h1>
        <p className='text-sm text-muted-foreground'>
          Tune the UI to match how you browse.
        </p>
      </div>

      <div className='glass-surface rounded-2xl p-5 sm:p-7 space-y-6'>
        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>UI</h2>

          <div className='flex items-center justify-between gap-4 glass-surface rounded-xl px-4 py-3'>
            <div className='min-w-0'>
              <div className='text-sm font-semibold text-foreground'>
                Focus mode
              </div>
              <div className='text-xs text-muted-foreground'>
                Hide the floating command bar and extra chrome for a pure
                gallery view.
              </div>
            </div>

            <button
              onClick={toggleFocusMode}
              className={`btn-glass ${
                focusMode ? 'btn-glass--primary' : 'btn-glass--muted'
              } text-xs px-3 py-2`}
            >
              {focusMode ? 'On' : 'Off'}
            </button>
          </div>
        </section>

        <section id='library' className='space-y-2 scroll-mt-24'>
          <h2 className='text-sm font-semibold text-foreground'>Library</h2>
          <div className='text-xs text-muted-foreground'>
            Add folders to scan/index. Scheduling and reindex policies are
            planned, but scans work now.
          </div>

          <div className='glass-surface rounded-xl px-4 py-3 space-y-3'>
            <div className='flex flex-wrap items-center gap-2'>
              <input
                value={folderInput}
                onChange={(e) => setFolderInput(e.target.value)}
                placeholder='Add a folder path…'
                className='flex-1 min-w-[240px] glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none'
              />
              <button
                onClick={addFolder}
                disabled={scanBusy || folderInput.trim().length === 0}
                className='btn-glass btn-glass--primary text-sm px-4 py-2 disabled:opacity-50'
              >
                Add & scan
              </button>
            </div>

            {scanMessage && (
              <div className='text-xs text-muted-foreground'>{scanMessage}</div>
            )}

            {folders.length === 0 ? (
              <div className='text-sm text-muted-foreground'>
                No folders added yet.
              </div>
            ) : (
              <div className='space-y-2'>
                {folders.map((folder) => (
                  <div
                    key={folder}
                    className='flex flex-wrap items-center justify-between gap-2 rounded-lg bg-white/5 border border-white/10 px-3 py-2'
                  >
                    <div
                      className='text-sm text-foreground truncate'
                      title={folder}
                    >
                      {folder}
                    </div>
                    <div className='flex items-center gap-2'>
                      <button
                        onClick={() => scanFolder(folder)}
                        disabled={scanBusy}
                        className='btn-glass btn-glass--muted text-xs px-3 py-2 disabled:opacity-50'
                      >
                        Re-scan
                      </button>
                      <button
                        onClick={() =>
                          writeFolders(folders.filter((f) => f !== folder))
                        }
                        className='btn-glass btn-glass--danger text-xs px-3 py-2'
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className='space-y-2'>
          <h2 className='text-sm font-semibold text-foreground'>About</h2>
          <div className='text-sm text-muted-foreground'>Living Museum</div>
        </section>
      </div>
    </div>
  );
};

export default Settings;
