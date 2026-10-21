import { describe, expect, it } from 'vitest';
import { detectFormFactor, detectShell } from '../platform/detect';

type FakeWindow = Window & typeof globalThis;

function windowWithMedia(matches: Record<string, boolean>): FakeWindow {
  return {
    matchMedia: (query: string) => ({ matches: matches[query] ?? false }),
  } as unknown as FakeWindow;
}

describe('detectShell', () => {
  it('reports browser when nothing Tauri is injected', () => {
    expect(detectShell({})).toBe('browser');
  });

  it('reports tauri from the always-present __TAURI_INTERNALS__ marker', () => {
    // `window.__TAURI__` is only injected with app.withGlobalTauri, which this
    // app does not enable — relying on it reported "browser" inside the shell.
    expect(detectShell({ __TAURI_INTERNALS__: {} })).toBe('tauri');
  });

  it('reports browser with no window at all (SSR / tests)', () => {
    expect(detectShell(undefined)).toBe('browser');
  });
});

describe('detectFormFactor', () => {
  it('is desktop by default', () => {
    expect(detectFormFactor(windowWithMedia({}))).toBe('desktop');
  });

  it('is mobile on a narrow viewport', () => {
    expect(
      detectFormFactor(windowWithMedia({ '(max-width: 767px)': true }))
    ).toBe('mobile');
  });

  it('is mobile on a coarse-pointer (touch-primary) device regardless of width', () => {
    expect(
      detectFormFactor(windowWithMedia({ '(pointer: coarse)': true }))
    ).toBe('mobile');
  });

  it('falls back to desktop when matchMedia is unavailable', () => {
    expect(detectFormFactor({} as FakeWindow)).toBe('desktop');
    expect(detectFormFactor(undefined)).toBe('desktop');
  });
});
