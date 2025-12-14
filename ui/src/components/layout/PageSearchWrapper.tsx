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
    favoritesFilter,
    setFavoritesFilter,
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
          favoritesFilter={favoritesFilter}
          setFavoritesFilter={setFavoritesFilter}
          onSearch={() => search(searchQuery)}
          isCompact={false}
          heroTitle={null}
        />
      </motion.div>

      {/* Page Content */}
      {children}
    </div>
  );
};
