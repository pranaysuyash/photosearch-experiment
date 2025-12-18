import { useEffect, useMemo, useRef, useState } from 'react';
import { X, HardDrive, Cloud, Database, KeyRound } from 'lucide-react';
import { api } from '../../api';
import { pickDirectory } from '../../utils/pickDirectory';
import { usePlatformDetect } from '../../hooks/usePlatformDetect';
import { isLocalStorageAvailable, localGetItem, localSetItem } from '../../utils/storage';

type Tab = 'local' | 'google_drive' | 's3';

export function ConnectSourceModal({
  open,
  onClose,
  onConnected,
  initialTab = 'local',
}: {
  open: boolean;
  onClose: () => void;
  onConnected?: () => void;
  initialTab?: Tab;
}) {
  const { isDesktopApp } = usePlatformDetect();
  const [tab, setTab] = useState<Tab>(initialTab);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Local folder state (no manual path entry)
  const [pickedPath, setPickedPath] = useState<string | null>(null);
  const [localName, setLocalName] = useState<string>('Local Folder');

  // S3 state
  const [s3Name, setS3Name] = useState('S3 Source');
  const [s3Endpoint, setS3Endpoint] = useState('');
  const [s3Region, setS3Region] = useState('auto');
  const [s3Bucket, setS3Bucket] = useState('');
  const [s3Prefix, setS3Prefix] = useState('');
  const [s3AccessKey, setS3AccessKey] = useState('');
  const [s3SecretKey, setS3SecretKey] = useState('');

  // Google Drive state
  const [gdName, setGdName] = useState('Google Drive');
  const [gdClientId, setGdClientId] = useState('');
  const [gdClientSecret, setGdClientSecret] = useState('');
  const popupRef = useRef<Window | null>(null);

  useEffect(() => {
    if (!open) return;
    setTab(initialTab);
    setBusy(false);
    setError(null);
    setPickedPath(null);
  }, [open, initialTab]);

  const recordRecentJob = (jobId: string) => {
    try {
      if (!isLocalStorageAvailable()) return;
      const raw = localGetItem('lm:recentJobs');
      const existing: string[] = raw ? JSON.parse(raw) : [];
      const next = [jobId, ...existing.filter((id) => id !== jobId)].slice(0, 20);
      localSetItem('lm:recentJobs', JSON.stringify(next));
      window.dispatchEvent(new Event('lm:jobsChange'));
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (!open) return;
    const onMsg = (ev: MessageEvent) => {
      if (!ev?.data || typeof ev.data !== 'object') return;
      if ((ev.data as any).type === 'lm:sourceConnected') {
        const jobId = (ev.data as any).jobId as string | undefined;
        if (jobId) recordRecentJob(jobId);
        try {
          popupRef.current?.close?.();
        } catch {
          // ignore
        }
        popupRef.current = null;
        onConnected?.();
        onClose();
      }
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, [onClose, onConnected, open]);

  const localHint = useMemo(() => {
    if (isDesktopApp) return 'Choose a folder from your machine (no path pasting).';
    return 'Local folders require the desktop app. Use cloud sources in the web build.';
  }, [isDesktopApp]);

  const chooseFolder = async () => {
    setError(null);
    const selected = await pickDirectory();
    if (!selected) {
      setError(
        isDesktopApp
          ? 'Folder picker is unavailable. Ensure the Tauri dialog plugin is enabled.'
          : 'Local folder picking is only available in the desktop app.'
      );
      return;
    }
    setPickedPath(selected);
    const base = selected.split(/[\\/]/).filter(Boolean).pop();
    if (base) setLocalName(base);
  };

  const connectLocal = async () => {
    if (!pickedPath) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.addLocalFolderSource(pickedPath, localName, false);
      if (res?.job_id) recordRecentJob(res.job_id);
      onConnected?.();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const connectS3 = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.addS3Source({
        name: s3Name.trim() || 'S3 Source',
        endpoint_url: s3Endpoint.trim(),
        region: s3Region.trim() || 'auto',
        bucket: s3Bucket.trim(),
        prefix: s3Prefix.trim() || undefined,
        access_key_id: s3AccessKey.trim(),
        secret_access_key: s3SecretKey,
      });
      if (res?.job_id) recordRecentJob(res.job_id);
      onConnected?.();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const connectGoogleDrive = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.addGoogleDriveSource({
        name: gdName.trim() || 'Google Drive',
        client_id: gdClientId.trim(),
        client_secret: gdClientSecret.trim(),
      });
      const w = window.open(res.auth_url, 'lm_google_drive_auth', 'popup,width=520,height=720');
      if (!w) {
        setError('Popup blocked. Allow popups to connect Google Drive.');
        return;
      }
      popupRef.current = w;
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      <div
        className="relative w-full max-w-2xl glass-surface glass-surface--strong rounded-2xl border border-white/10 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-foreground">Connect a source</div>
            <div className="text-xs text-muted-foreground">Local + cloud, one library.</div>
          </div>
          <button className="btn-glass btn-glass--muted w-9 h-9 p-0 justify-center" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 pt-4">
          <div className="flex flex-wrap gap-2">
            <button
              className={`btn-glass ${tab === 'local' ? 'btn-glass--primary' : 'btn-glass--muted'} text-xs px-3 py-2`}
              onClick={() => setTab('local')}
            >
              <HardDrive size={14} /> Local folder
            </button>
            <button
              className={`btn-glass ${tab === 'google_drive' ? 'btn-glass--primary' : 'btn-glass--muted'} text-xs px-3 py-2`}
              onClick={() => setTab('google_drive')}
            >
              <Cloud size={14} /> Google Drive
            </button>
            <button
              className={`btn-glass ${tab === 's3' ? 'btn-glass--primary' : 'btn-glass--muted'} text-xs px-3 py-2`}
              onClick={() => setTab('s3')}
            >
              <Database size={14} /> S3-compatible
            </button>
          </div>

          {error && (
            <div className="mt-4 text-sm text-destructive glass-surface rounded-xl p-3 border border-white/10">
              {error}
            </div>
          )}
        </div>

        <div className="px-5 pb-5 pt-4">
          {tab === 'local' && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">{localHint}</div>

              <div className="glass-surface rounded-xl p-4 border border-white/10 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    className="btn-glass btn-glass--primary text-sm px-4 py-2"
                    onClick={chooseFolder}
                    disabled={busy}
                  >
                    Choose folder…
                  </button>
                  {pickedPath && (
                    <span className="text-xs text-muted-foreground truncate" title={pickedPath}>
                      {pickedPath}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <label className="text-xs text-muted-foreground">Name</label>
                  <input
                    value={localName}
                    onChange={(e) => setLocalName(e.target.value)}
                    className="flex-1 min-w-[240px] glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    placeholder="Local Folder"
                    disabled={busy || !pickedPath}
                  />
                </div>

                <div className="flex items-center justify-end gap-2">
                  <button className="btn-glass btn-glass--muted text-sm px-4 py-2" onClick={onClose} disabled={busy}>
                    Cancel
                  </button>
                  <button
                    className="btn-glass btn-glass--primary text-sm px-4 py-2 disabled:opacity-50"
                    onClick={connectLocal}
                    disabled={busy || !pickedPath || !isDesktopApp}
                  >
                    {busy ? 'Connecting…' : 'Connect'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {tab === 's3' && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                Works with AWS S3 and S3-compatible providers (R2/B2/MinIO). We only store credentials server-side.
              </div>

              <div className="glass-surface rounded-xl p-4 border border-white/10 grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground">Name</label>
                  <input
                    value={s3Name}
                    onChange={(e) => setS3Name(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground">Endpoint URL</label>
                  <input
                    value={s3Endpoint}
                    onChange={(e) => setS3Endpoint(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    placeholder="https://<account>.r2.cloudflarestorage.com"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Region</label>
                  <input
                    value={s3Region}
                    onChange={(e) => setS3Region(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    placeholder="auto"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Bucket</label>
                  <input
                    value={s3Bucket}
                    onChange={(e) => setS3Bucket(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground">Prefix (optional)</label>
                  <input
                    value={s3Prefix}
                    onChange={(e) => setS3Prefix(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    placeholder="photos/"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Access Key ID</label>
                  <input
                    value={s3AccessKey}
                    onChange={(e) => setS3AccessKey(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Secret Access Key</label>
                  <input
                    value={s3SecretKey}
                    onChange={(e) => setS3SecretKey(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    type="password"
                  />
                </div>
                <div className="md:col-span-2 flex items-center justify-end gap-2">
                  <button className="btn-glass btn-glass--muted text-sm px-4 py-2" onClick={onClose} disabled={busy}>
                    Cancel
                  </button>
                  <button className="btn-glass btn-glass--primary text-sm px-4 py-2" onClick={connectS3} disabled={busy}>
                    {busy ? 'Connecting…' : 'Connect'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {tab === 'google_drive' && (
            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                Provide a Google OAuth client (Web application) and we’ll connect Drive via a browser authorization popup.
              </div>

              <div className="glass-surface rounded-xl p-4 border border-white/10 space-y-3">
                <div>
                  <label className="text-xs text-muted-foreground">Name</label>
                  <input
                    value={gdName}
                    onChange={(e) => setGdName(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Client ID</label>
                  <input
                    value={gdClientId}
                    onChange={(e) => setGdClientId(e.target.value)}
                    className="w-full glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                    placeholder="xxxxxxxxxxxx.apps.googleusercontent.com"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Client Secret</label>
                  <div className="flex items-center gap-2">
                    <KeyRound size={14} className="text-muted-foreground" aria-hidden="true" />
                    <input
                      value={gdClientSecret}
                      onChange={(e) => setGdClientSecret(e.target.value)}
                      className="flex-1 glass-surface rounded-full px-4 py-2 text-sm bg-transparent outline-none"
                      type="password"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2">
                  <button className="btn-glass btn-glass--muted text-sm px-4 py-2" onClick={onClose} disabled={busy}>
                    Cancel
                  </button>
                  <button
                    className="btn-glass btn-glass--primary text-sm px-4 py-2 disabled:opacity-50"
                    onClick={connectGoogleDrive}
                    disabled={busy || gdClientId.trim().length === 0 || gdClientSecret.trim().length === 0}
                  >
                    {busy ? 'Starting…' : 'Authorize…'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
