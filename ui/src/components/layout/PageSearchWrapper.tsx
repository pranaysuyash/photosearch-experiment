/**
 * PageSearchWrapper
 *
 * Wraps page content with centered search bar at top
 * Search hides on scroll, visible on all pages
 */

import React from 'react';
import { motion } from 'framer-motion';
import { usePhotoSearchContext } from '../../contexts/PhotoSearchContext';
import { EnhancedSearchUI } from '../search/EnhancedSearchUI';
import { Hash, X } from 'lucide-react';

interface PageSearchWrapperProps {
  children: React.ReactNode;
  headerHidden?: boolean;
}

export const PageSearchWrapper = ({
  children,
  headerHidden = false,
}: PageSearchWrapperProps) => {
  const {
    searchQuery,
    setSearchQuery,
    searchMode,
    setSearchMode,
    sortBy,
    setSortBy,
    typeFilter,
    setTypeFilter,
    sourceFilter,
    setSourceFilter,
    favoritesFilter,
    setFavoritesFilter,
    tag,
    setTag,
    search,
  } = usePhotoSearchContext();

  return (
    <div className='w-full'>
      {/* Centered Search Bar */}
      <motion.div
        className='w-full max-w-7xl mx-auto px-4 md:px-6 pt-6 pb-8'
        initial={{ opacity: 0, y: 20 }}
        animate={headerHidden ? { opacity: 0, y: -20 } : { opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        <EnhancedSearchUI
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          searchMode={searchMode}
          setSearchMode={setSearchMode}
          sortBy={sortBy}
          setSortBy={setSortBy}
          typeFilter={typeFilter}
          setTypeFilter={setTypeFilter}
          sourceFilter={sourceFilter}
          setSourceFilter={setSourceFilter}
          favoritesFilter={favoritesFilter}
          setFavoritesFilter={setFavoritesFilter}
          tag={tag}
          setTag={setTag}
          onSearch={() => search(searchQuery)}
          isCompact={false}
          heroTitle={null}
        />

        {tag && (
          <div className='mt-3 flex items-center justify-center'>
            <div className='glass-surface rounded-full px-2 py-1 flex items-center gap-2'>
              <div className='flex items-center gap-1 text-xs text-muted-foreground px-2 py-1'>
                <Hash size={12} />
                <span className='text-foreground font-semibold'>#{tag}</span>
              </div>
              <button
                className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center'
                onClick={() => setTag(null)}
                title='Clear tag filter'
                aria-label='Clear tag filter'
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        {sourceFilter && sourceFilter !== 'all' && (
          <div className='mt-3 flex items-center justify-center'>
            <div className='glass-surface rounded-full px-3 py-1 flex items-center gap-2 text-xs'>
              <span className='text-muted-foreground'>Source:</span>
              <span className='text-foreground font-semibold'>
                {sourceFilter.charAt(0).toUpperCase() + sourceFilter.slice(1)}
              </span>
              <button
                className='btn-glass btn-glass--muted w-8 h-8 p-0 justify-center'
                onClick={() => setSourceFilter('all')}
                title='Clear source filter'
                aria-label='Clear source filter'
              >
                <X size={14} />
              </button>
            </div>
          </div>
        )}
      </motion.div>

      {/* Page Content */}
      {children}
    </div>
  );
};
