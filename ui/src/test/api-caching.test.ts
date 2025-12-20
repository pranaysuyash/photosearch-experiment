import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from '../api';

describe('getSignedImageUrl caching', () => {
  const testPath = 's3://demo-bucket/photo.jpg';

  beforeEach(() => {
    vi.restoreAllMocks();
    // reset internal caches if present
    (api as any)._tokenCache = (api as any)._tokenCache || new Map();
    (api as any)._signedUrlEnabledCache = null;
    (api as any)._signedUrlEnabledCacheExpires = 0;
  });

  afterEach(() => {
    (api as any)._tokenCache.clear();
  });

  test('falls back to path when signed URLs are disabled', async () => {
    vi.spyOn(api, 'getServerConfig').mockResolvedValue({
      signed_url_enabled: false,
    });
    const url = await api.getSignedImageUrl(testPath, 96);
    expect(url).toContain('/image/thumbnail?path=');
    expect(url).toContain(encodeURIComponent(testPath));
  });

  test('uses cached token when present', async () => {
    // Simulate server enabling signed urls
    vi.spyOn(api, 'getServerConfig').mockResolvedValue({
      signed_url_enabled: true,
    });

    const fakeToken = 'tok_abc123';
    const expiresAt = Date.now() + 30_000;
    (api as any)._tokenCache.set(testPath, { token: fakeToken, expiresAt });

    const url = await api.getSignedImageUrl(testPath, 128);
    expect(url).toContain('token=');
    expect(url).toContain(fakeToken);
  });
});
