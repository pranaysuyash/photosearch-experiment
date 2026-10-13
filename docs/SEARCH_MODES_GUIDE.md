# Search Modes Guide - Living Museum Interface

## Overview

The Living Museum Interface provides three powerful search modes designed for professional photo workflows. Each mode uses different technologies and query structures to help you find exactly what you're looking for.

## Search Modes

### 1. **Metadata Search** 🗂️
*SQL-powered structured search through file metadata*

**Best for:**
- Finding photos by specific technical details
- Date/time-based searches
- Camera equipment queries
- File properties and locations

**Query Structure:**
```sql
-- Basic field searches
camera.make = "Canon"
lens.model LIKE "%85mm%"
file.size > 5000000

-- Date searches
date.taken >= "2023-01-01"
date.taken BETWEEN "2023-06-01" AND "2023-08-31"

-- Location searches
gps.city = "San Francisco"
file.path LIKE "%vacation%"

-- Combined queries
camera.make = "Sony" AND lens.focal_length > 50
```

**Available Fields:**
- **File**: `path`, `filename`, `size`, `created`, `modified`
- **Camera**: `make`, `model`, `serial_number`
- **Lens**: `model`, `focal_length`, `aperture`
- **Settings**: `iso`, `shutter_speed`, `flash`
- **GPS**: `latitude`, `longitude`, `city`, `country`
- **Date**: `taken`, `digitized`, `modified`

**Example Queries:**
```sql
-- All Canon photos from 2023
camera.make = "Canon" AND date.taken >= "2023-01-01"

-- Portrait lens photos (85mm+)
lens.focal_length >= 85

-- Large files (>10MB)
file.size > 10485760

-- Photos taken in specific location
gps.city = "New York"

-- Night photography (high ISO)
iso >= 1600

-- Wide aperture shots
lens.aperture <= 2.8
```

### 2. **Semantic Search** 🧠
*AI-powered natural language search using CLIP embeddings*

**Best for:**
- Describing visual content
- Finding photos by mood or style
- Content-based discovery
- Creative searches

**Query Structure:**
Use natural language to describe what you see or want to find:

```
-- Objects and subjects
"a red car"
"people laughing"
"mountain landscape"
"close-up of flowers"

-- Moods and styles
"dramatic sunset"
"cozy indoor scene"
"minimalist composition"
"vintage aesthetic"

-- Activities and events
"wedding ceremony"
"children playing"
"cooking in kitchen"
"outdoor concert"

-- Colors and lighting
"golden hour lighting"
"black and white portrait"
"vibrant blue sky"
"soft natural light"
```

**Tips for Better Results:**
- Be descriptive but concise
- Include key visual elements
- Mention lighting, colors, or mood
- Use specific object names when possible

**Example Queries:**
```
"sunset over ocean"
"dog running in park"
"birthday party with cake"
"snowy mountain peak"
"vintage car on street"
"family dinner table"
"colorful street art"
"peaceful lake reflection"
```

### 3. **Hybrid Search** 🔄
*Combines metadata and semantic search with weighted scoring*

**Best for:**
- Complex searches requiring both technical and visual criteria
- Professional workflows needing precision
- Finding specific content with technical constraints

**How it Works:**
- Runs both metadata and semantic searches
- Combines results with weighted scoring:
  - **Metadata Weight**: 60% (precision)
  - **Semantic Weight**: 40% (content relevance)
- Normalizes and ranks results by combined score

**Query Structure:**
Use natural language that can work for both modes:

```
-- Technical + Visual
"Canon portrait" (finds Canon cameras + portrait content)
"macro flower" (finds macro lens + flower subjects)
"night city" (finds night settings + urban scenes)

-- Location + Content
"beach sunset" (finds beach locations + sunset lighting)
"mountain hiking" (finds mountain GPS + hiking activities)

-- Equipment + Style
"85mm portrait" (finds 85mm lens + portrait compositions)
"wide angle landscape" (finds wide lenses + landscape scenes)
```

**Example Hybrid Queries:**
```
"Sony street photography"
"wedding Canon 85mm"
"landscape wide angle"
"macro flower close-up"
"concert low light"
"travel sunset golden hour"
```

## UX Improvements

### 1. **Scroll to Top Button** ⬆️
- Appears when scrolling down more than 500px
- Smooth scroll animation back to top
- Positioned in bottom-right corner
- Accessible with keyboard navigation

### 2. **Interactive Timeline** 📅
- **Visual Timeline**: Shows photo distribution by month/year
- **Clickable Bars**: Click any timeline bar to filter photos from that period
- **Smart Filtering**: Automatically switches to metadata search mode
- **Hover Details**: Shows exact count and date information
- **Minimize Option**: Collapse timeline when not needed

**How Timeline Filtering Works:**
1. Click any bar in the timeline
2. Automatically generates date-based search query
3. Switches to metadata search mode for precision
4. Shows only photos from that time period
5. Clear search to return to full collection

### 3. **Enhanced Search Experience**
- **Mode Indicators**: Clear visual feedback for active search mode
- **Query Suggestions**: Contextual help for each search mode
- **Real-time Results**: Instant feedback as you type
- **Search History**: Remember recent successful queries
- **Export Integration**: Select and export search results

## Performance Notes

### Search Mode Performance:
- **Metadata**: Fastest (~10-50ms) - Direct SQL queries
- **Semantic**: Moderate (~200-500ms) - AI embedding comparison
- **Hybrid**: Slower (~300-800ms) - Combines both methods

### Optimization Tips:
- Use metadata search for known technical criteria
- Use semantic search for visual content discovery
- Use hybrid search when you need both precision and content relevance
- Timeline filtering is optimized for large collections

## Professional Workflows

### Portrait Photographers:
```sql
-- Metadata: Find all 85mm portraits
lens.focal_length = 85 AND camera.mode = "Portrait"

-- Semantic: Find emotional expressions
"happy couple portrait"

-- Hybrid: Combine technical and emotional
"85mm wedding portrait"
```

### Landscape Photographers:
```sql
-- Metadata: Golden hour timing
date.hour BETWEEN 6 AND 8 OR date.hour BETWEEN 17 AND 19

-- Semantic: Scenic content
"dramatic mountain landscape"

-- Hybrid: Technical + scenic
"wide angle sunset landscape"
```

### Event Photographers:
```sql
-- Metadata: High ISO low light
iso >= 1600 AND lens.aperture <= 2.8

-- Semantic: Event moments
"people dancing at party"

-- Hybrid: Technical + moments
"low light wedding reception"
```

## Advanced Tips

1. **Combine Filters**: Use type filters (photos/videos) with any search mode
2. **Sort Results**: Choose sorting that matches your workflow needs
3. **Timeline Navigation**: Use timeline for temporal organization
4. **Export Workflows**: Select results and export for client delivery
5. **Batch Operations**: Use selection mode for bulk actions

This search system is designed to scale with professional collections of 10,000+ photos while maintaining fast, relevant results.
