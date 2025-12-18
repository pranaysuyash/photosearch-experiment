import { useCallback, useEffect, useMemo, useState } from 'react';
import { Cloud, HardDrive, RefreshCw, Trash2, Plus } from 'lucide-react';
import { api, type Source } from '../../api';
import { ConnectSourceModal } from './ConnectSourceModal';
import { isLocalStorageAvailable, localGetItem, localSetItem } from '../../utils/storage';

function badgeClass(status: Source['status']) {
  switch (status) {
    case 'connected':
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20';
    case 'auth_required':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/20';
    case 'pending':
      return 'bg-sky-500/15 text-sky-300 border-sky-500/20';
    case 'error':
      return 'bg-red-500/15 text-red-300 border-red-500/20';
    default:
      return 'bg-white/10 text-white/70 border-white/10';
  }
}

function typeLabel(type: Source['type']) {
  if (type === 'local_folder') return 'Local folder';
  if (type === 'google_drive') return 'Google Drive';
  return 'S3-compatible';
}

export function SourcesPanel() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectOpen, setConnectOpen] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listSources();
      setSources(res.sources || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const hasAny = sources.length > 0;
  const localCount = useMemo(
    () => sources.filter((s) => s.type === 'local_folder').length,
    [sources]
  );

  const removeSource = async (id: string) => {
    if (!window.confirm('Remove this source? This does not delete your originals.')) return;
    setLoading(true);
    setError(null);
    try {
      await api.deleteSource(id);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const rescanSource = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.rescanSource(id, false);
      if (res?.job_id) {
        try {
          if (isLocalStorageAvailable()) {
            const raw = localGetItem('lm:recentJobs');
            const existing: string[] = raw ? JSON.parse(raw) : [];
            const next = [res.job_id, ...existing.filter((j) => j !== res.job_id)].slice(0, 20);
            localSetItem('lm:recentJobs', JSON.stringify(next));
            window.dispatchEvent(new Event('lm:jobsChange'));
          }
        } catch {
          // ignore
        }
      }
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const syncSource = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.syncSource(id);
      if (res?.job_id) {
        try {
          if (isLocalStorageAvailable()) {
            const raw = localGetItem('lm:recentJobs');
            const existing: string[] = raw ? JSON.parse(raw) : [];
            const next = [res.job_id, ...existing.filter((j) => j !== res.job_id)].slice(0, 20);
            localSetItem('lm:recentJobs', JSON.stringify(next));
            window.dispatchEvent(new Event('lm:jobsChange'));
          }
        } catch {
          // ignore
        }
      }
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-foreground">Sources</div>
          <div className="text-xs text-muted-foreground">
            Connected libraries ({localCount} local{sources.length - localCount ? `, ${sources.length - localCount} cloud` : ''})
          </div>
        </div>
        <button
          className="btn-glass btn-glass--primary text-sm px-4 py-2"
          onClick={() => setConnectOpen(true)}
          disabled={loading}
        >
          <Plus size={14} />
          Connect source
        </button>
      </div>

      {error && (
        <div className="text-sm text-destructive glass-surface rounded-xl p-3 border border-white/10">
          {error}
        </div>
      )}

      {!hasAny && !loading && (
        <div className="glass-surface rounded-2xl p-6 text-sm text-muted-foreground">
          No sources connected yet. Connect Google Drive, an S3 bucket, or add a local folder (desktop app).
        </div>
      )}

      {sources.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {sources.map((s) => (
            <div key={s.id} className="glass-surface rounded-2xl p-4 border border-white/10">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 text-muted-foreground">
                  {s.type === 'local_folder' ? <HardDrive size={18} /> : <Cloud size={18} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <div className="text-sm font-semibold text-foreground truncate">{s.name}</div>
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${badgeClass(s.status)}`}>
                      {s.status}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{typeLabel(s.type)}</div>
                  {s.last_error && (
                    <div className="text-xs text-destructive mt-2 break-words">{s.last_error}</div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {s.type === 'local_folder' && (
                    <button
                      className="btn-glass btn-glass--muted text-xs px-3 py-2"
                      onClick={() => rescanSource(s.id)}
                      disabled={loading}
                      title="Re-scan"
                    >
                      <RefreshCw size={14} />
                      Re-scan
                    </button>
                  )}
                  {s.type !== 'local_folder' && (
                    <button
                      className="btn-glass btn-glass--muted text-xs px-3 py-2"
                      onClick={() => syncSource(s.id)}
                      disabled={loading}
                      title="Sync"
                    >
                      <RefreshCw size={14} />
                      Sync
                    </button>
                  )}
                  <button
                    className="btn-glass btn-glass--danger text-xs px-3 py-2"
                    onClick={() => removeSource(s.id)}
                    disabled={loading}
                    title="Remove source"
                  >
                    <Trash2 size={14} />
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConnectSourceModal open={connectOpen} onClose={() => setConnectOpen(false)} onConnected={refresh} />
    </div>
  );
}
