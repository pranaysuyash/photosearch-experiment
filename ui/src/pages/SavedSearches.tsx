/**
 * Saved Searches Page
 *
 * Manage and organize saved searches
 */

import SavedSearchList from '../components/search/SavedSearchList';

const SavedSearches = () => {
  return (
    <div className='mx-auto w-full max-w-6xl'>
      <div className='mb-6'>
        <h1 className='text-2xl font-semibold tracking-tight text-foreground'>
          Saved Searches
        </h1>
        <p className='text-sm text-muted-foreground'>
          Re-run and organize your favorite queries.
        </p>
      </div>

      <div className='glass-surface rounded-2xl p-4 sm:p-6'>
        <SavedSearchList />
      </div>
    </div>
  );
};

export default SavedSearches;
