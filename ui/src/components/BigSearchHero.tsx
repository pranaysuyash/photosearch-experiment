import { motion } from 'framer-motion';
import { Search } from 'lucide-react';
import { SearchToggle, type SearchMode } from './SearchToggle';

interface BigSearchHeroProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchMode: SearchMode;
  setSearchMode: (mode: SearchMode) => void;
  onSearch: () => void;
}

export function BigSearchHero({
  searchQuery,
  setSearchQuery,
  searchMode,
  setSearchMode,
  onSearch
}: BigSearchHeroProps) {
  return (
    <motion.div
      className="flex flex-col items-center justify-center py-16 px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50, scale: 0.9 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <motion.h1
        className="text-4xl md:text-5xl font-thin tracking-tight mb-8 text-center bg-gradient-to-b from-foreground to-muted-foreground bg-clip-text text-transparent"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        Rediscover your memories
      </motion.h1>

      <motion.div
        className="relative w-full max-w-2xl group"
        layoutId="search-container"
      >
        <div className="absolute inset-0 bg-primary/20 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 rounded-full" />

        <motion.div
          className="relative flex items-center bg-white/5 dark:bg-black/20 backdrop-blur-xl border border-white/10 rounded-full shadow-2xl p-2 transition-all duration-300 focus-within:ring-2 focus-within:ring-primary/50 focus-within:border-primary/50"
          layoutId="search-bar"
        >
          <Search className="ml-4 text-muted-foreground w-6 h-6" />
          <input
            type="text"
            className="flex-1 bg-transparent border-none outline-none px-4 py-3 text-lg placeholder:text-muted-foreground/50"
            placeholder="Search for 'sunset in paris' or 'birthday cake'"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onSearch();
              }
            }}
            autoFocus
          />
          <button
            onClick={onSearch}
            className="bg-primary text-primary-foreground px-6 py-2.5 rounded-full font-medium hover:opacity-90 transition-opacity"
          >
            Search
          </button>
        </motion.div>
      </motion.div>

      <motion.div
        className="mt-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.4 }}
      >
        <SearchToggle value={searchMode} onChange={setSearchMode} />
      </motion.div>

      <motion.p
        className="mt-4 text-sm text-muted-foreground/60 italic"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.4 }}
      >
        Try "red cars", "smiling faces", or "documents from 2023"
      </motion.p>
    </motion.div>
  );
}

