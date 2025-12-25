import { describe, test, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { PhotoGrid } from '../components/gallery/PhotoGrid';
import { api, type Photo } from '../api';
import { AmbientThemeProvider } from '../contexts/AmbientThemeContext';
import { PhotoSearchProvider } from '../contexts/PhotoSearchContext';

// Simple flush helper
const flush = () => new Promise((r) => setTimeout(r, 0));

describe('PhotoGrid favorites batching', () => {
  const photos: Photo[] = [
    {
      path: '/media/photo1.jpg',
      filename: 'photo1.jpg',
      score: 0,
      metadata: {},
    },
    {
      path: '/media/photo2.jpg',
      filename: 'photo2.jpg',
      score: 0,
      metadata: {},
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test('calls getFavorites once and marks favorited items', async () => {
    const getFavSpy = vi
      .spyOn(api, 'getFavorites')
      .mockResolvedValue({ results: [{ file_path: '/media/photo1.jpg' }] });

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    root.render(
      <AmbientThemeProvider>
        <PhotoSearchProvider>
          <PhotoGrid photos={photos} onPhotoSelect={() => {}} />
        </PhotoSearchProvider>
      </AmbientThemeProvider>
    );

    // Wait for effect to run
    await flush();
    await flush();

    expect(getFavSpy).toHaveBeenCalledTimes(1);

    // Check the DOM for favorites toggle button titles
    const favButtons = Array.from(
      container.querySelectorAll('button[title]')
    ).filter((b) => b.getAttribute('title')?.includes('favorites'));

    // We expect at least one 'Remove from favorites' for photo1, and one 'Add to favorites' for photo2
    const hasRemove = favButtons.some(
      (b) => b.getAttribute('title') === 'Remove from favorites'
    );
    const hasAdd = favButtons.some(
      (b) => b.getAttribute('title') === 'Add to favorites'
    );

    expect(hasRemove).toBe(true);
    expect(hasAdd).toBe(true);

    // Cleanup
    root.unmount();
    container.remove();
  });
});
