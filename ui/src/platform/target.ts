/**
 * Build-target topology — the single source of truth for two facts that must
 * never drift apart:
 *
 *   1. where this bundle's assets are served from (`assetBaseForTarget`)
 *   2. where this bundle finds its backend (`apiBaseForTarget`)
 *
 * The facts come from the deployment topology, not from the machine:
 *
 *   desktop   — the SPA runs inside a Tauri webview (origin `tauri://localhost`)
 *               while the backend is a *separate* origin on loopback, so API
 *               calls need an absolute base.
 *   companion — FastAPI serves the SPA itself at `/app/`, so the API is the
 *               *same* origin and every call is same-origin.
 *
 * A Vite mode is the signal for the target, so the target is derived from the
 * mode and both bases follow from it. Nothing here is machine-local: the same
 * commit must produce the same bundle everywhere.
 */

/** The vite mode that builds the companion bundle served by FastAPI. */
export const COMPANION_MODE = 'web';

export type BuildTarget = 'desktop' | 'companion';

/** The colocated backend the desktop app talks to by default. */
export const DESKTOP_API_BASE = 'http://127.0.0.1:8000';

export function targetForMode(mode: string): BuildTarget {
  return mode === COMPANION_MODE ? 'companion' : 'desktop';
}

/** Empty string means "same origin" — the SPA and the API are one origin. */
export function apiBaseForTarget(target: BuildTarget): string {
  return target === 'companion' ? '' : DESKTOP_API_BASE;
}

/** Where the built assets are served from (must match the API's mount point). */
export function assetBaseForTarget(target: BuildTarget): string {
  return target === 'companion' ? '/app/' : '/';
}

/**
 * The API base this bundle will actually use.
 *
 * The companion target is fixed (same origin, every device). The desktop
 * target may be pointed at another backend by `VITE_API_URL` — that is the
 * escape hatch for a custom backend port, a NAS, or a tunnel.
 */
export function effectiveApiBase(
  target: BuildTarget,
  env: { VITE_API_URL?: string } = {},
): string {
  if (target === 'companion') return apiBaseForTarget(target);
  const configured = env.VITE_API_URL;
  if (configured === undefined) return apiBaseForTarget(target);
  return configured.replace(/\/+$/, '');
}

/**
 * Build-time invariant: the base must match the target's topology.
 *
 *   companion — the SPA is served BY the API, so the base is same-origin.
 *   desktop   — the SPA is a separate origin, so the base must be absolute.
 *
 * A same-origin desktop bundle is silently dead (every call goes to
 * `tauri://localhost/api/…`); an absolute companion bundle points every
 * device at its own localhost. Both must fail the build, not the device.
 */
export function assertApiBaseUsable(target: BuildTarget, apiBase: string): void {
  if (target === 'companion') {
    if (apiBase === '') return;
    throw new Error(
      `[photosearch] the companion bundle must be same-origin, but resolved "${apiBase}". ` +
        'FastAPI serves the SPA at /app/ — API calls must not carry a host.',
    );
  }
  if (/^https?:\/\//.test(apiBase)) return;
  throw new Error(
    `[photosearch] the desktop bundle needs an absolute API base, but resolved "${apiBase}". ` +
      'A same-origin base only works when the SPA is served by the API (the companion target). ' +
      'Set VITE_API_URL to an absolute origin, or leave it unset to use http://127.0.0.1:8000.',
  );
}

/**
 * Build-time invariant: the asset base and the API base are two faces of one
 * target, so a hand-edited asset base in vite.config.ts is a configuration
 * error, not a variation. Fail the build instead of shipping a bundle that
 * loads its JS from one prefix and calls an API at another.
 */
export function assertTargetConsistency(target: BuildTarget, assetBase: string): void {
  const expected = assetBaseForTarget(target);
  if (assetBase === expected) return;
  throw new Error(
    `[photosearch] build target "${target}" expects asset base "${expected}" but the build ` +
      `resolved "${assetBase}". The asset base and the API base are derived from the same ` +
      'target — change src/platform/target.ts, not vite.config.ts.',
  );
}
