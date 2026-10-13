import { describe, test, expect, vi, beforeEach } from 'vitest';
import { api } from '../api';

describe('api.ping', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test('returns true when /health responds', async () => {
    const spy = vi
      .spyOn(api.http, 'get')
      .mockResolvedValueOnce({ data: { status: 'ok' } } as any);

    const ok = await api.ping(10);
    expect(ok).toBe(true);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0]?.[0]).toBe('/health');
  });

  test('falls back to / when /health is missing (404)', async () => {
    const notFoundErr = { response: { status: 404 } };

    const spy = vi
      .spyOn(api.http, 'get')
      .mockRejectedValueOnce(notFoundErr as any)
      .mockResolvedValueOnce({ data: { status: 'ok' } } as any);

    const ok = await api.ping(10);
    expect(ok).toBe(true);
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[0]?.[0]).toBe('/health');
    expect(spy.mock.calls[1]?.[0]).toBe('/');
  });

  test('returns false when neither /health nor / responds', async () => {
    const spy = vi
      .spyOn(api.http, 'get')
      .mockRejectedValueOnce({ code: 'ECONNREFUSED' } as any);

    const ok = await api.ping(10);
    expect(ok).toBe(false);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
