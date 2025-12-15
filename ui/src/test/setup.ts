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