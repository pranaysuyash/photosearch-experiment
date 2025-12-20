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
global.fetch = vi.fn();

// Mock window.open for tests
window.open = vi.fn();

// Mock IntersectionObserver (jsdom doesn't implement it)
class MockIntersectionObserver {
  root: any;
  rootMargin: string;
  thresholds: any;
  callback: any;
  constructor(callback: any, options?: any) {
    this.callback = callback;
    this.root = options?.root || null;
    this.rootMargin = options?.rootMargin || '';
    this.thresholds = options?.threshold || [];
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

(global as any).IntersectionObserver = MockIntersectionObserver as any;
