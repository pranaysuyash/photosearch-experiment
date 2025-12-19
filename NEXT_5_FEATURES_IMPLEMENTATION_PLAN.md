# Next Features - Implementation Plan

**Date**: 2025-12-18  
**Status**: Updated reality-check + next set  
**Priority**: Baseline completion + differentiation (no mobile v1)

---

## Reality Check (what already exists in this repo)

Several items that were “next” are already partially or fully implemented. This section prevents duplicated work and keeps execution aligned with the current codebase.

### Already implemented

- **Photo ratings (1–5 stars)**: API + UI are present (see `server/main.py` rating endpoints and `ui/src/components/gallery/PhotoDetail.tsx` rating section).
- **Import wizard UX**: An import page + wizard exist (`ui/src/pages/Import.tsx`, `ui/src/components/import/ImportWizard.tsx`).
- **People page (face clusters)**: A management UI exists (`ui/src/pages/People.tsx`) with labeling support.
- **Duplicates review lens**: UI + wiring exist (end-user review flow is present).
- **Editor wiring (non-destructive)**: Editor is wired into the viewer; save/load are hooked up.
- **People ↔ viewer integration**: Per-photo People chips + person filters are integrated.
- **Per-photo notes/captions**: Notes storage exists and is exposed via API/UI.
- **Export/share polish**: Export/share wiring is implemented (ZIP + metadata options and share flow hooks).

### Partially implemented (known gaps)

- **Face model reliability**: InsightFace model download URLs historically produced noisy 404s; multi-backend support is being added to reduce fragility and enable comparisons.

---

## 📋 Set A (carry-over): finish what’s partially done

These are the “must-have” items that already have some scaffolding and are fastest to complete cleanly.

### **A1. 🔄 Duplicates Review Lens (UI)**

**Priority**: P0 - Essential for any media library
**Current**: ✅ completed
**Impact**: Storage hygiene, trust, “standard app” credibility

### **A2. 🎨 Editor Wiring (non-destructive)**

**Priority**: P1 - Expected in modern photo apps
**Current**: ✅ completed
**Impact**: Keeps users in-product for “small fixes” and enables premium workflows

### **A3. 👥 People ↔ Viewer Integration**

**Priority**: P1 - Differentiator + baseline expectation now
**Current**: ✅ completed
**Impact**: Makes faces feel “real” rather than a separate demo page

### **A4. 🗒️ Per-photo Notes/Captions (Library metadata)**

**Priority**: P1 - Standard library capability
**Current**: ✅ completed
**Impact**: Enables pro workflows (“client note”, “shot list”, “deliverable status”) and improves search

### **A5. 📤 Export/Share Polish (beyond ZIP)**

**Priority**: P1 - Expected “finish”
**Current**: ✅ completed
**Impact**: Converts browsing into delivery (the moment users pay for)

---

## 📋 Set B: next set of 5 (after Set A)

Once Set A is done, these are the next five highest-leverage improvements to make the app feel complete (and uniquely “Living Museum”) without introducing mobile commitments.

### **B1. 🧭 Provenance Chips + Availability States (Local/Cloud/Offline)**

**Why**: Dual local + cloud is the product promise; the UI needs “where is this from?” and “can I open it now?”
**What**: Source chips in grid + viewer, plus clear states: `Available`, `Syncing`, `Offline`, `Degraded`.
**Unique**: Works across Globe/Timeline/Story as a “lens”, not a settings page.

### **B2. 🧹 Safe Bulk Actions (Undo + clear semantics)**

**Why**: “Delete” anxiety is the #1 churn driver in media apps.
**What**: Undo toast for Trash/Remove, and consistent copy: “Move to Trash” vs “Remove from Library”.
**Unique**: Calm feedback via notch-toasts + job popover, not modal spam.

### **B3. 🔎 Multi-tag Filtering (AND/OR)**

**Why**: Tags become truly useful only when combined (“trip” + “deliver” + “favorites”).
**What**: Extend search to accept multiple tags, keep chip-based UX in the notch.
**Unique**: Tags become “lenses” for Globe/Story (e.g., show only `#wedding`).

### **B4. 🧩 Version Stacks (edited copies + originals)**

**Why**: If we add an editor, users need a clean “original vs edited” story.
**What**: Group variants under one item with a “stack” affordance.
**Unique**: A “museum restoration” metaphor (original artifact + restorations).

### **B5. 🗺️ Place Correction + Location Clustering**

### **B6. 🙂 Multi-backend Face Models + Reliability**

**Why**: Face features must not depend on a single brittle model download path.
**What**: Support selecting face detection backends (InsightFace / MediaPipe / YOLO) and reduce noisy failures.
**Docs**: See `docs/FACE_MODELS_BACKENDS.md`.
**Notes**: Clustering still requires embeddings; today that means InsightFace.

**Why**: GPS is messy; people want “Paris” not raw coordinates.
**What**: Basic place naming/correction and clustering (city/country), feeding Globe/Places.
**Unique**: “Trips” and “Stories” become more compelling when places are human.

---

## Notes

- This plan intentionally avoids “mobile v1” commitments.
- Keep the glass/notch design language: baseline features should be calm surfaces and chips, not new dashboards.

---

## 📋 Set C: next set of 5 (after Set B)

These are the next five features that (a) reinforce the dual local + cloud promise, (b) increase “pro” utility, and (c) keep COGS low by avoiding becoming a storage company by default.

### **C1. 🔁 Backup Destinations (Drive + S3)**

**Why**: Users want “I never lose photos” without us hosting all originals.
**What**: Choose a local source → back up to a destination source (Google Drive or S3), with schedules + retention + verification.
**Unique**: “Connect your own backup” fits the Living Museum: your archive stays yours, we provide the control plane.

### **C2. 🔗 Share Links + Client Proofing (lightweight)**

**Why**: Export ZIP is not the final mile for agencies/teams.
**What**: Share an album/story as a link (view-only), optional selection + comments, expiry, and revocation.
**Unique**: Share “Stories” (not folders) and keep provenance visible (what source, when captured).

### **C3. 🧠 Smart Album Builder (rule UI)**

**Why**: Smart albums already exist; users need a way to create/edit rules.
**What**: Rule editor with calm chips (tags, ratings, dates, source, media type) + live match count.
**Unique**: Rules become reusable “lenses” for Globe/Timeline/Story.

### **C4. 🧾 Activity Log + Library Health (trust)**

**Why**: Dual-mode systems fail in invisible ways; users need confidence.
**What**: Recent activity feed (ingest/sync/index/export/restore) + health cards (last sync, errors, cache size).
**Unique**: Surface health in the notch/status popover, not a noisy admin dashboard.

### **C5. 🧪 Workflow Automations (import + curation)**

**Why**: Pros pay for “less clicking”.
**What**: Simple rules: on ingest from Source X → tag Y, add to Album Z, set rating, start face scan, etc.
**Unique**: Automation can trigger Story recipes (“Trip Story for last weekend”).

---

## 📋 Set D: next set of 5 (after Set C)

These focus on “Studio-grade” workflows and monetizable value, while still avoiding becoming a storage company by default.

### **D1. ✅ Selections + Approvals (agency workflow)**

**Why**: Agencies need a clear “pick/reject/deliver” pipeline.
**What**: Selection sets (not just albums): `Selects`, `Rejects`, `To Deliver`, `Delivered` with timestamps, notes, and batch actions.
**Unique**: Selections can be applied inside Story/Timeline/Globe as a lens (“Show only Selects in this Trip”).

### **D2. 🏷️ Metadata Editing + Sidecar Export (XMP)**

**Why**: Pro users expect captions/keywords/rights to be editable and portable.
**What**: Edit captions/keywords/ratings/rights; batch-apply; export to XMP sidecars (and/or keep in DB when read-only).
**Unique**: “Museum label” metaphor: curated captions and provenance become first-class.

### **D3. 🔄 Incremental Sync + Webhooks/Delta (Drive/S3)**

**Why**: Full re-scans don’t scale; cloud sync must feel reliable.
**What**: Delta tokens/webhooks where possible; periodic reconciliation; clear conflict rules; UI states for backlog/degraded.
**Unique**: Sync becomes a calm “health surface” rather than a confusing background mystery.

### **D4. 🧩 Integrations (Lightroom/Capture One)**

**Why**: Switching costs block adoption; import/export integrations unlock teams.
**What**: Import catalogs (at least keywords/ratings/collections); roundtrip export to working folders; preserve IDs.
**Unique**: Treat external tools as sources/destinations inside the same library model.

### **D5. 🔐 Workspaces + Sharing Controls (team-ready)**

**Why**: Collaboration is where high ARPU lives.
**What**: Workspaces with roles (viewer/editor/admin), share controls per album/story, audit-friendly activity.
**Unique**: “Studio” mode as a paid layer over the same library (no separate product).

---

## Appendix: Archived (superseded) draft plan

The remainder of this file is preserved from an older plan draft for reference, but it contains known inaccuracies (e.g., claiming ratings/import/people are unimplemented) and should not be used as the execution plan.

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
  1: SourceSelection; // Choose import source
  2: DestinationSetup; // Where to organize
  3: OrganizationRules; // Date/folder structure
  4: DuplicateHandling; // Skip/replace duplicates
  5: Progress; // Import progress
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
