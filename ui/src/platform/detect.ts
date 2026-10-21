/**
 * Platform detection — the single source of truth for "what are we running
 * in" (shell) and "what is the user holding" (form factor). These are
 * deliberately separate axes: a narrow desktop window is not a phone, and a
 * tablet in the web companion is not the Tauri shell.
 */
import { useEffect, useState } from 'react';
import { isTauri } from '@tauri-apps/api/core';

export type Shell = 'tauri' | 'browser';
export type FormFactor = 'desktop' | 'mobile';

/**
 * Tauri v2 always injects `__TAURI_INTERNALS__`; `window.__TAURI__` only
 * exists when `app.withGlobalTauri` is enabled, which this app does not do —
 * checking it reports "browser" inside the real desktop app.
 */
export function detectShell(win: object | undefined = globalThis.window): Shell {
  if (!win) return 'browser';
  try {
    if (isTauri()) return 'tauri';
  } catch {
    // @tauri-apps/api throws outside a Tauri webview in some bundlers
  }
  return '__TAURI_INTERNALS__' in win ? 'tauri' : 'browser';
}

export const shell: Shell = detectShell();
export const isDesktopApp = shell === 'tauri';

const NARROW_QUERY = '(max-width: 767px)';
const COARSE_POINTER_QUERY = '(pointer: coarse)';

export function detectFormFactor(
  win: (Window & typeof globalThis) | undefined = globalThis.window
): FormFactor {
  if (!win || typeof win.matchMedia !== 'function') return 'desktop';
  const narrow = win.matchMedia(NARROW_QUERY).matches;
  const coarse = win.matchMedia(COARSE_POINTER_QUERY).matches;
  return narrow || coarse ? 'mobile' : 'desktop';
}

/** Re-evaluates on viewport and pointer changes (rotation, window resize, docking). */
export function useFormFactor(): FormFactor {
  const [formFactor, setFormFactor] = useState<FormFactor>(detectFormFactor);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }
    const queries = [NARROW_QUERY, COARSE_POINTER_QUERY].map((q) =>
      window.matchMedia(q)
    );
    const update = () => setFormFactor(detectFormFactor());
    queries.forEach((q) => q.addEventListener('change', update));
    return () => queries.forEach((q) => q.removeEventListener('change', update));
  }, []);

  return formFactor;
}

export interface Platform {
  shell: Shell;
  isDesktopApp: boolean;
  formFactor: FormFactor;
  isMobile: boolean;
}

export function usePlatform(): Platform {
  const formFactor = useFormFactor();
  return { shell, isDesktopApp, formFactor, isMobile: formFactor === 'mobile' };
}
