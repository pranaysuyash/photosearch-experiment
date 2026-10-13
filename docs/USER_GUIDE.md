# Living Museum Interface - Complete User Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Search System](#search-system)
4. [Navigation & UX Features](#navigation--ux-features)
5. [Professional Workflows](#professional-workflows)
6. [Advanced Features](#advanced-features)
7. [Performance & Optimization](#performance--optimization)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Living Museum Interface is a professional-grade AI photo workstation designed for photographers, media organizations, and content creators who need intelligent photo search and organization capabilities. Built for a dual local + cloud library, it keeps privacy and control front-and-center while providing powerful search across large collections.

### Key Capabilities
- **Multi-modal Search**: Three distinct search modes for different use cases
- **Real-time Indexing**: Automatic detection and processing of new files
- **Professional Workflow**: Batch operations, export capabilities, and advanced filtering
- **3D Visualization**: Interactive photo browsing with Three.js
- **Privacy by Design**: No data mining, clear source provenance, and configurable processing (local and/or cloud, depending on plan)

---

## Getting Started

### Interface Overview
The interface consists of several key areas:
- **Top-left mode rail**: Switch between Grid / Globe / Story (collapses to the active mode icon)
- **Bottom dock**: Primary navigation (Library, Search, Saved, Tasks)
- **Search toolbar**: Primary CTA; shows a hero on empty state and collapses to a compact sticky toolbar when photos are loaded
- **Timeline widget**: Bottom-left temporal scrubber (collapsible)
- **Command palette (Spotlight)**: Keyboard-first actions (scan, open photos, etc.)

### View Modes
1. **Grid (Library)**: Dense, fast browsing + selection/export tools
2. **Globe**: 3D visualization for spatial-style exploration (click markers to open details)
3. **Story**: A more cinematic browse mode with fewer controls and more flow

### Tasks (background jobs)
Some actions run asynchronously (like scanning/indexing). These show up under **Tasks** and expose progress via job IDs.

---

## Search System

The Living Museum Interface provides three powerful search modes, each optimized for different types of queries and use cases.

### 1. Metadata Search 🗂️
*SQL-powered structured search through comprehensive file metadata*

#### When to Use
- Finding photos by specific technical details
- Date and time-based searches
- Camera equipment and settings queries
- File properties and location searches
- Precise technical criteria

#### Query Syntax
Uses SQL-like syntax for precise field-based searches:

```sql
-- Basic field searches
camera.make = "Canon"
lens.model LIKE "%85mm%"
file.size > 5000000

-- Date range searches
date.taken >= "2023-01-01"
date.taken BETWEEN "2023-06-01" AND "2023-08-31"

-- Location-based searches
gps.city = "San Francisco"
file.path LIKE "%vacation%"

-- Combined logical queries
camera.make = "Sony" AND lens.focal_length > 50
iso >= 1600 OR lens.aperture <= 2.8
```

#### Available Metadata Fields

**File System Properties:**
- `file.path` - Full file path
- `file.filename` - File name only
- `file.size` - File size in bytes
- `file.created` - File creation date
- `file.modified` - Last modification date

**Camera Information:**
- `camera.make` - Camera manufacturer (Canon, Sony, Nikon, etc.)
- `camera.model` - Specific camera model
- `camera.serial_number` - Camera serial number

**Lens Information:**
- `lens.model` - Lens model name
- `lens.focal_length` - Focal length in mm
- `lens.aperture` - Maximum aperture (f-number)

**Camera Settings:**
- `iso` - ISO sensitivity value
- `shutter_speed` - Shutter speed (e.g., "1/125")
- `flash` - Flash usage (on/off/auto)
- `exposure_mode` - Exposure mode (manual, aperture priority, etc.)

**GPS & Location:**
- `gps.latitude` - GPS latitude coordinate
- `gps.longitude` - GPS longitude coordinate
- `gps.city` - City name (if available)
- `gps.country` - Country name (if available)

**Date & Time:**
- `date.taken` - Photo capture date/time
- `date.digitized` - Digital processing date
- `date.modified` - Last modification date

#### Practical Examples

```sql
-- All Canon photos from 2023
camera.make = "Canon" AND date.taken >= "2023-01-01"

-- Portrait lens photography (85mm and above)
lens.focal_length >= 85

-- Large high-resolution files (over 10MB)
file.size > 10485760

-- Photos taken in New York City
gps.city = "New York"

-- Low light photography (high ISO)
iso >= 1600

-- Wide aperture portrait shots
lens.aperture <= 2.8 AND lens.focal_length >= 85

-- Wedding photos from specific date range
file.path LIKE "%wedding%" AND date.taken BETWEEN "2023-06-15" AND "2023-06-16"

-- Travel photography from 2023
(gps.city IS NOT NULL OR file.path LIKE "%travel%") AND date.taken >= "2023-01-01"
```

### 2. Semantic Search 🧠
*AI-powered natural language search using CLIP embeddings*

#### When to Use
- Describing visual content you're looking for
- Finding photos by mood, style, or atmosphere
- Content-based discovery and exploration
- Creative and artistic searches
- When you know what you want to see but not the technical details

#### Query Approach
Use natural, descriptive language to describe what you see or want to find:

**Objects and Subjects:**
```
"a red sports car"
"people laughing at dinner"
"mountain landscape with snow"
"close-up of colorful flowers"
"dog running in a park"
"children playing on beach"
```

**Moods and Atmosphere:**
```
"dramatic stormy sunset"
"cozy indoor fireplace scene"
"minimalist modern architecture"
"vintage retro aesthetic"
"peaceful morning light"
"energetic concert crowd"
```

**Activities and Events:**
```
"wedding ceremony outdoors"
"birthday party with cake"
"cooking in modern kitchen"
"hiking on mountain trail"
"surfing large waves"
"graduation celebration"
```

**Colors and Lighting:**
```
"golden hour warm lighting"
"black and white street photography"
"vibrant blue ocean water"
"soft natural window light"
"neon lights at night"
"autumn orange and red leaves"
```

**Composition and Style:**
```
"symmetrical architectural photography"
"shallow depth of field portrait"
"wide angle landscape vista"
"macro photography extreme closeup"
"aerial drone photography"
"long exposure light trails"
```

#### Tips for Better Semantic Search Results

1. **Be Descriptive but Concise**: Include key visual elements without being overly verbose
2. **Mention Key Objects**: Specify main subjects (people, animals, objects)
3. **Include Lighting/Mood**: Describe the atmosphere or lighting conditions
4. **Use Specific Terms**: "golden retriever" vs "dog", "sports car" vs "car"
5. **Combine Elements**: "sunset beach with palm trees" combines location, time, and objects

### 3. Hybrid Search 🔄
*Intelligent combination of metadata and semantic search with weighted scoring*

#### When to Use
- Complex searches requiring both technical and visual criteria
- Professional workflows needing precision and content relevance
- Finding specific visual content with technical constraints
- When you want the best of both search approaches

#### How Hybrid Search Works

The hybrid search engine:
1. **Runs Both Searches**: Executes metadata and semantic searches simultaneously
2. **Normalizes Scores**: Converts different scoring systems to comparable scales
3. **Applies Weights**:
   - Metadata results: 60% weight (precision focus)
   - Semantic results: 40% weight (content relevance)
4. **Merges Results**: Combines and ranks by weighted composite score
5. **Eliminates Duplicates**: Ensures each photo appears only once with best combined score

#### Query Strategy
Use natural language that can work effectively for both search modes:

**Technical + Visual Combinations:**
```
"Canon portrait photography"
→ Finds: Canon cameras + portrait compositions

"macro flower photography"
→ Finds: macro lenses + flower subjects

"night street photography"
→ Finds: high ISO settings + urban night scenes

"wedding 85mm lens"
→ Finds: 85mm focal length + wedding events
```

**Location + Content:**
```
"beach sunset golden hour"
→ Finds: beach GPS locations + sunset lighting

"mountain hiking adventure"
→ Finds: mountain locations + hiking activities

"urban architecture photography"
→ Finds: city locations + architectural subjects
```

**Equipment + Style:**
```
"Sony wide angle landscape"
→ Finds: Sony cameras + wide lenses + landscape scenes

"Nikon low light concert"
→ Finds: Nikon cameras + high ISO + concert venues

"Canon telephoto wildlife"
→ Finds: Canon cameras + long lenses + animal subjects
```

#### Scoring System
- **Perfect Match**: Photo matches both metadata and semantic criteria (score: 0.8-1.0)
- **Strong Match**: Photo strongly matches one mode, partially matches other (score: 0.6-0.8)
- **Good Match**: Photo matches one mode well (score: 0.4-0.6)
- **Weak Match**: Photo partially matches criteria (score: 0.2-0.4)

---

## Navigation & UX Features

### Interactive Timeline 📅

The timeline provides powerful temporal navigation for large photo collections.

#### Features
- **Visual Distribution**: Shows photo count distribution across months/years
- **Hover Information**: Displays exact photo counts and formatted dates
- **Clickable Filtering**: Click any bar to filter photos from that time period
- **Smart Search Integration**: Automatically generates optimized date queries
- **Minimize Option**: Collapse timeline when not needed

#### How to Use Timeline Filtering
1. **Locate Time Period**: Find the desired month/year in the timeline
2. **Click Timeline Bar**: Click on any bar to filter to that period
3. **Automatic Search**: System automatically:
   - Switches to metadata search mode
   - Generates date-based query (e.g., "June 2023")
   - Filters photos to show only that time period
4. **Clear Filter**: Clear search query to return to full collection

#### Timeline Navigation Tips
- **Hover for Details**: Hover over bars to see exact photo counts
- **Visual Density**: Taller bars indicate more photos in that period
- **Quick Browsing**: Use timeline for rapid temporal navigation
- **Batch Operations**: Filter by date, then select and export photos

### Scroll to Top Button ⬆️

Efficient navigation for large photo collections.

#### Behavior
- **Automatic Appearance**: Shows after scrolling down 500+ pixels
- **Smooth Animation**: Fade in/out with scale effects
- **One-Click Return**: Instantly scroll back to top with smooth animation
- **Accessibility**: Proper ARIA labels and keyboard navigation support

### Gallery View Modes

#### Traditional Mode
- **Classic Grid**: Responsive grid layout optimized for browsing
- **Hover Effects**: Smooth animations and metadata overlays
- **Selection Tools**: Multi-select with batch operations
- **Export Integration**: Select photos and export collections

#### Modern Mode
- **Advanced CSS**: Utilizes modern CSS Grid and subgrid features
- **Masonry Layout**: Dynamic column layout for varied photo sizes
- **Enhanced Animations**: Scroll-driven animations and 3D effects
- **Visual Polish**: Advanced shadows, gradients, and transitions

#### Globe Mode
- **3D Visualization**: Interactive Three.js-powered photo exploration
- **Spatial Navigation**: Navigate photos in 3D space
- **Immersive Experience**: Full-screen 3D photo browsing

### Search Interface

#### Search Bar Features
- **Real-time Results**: Instant feedback as you type
- **Mode Indicators**: Clear visual feedback for active search mode
- **Query Validation**: Syntax highlighting for metadata queries
- **Clear Function**: One-click search clearing

#### Filter Controls
- **Type Filters**: Photos only, videos only, or all media
- **Sort Options**: Date (newest/oldest), name (A-Z), size (largest first)
- **Quick Toggles**: Rapid switching between common filter combinations

---

## Professional Workflows

### Portrait Photographers

**Finding Specific Equipment Combinations:**
```sql
-- Metadata: All 85mm portrait shots
lens.focal_length = 85 AND camera.mode = "Portrait"

-- Semantic: Emotional expressions
"happy couple engagement portrait"

-- Hybrid: Technical + emotional combination
"85mm wedding portrait natural light"
```

**Client Delivery Workflows:**
1. Search for specific event: `file.path LIKE "%Johnson_Wedding%"`
2. Filter by date range: `date.taken BETWEEN "2023-08-15" AND "2023-08-16"`
3. Use semantic search for specific moments: `"first dance romantic lighting"`
4. Select best photos using selection mode
5. Export collection for client delivery

### Landscape Photographers

**Golden Hour Photography:**
```sql
-- Metadata: Time-based search
date.hour BETWEEN 6 AND 8 OR date.hour BETWEEN 17 AND 19

-- Semantic: Scenic content
"dramatic mountain landscape golden hour"

-- Hybrid: Technical timing + scenic content
"wide angle sunset landscape dramatic clouds"
```

**Location-Based Organization:**
1. Use GPS metadata: `gps.country = "Iceland"`
2. Combine with semantic content: `"waterfall long exposure"`
3. Filter by equipment: `lens.focal_length <= 24`
4. Sort by date for chronological story

### Event Photographers

**Low Light Event Photography:**
```sql
-- Metadata: Technical settings for low light
iso >= 1600 AND lens.aperture <= 2.8

-- Semantic: Event atmosphere
"people dancing at wedding reception"

-- Hybrid: Technical + atmospheric
"low light wedding reception candid moments"
```

**Event Coverage Workflow:**
1. Timeline navigation to event date
2. Metadata search for different camera settings phases
3. Semantic search for key moments: `"cake cutting ceremony"`
4. Hybrid search for technical + emotional combinations
5. Batch selection and export for different deliverables

### Travel Photographers

**Destination Documentation:**
```sql
-- Metadata: Location-based organization
gps.city = "Tokyo" AND date.taken >= "2023-03-01"

-- Semantic: Cultural content
"traditional Japanese temple architecture"

-- Hybrid: Location + cultural elements
"Tokyo street food market bustling crowd"
```

**Travel Story Creation:**
1. Use timeline to navigate trip chronologically
2. GPS metadata for location-based organization
3. Semantic search for cultural and atmospheric shots
4. Create themed collections using hybrid search
5. Export organized collections for different purposes

---

## Advanced Features

### Batch Operations

#### Selection Mode
- **Multi-Select**: Click and drag or Ctrl+click for multiple selections
- **Select All**: Choose all photos in current view or search results
- **Smart Selection**: Select by criteria (date range, camera type, etc.)

#### Export Capabilities
- **Format Options**: Original files, resized copies, or specific formats
- **Metadata Preservation**: Maintain or strip metadata as needed
- **Folder Organization**: Export with organized folder structure
- **Batch Naming**: Apply consistent naming conventions

### Search History and Bookmarks

#### Recent Searches
- **Auto-Save**: System remembers recent successful searches
- **Quick Access**: Dropdown menu with recent queries
- **Search Patterns**: Identifies frequently used search patterns

#### Saved Searches
- **Bookmark Queries**: Save complex or frequently used searches
- **Named Collections**: Create named search collections
- **Workflow Integration**: Integrate saved searches into regular workflows

### Keyboard Shortcuts

#### Navigation
- `Space`: Scroll down one page
- `Shift + Space`: Scroll up one page
- `Home`: Jump to top of collection
- `End`: Jump to bottom of collection

#### Search
- `Ctrl + F`: Focus search bar
- `Ctrl + K`: Quick search mode
- `Esc`: Clear search and return to full collection

#### Selection
- `Ctrl + A`: Select all visible photos
- `Ctrl + D`: Deselect all
- `Shift + Click`: Select range of photos

---

## Performance & Optimization

### Search Performance

#### Speed Expectations
- **Metadata Search**: 10-50ms (fastest, direct SQL queries)
- **Semantic Search**: 200-500ms (moderate, AI processing required)
- **Hybrid Search**: 300-800ms (slower, combines both methods)

#### Optimization Strategies
1. **Use Appropriate Mode**: Choose the fastest mode that meets your needs
2. **Specific Queries**: More specific queries return faster results
3. **Metadata First**: Start with metadata search for technical criteria
4. **Semantic for Discovery**: Use semantic search for content exploration
5. **Hybrid for Complex**: Reserve hybrid search for complex requirements

### Collection Size Handling

#### Large Collections (10,000+ photos)
- **Lazy Loading**: Images load as they come into view
- **Virtualization**: Efficient rendering of large photo grids
- **Pagination**: Results delivered in manageable chunks
- **Caching**: Intelligent caching of search results and thumbnails

#### Memory Management
- **Thumbnail Generation**: On-demand thumbnail creation
- **Image Optimization**: Automatic image size optimization
- **Cache Cleanup**: Automatic cleanup of unused cached data

### Network Optimization

#### Local Processing
- **AI Models**: All AI processing happens locally
- **No External Calls**: No data sent to external services
- **Privacy Protection**: Complete data privacy and security

#### API Efficiency
- **Debounced Requests**: Prevents excessive API calls during typing
- **Request Deduplication**: Eliminates duplicate simultaneous requests
- **Connection Pooling**: Efficient HTTP connection management

---

## Troubleshooting

### Common Issues

#### Search Not Returning Expected Results

**Metadata Search Issues:**
- **Check Syntax**: Ensure proper SQL syntax in queries
- **Field Names**: Verify correct field names (case-sensitive)
- **Data Availability**: Not all photos may have all metadata fields
- **Quote Strings**: Use quotes around text values: `camera.make = "Canon"`

**Semantic Search Issues:**
- **Be Descriptive**: More descriptive queries yield better results
- **Try Variations**: Experiment with different descriptions of same content
- **Check Spelling**: Ensure correct spelling in natural language queries
- **Model Limitations**: AI model may not recognize very specific or unusual content

**Hybrid Search Issues:**
- **Query Compatibility**: Ensure query works for both metadata and semantic modes
- **Score Interpretation**: Lower scores don't necessarily mean poor matches
- **Result Diversity**: Hybrid results may include unexpected but relevant photos

#### Performance Issues

**Slow Search Results:**
- **Collection Size**: Very large collections may have slower initial searches
- **First-Time Semantic**: First semantic search loads AI model (one-time delay)
- **Complex Queries**: Simplify queries for faster results
- **System Resources**: Ensure adequate RAM and CPU for AI processing

**Interface Responsiveness:**
- **Browser Performance**: Try different browsers for better performance
- **Clear Cache**: Clear browser cache if interface becomes sluggish
- **Restart Application**: Restart both frontend and backend if needed

#### Data and Indexing Issues

**Missing Photos:**
- **Scan Status**: Ensure directories have been scanned and indexed
- **File Formats**: Verify file formats are supported
- **Permissions**: Check file system permissions for photo directories
- **Path Changes**: Re-scan if photo locations have changed

**Metadata Missing:**
- **File Support**: Some file formats may not contain full metadata
- **Extraction Errors**: Check logs for metadata extraction errors
- **Re-indexing**: Force re-scan to update metadata

### Getting Help

#### Log Files
- **Backend Logs**: Check server console for API and processing errors
- **Browser Console**: Check browser developer tools for frontend errors
- **Search Logs**: Enable verbose logging for search debugging

#### Performance Monitoring
- **Search Times**: Monitor search response times in browser network tab
- **Memory Usage**: Check system memory usage during large operations
- **Disk Space**: Ensure adequate disk space for thumbnails and cache

#### Support Resources
- **Documentation**: Refer to technical documentation for advanced configuration
- **Community**: Check community forums for common solutions
- **Issue Reporting**: Report bugs with detailed reproduction steps

---

## Conclusion

The Living Museum Interface provides a comprehensive solution for professional photo management and discovery. By understanding and utilizing the three search modes effectively, along with the advanced navigation and UX features, users can efficiently manage and explore large photo collections while maintaining complete privacy and control over their data.

The system is designed to scale with professional workflows, supporting collections of 10,000+ photos while maintaining fast, relevant search results and smooth user experience.
