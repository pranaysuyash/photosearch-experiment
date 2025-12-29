# PhotoSearch Metadata Extraction - Complete Roadmap

**Date**: 2025-12-29
**Status**: Comprehensive implementation plan
**Scope**: Path from 240 fields → 7,870+ fields

---

## Executive Summary

This roadmap integrates all metadata documentation into a phased implementation plan:

| Document | Fields Documented | Purpose |
|----------|-------------------|---------|
| `COMPLETE_METADATA_CATALOG.md` | 240 | Currently implemented |
| `METADATA_GAPS_ANALYSIS.md` | +360 | High-priority missing fields |
| `METADATA_COMPLETE_EXHAUSTIVE.md` | +1,270 | Vendor-specific & specialized |
| `METADATA_COMPLETE_UNIVERSE.md` | +6,000 | DICOM, FITS, all codecs, future standards |
| **TOTAL UNIVERSE** | **~7,870** | **Complete metadata ecosystem** |

**Realistic Target for PhotoSearch**: 740-1,500 fields (Phases 1-4)
**Coverage**: 9-19% of total universe = **Best-in-class** for general photo management

---

## Phase 1: Critical Gaps (Q1 2026)
**Timeline**: 6-8 weeks
**Fields**: 240 → 360 (+120)
**Priority**: HIGH - Essential for professional use

### 1.1 IPTC Core (50 fields)
**Effort**: 3 days
**Library**: `iptcinfo3`
**Why**: Industry standard for professional photography

**Key Fields**:
- Rights Management: Copyright, credit, source, rights usage
- Creator Info: Photographer, contact details
- Location: City, state, country, sublocation
- Content: Title, headline, description, keywords
- Workflow: Job ID, instructions

**Implementation**:
```python
# src/metadata_extractor.py
def extract_iptc_metadata(filepath: str) -> Dict[str, Any]:
    from iptcinfo3 import IPTCInfo
    info = IPTCInfo(filepath)
    return {
        'copyright': info['copyright notice'],
        'creator': info['by-line'],
        'title': info['object name'],
        'keywords': info['keywords'],
        # ... 46 more fields
    }
```

### 1.2 XMP Dublin Core (15 fields)
**Effort**: 2 days
**Library**: `python-xmp-toolkit`

**Key Fields**:
- dc:title, dc:description, dc:creator
- dc:subject, dc:rights, dc:publisher
- dc:date, dc:format

### 1.3 Perceptual Hashing (5 fields)
**Effort**: 1 day
**Library**: `imagehash`

**Fields**:
- phash, dhash, ahash, whash, colorhash

**Use Case**: Duplicate detection, similar image search

### 1.4 Reverse Geocoding (10 fields)
**Effort**: 2 days
**API**: OpenStreetMap Nominatim

**Fields**:
- location_name, city, state, country
- postal_code, neighborhood, timezone

### 1.5 Color Palette (10 fields)
**Effort**: 1 day
**Library**: `scikit-learn` (k-means)

**Fields**:
- dominant_colors (top 5), color_histogram
- Average RGB, color_vibrancy

### 1.6 Mobile Basics (30 fields)
**Effort**: 2 days

**iPhone** (15 fields):
- Live Photo metadata, Portrait mode, HDR info
- Burst UUID, Content ID

**Android** (15 fields):
- Night Sight, Motion Photo, HDR+
- Device model, scene mode

**Phase 1 Total**: 11 dev days, ~360 cumulative fields

---

## Phase 2: Professional Features (Q2-Q3 2026)
**Timeline**: 8-10 weeks
**Fields**: 360 → 540 (+180)
**Priority**: MEDIUM-HIGH - Competitive parity

### 2.1 Extended XMP (50 fields)
**Effort**: 4 days

**Adobe Camera Raw** (30 fields):
- Temperature, Tint, Exposure, Shadows
- Highlights, Whites, Blacks, Clarity
- Vibrance, Saturation, all adjustment sliders

**Photoshop** (20 fields):
- Layer info, edit history, text layers

### 2.2 Top Vendor MakerNotes (200 fields)
**Effort**: 5 days
**Library**: Enhanced `exifread` parsing or `exiftool`

**Canon** (50 fields):
- Picture Style settings, AF info, dual pixel data
- Color data, lens corrections

**Nikon** (50 fields):
- Active D-Lighting, VR info, Picture Control
- Flash info, focus settings

**Sony** (50 fields):
- DRO levels, creative style, focus modes
- Lens corrections, image stabilization

**Fujifilm** (50 fields):
- Film simulation, dynamic range
- Color chrome, grain effect

### 2.3 Extended Audio Tags (40 fields)
**Effort**: 2 days

**MusicBrainz IDs** (10 fields):
- Track ID, album ID, artist ID, release group ID

**ReplayGain** (4 fields):
- Track gain/peak, album gain/peak

**Podcast** (10 fields):
- Podcast URL, category, description, episode ID

**Advanced** (16 fields):
- BPM, initial key, mood, composer
- Album artist sort, disc number

### 2.4 Quality Metrics (15 fields)
**Effort**: 3 days
**Library**: `opencv-python`, `scikit-image`

**Fields**:
- BRISQUE score, sharpness, blur detection
- Noise level, contrast, edge density
- JPEG quality estimate

### 2.5 Temporal/Astronomical (25 fields)
**Effort**: 2 days
**Library**: `ephem` or `astropy`

**Solar** (10 fields):
- Sun azimuth/altitude, golden hour flag
- Sunrise/sunset times, solar noon

**Lunar** (10 fields):
- Moon phase, illumination, position

**Context** (5 fields):
- Day length, season, twilight times

### 2.6 Advanced Video Codec (50 fields)
**Effort**: 3 days

**H.264/265** (30 fields):
- Profile, level, entropy coding, ref frames
- B-pyramid, deblock filter

**VP9/AV1** (20 fields):
- Tile configuration, row multithreading
- Film grain synthesis

**Phase 2 Total**: 19 dev days, ~540 cumulative fields

---

## Phase 3: Advanced Capabilities (Q3-Q4 2026)
**Timeline**: 12 weeks
**Fields**: 540 → 740 (+200)
**Priority**: MEDIUM - Power user features

### 3.1 RAW File Support (25 fields)
**Effort**: 4 days
**Library**: `rawpy`

**DNG Fields** (15 fields):
- Color matrices, calibration data
- Black/white levels, crop info

**Manufacturer RAW** (10 fields):
- CR2/CR3, NEF, ARW specific fields

### 3.2 Specialized Equipment (50 fields)
**Effort**: 3 days

**Drones** (18 fields):
- Flight altitude, speed, gimbal angles
- RTK positioning, battery level

**360° Cameras** (13 fields):
- Projection type, initial view angles
- Cropped area dimensions

**Action Cameras** (12 fields):
- ProTune settings, FOV, stabilization
- Video mode

**Webcams** (7 fields):
- Streaming resolution, bitrate, encoder

### 3.3 Workflow/DAM (40 fields)
**Effort**: 3 days

**Asset Management**:
- Asset ID, version, workflow state
- Approval status, assigned to, due date
- Project info, client name, job number

### 3.4 Professional Codecs (60 fields)
**Effort**: 4 days

**ProRes** (20 fields):
- Profile, codec tag, color primaries
- Matrix coefficients, alpha channel

**DNxHD/HR** (15 fields):
- Compression ID, bitrate, bit depth

**LAME MP3** (20 fields):
- VBR method, quality preset, encoder delay
- ReplayGain, psychoacoustic settings

**Dolby Digital/DTS** (5 fields):

### 3.5 PLUS Licensing (25 fields)
**Effort**: 2 days

**Fields**:
- Licensor info, image creator, copyright owner
- Model/property release status
- Usage terms, expiration date

**Phase 3 Total**: 16 dev days, ~740 cumulative fields

---

## Phase 4: Extensibility Framework (Q4 2026)
**Timeline**: 6 weeks
**Fields**: 740 → 740+ (unlimited via plugins)
**Priority**: HIGH - Future-proofing

### 4.1 Custom XMP Namespace Support
**Effort**: 10 days

**Features**:
- User-defined XMP schemas
- Import/export namespace definitions
- Dynamic field registration
- UI for custom field mapping

### 4.2 Plugin Architecture
**Effort**: 15 days

**Features**:
- Metadata extractor plugins
- Custom field definitions
- Third-party integrations
- Plugin marketplace/registry

**Examples**:
```python
# plugins/real_estate_metadata.py
class RealEstateMetadataPlugin(MetadataPlugin):
    namespace = "realestate"

    def extract(self, filepath):
        return {
            'property_type': ...,
            'listing_price': ...,
            'square_feet': ...,
        }
```

**Phase 4 Total**: 25 dev days, Unlimited extensibility

---

## Phase 5: Specialized Domains (2027+)
**Timeline**: As needed / Plugin-based
**Fields**: 740+ → 1,240+ (+500)
**Priority**: LOW-MEDIUM - Niche markets

### 5.1 DICOM Medical Imaging (Plugin)
**Total Fields**: 4,000+
**Implementation Tiers**:

**Tier 1: Basic** (50 fields) - 5 days
- Patient info (anonymized)
- Study/Series IDs
- Equipment info
- Image dimensions
- Modality type

**Tier 2: Clinical** (200 fields) - 10 days
- CT: KVP, reconstruction kernel, dose
- MRI: TR, TE, field strength, sequences
- Ultrasound: transducer frequency, Doppler
- X-Ray: exposure settings

**Tier 3: Research** (500+ fields) - 5+ days
- Advanced modality parameters
- Private tags
- Waveforms

**Use Cases**:
- Medical photo management
- Research institutions
- Healthcare integration

### 5.2 FITS Astronomy (Plugin)
**Total Fields**: 500+
**Implementation Tiers**:

**Tier 1: Basic** (30 fields) - 3 days
- WCS coordinates (RA/DEC)
- Object name, telescope, instrument
- Exposure time, filter, date

**Tier 2: Astrophotography** (100 fields) - 7 days
- All WCS keywords
- Calibration status (flat, dark, bias)
- Stacking info, processing history
- Photometry basics

**Tier 3: Professional** (300+ fields) - 5+ days
- Spectroscopy keywords
- Radio astronomy
- Advanced calibration

**Use Cases**:
- Astrophotography management
- Observatory data
- Amateur astronomy

### 5.3 Regional Extensions (Plugins)

**Japanese** (80 fields) - 5 days
- JEITA standards
- ARIB broadcast metadata

**European** (80 fields) - 5 days
- EBU Core
- European IPTC extensions

**Chinese/Other** (40 fields) - 3 days
- CPCA copyright
- Regional variations

**Phase 5 Total**: 38+ dev days (as needed), ~1,240+ cumulative

---

## Phase 6: Future Standards (2025-2028+)
**Timeline**: Ongoing
**Fields**: 1,240+ → 1,500+ (+260)
**Priority**: CUTTING EDGE - Stay current

### 6.1 C2PA / Content Credentials (2025-2026)
**Effort**: 8 days
**Fields**: 80

**Purpose**: AI provenance, deepfake prevention

**Key Fields**:
- Claim generator, signature, assertions
- Actions taken (edits, AI generation)
- Ingredients (source materials)
- AI model info, human review flags

### 6.2 XR/Spatial Media (2026-2027)
**Effort**: 6 days
**Fields**: 60

**VR/360** (40 fields):
- Projection type, stereo mode
- Initial view angles, crop regions
- Full panorama dimensions

**AR** (20 fields):
- Anchor type, scale, position/rotation
- Lighting estimates

### 6.3 HDR10+ / Dolby Vision (2026)
**Effort**: 5 days
**Fields**: 50

**HDR10+** (25 fields):
- Dynamic metadata per scene
- Target luminance, distribution

**Dolby Vision** (25 fields):
- Proprietary enhancement layers

### 6.4 Environmental/IoT (2027+)
**Effort**: 4 days
**Fields**: 30

**Sensors**:
- Temperature, humidity, pressure
- Air quality, UV index, noise level

**IoT**:
- Device ID, network ID, battery
- Edge processing flags

### 6.5 Web3/Decentralized (2027+)
**Effort**: 3 days
**Fields**: 20

**IPFS/Filecoin**:
- Content ID (CID), multihash
- Pin count, storage info

**Blockchain**:
- Transaction hash, block height

### 6.6 Biometric/Behavioral (2028+)
**Effort**: 4 days
**Fields**: 20

**Eye Tracking** (VR/AR):
- Gaze points, fixations, pupil diameter

**Emotion Detection**:
- Detected emotions, confidence scores

**Phase 6 Total**: 30+ dev days (ongoing), ~1,500+ cumulative

---

## Implementation Timeline Summary

| Phase | Timeline | Dev Days | Calendar Time | Fields Added | Cumulative | Priority |
|-------|----------|----------|---------------|--------------|------------|----------|
| **Current** | - | - | - | 0 | 240 | ✅ Complete |
| **Phase 1** | Q1 2026 | 11 | 6-8 weeks | +120 | 360 | 🔴 HIGH |
| **Phase 2** | Q2-Q3 2026 | 19 | 8-10 weeks | +180 | 540 | 🟡 MED-HIGH |
| **Phase 3** | Q3-Q4 2026 | 16 | 12 weeks | +200 | 740 | 🟡 MEDIUM |
| **Phase 4** | Q4 2026 | 25 | 6 weeks | Unlimited | 740+ | 🔴 HIGH |
| **Phase 5** | 2027+ | 38+ | As needed | +500 | 1,240+ | 🟢 LOW-MED |
| **Phase 6** | 2025-2028+ | 30+ | Ongoing | +260 | 1,500+ | 🔵 FUTURE |
| **TOTAL** | ~2 years | **139+ days** | **Phased** | **+1,260** | **1,500+** | - |

---

## Resource Requirements

### Team Composition

**Phase 1-3** (2026):
- 1-2 Backend developers
- 1 Frontend developer (for UI integration)
- 0.5 QA engineer

**Phase 4** (Plugin architecture):
- 2 Backend developers
- 1 Frontend developer
- 1 DevOps engineer (plugin deployment)

**Phase 5-6** (Ongoing):
- 1 Backend developer (as needed)
- Community contributors

### Library Dependencies

**Phase 1**:
```
iptcinfo3==2.0.0
python-xmp-toolkit==2.0.1
imagehash==4.3.1
geopy==2.4.1
scikit-learn==1.3.2
```

**Phase 2**:
```
opencv-python==4.8.1.78
ephem==4.1.5
mutagen==1.47.0 (extended use)
```

**Phase 3**:
```
rawpy==0.19.0
ffmpeg-python==0.2.0 (extended parsing)
```

**Phase 5**:
```
pydicom==2.4.4 (optional)
astropy==6.0.0 (optional)
```

**Phase 6**:
```
# Future libraries TBD as standards emerge
```

### Database Schema Evolution

**Phase 1**: Add columns
```sql
ALTER TABLE metadata ADD COLUMN iptc_copyright TEXT;
ALTER TABLE metadata ADD COLUMN iptc_creator TEXT;
ALTER TABLE metadata ADD COLUMN xmp_title TEXT;
ALTER TABLE metadata ADD COLUMN phash TEXT;
ALTER TABLE metadata ADD COLUMN location_city TEXT;
ALTER TABLE metadata ADD COLUMN dominant_color_1 TEXT;
-- ... ~120 new columns
```

**Phase 2**: Separate tables for complex data
```sql
CREATE TABLE vendor_makernote (
    file_path TEXT PRIMARY KEY,
    canon_data JSONB,
    nikon_data JSONB,
    sony_data JSONB,
    fuji_data JSONB
);

CREATE TABLE audio_extended (
    file_path TEXT PRIMARY KEY,
    musicbrainz_track_id TEXT,
    replaygain_track_gain REAL,
    bpm INTEGER,
    key TEXT
);
```

**Phase 3**: Specialized tables
```sql
CREATE TABLE raw_metadata (
    file_path TEXT PRIMARY KEY,
    color_matrix_1 TEXT,
    camera_calibration TEXT,
    black_levels TEXT
);
```

**Phase 4**: Dynamic schema
```sql
CREATE TABLE custom_metadata (
    file_path TEXT,
    namespace TEXT,
    field_name TEXT,
    field_value TEXT,
    PRIMARY KEY (file_path, namespace, field_name)
);
```

---

## Success Metrics

### Phase 1 KPIs
- ✅ IPTC extraction success rate >95%
- ✅ Duplicate detection accuracy >98%
- ✅ Reverse geocoding latency <500ms
- ✅ Color palette extraction <100ms per image
- ✅ Mobile metadata coverage >90% for iPhone/Pixel

### Phase 2 KPIs
- ✅ MakerNote parsing success for top 4 brands >90%
- ✅ Music metadata completeness >95%
- ✅ Quality score correlation with human judgment >0.8
- ✅ Astronomical calculations accurate to ±1 minute

### Phase 3 KPIs
- ✅ RAW file support for top 4 manufacturers
- ✅ Drone metadata extraction from DJI >95%
- ✅ ProRes metadata completeness >90%

### Phase 4 KPIs
- ✅ 5+ community plugins published
- ✅ Custom namespace creation <5 minutes
- ✅ Plugin installation <30 seconds

### Overall Success
- ✅ Competitive with Adobe Bridge
- ✅ Better metadata coverage than Apple Photos
- ✅ Extensible beyond ExifTool

---

## Competitive Analysis

### vs. ExifTool
| Metric | ExifTool | PhotoSearch (Target) | Advantage |
|--------|----------|----------------------|-----------|
| **Total Fields** | ~4,500 | 1,500+ | ExifTool (specialization) |
| **Core Photography** | ~600 | 740 | PhotoSearch (UI, search) |
| **User Interface** | CLI only | Modern web UI | PhotoSearch |
| **Search** | grep | Advanced filters, AI | PhotoSearch |
| **Speed** | Very fast | Fast enough | ExifTool |
| **Extensibility** | Config files | Plugin system | PhotoSearch |

### vs. Adobe Bridge
| Metric | Adobe Bridge | PhotoSearch (Target) | Advantage |
|--------|--------------|----------------------|-----------|
| **Total Fields** | ~600 | 740 | PhotoSearch |
| **XMP Support** | Excellent | Good | Adobe Bridge |
| **Price** | $9.99/month | Free (open source) | PhotoSearch |
| **AI Features** | Limited | Face recognition, VLM | PhotoSearch |
| **Platform** | Desktop only | Web-based | PhotoSearch |
| **Speed** | Fast | Fast | Tie |

### vs. Photo Mechanic
| Metric | Photo Mechanic | PhotoSearch (Target) | Advantage |
|--------|----------------|----------------------|-----------|
| **Total Fields** | ~400 | 740 | PhotoSearch |
| **Ingest Speed** | Very fast | Fast | Photo Mechanic |
| **IPTC/XMP** | Excellent | Excellent | Tie |
| **Price** | $139 | Free | PhotoSearch |
| **Sports Photography** | Excellent | Good | Photo Mechanic |
| **Search** | Basic | Advanced | PhotoSearch |

**Conclusion**: PhotoSearch targets the sweet spot between consumer tools (Apple Photos) and professional tools (ExifTool, Photo Mechanic), with modern UX and AI integration.

---

## Risk Assessment & Mitigation

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| **Performance degradation with 1000+ fields** | High | Medium | Lazy loading, database indexing, caching |
| **Library compatibility issues** | Medium | Medium | Version pinning, extensive testing |
| **Plugin ecosystem doesn't emerge** | Low | Low | Seed with official plugins, documentation |
| **DICOM/FITS bloat for general users** | Medium | High | Optional plugins, not in core |
| **Maintenance burden** | High | High | Modular architecture, automated tests |
| **New standards change rapidly** | Medium | High | Plugin system, rolling updates |

---

## Next Steps (Immediate Actions)

### 1. Review & Approval
- [ ] Stakeholder review of roadmap
- [ ] Prioritize Phase 1 features
- [ ] Budget approval for resources

### 2. Phase 1 Kickoff (Week 1)
- [ ] Set up development branch `feature/metadata-phase-1`
- [ ] Install dependencies (`iptcinfo3`, `python-xmp-toolkit`, etc.)
- [ ] Create database migration scripts
- [ ] Set up automated tests

### 3. Sprint Planning (Week 2)
- [ ] Break Phase 1 into 2-week sprints
- [ ] Assign developers to tasks
- [ ] Set up CI/CD for metadata tests
- [ ] Create UI mockups for new fields

### 4. Implementation (Weeks 3-8)
- [ ] Implement IPTC extraction
- [ ] Implement XMP Dublin Core
- [ ] Implement perceptual hashing
- [ ] Implement reverse geocoding
- [ ] Implement color palette
- [ ] Implement mobile metadata
- [ ] Integration testing
- [ ] Documentation

### 5. Release (Week 9)
- [ ] Beta release to early adopters
- [ ] Gather feedback
- [ ] Bug fixes
- [ ] Production deployment
- [ ] Announce Phase 1 completion
- [ ] Plan Phase 2

---

## Conclusion

This roadmap provides a clear path from PhotoSearch's current **240 fields** to a best-in-class **1,500+ field** metadata extraction system, with extensibility to support the entire **7,870 field universe** through plugins.

**Key Takeaways**:
1. ✅ **Phases 1-3** (740 fields) make PhotoSearch competitive with professional tools
2. ✅ **Phase 4** (extensibility) future-proofs the architecture
3. ✅ **Phases 5-6** (specialized/future) address niche markets without bloat
4. ✅ **~2 year timeline** is realistic for full implementation
5. ✅ **Open source** + **modern UX** + **AI integration** = differentiation

**Decision Point**: Approve Phase 1 to begin implementation in Q1 2026.

---

**Document Status**: COMPLETE
**Ready for**: Stakeholder Review → Implementation
