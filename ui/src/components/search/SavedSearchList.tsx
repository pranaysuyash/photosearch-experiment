/**
 * Saved Search List Component
 *
 * Displays a list of saved searches with filtering and management options
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, Play, Trash2 } from 'lucide-react';
import { api, type SavedSearch } from '../../api';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import type { SearchMode } from './SearchToggle';

const SavedSearchList = () => {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all'); // all, favorites, recent
  const navigate = useNavigate();
  const { setSearchQuery, setSearchMode, search } = usePhotoSearchContext();

  // Fetch saved searches
  const fetchSearches = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await api.listSavedSearches(filter);
      setSearches(data.searches || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching saved searches:', err);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // Fetch on mount and when filter changes
  useEffect(() => {
    fetchSearches();
  }, [fetchSearches]);

  // Execute a saved search
  const executeSearch = async (searchId: string) => {
    try {
      const result = await api.executeSavedSearch(searchId);
      setSearchQuery(result.search.query);
      // Best-effort: saved mode should match our SearchMode union.
      setSearchMode(result.search.mode as SearchMode);
      search(result.search.query);
      navigate('/search');
    } catch (err) {
      console.error('Error executing search:', err);
    }
  };

  // Toggle favorite status
  const toggleFavorite = async (searchId: string, isFavorite: boolean) => {
    try {
      await api.updateSavedSearch(searchId, { is_favorite: !isFavorite });
      // Refresh the list
      fetchSearches();
    } catch (err) {
      console.error('Error updating favorite:', err);
    }
  };

  // Delete a saved search
  const deleteSearch = async (searchId: string) => {
    if (window.confirm('Are you sure you want to delete this saved search?')) {
      try {
        await api.deleteSavedSearch(searchId);
        // Refresh the list
        fetchSearches();
      } catch (err) {
        console.error('Error deleting search:', err);
      }
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className='text-sm text-muted-foreground py-10 text-center'>
        Loading saved searches…
      </div>
    );
  }

  if (error) {
    return (
      <div className='text-sm text-destructive py-10 text-center'>
        Error: {error}
      </div>
    );
  }

  return (
    <div className='space-y-4'>
      <div className='flex flex-wrap items-center gap-2'>
        <button
          className={`btn-glass ${filter === 'all' ? 'btn-glass--primary' : 'btn-glass--muted'
            } text-xs px-3 py-2`}
          onClick={() => setFilter('all')}
        >
          All ({searches.length})
        </button>
        <button
          className={`btn-glass ${filter === 'favorites' ? 'btn-glass--primary' : 'btn-glass--muted'
            } text-xs px-3 py-2`}
          onClick={() => setFilter('favorites')}
        >
          Favorites
        </button>
        <button
          className={`btn-glass ${filter === 'recent' ? 'btn-glass--primary' : 'btn-glass--muted'
            } text-xs px-3 py-2`}
          onClick={() => setFilter('recent')}
        >
          Recent
        </button>
      </div>

      {searches.length === 0 ? (
        <div className='glass-surface rounded-2xl p-10 text-center text-muted-foreground'>
          <p className='text-sm'>No saved searches yet.</p>
          <p className='text-xs opacity-70 mt-1'>
            Run a search and save it to revisit later.
          </p>
        </div>
      ) : (
        <div className='grid grid-cols-1 gap-3'>
          {searches.map((saved) => (
            <div
              key={saved.id}
              className='glass-surface rounded-2xl p-4 flex flex-col gap-3'
            >
              <div className='flex items-start gap-3'>
                <div className='min-w-0 flex-1'>
                  <div className='text-sm font-semibold text-foreground truncate'>
                    {saved.query}
                  </div>
                  <div className='text-xs text-muted-foreground mt-1 flex flex-wrap gap-x-3 gap-y-1'>
                    <span>Mode: {saved.mode}</span>
                    {saved.intent && <span>Intent: {saved.intent}</span>}
                    <span>Saved: {formatDate(saved.created_at)}</span>
                    <span>Results: {saved.results_count}</span>
                  </div>
                </div>

                <div className='flex items-center gap-2'>
                  <button
                    className={`btn-glass ${saved.is_favorite
                        ? 'btn-glass--primary'
                        : 'btn-glass--muted'
                      } w-9 h-9 p-0 justify-center`}
                    onClick={() => toggleFavorite(saved.id, saved.is_favorite)}
                    title={saved.is_favorite ? 'Unfavorite' : 'Favorite'}
                  >
                    <Star size={16} />
                  </button>
                  <button
                    className='btn-glass btn-glass--primary w-9 h-9 p-0 justify-center'
                    onClick={() => executeSearch(saved.id)}
                    title='Run search'
                  >
                    <Play size={16} />
                  </button>
                  <button
                    className='btn-glass btn-glass--danger w-9 h-9 p-0 justify-center'
                    onClick={() => deleteSearch(saved.id)}
                    title='Delete saved search'
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {saved.notes && (
                <div className='text-xs text-muted-foreground/80 leading-relaxed'>
                  {saved.notes}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SavedSearchList;
