import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  API_BASE,
  api,
  apiFetch,
  apiUrl,
  mediaUrl,
  resolveApiBase,
  setUnauthorizedHandler,
} from '../api';
import {
  assetBaseForTarget,
  assertApiBaseUsable,
  assertTargetConsistency,
  targetForMode,
} from '../platform/target';

describe('resolveApiBase', () => {
  it('defaults to the loopback desktop backend when unset', () => {
    expect(resolveApiBase({})).toBe('http://127.0.0.1:8000');
  });

  it('treats an explicitly empty value as same-origin (web companion build)', () => {
    expect(resolveApiBase({ VITE_API_URL: '' })).toBe('');
  });

  it('strips trailing slashes from a configured origin', () => {
    expect(resolveApiBase({ VITE_API_URL: 'http://nas.local:8000/' })).toBe(
      'http://nas.local:8000'
    );
  });

  it('derives same-origin from the companion build mode, with no env file', () => {
    expect(resolveApiBase({ MODE: 'web' })).toBe('');
  });

  it('ignores an env override in the companion build — the API is its own origin', () => {
    expect(resolveApiBase({ MODE: 'web', VITE_API_URL: 'http://127.0.0.1:8000' })).toBe('');
  });

  it('keeps the desktop build absolute even when an env file is present', () => {
    expect(resolveApiBase({ MODE: 'production' })).toBe('http://127.0.0.1:8000');
  });

  it('lets the dev server be pointed at another backend', () => {
    expect(resolveApiBase({ MODE: 'development', VITE_API_URL: 'http://nas.local:9000' })).toBe(
      'http://nas.local:9000'
    );
  });
});

describe('build target topology', () => {
  it('maps the vite mode to a target', () => {
    expect(targetForMode('web')).toBe('companion');
    expect(targetForMode('production')).toBe('desktop');
    expect(targetForMode('development')).toBe('desktop');
  });

  it('serves the companion bundle from the API mount point', () => {
    expect(assetBaseForTarget('companion')).toBe('/app/');
    expect(assetBaseForTarget('desktop')).toBe('/');
  });

  it('rejects a hand-edited asset base that disagrees with the target', () => {
    expect(() => assertTargetConsistency('companion', '/app/')).not.toThrow();
    expect(() => assertTargetConsistency('companion', '/')).toThrow(/expects asset base/);
    expect(() => assertTargetConsistency('desktop', '/app/')).toThrow(/expects asset base/);
  });

  it('rejects an API base that contradicts the target topology', () => {
    // Same-origin is only valid when the SPA is served by the API.
    expect(() => assertApiBaseUsable('companion', '')).not.toThrow();
    expect(() => assertApiBaseUsable('companion', 'http://127.0.0.1:8000')).toThrow(
      /must be same-origin/,
    );
    // A separate origin needs an absolute base.
    expect(() => assertApiBaseUsable('desktop', 'http://127.0.0.1:8000')).not.toThrow();
    expect(() => assertApiBaseUsable('desktop', '')).toThrow(/needs an absolute API base/);
  });
});

describe('apiUrl', () => {
  it('prefixes paths with the resolved base and tolerates a missing slash', () => {
    expect(apiUrl('/api/x')).toBe(`${API_BASE}/api/x`);
    expect(apiUrl('api/x')).toBe(`${API_BASE}/api/x`);
  });
});

describe('apiFetch', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    api.setAuthToken(null);
    api.setIssuerKey(null);
    setUnauthorizedHandler(null);
  });

  it('routes through the resolved base and stamps identity', async () => {
    await apiFetch('/api/faces/stats');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${API_BASE}/api/faces/stats`);
    expect((init.headers as Headers).get('X-User-ID')).toBe('default_user');
    expect(init.credentials).toBe('include');
  });

  it('carries the same auth headers the axios client was given', async () => {
    api.setAuthToken('tok');
    api.setIssuerKey('key');
    await apiFetch('/api/x');
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer tok');
    expect(headers.get('x-api-key')).toBe('key');
  });

  it('does not clobber headers the caller set explicitly', async () => {
    await apiFetch('/api/x', { headers: { 'Content-Type': 'text/plain' } });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Headers).get('Content-Type')).toBe('text/plain');
  });

  it('notifies the shell on 401 so the web companion can route to pairing', async () => {
    fetchMock.mockResolvedValue(new Response('', { status: 401 }));
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    await apiFetch('/api/x');
    expect(handler).toHaveBeenCalledTimes(1);
  });
});

describe('mediaUrl', () => {
  it('builds every media URL on the same base with identity attached', () => {
    expect(mediaUrl.thumbnail('/p/a.jpg', 256)).toBe(
      `${API_BASE}/image/thumbnail?path=%2Fp%2Fa.jpg&size=256&user_id=default_user`
    );
    expect(mediaUrl.video('/p/v.mp4')).toBe(
      `${API_BASE}/video?path=%2Fp%2Fv.mp4&user_id=default_user`
    );
    expect(mediaUrl.file('/p/a.jpg', { download: true })).toBe(
      `${API_BASE}/file?path=%2Fp%2Fa.jpg&download=true&user_id=default_user`
    );
    expect(mediaUrl.faceCrop(42)).toBe(
      `${API_BASE}/api/faces/crop/42?size=150&user_id=default_user`
    );
  });

  it('keeps the legacy api.* URL helpers as thin wrappers', () => {
    expect(api.getImageUrl('/p/a.jpg', 96)).toBe(mediaUrl.thumbnail('/p/a.jpg', 96));
    expect(api.getVideoUrl('/p/v.mp4')).toBe(mediaUrl.video('/p/v.mp4'));
    expect(api.getFileUrl('/p/a.jpg')).toBe(mediaUrl.file('/p/a.jpg'));
  });
});
