/**
 * Native-capability seam. Callers never ask "am I in Tauri"; they ask for the
 * capability and get the best available implementation. Today only folder
 * picking is native; reveal/launch go through the backend on both shells
 * because the server runs on the same machine as the files. When Tauri takes
 * those over (shell/opener plugins), only this file changes.
 */
import { apiFetch } from '@/api';
import { shell } from './detect';

/** Native directory picker. `null` outside Tauri, on cancel, or on failure. */
export async function pickFolder(): Promise<string | null> {
  if (shell !== 'tauri') return null;
  try {
    const dialog = await import('@tauri-apps/plugin-dialog');
    const selected = await dialog.open({
      directory: true,
      multiple: false,
      title: 'Choose a folder',
    });
    return typeof selected === 'string' ? selected : null;
  } catch (err) {
    console.error('[platform.pickFolder] dialog failed', err);
    return null;
  }
}

/** Show the file in the OS file manager (Finder/Explorer). */
export async function revealInFileManager(path: string): Promise<boolean> {
  const response = await apiFetch('/api/actions/open-location', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  return response.ok;
}

/**
 * Open the file with an installed application the server knows about.
 * Resolves to the server's result payload (e.g. `appName`), or `null` on failure.
 */
export async function launchApp(
  appId: string,
  filePath: string
): Promise<Record<string, unknown> | null> {
  const response = await apiFetch('/api/actions/launch-app', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ appId, filePath }),
  });
  if (!response.ok) return null;
  return (await response.json()) as Record<string, unknown>;
}

/**
 * Open a URL outside the app. In the Tauri webview `window.open` is the
 * stock behaviour until the opener plugin lands (Phase 4).
 */
export function openExternal(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer');
}
