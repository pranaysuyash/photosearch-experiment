import { describe, test, expect, vi, beforeEach } from 'vitest';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';

import ReviewInbox from '../components/people/ReviewInbox';
import { api } from '../api';

const flush = () => new Promise((r) => setTimeout(r, 0));

describe('ReviewInbox', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test('renders queue counts from API', async () => {
    vi.spyOn(api, 'getUnassignedFaces').mockResolvedValue({ total: 12, faces: [] });
    vi.spyOn(api, 'getReviewQueueCount').mockResolvedValue(3);
    vi.spyOn(api, 'getMixedClusters').mockResolvedValue({ count: 1, clusters: [] });
    vi.spyOn(api, 'getMergeSuggestions').mockResolvedValue({ count: 2, suggestions: [] });
    vi.spyOn(api, 'getLowConfidenceFaces').mockResolvedValue({ total: 4, count: 1, threshold: 0.8, faces: [] });

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter>
          <ReviewInbox
            onOpenNeedsReview={() => {}}
            onOpenMergeSuggestions={() => {}}
          />
        </MemoryRouter>
      );
      await flush();
      await flush();
    });

    const text = container.textContent || '';
    expect(text).toContain('Review Inbox');
    expect(text).toContain('Unassigned');
    expect(text).toContain('Needs Review');
    expect(text).toContain('Merge Suggestions');
    expect(text).toContain('Low Confidence');

    // Numbers are rendered as strings in the UI.
    expect(text).toContain('12');
    expect(text).toContain('3');
    expect(text).toContain('2');
    expect(text).toContain('4');

    act(() => {
      root.unmount();
    });
    container.remove();
  });
});
