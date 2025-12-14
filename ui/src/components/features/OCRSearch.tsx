/**
 * OCR Search Component
 *
 * Allows searching for text within images using OCR
 */

import React, { useState, useEffect } from 'react';
import './OCRSearch.css';

const OCRSearch = () => {
  const [query, setQuery] = useState<string>('');
  interface OCRResult {
    image_path: string;
    filename: string;
    text: string;
    confidence: number;
    text_length: number;
  }
  const [results, setResults] = useState<OCRResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  interface OCRStats {
    total_images?: number;
    images_with_text?: number;
    total_characters?: number;
  }
  const [stats, setStats] = useState<OCRStats | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractProgress, setExtractProgress] = useState<number>(0);

  // Fetch OCR stats on mount
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/ocr/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Error fetching OCR stats:', err);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // Search for text in images
  const searchText = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/ocr/search?query=${encodeURIComponent(query)}`
      );
      if (!response.ok) {
        throw new Error('Failed to search OCR text');
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error searching OCR text:', err);
    } finally {
      setLoading(false);
    }
  };

  // Extract text from all images
  const extractTextFromAll = async () => {
    try {
      setIsExtracting(true);
      setError(null);
      setExtractProgress(0);

      // In a real app, you would get the list of all images
      // For now, we'll extract from all images
      const response = await fetch('/api/ocr/extract', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_paths: [], // Empty means extract from all images
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to extract text');
      }

      const result = await response.json();
      console.log('Extraction result:', result);

      // Simulate progress (in real app, this would come from backend)
      for (let i = 0; i <= 100; i += 10) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        setExtractProgress(i);
      }

      // Refresh stats
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error extracting text:', err);
    } finally {
      setIsExtracting(false);
    }
  };

  // Clear all OCR data
  const clearAllData = async () => {
    if (window.confirm('Are you sure you want to clear all OCR data?')) {
      try {
        const response = await fetch('/api/ocr/all', {
          method: 'DELETE',
        });

        if (!response.ok) {
          throw new Error('Failed to clear OCR data');
        }

        // Refresh stats
        fetchStats();
        setResults([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Error clearing OCR data:', err);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchText();
    }
  };

  return (
    <div className='ocr-search'>
      <div className='header'>
        <h2>OCR Search</h2>
        <div className='controls'>
          <button
            onClick={extractTextFromAll}
            disabled={isExtracting}
            className='extract-btn'
          >
            {isExtracting ? 'Extracting...' : 'Extract Text from Images'}
          </button>
          <button onClick={clearAllData} className='clear-btn'>
            Clear All Data
          </button>
        </div>
      </div>

      {isExtracting && (
        <div className='progress-bar'>
          <div
            className={`progress-fill score-fill-${
              Math.round(Math.max(0, Math.min(100, extractProgress)) / 10) * 10
            }`}
          ></div>
          <span className='progress-text'>{extractProgress}% Complete</span>
        </div>
      )}

      {stats && (
        <div className='stats'>
          <div className='stat-item'>
            <span className='stat-label'>Total Images:</span>
            <span className='stat-value'>{stats.total_images}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Images with Text:</span>
            <span className='stat-value'>{stats.images_with_text}</span>
          </div>
          <div className='stat-item'>
            <span className='stat-label'>Total Characters:</span>
            <span className='stat-value'>{stats.total_characters}</span>
          </div>
        </div>
      )}

      <div className='search-box'>
        <input
          type='text'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder='Search for text in images...'
          disabled={loading}
        />
        <button
          onClick={searchText}
          disabled={loading || !query.trim()}
          className='search-btn'
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {error && <div className='error'>Error: {error}</div>}

      {results.length > 0 ? (
        <div className='results'>
          <h3>Search Results ({results.length})</h3>
          <div className='results-grid'>
            {results.map((result, index) => (
              <div key={index} className='result-item'>
                <div className='result-image'>
                  <img
                    src={`/api/image/thumbnail?path=${encodeURIComponent(
                      result.image_path
                    )}&size=200`}
                    alt={`OCR result ${index + 1}`}
                    onError={(e: React.SyntheticEvent<HTMLImageElement>) => {
                      (e.target as HTMLImageElement).src =
                        '/placeholder-image.jpg';
                      (e.target as HTMLImageElement).onerror = null;
                    }}
                  />
                </div>
                <div className='result-info'>
                  <h4>{result.filename}</h4>
                  <div className='result-text'>
                    <p>{result.text}</p>
                  </div>
                  <div className='result-meta'>
                    <span className='confidence'>
                      Confidence: {(result.confidence * 100).toFixed(1)}%
                    </span>
                    <span className='char-count'>
                      {result.text_length} characters
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className='empty-state'>
          {query ? (
            <p>No images found containing "{query}".</p>
          ) : (
            <p>Enter a search term to find text in your images.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default OCRSearch;
