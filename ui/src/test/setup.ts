// Test setup file for vitest
import { vi } from 'vitest';

// Mock navigator.clipboard for tests
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve('')),
  },
});

// Mock fetch for tests
global.fetch = vi.fn() as unknown as typeof fetch;

// Mock window.open for tests
window.open = vi.fn() as unknown as typeof window.open;

// Mock IntersectionObserver (jsdom doesn't implement it)
class MockIntersectionObserver {
  root: Element | Document | null;
  rootMargin: string;
  thresholds: readonly number[];
  callback: IntersectionObserverCallback;
  constructor(
    callback: IntersectionObserverCallback,
    options?: IntersectionObserverInit
  ) {
    this.callback = callback;
    this.root = options?.root ?? null;
    this.rootMargin = options?.rootMargin ?? '';
    this.thresholds = options?.threshold ?? [];
  }
  observe() {
    // No-op
  }
  unobserve() {
    // No-op
  }
  disconnect() {
    // No-op
  }
  takeRecords() {
    return [];
  }
}
(
  globalThis as typeof globalThis & {
    IntersectionObserver: typeof MockIntersectionObserver;
  }
).IntersectionObserver = MockIntersectionObserver;
