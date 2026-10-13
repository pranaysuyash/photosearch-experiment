# Ideas Extracted from Old Photo Search Project

> **Source**: `/Users/pranay/Projects/adhoc_projects/photo-search/docs` > **Extraction Date**: 2025-12-09
> **Purpose**: Comprehensive list of ideas from the previous project that may be valuable for the upgraded photosearch_experiment

---

## Table of Contents

1. [Core Search & AI Features](#1-core-search--ai-features)
2. [Collections & Organization](#2-collections--organization)
3. [People & Faces](#3-people--faces)
4. [Location & Maps](#4-location--maps)
5. [OCR & Text Search](#5-ocr--text-search)
6. [AI Capabilities](#6-ai-capabilities)
7. [Image Editing & Enhancement](#7-image-editing--enhancement)
8. [Similarity & Duplicates](#8-similarity--duplicates)
9. [Performance & Architecture](#9-performance--architecture)
10. [Offline-First Features](#10-offline-first-features)
11. [Desktop (Electron) Features](#11-desktop-electron-features)
12. [User Management & Sharing](#12-user-management--sharing)
13. [Analytics & Insights](#13-analytics--insights)
14. [UI/UX Enhancements](#14-uiux-enhancements)
15. [Search Intent Recognition](#15-search-intent-recognition)
16. [Export & Sharing](#16-export--sharing)
17. [Automation & Workflows](#17-automation--workflows)
18. [Testing & Quality](#18-testing--quality)
19. [Accessibility](#19-accessibility)
20. [Future/Advanced Features](#20-futureadvanced-features)

---

## 1. Core Search & AI Features

### Semantic Search

- **CLIP-based semantic search** - Natural language queries like "kids at the beach"
- **Hybrid search** - Combine text + visual similarity
- **Search-like-plus** - Advanced similarity with text guidance

### Search Enhancements

- **Saved searches** - Save and reuse complex queries
- **Search history** with analytics
- **Recent searches** quick access
- **Boolean/fielded search** - `person:"Alice" AND has_text:true AND camera:"iPhone"`
- **Filter chips** - Visual, removable filter tags

### Fast Index Options

- **FAISS** - High priority for large libraries (30k+ photos)
- **HNSW** (hnswlib) - Middle priority, good for 5k-30k
- **Annoy** - Lightest dependency, decent speedup
- **Auto-selection** - Automatically pick best available backend
- **Fallback to exact** - Graceful degradation when indexes unavailable

---

## 2. Collections & Organization

### Manual Collections

- Create/edit/delete collections
- Drag-and-drop photo assignment
- **Cover photo selection** with persistence
- **Collection themes** (visual styling)
- Nested/hierarchical collections
- Collection templates

### Smart Collections

- **Rule-based dynamic collections** - "Photos from last month with people"
- Rule builder UI with dropdowns
- Live preview before saving
- Auto-refresh when conditions change
- Template smart collections (Recent, Favorites, etc.)

### Tags & Metadata

- Tag cloud view
- Tag autocomplete
- Batch tagging
- **Tag colors** for visual organization
- Custom metadata fields
- Batch rename functionality

### Favorites & Ratings

- 1-5 star ratings
- Quick favorite toggle (heart)
- Filter by minimum rating
- Rating overlay on photos

---

## 3. People & Faces

### Face Detection & Clustering

- **Face detection** API endpoint
- **Face clustering** - Group similar faces
- **Name face clusters** - Assign names to people
- Face-based photo filtering
- **Person albums** - Auto-generated from faces
- Face recognition training (user feedback)

### People View

- Face grid display
- Cluster viewer with representative photos
- Find similar faces
- Face timeline (see person over time)
- Progress indicators during face building

---

## 4. Location & Maps

### GPS & Location Features

- **EXIF GPS extraction** from photos
- **Reverse geocoding** - Convert coordinates to addresses
- **Location clustering** - Group nearby photos
- **Trip detection** - Auto-detect travel sequences
- Timeline + map combo view

### Map View

- Interactive map (react-leaflet)
- Photo markers with clustering
- Location-based search
- **Travel timeline** visualization
- Trip highlights with place/time labels

### Trips Feature

- Build trips from metadata
- List detected trips
- Trip detail view with highlights
- Save trip as collection

---

## 5. OCR & Text Search

### OCR Implementation

- Build OCR index (extract text from images)
- `has_text:true` filter
- OCR snippets API - Show text previews
- Search within extracted text
- Highlight matching text regions in images

### Use Cases

- Find receipts, documents, slides
- Search screenshots by text content
- OCR hover card with count and one-click build

---

## 6. AI Capabilities

### Caption Generation

- **Build captions API** - Generate AI descriptions
- Caption-based semantic search
- Manual caption editing
- Batch caption generation
- Approve/reject AI captions

### Auto-tagging

- Automatic tag suggestions based on content
- Batch tag approval workflow
- Scene detection (indoor/outdoor, nature, urban)
- Object detection (car, dog, food, etc.)
- Emotion detection in faces

### VLM (Vision Language Model) Configuration

- Model selection dropdown (GPT-4V, Claude-3, Gemini Vision, Local)
- API key configuration with secure masking
- Model parameters (temperature, max tokens, confidence)
- Test connection with status indicator
- Quality vs speed trade-offs

---

## 7. Image Editing & Enhancement

### Basic Editing

- **Crop** with draggable handles
- **Rotate/flip** operations
- Basic filters (brightness, contrast, saturation)
- Non-destructive editing with undo/redo
- Edit history

### AI Enhancement

- **AI upscaling** (super resolution)
- Background removal
- Style transfer
- Quality assessment automation

### FAL Qwen Image Edit Integration

- AI-powered image editing via FAL API
- Icon generation from prompts
- Background pattern creation
- Illustration elements
- Batch asset generation (47+ assets possible)

---

## 8. Similarity & Duplicates

### Find Similar

- "Find Similar" button on photo details
- Visual similarity scoring
- Search-like functionality

### Duplicate Detection

- **Lookalikes API** - Find duplicate/similar photos
- Duplicate groups display
- Side-by-side comparison view
- Batch duplicate resolution
- Safe deletion workflow with confirmation
- Mark as resolved

---

## 9. Performance & Architecture

### Virtualization

- **react-window** for large lists
- Virtual scrolling for photo grids
- FixedSizeList for panels
- Overscan for smooth scrolling

### Performance Monitoring

- PerformanceMonitor class for tracking
- React hooks integration (`usePerformanceMonitor`)
- Component-level timing
- Ctrl+Shift+P toggle for metrics display
- Memory usage tracking
- Render time analysis

### Bundle Optimization

- Code splitting by route
- Lazy loading of features
- Manual chunks for vendors
- Brotli compression
- Target: <250KB gzipped

### Architecture Patterns

- **Plugin-based architecture** for extensibility
- Feature flags for gradual rollout
- Domain-based Zustand stores
- Component registry for dynamic UI
- API manager with centralized calling

---

## 10. Offline and Online Features

### Core Dual-Mode Strategy

- **Support both offline and online modes** - React chosen for flexibility in handling both
- IndexedDB for local caching
- Service worker for PWA
- Cache photo metadata and embeddings
- Background sync when online

### Offline Search

- Use cached embeddings for semantic search
- Local CLIP models (runs without internet)
- Cache search results for reuse

### Data Hydration

- Fetch and cache on startup when online
- Pre-populate search indices
- Selective caching for large libraries I### Model Bundling for Offline
- **First-run model import UX** - Select model directory
- **Electron bundled models** - Ship with installer
- Environment-based model detection
- Model directory configuration persistence

---

## 11. Desktop (Electron) Features

### Model Management

- `PHOTOVAULT_MODEL_DIR` environment variable
- Auto-detect model locations:
  - macOS: `~/Library/Caches/photo-search/models`
  - Linux: `~/.cache/photo-search/models`
  - Windows: `%LOCALAPPDATA%\photo-search\models`
- "Refresh Bundled Models" menu action

### First-Run Experience

- **Quick Start** - Scan default photo folders
- **Custom Setup** - Choose specific folders
- **Demo Mode** - Try with sample library
- Pre-scan counts before indexing
- "Indexing runs in background; you can search immediately"

### IPC Integration

- File system access handlers
- Native folder picker dialogs
- Backend process management
- Menu action wiring

### Jobs Center

- View progress of long-running tasks
- Pause/resume indexing
- Cancel operations
- ETA estimates
- Per-task progress

---

## 12. User Management & Sharing

### User Profiles

- Display name, avatar, role (admin/editor/viewer)
- User preferences storage
- Theme, language, notifications settings
- Privacy settings (profile visible, activity visible)

### Permissions

- Resource-level permissions (photo, collection, workspace)
- Permission levels: view, comment, edit, admin
- Expiry dates for temporary access
- Permission revocation

### Share Links

- Generate shareable URLs
- Password protection
- Expiry dates
- Max views limit
- View tracking

### Activity Tracking

- Track view/edit/comment/share/favorite/delete actions
- Activity feed per user
- Recent activity panel
- Collaborator list for resources

---

## 13. Analytics & Insights

### Library Analytics

- Photo count by date, camera, location
- Storage usage breakdown
- Camera equipment statistics
- Index status monitoring

### Search Analytics

- Query success rate
- First result click time
- Results latency
- Popular searches
- Search pattern analysis

### Attention/Discovery

- **Most viewed photos**
- **Forgotten photos** (never viewed)
- Photo popularity insights
- Feature usage tracking

---

## 14. UI/UX Enhancements

### Design System

- Glassmorphism (frosted glass effects)
- Modern gradients
- Depth and layering with shadows
- Typography scale (perfect fourth - 1.333)
- Motion design with easing curves

### Photo Grid

- Justified layout (photos fill rows perfectly)
- Responsive aspect ratios (no cropping)
- Smooth 60fps virtual scrolling
- Hover effects with scale + shadow
- Selection mode with checkboxes

### Search Bar (Cmd+K)

- Command palette style
- AI-powered suggestions
- Voice search option
- Loading state with shimmer
- Recent searches dropdown

### Lightbox Viewer

- Fullscreen mode
- Keyboard navigation (arrows, ESC)
- Pinch zoom (mobile)
- EXIF panel slide-in
- Share sheet
- Swipe navigation (mobile)

### Timeline View

- Day/week/month buckets
- Sticky date headers
- Jump shortcuts (T/M/L/O keys)
- Month scrubber navigation

### Animations

- Page transitions
- Card hover animations
- Skeleton loaders
- Micro-interactions
- Toast notifications
- Respect `prefers-reduced-motion`

---

## 15. Search Intent Recognition

### 12 Intent Types Identified

1. **Discovery** - Exploring/browsing
2. **Specific** - Looking for particular photo
3. **Temporal** - Time-based ("photos from today")
4. **Location** - Place-based ("beach photos")
5. **Person** - People-based ("photos with Alice")
6. **Activity** - Event-based ("birthday party")
7. **Technical** - Camera settings ("f/2.8")
8. **Emotional** - Mood-based ("happy moments")
9. **Comparison** - Finding similar
10. **Narrative** - Story/sequence
11. **Quality** - By image quality
12. **Unknown** - Fallback

### Intent Features

- Context extraction (time, location, people, activities)
- Confidence scoring
- Query complexity analysis (simple/moderate/complex)
- Smart suggestion generation
- 200+ pattern rules for recognition
- 200+ synonym mappings

### Suggestion Types

- **AI Suggestions** - Intent-based (blue badge)
- **Spelling Corrections** - "Did you mean?" (amber badge)
- **Synonyms** - "Try also" (green badge)
- **Popular Searches** - Trending (purple badge)

---

## 16. Export & Sharing

### Export Features

- Export to folder (copy or symlink)
- EXIF strip option for privacy
- Export presets (social media sizes)
- Batch export

### Local Sharing

- Local share link creation
- Copy to clipboard
- Finder/Explorer open

### Cloud Options (Future)

- OAuth for Google Drive, Dropbox
- AWS S3 configuration
- iCloud Drive integration
- Secure credential storage

---

## 17. Automation & Workflows

### Rule-Based Actions

- Auto-organize by date/location
- Auto-tag based on content
- Event trigger automation

### Processing Pipelines

- Import automation
- Scheduled tasks (e.g., nightly indexing)
- Custom scripts support

### Background Tasks

- Index building
- OCR extraction
- Face detection
- Caption generation
- Fast index building

---

## 18. Testing & Quality

### Testing Strategy

- Unit tests (Vitest) - 70%+ coverage target
- Integration tests for modules
- E2E tests (Playwright)
- Visual regression testing
- Cross-browser testing
- Performance benchmarks

### Quality Metrics

- Zero critical bugs
- <100ms search response
- 60fps UI animations
- <3 second initial load
- 95% test coverage goal

---

## 19. Accessibility

### Keyboard Navigation

- Full keyboard support
- `?` for help/shortcuts
- `/` to focus search
- Arrow keys for navigation
- Tab/Shift+Tab focus management

### Screen Readers

- ARIA labels and roles
- Announcements for actions
- Focus management

### Visual

- High contrast mode
- Readable font sizes
- Color contrast compliance
- Reduced motion support

### Standards

- WCAG 2.1 AA compliance target
- Accessibility audit documentation

---

## 20. Future/Advanced Features

### AI Generation

- AI art generation
- Background replacement
- Style transfer
- Object removal
- Face beautification

### 3D/VR/AR

- 3D photo viewing
- 360° panoramas
- AR viewing mode
- VR galleries
- Photogrammetry

### Video Support

- Video thumbnail generation
- Video playback integration
- Video metadata extraction
- Video timeline scrubbing

### Social Features

- Public collections
- Community features
- NFT minting (future)
- Print services integration

### Plugin Marketplace

- Plugin API specification
- Third-party integrations
- Custom workflow plugins
- Plugin installation UI

---

## Priority Ideas to Consider

### High Impact / Medium Effort

1. **Collections Management** - Create/edit/delete with drag-drop
2. **Face Detection UI** - Integrate face clustering
3. **Smart Collections** - Rule-based dynamic albums
4. **OCR Text Search** - Find documents/screenshots
5. **Duplicate Detection** - Clean up library

### High Impact / Higher Effort

1. **Offline-First Architecture** - Full offline capability
2. **Search Intent Recognition** - Smarter query understanding
3. **Fast Indexes (FAISS/Annoy)** - Speed up large libraries
4. **Trip Detection** - Auto-discover travel sequences
5. **AI Captions** - Better semantic search

### Quick Wins

1. **Saved Searches** - Simple to implement, high value
2. **Favorites/Ratings** - Toggle + filter
3. **Timeline View** - Date grouping
4. **Filter Chips** - Visual query building
5. **Keyboard Shortcuts** - Power user productivity

---

## API Endpoints Available (47 Total)

### Fully Integrated (18/47 = 38%)

- `apiSearch`, `apiSearchWorkspace`, `apiIndex`, `apiBuildFast`
- `apiFacesClusters`, `apiBuildOCR`
- `apiGetMetadata`, `apiBuildMetadata`, `apiGetTags`, `apiMap`
- `apiGetFavorites`, `apiSetFavorite`, `apiGetSaved`
- `apiExport`, `apiLibrary`, `apiWorkspaceAdd`, `apiDelete`, `apiUndoDelete`
- `apiDiagnostics`, `thumbUrl`

### Not Yet Integrated (29/47 = 62%)

- Collections: `apiGetCollections`, `apiSetCollection`, `apiDeleteCollection`
- Smart: `apiGetSmart`, `apiSetSmart`, `apiDeleteSmart`, `apiResolveSmart`
- Trips: `apiTripsBuild`, `apiTripsList`
- Faces: `apiBuildFaces`, `apiFacesName`
- OCR: `apiOcrSnippets`
- Tags: `apiSetTags`, `apiMetadataDetail`
- Saved: `apiAddSaved`, `apiDeleteSaved`
- Edit: `apiEditOps`, `apiUpscale`, `apiOpen`
- Similarity: `apiSearchLikePlus`, `apiLookalikes`, `apiResolveLookalike`
- Captions: `apiBuildCaptions`
- System: `apiFeedback`, `apiTodo`, `apiWorkspaceRemove`, `apiWorkspaceList`

---

## Key Design Principles from Old Project

1. **Intent-First** - Reduce time-to-first-value (TTFV)
   _This document extracted from 20+ documentation files from the old photo-search project. Each idea listed may merit further investigation for your upgraded project._

## Appendix: Expanded ideas & minute items (clean skimming from old project docs)

This appendix gathers smaller, concrete ideas and refinements from the old project's documentation that are worth considering. These are intentionally terse — no implementation details — just ideas you can pick and choose from.

### Offline & First-Run

- `PhotoDataSource` abstraction (offline manifest vs online API) for easy swapping
- Use a manifest JSON for offline preload with a manifest hash/version; cache in IndexedDB
- Provide a manifest generator script and a `demo_manifest.json` for demo mode
- Thumbnail resolver: cache → file → API → placeholder (placeholder-first to avoid layout jank)
- Feature flags for offline: `VITE_OFFLINE_GRID`, `VITE_FORCE_OFFLINE` for gated rollout/testing
- Offline queue + action batching + conflict resolution + background sync when connectivity returns
- Offer an explicit
