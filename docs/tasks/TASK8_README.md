# Task 8: Story Mode (2D Default Interface)

**Files:** 
- `ui/src/components/StoryMode.tsx`
- `ui/src/components/HeroCarousel.tsx`

**Status:** ✅ Complete  
**Date:** 2025-12-07  
**Dependencies:** Task 6 (UI Foundation), Task 7 (Spotlight)

---

## What It Does

Creates the default "landing experience" for the Living Museum. Instead of a raw file grid, users see a curated "Story Mode" with a hero carousel and date-grouped photos.

---

## Features

- ✅ **Hero Carousel**: Full-width, auto-playing highlights (5-second interval)
- ✅ **Grouped Feed**: Photos organized into sections (Recent Highlights, Everything Else)
- ✅ **Featured Layout**: First photo in first group is large (2x2 grid span)
- ✅ **Smooth Animations**: `whileInView` animations using Framer Motion
- ✅ **Search Toggle**: Typing seamlessly switches to search grid

---

## Usage

1. Open the app at `http://localhost:5173`
2. Default view is Story Mode with Hero Carousel
3. Type in search bar to switch to search results
4. Clear search to return to Story Mode

---

## Technical Notes

- `HeroCarousel` uses `AnimatePresence` for crossfade transitions
- Currently uses mock grouping (first 4 photos vs rest)
- Future: Parse `metadata.filesystem.created` for real date grouping
- Fixed `verbatimModuleSyntax` TypeScript errors

---

## What Could Be Improved

- **Real date parsing**: Use `date-fns` to parse metadata dates
- **Infinite scroll**: Load more photos as user scrolls
- **Detail modal**: Click photo to open lightbox overlay

---

## Lessons Learned

1. `whileInView` from Framer Motion is great for scroll-triggered animations
2. Conditional rendering in React (`isSearching ? Grid : StoryMode`) works smoothly
3. Sticky headers with `backdrop-blur` create nice visual hierarchy
