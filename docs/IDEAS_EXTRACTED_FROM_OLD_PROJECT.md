# Complete Ideas Extraction from Old Photo Search Project

> **Source**: `old_project_docs/` (93 files analyzed)
> **Date**: 2025-12-09
> **Purpose**: Every idea with potential merit from the previous project, cleaned and organized for consideration in the upgraded photosearch_experiment

---

## 🎯 Core Search & Discovery

### Semantic Search Enhancements
- CLIP-based semantic search with natural language ("kids at the beach")
- Hybrid search combining text + visual similarity
- Search-like-plus with text guidance for advanced similarity
- Cross-modal search (text finds images, images find similar)
- Query expansion with 200+ synonym mappings
- Boolean/fielded search syntax: `person:"Alice" AND has_text:true AND camera:"iPhone"`
- Saved searches with custom names and parameters
- Search history with analytics and frequency tracking
- Recent searches quick access dropdown
- Search templates for common patterns

### Search Intent Recognition (12 Types)
1. **Discovery** - Exploring/browsing behavior
2. **Specific** - Looking for particular photo
3. **Temporal** - Time-based ("photos from today", "last summer")
4. **Location** - Place-based ("beach photos", "Paris trip")
5. **Person** - People-based ("photos with Alice")
6. **Activity** - Event-based ("birthday party", "hiking")
7. **Technical** - Camera settings ("shot at f/2.8", "ISO 3200")
8. **Emotional** - Mood-based ("happy moments", "peaceful scenes")
9. **Comparison** - Finding similar photos
10. **Narrative** - Story/sequence detection
11. **Quality** - By image quality metrics
12. **Unknown** - Fallback with suggestions

### Intent Recognition Features
- Context extraction (time, location, people, activities, mood, quality, technical specs)
- Confidence scoring for intent classification
- Query complexity analysis (simple/moderate/complex)
- Smart suggestion generation based on intent
- 200+ pattern rules for recognition
- Spelling correction ("Did you mean?")
- Synonym suggestions ("Try also")
- Popular searches display

### Search UI Enhancements
- Filter chips - Visual, removable tags
- Voice search integration
- Command palette style (Cmd+K launcher)
- AI-powered suggestions inline
- Loading state with skeleton shimmer
- Suggestion type badges (AI/Fix/Syn/Trend in different colors)
- Quick filters: has_text, has_faces, has_gps, favorited
- Advanced search modal with all filter options

---

## 🗂️ Collections & Organization

### Manual Collections
- Create/edit/delete with confirmation dialogs
- Drag-and-drop photo assignment
- Cover photo selection with persistence to API/localStorage
- Collection themes (visual styling) with persistence
- Nested/hierarchical collection support
- Collection templates for quick starts
- Batch operations (add multiple photos at once)
- Collection metadata (description, creation date, photo count)

### Smart Collections (Rule-Based)
- Rule builder UI with dropdown selectors
- Live preview before saving rules
- Auto-refresh when conditions change
- Template smart collections: Recent (7 days), Favorites, Large files (>5MB), Screenshots
- Boolean logic: Date > X AND Rating > Y
- Multiple rule conditions with AND/OR
- Save rules to API with resolve endpoint

### Tags & Metadata
- Tag cloud visualization
- Tag autocomplete with frequency
- Batch tagging for multiple photos
- Tag colors for visual organization
- Custom metadata field support
- Batch rename with pattern matching
- Tag statistics (usage count, photos per tag)
- Tag merging and cleanup tools

### Favorites & Ratings
- 1-5 star rating system
- Quick favorite toggle (heart icon)
- Filter by minimum rating
- Rating overlay display on grid
- Batch rating assignment
- Most/least favorited views

---

## 👤 People & Faces

### Face Detection & Clustering
- Face detection API trigger from UI
- InsightFace clustering integration
- Name face clusters UI
- Face-based photo filtering
- Person albums auto-generated from faces
- Face recognition training with user feedback
- Confidence scores for face matches
- Face timeline showing person over time
- Progress indicators during face building
- "Build Face Index" button with provider selection

### People View
- Face grid display with representative photos
- Cluster viewer showing all photos of person
- Find similar faces functionality
- Face count badges
- Person detail view with all photos
- Merge faces (combine clusters)
- Remove wrong photos from clusters

---

## 🗺️ Location & Maps

### GPS & Location Features
- EXIF GPS extraction from photo metadata
- Reverse geocoding (coordinates → addresses)
- Location clustering by geographic proximity
- Trip detection from GPS + time sequences
- Significant location identification
- Address resolution and display
- Location-based search capabilities
- Heatmap visualization of photo locations

### Map View
- Interactive map with react-leaflet or Mapbox
- Photo markers with clustering for overlaps
- Click marker to view photos at location
- Location-based filtering
- Travel timeline visualization
- Trip highlights with place/time labels
- NASA Blue Marble texture for globe view
- 3D globe visualization option

### Trips Feature
- Auto-detect trips from metadata (GPS + time)
- Build trips API with provider selection
- List detected trips endpoint
- Trip detail view with photo highlights
- Save trip as collection
- Trip duration and distance stats
- Start/end location display
- Trip timeline scrubber

---

## 📄 OCR & Text Search

### OCR Implementation
- Build OCR index from images
- `has_text:true` filter in queries
- OCR snippets API showing text previews
- Search within extracted text
- Highlight matching text regions in images
- Text extraction confidence scores
- Multi-language OCR support
- OCR hover card with count and one-click build

### Use Cases
- Find receipts and documents
- Search screenshots by content
- Locate presentation slides
- Business card text extraction
- Sign and label text search

---

## 🤖 AI Capabilities

### Caption Generation
- Build captions API with AI models
- Caption-based semantic search enhancement
- Manual caption editing interface
- Batch caption generation
- Approve/reject AI captions workflow
- Multiple caption providers (GPT-4V, Claude-3, Gemini Vision)
- Caption quality assessment
- Translation of captions

### Auto-Tagging
- Automatic tag suggestions from content
- Batch tag approval workflow
- Scene detection (indoor/outdoor, nature, urban)
- Object detection (car, dog, food, buildings)
- Emotion detection in faces
- Activity recognition (sports, dining, working)
- Tag confidence scoring
- Custom tag training

### VLM Configuration
- Model selection dropdown with all providers
- API key configuration with secure input masking
- Model parameters (temperature, max tokens, confidence thresholds)
- Test connection button with status indicator
- Quality vs speed trade-offs configuration
- Features toggle (object detection, scene analysis, text extraction, face recognition)
- Provider-specific options
- Cost estimation display

---

## 🎨 Image Editing & Enhancement

### Basic Editing
- Crop with draggable handles
- Rotate (90°, 180°, 270°) and flip operations
- Basic filters (brightness, contrast, saturation, sharpness)
- Non-destructive editing with undo/redo
- Edit history view
- Preview before apply
- Batch edit operations
- Reset to original

### AI Enhancement
- AI upscaling (super resolution) via `/upscale` endpoint
- Background removal
- Style transfer options
- Quality assessment automation
- Noise reduction
- HDR enhancement
- Color grading presets

### FAL Qwen Image Edit
- AI-powered image editing via FAL API
- Icon generation from text prompts
- Background pattern creation
- Illustration element generation
- Batch asset generation (47+ assets possible)
- Custom style training
- Template library

---

## 🔍 Similarity & Duplicates

### Find Similar
- "Find Similar" button on photo detail view
- Visual similarity scoring display
- Search-like functionality with image as query
- Search-like-plus with text guidance
- Similar photo groups
- Threshold control for similarity
- Find similar faces across library

### Duplicate Detection
- Lookalikes API to find duplicates
- Duplicate groups display with comparison
- Side-by-side comparison view
- Visual diff highlighting
- Batch duplicate resolution workflow
- Safe deletion with confirmation
- Mark groups as resolved
- Keep best quality auto-selection
- Merge metadata from duplicates

---

## ⚡ Performance & Architecture

### Fast Index Options (ANN Backends)
- **FAISS** - Highest priority for 30k+ photos, fastest search
- **HNSW** (hnswlib) - Middle priority for 5k-30k photos
- **Annoy** - Lightest dependency, good for smaller libraries
- **Auto-selection** - Pick best available backend automatically
- **Graceful fallback** to exact search when ANN unavailable
- Build fast index API endpoint (`/fast/build`)
- Status check endpoint (`/fast/status`)
- Backend selection hint in search (`fast_kind` parameter)

### Virtualization
- React-window for large lists (or migrate to @tanstack/react-virtual)
- Virtual scrolling for photo grids
- FixedSizeList for activity panels
- Overscan count tuning (5 items recommended)
- Dynamic height support for variable items
- Smooth scrolling at 60fps target
- Memory-efficient rendering

### Performance Monitoring
- PerformanceMonitor class for metrics tracking
- React hooks integration (`usePerformanceMonitor`)
- Component-level timing
- Ctrl+Shift+P toggle for metrics display
- Memory usage tracking
- Render time analysis
- API call timing
- Cache hit/miss rates
- Real-time metrics dashboard

### Bundle Optimization
- Code splitting by route
- Lazy loading of features
- Manual chunks for vendors
- Brotli compression
- Target: <250KB gzipped (currently 242KB achieved in v1)
- Tree shaking configuration
- Dynamic imports for modals
- Preload critical resources

### Architecture Patterns
- Plugin-based architecture for extensibility
- Feature flags for gradual rollout
- Domain-based Zustand stores (separate search, selection, filters)
- Component registry for dynamic UI
- API manager with centralized error handling
- Service layer abstraction
- Repository pattern for data access

### State Management
- **Server State**: React Query for all API data
- **UI State**: Small Zustand stores per domain
- **Cache State**: Separate store for client cache
- **Selection State**: Dedicated store to avoid re-renders
- De-couple state to prevent App.tsx cascades
- Optimistic updates for UX
- Debounce: 150ms for search input

---

## 🌐 Offline-First Features

### Core Offline Strategy
- **Offline as primary, online as enhancement** philosophy
- IndexedDB for local caching
- Service worker for PWA capability
- Cache photo metadata and embeddings
- Background sync when connectivity returns
- Offline queue for pending actions
- Action batching and conflict resolution

### Offline Search
- Use cached embeddings for semantic search
- Local CLIP models (run without internet once downloaded)
- Cache search results with TTL
- LRU cache for recent queries
- Pre-warming for common searches
- Offline manifest JSON with version hash

### Data Hydration
- Fetch and cache on app startup when online
- Pre-populate search indices
- Selective caching for large libraries (prioritize recent/favorites)
- Progressive hydration strategy
- Cache validation and refresh
- Manifest generator script for offline mode

### Offline Components
- PhotoDataSource abstraction (offline manifest vs online API)
- Thumbnail resolver: cache → file → API → placeholder
- Feature flags: `VITE_OFFLINE_GRID`, `VITE_FORCE_OFFLINE`
- Offline status indicators in UI
- Sync progress display
- Queued actions UI

---

## 🖥️ Desktop (Electron) Features

### Model Management
- `PHOTOVAULT_MODEL_DIR` environment variable
- Auto-detect model locations per OS:
  - macOS: `~/Library/Caches/photo-search/models`
  - Linux: `~/.cache/photo-search/models`
  - Windows: `%LOCALAPPDATA%\photo-search\models`
- "Refresh Bundled Models" menu action
- Bundle CLIP models with installer
- First-run model import UX with directory selection
- Model directory persistence in settings

### First-Run Experience
- **Quick Start** - Scan default photo folders automatically
- **Custom Setup** - Choose specific folders with picker
- **Demo Mode** - Try with bundled sample library
- Pre-scan file counts before indexing
- Target: <90 seconds total setup time
- "Indexing runs in background" messaging
- Estimated completion time display

### Desktop UX
- Window position/size state persistence via electron-store
- Native menu integration
- System tray icon with quick actions
- Native folder picker dialogs
- Drag-and-drop file import
- App icon badge with progress
- Notification support
- Auto-update mechanism

### Security Hardening
- Context isolation: true in webPreferences
- CSP injection via webRequest.onHeadersReceived:
  ```
  default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline';
  script-src 'self'; font-src 'self' data:
  ```
- OpenExternal protection: whitelist only ['https:']
- IPC validation with Zod schemas for every message
- Signed builds for distribution

### IPC Integration
- File system access handlers
- Backend process management
- Menu action wiring
- Progress reporting channels
- Error reporting to renderer

### Jobs Center
- View progress of long-running tasks
- Pause/resume indexing operations
- Cancel operations with cleanup
- ETA estimates based on progress
- Per-task progress bars
- Job history with status
- Retry failed jobs

---

## 👥 User Management & Sharing

### User Profiles
- Display name, avatar, role (admin/editor/viewer)
- User preferences storage (theme, language, notifications)
- Privacy settings (profile visible, activity visible, collections public)
- Default view preference (grid/list/timeline)
- Grid size preference (small/medium/large)
- Last active tracking

### Permissions System
- Resource-level permissions (photo, collection, workspace)
- Permission levels: view, comment, edit, admin
- Expiry dates for temporary access (hours parameter)
- SharedBy and SharedAt tracking
- Permission revocation API
- Check permission utility function

### Share Links
- Generate shareable URLs with unique IDs
- Password protection option
- Expiry dates configuration
- Max views limit with tracking
- Current view count display
- Delete share link capability
- Share link analytics

### Activity Tracking
- Track actions: view, edit, comment, share, favorite, delete
- Activity feed per user with limit parameter
- Recent activity panel with virtualization
- Resource metadata in activity log
- Timestamp tracking
- Activity filtering and sorting
- Collaborator list for resources
- Search users for mentions/sharing

---

## 📊 Analytics & Insights

### Library Analytics
- Photo count by date/camera/location
- Storage usage breakdown by format
- Camera equipment statistics with most-used
- Index status monitoring (indexed vs total)
- Format distribution charts
- Resolution statistics
- File size histograms

### Search Analytics
- Query success rate tracking
- First result click time measurement
- Results latency monitoring
- Popular searches leaderboard
- Search pattern analysis
- Failed query tracking for improvements
- Query suggestion effectiveness
- Search session duration

### Attention/Discovery
- Most viewed photos (popularity endpoint)
- Forgotten photos (never viewed endpoint)
- Photo popularity insights with trends
- Feature usage tracking per user
- Seasonal photo suggestions
- Re-discovery prompts
- Usage heatmap by time

### Performance Metrics
- API response times
- Search latency percentiles
- Cache hit rates
- Memory usage trends
- Render performance
- Bundle load times
- Error rates by endpoint

---

## 🎨 UI/UX Enhancements

### Design System (World-Class)
- **Exaggerated minimalism** (2025 trend)
- Glassmorphism (frosted glass effects)
- Modern gradients with depth
- Layering with subtle shadows
- Typography scale (perfect fourth - 1.333)
- Motion design with easing curves
- Respect `prefers-reduced-motion`
- SF Pro Display/Text font family
- JetBrains Mono for code

### Color System
**Light Mode**:
- Primary: Deep blue (220 70% 50%)
- Accent: Purple (280 65% 60%)
- Success: Green (142 76% 36%)
- Warning: Amber (38 92% 50%)
- Error: Red (0 84% 60%)

**Dark Mode**:
- Background: Deep dark blue (222 47% 11%)
- Surface: Card surface (217 33% 17%)
- Lighter primary/accent for contrast

### Photo Grid
- **Justified layout** - Photos fill rows perfectly with no gaps
- Responsive aspect ratios (no cropping)
- Smooth 60fps virtual scrolling
- Hover effects with scale + shadow
- Selection mode with spring-animated checkboxes
- Quick actions on long press (mobile)
- Lazy loading images
- Placeholder-first strategy to avoid jank

### Search Bar (Cmd+K Style)
- Command palette interface
- Smart suggestions with AI
- Voice search option with microphone icon
- Loading state with shimmer effect
- Recent searches dropdown
- Filter chips below bar
- Keyboard-first navigation
- Icon + text for actions

### Lightbox Viewer
- Fullscreen distraction-free mode
- Keyboard navigation (arrows, ESC)
- Pinch zoom gesture (mobile)
- EXIF panel slide-in from side
- Share sheet with native feel
- Swipe navigation (mobile)
- Download original button
- Edit mode inline
- Photo info toggle
- Slideshow mode

### Timeline View
- Day/week/month bucket grouping
- Sticky date headers during scroll
- Jump shortcuts (T/M/L/O keys for Today/Month/Later/Older)
- Month scrubber navigation bar
- Photo count per bucket
- Infinite scroll support
- Date range selection

### Navigation
- **Sidebar** - Collapsible sections with icons and counts
- **Breadcrumbs** - Path navigation with click
- **Tab bar** (mobile) - Bottom navigation (4 tabs max)
- **Shortcuts** - Full keyboard support with help modal (?)
- **Active states** - Pill-shaped highlight
- **Recent items** - Quick access in sidebar

### Animations & Motion
- Page transitions with fade/slide
- Card hover animations (scale, shadow)
- Skeleton loaders for loading states
- Micro-interactions on buttons
- Toast notifications with slide-in
- Progress indicators with smooth animation
- Easing curves:
  - Spring: cubic-bezier(0.34, 1.56, 0.64, 1)
  - Smooth: cubic-bezier(0.4, 0.0, 0.2, 1)
  - Snappy: cubic-bezier(0.0, 0.0, 0.2, 1)
- Duration scale: 100ms (instant), 200ms (fast), 300ms (base), 500ms (slow)

### Mobile Considerations
- Bottom navigation limited to 4 tabs
- Touch-optimized tap targets (44px minimum)
- Swipe gestures for navigation
- Pull-to-refresh support
- Mobile-optimized image sizes
- Responsive breakpoints
- Native-feel transitions

---

## 🔄 Search Caching System

### LRU Cache Implementation
- In-memory LRU (Least Recently Used) cache
- TTL (Time-To-Live) expiration per entry
- Different TTL values by data type:
  - Search results: 10 minutes
  - Metadata: 1 hour
  - Thumbnails: 24 hours
- Cache size limits configuration
- Hit/miss statistics tracking

### Cache Key Generation
- MD5 hashing for consistent keys
- Include all relevant search parameters
- Exclude pagination (offset, limit) from key
- Version-aware keys for cache invalidation

### Performance Benefits
- Near-instant repeated searches
- Reduced embedding calculations
- Lower API call volume
- Better resource utilization
- Cache warming for common queries
- Adaptive TTL based on query frequency

### Cache Management
- Clear old metrics (>24 hours)
- Cache statistics dashboard
- Manual cache invalidation
- Pre-fetch predicted queries
- Redis support for distributed deployments

---

## 💾 Persistent Storage & Database

### SQLite Backend
- Alternative to file-based storage
- ACID transactions for consistency
- Concurrent access support
- Better performance for large collections
- Easy backup/restore (single .db file)
- Structured SQL queries

### Database Schema
Tables: photos, thumbnails, embeddings, tags, photo_tags, collections, photo_collections, search_history, activity_log, cached_search_results

### Two-Tier Caching
1. In-memory cache for hot data
2. SQLite for persistent storage
3. Automatic synchronization between tiers

### Database Features
- WAL (Write-Ahead Logging) mode for concurrency
- Connection pooling for efficiency
- Optimized indexes for common queries
- Full-text search capabilities (future)
- Migration utilities (file ↔ SQLite)
- Integrity checking
- Automated backups with timestamps

### CLI Commands
- `db init` - Initialize database
- `db migrate` - Migrate between backends
- `db stats` - View statistics
- `db backup` - Create backup
- `db restore` - Restore from backup
- `db analyze` - Update query statistics

---

## 📤 Export & Sharing

### Export Features
- Export to folder (copy or symlink options)
- EXIF strip option for privacy
- Export presets:
  - Social media sizes (1080x1080, 1920x1080)
  - Print sizes (4x6, 5x7, 8x10)
  - Original quality
- Batch export with progress
- Custom export settings
- Filename patterns (date, camera, location)

### Local Sharing
- Local share link creation
- Copy path to clipboard
- Reveal in Finder/Explorer
- Open with external app endpoint
- QR code generation for local share

### Cloud Options (Planned)
- OAuth for Google Drive, Dropbox
- AWS S3 credential configuration
- iCloud Drive integration (if possible)
- Secure credential storage in keychain
- Connection testing before upload
- Bandwidth throttling options

---

## 🤖 Automation & Workflows

### Rule-Based Actions
- Auto-organize by date folder structure
- Auto-organize by location
- Auto-tag based on content analysis
- Event trigger automation (on import, on edit)
- Scheduled tasks (nightly indexing, cleanup)
- Custom script support (plugin API)

### Processing Pipelines
- Import automation with rules
- Batch operations with retry logic
- Checkpoint system for long-running jobs
- Job queue with priority
- Parallel processing where safe
- Error recovery and rollback

### Background Tasks
- Index building with progress
- OCR extraction batch
- Face detection processing
- Caption generation queue
- Fast index building
- Thumbnail generation
- Metadata extraction
- Duplicate scanning

---

## 🧪 Testing & Quality

### Testing Strategy
- Unit tests (Vitest) - 70%+ coverage target
- Integration tests for modules
- E2E tests (Playwright) for critical paths
- Visual regression testing with snapshots
- Cross-browser testing matrix
- Performance benchmarks with thresholds
- Accessibility audits

### Visual Testing Specifics
- maxDiffPixelRatio: 0.02 (2% tolerance)
- Mask timestamps, counters, dynamic IDs
- Helper: dismissOverlays(page) before snapshots
- Helper: safeClick(page, selector) with retry
- Screenshot diffing with Percy or Chromatic

### Performance Thresholds
- Load time: < 3.0s (DOM + Paint)
- Search response: < 2.0s end-to-end
- Memory usage: < 100MB heap for long sessions
- Scroll FPS: > 55fps at 10k items
- First contentful paint: < 1.5s
- Time to interactive: < 3.5s

### Quality Metrics
- Zero critical bugs in production
- 95% test coverage goal
- <100ms UI response time
- 60fps animations maintained
- WCAG 2.1 AA compliance
- 90+ Lighthouse score

---

## ♿ Accessibility

### Keyboard Navigation
- Full keyboard support for all features
- `?` key for help/shortcuts modal
- `/` key to focus search
- `ESC` to close modals/clear
- Arrow keys for grid navigation
- `j/k` (Vim style) for list navigation
- Tab/Shift+Tab focus management
- Enter/Space for activation
- Home/End for boundaries

### Screen Readers
- ARIA labels on all interactive elements
- ARIA roles for semantic structure
- Live regions for dynamic content
- Announcements for actions
- Focus management on modals
- Skip links for main content
- Descriptive alt text for images
- Form labels and error messages

### Visual Accessibility
- High contrast mode support
- Minimum font size 14px (text-sm)
- Color contrast compliance (4.5:1)
- Reduced motion support with @media
- Focus indicators (2px outline)
- No color-only information
- Resizable text support

### Standards Compliance
- WCAG 2.1 AA target
- Section 508 compliance
- ARIA 1.2 best practices
- Accessibility audit documentation
- User testing with assistive tech

---

## 🚀 Advanced/Future Features

### AI Generation
- AI art generation from prompts
- Background replacement options
- Style transfer presets
- Object removal (inpainting)
- Face beautification
- Colorization of B&W photos
- Resolution enhancement beyond upscaling

### 3D/VR/AR
- 3D photo viewing (depth maps)
- 360° panorama support
- AR viewing mode (overlay on environment)
- VR galleries (immersive viewing)
- Photogrammetry (3D from 2D)
- Spatial audio for videos

### Advanced Video
- Video thumbnail generation from keyframes
- Video playback with custom controls
- Video metadata extraction (codecs, bitrate)
- Video timeline scrubbing
- Scene detection in videos
- Video chapter markers
- Subtitle/caption support

### Social Features
- Public collection sharing
- Community features (comments, likes)
- Collaboration on collections
- NFT minting integration (future consideration)
- Print service integration
- Photo contest submissions
- Social media cross-posting

### Plugin System
- Plugin API specification
- Third-party integration marketplace
- Custom workflow plugins
- Plugin installation UI
- Plugin sandboxing for security
- Plugin update mechanism
- Plugin rating and reviews

---

## 🎯 High-Priority Quick Wins

### Immediate Value (Low Effort)
1. **Saved searches** - Simple localStorage, high user value
2. **Favorites toggle** - Single API call, universal feature
3. **Timeline view** - Date grouping, already have data
4. **Filter chips** - Visual query builder, better UX
5. **Keyboard shortcuts** - Power user productivity boost
6. **Recent searches** - Simple cache, improves discovery
7. **Download original** - Single button, common need
8. **Grid size toggle** - 3 CSS classes, preference storage

### Medium Effort, High Impact
1. **Collections management** - Core organization feature
2. **Face detection UI** - Integrate existing backend
3. **Smart collections** - Rule builder with preview
4. **OCR text search** - Unlock document search
5. **Duplicate detection** - Library cleanup tool
6. **Batch operations** - Efficiency for power users
7. **Trip detection** - Auto-organize travel photos
8. **Multi-select mode** - Essential for batch actions

### Higher Effort, Transformative
1. **Offline-first architecture** - Complete offline capability
2. **Search intent recognition** - Smarter understanding
3. **Fast indexes (FAISS/Annoy)** - Speed for large libraries
4. **AI captions** - Better semantic search
5. **Electron desktop app** - Native experience
6. **Plugin architecture** - Infinite extensibility
7. **User management** - Collaboration support
8. **Cloud sync** - Multi-device access

---

## 🔧 Technical Implementation Details

### Environment Variables Referenced
- `STORAGE_BACKEND` - "sqlite" or "file"
- `OFFLINE_MODE` - "1" for offline
- `PHOTOVAULT_MODEL_DIR` - Model directory path
- `VITE_OFFLINE_GRID` - Feature flag for offline grid
- `VITE_FORCE_OFFLINE` - Force offline mode for testing
- `NODE_ENV` - "development" or "production"

### API Endpoints Available (From Old Project)
**Fully Integrated (18/47)**: Search, Index, Fast build, Faces clusters, OCR build, Metadata, Tags, Map, Favorites, Saved, Export, Library, Workspace add, Delete, Undo delete, Diagnostics, Thumbnails

**Not Integrated (29/47)**: Collections (get/set/delete), Smart collections (get/set/delete/resolve), Trips (build/list), Faces (build/name), OCR snippets, Tags set, Metadata detail, Saved (add/delete), Edit ops, Upscale, Open external, Search like plus, Lookalikes, Resolve lookalike, Build captions, Feedback, Todo, Workspace (remove/list), Attention (popularity/forgotten/seasonal)

### Design Principles from Old Project
1. **Intent-First** - Reduce time-to-first-value (TTFV)
2. **Local-Only by Default** - Privacy as core value
3. **Offline as Primary** - Online enhances, doesn't enable
4. **Smart Defaults** - Works out of box, no config needed
5. **Transparency & Reversibility** - Undo everything
6. **Plugin Architecture** - Scale to 1000+ features
7. **Performance First** - 60fps always, <100ms responses
8. **Accessibility** - Keyboard-first, screen reader friendly
9. **Deterministic** - Same input = same output always
10. **User Control** - Never auto-destructive actions

---

## 📝 Minute Details & Technical Nuances

### Font Strategy
- Bundle fonts locally in `assets/fonts/`
- Inter.woff2 for UI text
- JetBrains Mono for code/monospace
- Avoid external CDN requests (privacy + offline)

### Badge Color Semantics
- **Blue**: AI-generated suggestions
- **Amber**: Spelling corrections
- **Green**: Synonyms/related terms
- **Purple**: Popular/trending items
- Consistent across all badge uses

### Mobile UI Limits
- Bottom navigation: max 4 tabs (Home, Search, Favorites, Settings)
- Touch targets: minimum 44px
- Swipe sensitivity: 50px threshold
- Long press: 500ms duration

### Keyboard Shortcuts
- `/` - Focus search
- `?` - Help/shortcuts modal
- `ESC` - Close/clear
- `j/k` - Vim-style navigation
- `Ctrl+Shift+P` - Performance metrics
- Arrow keys - Grid navigation
- `Cmd+K` - Command palette

### Error Types Enum
- `NETWORK`, `VALIDATION`, `PERMISSION`, `NOT_FOUND`
- `TIMEOUT`, `RATE_LIMIT`, `SERVER`, `UNKNOWN`
- Consistent error context structure required

### Job Queue Implementation
- File-backed `jobs.json` with checkpointing
- Retry logic with exponential backoff
- Priority queue support
- Progress percentage tracking
- ETA calculation from throughput

### Debounce Values
- Search input: 150ms
- Resize events: 250ms
- Scroll events: 100ms
- API calls: 300ms

---

## 🎬 Conclusion

This document captures **every idea with potential merit** from 93 documentation files spanning the old photo-search project. Ideas range from fully-planned features (with backend APIs ready) to conceptual enhancements and minute UX details.

**Key Insights**:
- 29 backend API endpoints exist but lack frontend integration
- Offline-first architecture was deeply thought through
- Search intent recognition system was production-ready
- Electron desktop implementation had security hardening details
- Performance monitoring was comprehensive (metrics, thresholds)
- Design system was world-class (glassmorphism, perfect typography scale)
- Accessibility was a first-class concern (WCAG 2.1 AA)
- Plugin architecture was planned for extensibility

**Not Included**: Implementation code, specific file structures, detailed API contracts, testing code examples. This is purely an **ideas extraction** — what could be built, not how to build it.

**Next Steps**: Review this list, prioritize based on your current roadmap, and cherry-pick ideas that align with your upgraded vision for the photosearch_experiment project.

---

*Extracted from `old_project_docs/` on 2025-12-09. Every detail that had potential value has been captured for consideration.*
