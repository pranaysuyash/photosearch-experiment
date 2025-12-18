# Next 5 Must-Have Features - Implementation Plan
**Date**: 2025-12-18
**Status**: Ready for Implementation
**Priority**: Critical baseline completion

---

## 📋 5 Additional Must-Have Features Identified

After analyzing competitive requirements, user workflows, and existing roadmap, here are the next 5 essential features to complete the baseline:

### **1. 🔄 Duplicate Detection & Management**
**Priority**: P0 - Essential for any media library
**Gap**: Storage optimization and library hygiene
**Impact**: Prevents storage waste, improves organization

### **2. ⭐ Photo Rating System (1-5 Stars)**
**Priority**: P0 - Standard in all photo apps
**Gap**: Missing rating/ranking capability
**Impact**: Essential curation and workflow tool

### **3. 🎨 Basic Photo Editing (Crop, Rotate, Adjust)**
**Priority**: P1 - Expected in modern photo apps
**Gap**: No editing beyond rotation
**Impact**: Eliminates need for external editor for basic fixes

### **4. 👥 Face Recognition & People Management**
**Priority**: P1 - AI-powered differentiation
**Gap**: Face clustering exists but no UI integration
**Impact**: Major competitive advantage, leverages AI positioning

### **5. 🚀 Import Wizard & Bulk Organization**
**Priority**: P1 - Onboarding and workflow efficiency
**Gap**: No guided bulk import flow
**Impact**: Reduces friction for new users with large libraries

---

## 🔧 Implementation Details

### **Feature 1: Duplicate Detection & Management**

**Current Status**: ❌ Not implemented
**Backend Requirements**: Image hashing + perceptual comparison
**Frontend Requirements**: Duplicate review interface

#### **Implementation Plan**

**Backend (`server/duplicate_detection.py`)**:
```python
class DuplicateDetector:
    def find_duplicates(self, threshold=0.95):
        # MD5 hash for exact duplicates
        # Perceptual hash for near-duplicates
        # Return groups of similar images

    def get_duplicate_groups(self):
        # Return clustered duplicates for review
```

**Frontend (`ui/src/pages/Duplicates.tsx`)**:
- Glass design duplicate review interface
- Side-by-side comparison
- Bulk deletion with safety checks
- Preview thumbnails and metadata comparison

**API Endpoints**:
- `GET /api/duplicates` - Get duplicate groups
- `POST /api/duplicates/resolve` - Mark resolution decisions
- `DELETE /api/duplicates/remove` - Delete selected duplicates

**Design Integration**:
- Add "Duplicates" to ActionsPod navigation
- Use existing glass design patterns
- Progress indicator for scanning process

---

### **Feature 2: Photo Rating System (1-5 Stars)**

**Current Status**: ❌ Not implemented
**Database**: Add `rating` column to photos table
**UI Integration**: Rating picker + filter by rating

#### **Implementation Plan**

**Backend (`server/ratings.py`)**:
```python
# Add rating column to database schema
ALTER TABLE photos ADD COLUMN rating INTEGER DEFAULT 0;

# API endpoints for rating management
@app.post("/api/photos/{photo_path}/rating")
async def set_rating(photo_path: str, rating: int):
    # Validate rating 0-5, update database
```

**Frontend Components**:
- `StarRating.tsx` - Interactive 5-star picker
- `RatingFilter.tsx` - Filter by rating in search
- Integration in PhotoDetail quick actions
- Grid overlay showing ratings

**PhotoDetail Integration**:
```typescript
// Add to PhotoDetail.tsx quick actions
<button className="btn-glass btn-glass--muted" onClick={() => setRating(5)}>
  <Star size={14} />
  Rate
</button>
```

**Search Integration**:
- Add `rating:5` syntax to search
- Filter sidebar with star ratings
- Sort by rating option

---

### **Feature 3: Basic Photo Editing (Crop, Rotate, Adjust)**

**Current Status**: 🟡 Rotation exists, needs crop/adjust
**Approach**: Canvas-based editing with glass UI
**Non-destructive**: Save edits as separate files or metadata

#### **Implementation Plan**

**Frontend (`ui/src/components/editing/PhotoEditor.tsx`)**:
```typescript
interface EditingTools {
  crop: CropTool;
  brightness: number;
  contrast: number;
  saturation: number;
  rotation: number; // Extend existing
}
```

**Editing Modal**:
- Canvas-based editing interface
- Glass design toolbars
- Real-time preview
- Save/Cancel with confirmation

**Tools Implementation**:
1. **Crop Tool**: Draggable crop rectangle
2. **Adjustments**: Brightness/Contrast/Saturation sliders
3. **Rotation**: Extend existing rotation (90°, free rotation)

**Save Strategy**:
- Option 1: Save edited version as new file (`_edited` suffix)
- Option 2: Store edit instructions as metadata (non-destructive)

**Integration Points**:
- Add "Edit" button to PhotoDetail
- Keyboard shortcut (E key)
- Preserve existing glass design language

---

### **Feature 4: Face Recognition & People Management**

**Current Status**: 🟡 Backend exists, needs UI integration
**Existing**: `src/face_clustering.py` + `FaceClustering.tsx`
**Gap**: Full UI integration and management workflow

#### **Implementation Plan**

**UI Integration (`ui/src/pages/People.tsx`)**:
```typescript
// Face cluster management interface
interface FaceCluster {
  id: string;
  name?: string;
  faceCount: number;
  photoCount: number;
  thumbnail: string;
  photos: Photo[];
}
```

**People Management Workflow**:
1. **Face Detection**: Auto-detect faces on import
2. **Clustering**: Group similar faces
3. **Naming**: User assigns names to clusters
4. **Search**: Search by person name
5. **Albums**: Auto-create person albums

**Integration Points**:
- Add "People" to ActionsPod navigation
- People filter in search (`person:john`)
- Face thumbnails in photo metadata
- Auto-suggest people in tagging

**Face Detection Pipeline**:
- Integrate with existing job system
- Progress tracking for face detection jobs
- Background processing for large libraries

---

### **Feature 5: Import Wizard & Bulk Organization**

**Current Status**: 🟡 Basic source connection exists
**Gap**: Guided bulk import with organization options
**Focus**: First-time user experience and large library management

#### **Implementation Plan**

**Import Wizard (`ui/src/components/import/ImportWizard.tsx`)**:
```typescript
interface ImportWizardSteps {
  1: SourceSelection;    // Choose import source
  2: DestinationSetup;   // Where to organize
  3: OrganizationRules;  // Date/folder structure
  4: DuplicateHandling;  // Skip/replace duplicates
  5: Progress;           // Import progress
}
```

**Organization Options**:
- Date-based folders (`YYYY/MM/`)
- Event-based organization
- Maintain source structure
- Custom folder naming patterns

**Duplicate Handling**:
- Skip duplicates (default)
- Replace existing
- Keep both with suffix
- Review manually

**Bulk Operations**:
- Mass tagging during import
- Auto-album creation by date/event
- Batch metadata extraction
- Progress tracking and cancellation

**UI Integration**:
- Launch from first-run modal
- "Import More" action in sources panel
- Glass design wizard steps
- Clear progress indicators

---

## 🎯 Implementation Sequence

### **Phase 1: Foundation (Week 1)**
1. **Photo Rating System** - Quick win, high impact
2. **Duplicate Detection Backend** - Essential infrastructure

### **Phase 2: User Experience (Week 2)**
3. **Duplicate Detection UI** - Complete the detection feature
4. **Import Wizard** - Improve onboarding experience

### **Phase 3: Advanced Features (Week 3)**
5. **Basic Photo Editing** - Add editing capabilities
6. **Face Recognition Integration** - Complete existing face clustering

---

## 📊 Technical Specifications

### **Database Schema Changes**

```sql
-- Add rating column
ALTER TABLE photos ADD COLUMN rating INTEGER DEFAULT 0 CHECK (rating >= 0 AND rating <= 5);

-- Add duplicate groups table
CREATE TABLE duplicate_groups (
  id TEXT PRIMARY KEY,
  hash_type TEXT NOT NULL,
  photos JSON NOT NULL,
  resolved_at TEXT,
  resolution TEXT
);

-- Add face clusters table (if not exists)
CREATE TABLE face_clusters (
  id TEXT PRIMARY KEY,
  name TEXT,
  face_count INTEGER,
  photo_count INTEGER,
  created_at TEXT
);

-- Add photo edits table (non-destructive editing)
CREATE TABLE photo_edits (
  photo_path TEXT PRIMARY KEY,
  edit_data JSON,
  created_at TEXT,
  updated_at TEXT
);
```

### **API Endpoints**

```typescript
// Rating API
POST /api/photos/{path}/rating
GET /api/photos/by-rating/{rating}

// Duplicates API
GET /api/duplicates
POST /api/duplicates/scan
DELETE /api/duplicates/resolve

// Editing API
GET /api/photos/{path}/edits
POST /api/photos/{path}/edit
POST /api/photos/{path}/save-edit

// People API (extend existing)
GET /api/faces/people
POST /api/faces/clusters/{id}/name
GET /api/photos/by-person/{name}

// Import API
POST /api/import/wizard/start
GET /api/import/wizard/progress
POST /api/import/wizard/complete
```

### **Component Architecture**

```
ui/src/components/
├── duplicates/
│   ├── DuplicatesPage.tsx
│   ├── DuplicateGroup.tsx
│   └── DuplicateReview.tsx
├── editing/
│   ├── PhotoEditor.tsx
│   ├── CropTool.tsx
│   └── AdjustmentSliders.tsx
├── people/
│   ├── PeoplePage.tsx
│   ├── PersonCluster.tsx
│   └── FaceNaming.tsx
├── import/
│   ├── ImportWizard.tsx
│   ├── ImportProgress.tsx
│   └── OrganizationRules.tsx
└── rating/
    ├── StarRating.tsx
    └── RatingFilter.tsx
```

---

## 🔒 Design System Compliance

### **Glass Design Integration**
- All new components use `glass.surface` patterns
- Button styles follow `btn-glass` variants
- Consistent spacing and typography
- Calm animations and transitions

### **Interaction Patterns**
- Keyboard shortcuts for all major actions
- Context menus for secondary actions
- Progress indicators for long operations
- Confirmation dialogs for destructive actions

### **Accessibility**
- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader compatibility
- Focus management in modals

---

## ⚡ Performance Considerations

### **Duplicate Detection**
- Background processing for large libraries
- Incremental scanning (new photos only)
- Efficient hash storage and comparison
- Progress reporting and cancellation

### **Face Recognition**
- GPU acceleration when available
- Batch processing for efficiency
- Progressive enhancement (works without GPU)
- Optional feature (can be disabled)

### **Photo Editing**
- Canvas-based rendering for performance
- Lazy loading of editing tools
- Memory management for large images
- WebGL acceleration when available

---

## 🧪 Testing Strategy

### **Unit Tests**
- Duplicate detection algorithms
- Rating system validation
- Face clustering accuracy
- Import wizard workflow

### **Integration Tests**
- API endpoint functionality
- Database schema migrations
- File system operations
- Cross-component interactions

### **E2E Tests**
- Complete import workflow
- Duplicate resolution process
- Photo editing and saving
- People naming and search

---

## 📈 Success Metrics

### **Feature Adoption**
- Rating usage (% of photos rated)
- Duplicate resolution rate
- Editing feature engagement
- People tagging completion

### **User Experience**
- Import completion rates
- Time to first successful search
- Feature discovery metrics
- Error rates and user friction

### **Performance**
- Duplicate scan speed
- Face detection accuracy
- Editing responsiveness
- Import throughput

---

**Next Steps**: Begin implementation with Phase 1 features (Rating System + Duplicate Detection Backend) for immediate user value and foundation for advanced features.