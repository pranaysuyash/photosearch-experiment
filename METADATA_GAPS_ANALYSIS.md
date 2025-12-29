# Missing Metadata Fields - Gap Analysis

**Date**: 2025-12-29
**Scope**: Media files (Images, Videos, Audio) - excluding PDFs/docs
**Purpose**: Identify metadata fields NOT currently extracted by PhotoSearch

---

## Summary

The COMPLETE_METADATA_CATALOG.md documents **240+ implemented fields**, but there are additional metadata fields that exist in media files that PhotoSearch doesn't currently extract:

---

## 1. IMAGE METADATA GAPS

### ❌ IPTC Core (Not Implemented)
**Standard**: IPTC Core Schema (professional photography metadata)
**Library Needed**: `iptcinfo3` or `python-xmp-toolkit`

| Field | IPTC Tag | Description |
|-------|----------|-------------|
| **Rights Management** |
| `copyright_notice` | Copyright Notice | Copyright text |
| `rights_usage_terms` | Rights Usage Terms | Licensing terms |
| `web_statement` | Web Statement of Rights | URL to rights statement |
| `credit_line` | Credit Line | Required credit line |
| `source` | Source | Original image source |
| **Creator Info** |
| `creator` | Creator | Photographer name |
| `creator_job_title` | Creator's Job Title | Role/position |
| `creator_address` | Creator's Address | Contact address |
| `creator_city` | Creator's City | City |
| `creator_region` | Creator's State/Province | State/province |
| `creator_postal_code` | Creator's Postal Code | Postal code |
| `creator_country` | Creator's Country | Country |
| `creator_phone` | Creator's Phone | Phone numbers |
| `creator_email` | Creator's Email | Email addresses |
| `creator_website` | Creator's Website | Website URLs |
| **Content Description** |
| `title` | Title | Image title |
| `headline` | Headline | Brief headline |
| `description` | Description/Caption | Full description |
| `keywords` | Keywords | Keyword tags (array) |
| `subject_code` | Subject Code | IPTC subject codes |
| `description_writer` | Description Writer | Who wrote caption |
| **Location** |
| `location` | Sublocation | Specific location |
| `city` | City | City name |
| `state_province` | Province/State | State/province |
| `country_name` | Country Name | Country |
| `country_code` | Country Code | ISO country code |
| `world_region` | World Region | Geographic region |
| `location_shown` | Location Shown | Places visible in image |
| `location_created` | Location Created | Where photo was taken |
| **Event/Scene** |
| `event` | Event | Event name |
| `scene_code` | Scene Code | IPTC scene codes |
| `intellectual_genre` | Intellectual Genre | Genre classification |
| **Date/Time** |
| `date_created` | Date Created | Creation date |
| `digital_creation_date` | Digital Creation Date | Digitization date |
| **Workflow** |
| `instructions` | Instructions | Special instructions |
| `job_id` | Job Identifier | Job/assignment ID |
| `transmission_reference` | Transmission Reference | Routing info |
| **Image Properties** |
| `max_avail_width` | Max Avail Width | Max available width |
| `max_avail_height` | Max Avail Height | Max available height |
| `source_type` | Source Type | Image source type |

### ❌ XMP (Extensible Metadata Platform) - Not Implemented
**Standard**: Adobe XMP
**Library Needed**: `python-xmp-toolkit` or `libxmp`

| Field | XMP Namespace | Description |
|-------|---------------|-------------|
| **Dublin Core** |
| `dc:title` | dc | Title |
| `dc:description` | dc | Description |
| `dc:creator` | dc | Creator |
| `dc:subject` | dc | Keywords/subjects |
| `dc:rights` | dc | Copyright/rights |
| `dc:publisher` | dc | Publisher |
| `dc:contributor` | dc | Contributors |
| `dc:date` | dc | Date |
| `dc:format` | dc | File format |
| `dc:identifier` | dc | Unique identifier |
| `dc:language` | dc | Language |
| `dc:coverage` | dc | Spatial/temporal coverage |
| **Photoshop** |
| `photoshop:AuthorsPosition` | photoshop | Author's position |
| `photoshop:CaptionWriter` | photoshop | Caption writer |
| `photoshop:Category` | photoshop | Category |
| `photoshop:City` | photoshop | City |
| `photoshop:Country` | photoshop | Country |
| `photoshop:Credit` | photoshop | Credit |
| `photoshop:DateCreated` | photoshop | Date created |
| `photoshop:Headline` | photoshop | Headline |
| `photoshop:Instructions` | photoshop | Instructions |
| `photoshop:Source` | photoshop | Source |
| `photoshop:State` | photoshop | State/province |
| `photoshop:SupplementalCategories` | photoshop | Supplemental categories |
| `photoshop:TransmissionReference` | photoshop | Transmission reference |
| `photoshop:Urgency` | photoshop | Urgency (1-8) |
| `photoshop:ColorMode` | photoshop | Color mode |
| `photoshop:ICCProfile` | photoshop | ICC profile name |
| **Camera Raw** |
| `crs:Version` | crs | Camera Raw version |
| `crs:WhiteBalance` | crs | White balance |
| `crs:Temperature` | crs | Color temperature |
| `crs:Tint` | crs | Tint |
| `crs:Exposure` | crs | Exposure adjustment |
| `crs:Shadows` | crs | Shadows adjustment |
| `crs:Brightness` | crs | Brightness |
| `crs:Contrast` | crs | Contrast |
| `crs:Saturation` | crs | Saturation |
| `crs:Sharpness` | crs | Sharpness |
| `crs:LuminanceSmoothing` | crs | Luminance noise reduction |
| `crs:ColorNoiseReduction` | crs | Color noise reduction |
| `crs:ChromaticAberration` | crs | Chromatic aberration |
| `crs:VignetteAmount` | crs | Vignette amount |
| `crs:ShadowTint` | crs | Shadow tint |
| `crs:RedHue` | crs | Red hue |
| `crs:RedSaturation` | crs | Red saturation |
| `crs:GreenHue` | crs | Green hue |
| `crs:GreenSaturation` | crs | Green saturation |
| `crs:BlueHue` | crs | Blue hue |
| `crs:BlueSaturation` | crs | Blue saturation |
| `crs:HasSettings` | crs | Has adjustments |
| `crs:HasCrop` | crs | Has crop |
| `crs:AlreadyApplied` | crs | Adjustments applied |
| **Lightroom** |
| `lr:hierarchicalSubject` | lr | Hierarchical keywords |
| `lr:privateRTKInfo` | lr | Lightroom catalog info |
| **EXIF Extended** |
| `exif:GPSVersionID` | exif | GPS version |
| `exif:GPSProcessingMethod` | exif | GPS processing method |
| `exif:GPSAreaInformation` | exif | GPS area name |
| `exif:GPSDifferential` | exif | GPS differential correction |
| `exif:ImageUniqueID` | exif | Unique image ID |
| `exif:CameraOwnerName` | exif | Camera owner |
| `exif:BodySerialNumber` | exif | Camera serial number |
| `exif:LensSerialNumber` | exif | Lens serial number |
| `exif:LensSpecification` | exif | Lens specification |
| `exif:Gamma` | exif | Gamma value |
| **TIFF Extended** |
| `tiff:ImageID` | tiff | Image identifier |
| `tiff:Rating` | tiff | Star rating (0-5) |
| `tiff:RatingPercent` | tiff | Rating percentage |
| **PDF/A** |
| `pdfaid:part` | pdfaid | PDF/A version part |
| `pdfaid:conformance` | pdfaid | PDF/A conformance |

### ❌ Perceptual Hashing (Not Implemented)
**Purpose**: Duplicate detection, similarity search
**Library**: `imagehash`, `pillow`

| Field | Algorithm | Description |
|-------|-----------|-------------|
| `phash` | Perceptual Hash | Robust to minor changes |
| `dhash` | Difference Hash | Detects gradient changes |
| `ahash` | Average Hash | Fast, basic similarity |
| `whash` | Wavelet Hash | Frequency-based |
| `colorhash` | Color Hash | Color distribution |

### ❌ Advanced Image Analysis (Not Implemented)
**Purpose**: Computer vision, quality assessment
**Libraries**: `opencv-python`, `numpy`, `scikit-image`

| Field | Type | Description |
|-------|------|-------------|
| **Color Analysis** |
| `dominant_colors` | array | Top N colors (RGB) via k-means |
| `color_palette` | array | Color palette (hex codes) |
| `color_histogram.red` | array | Red channel histogram |
| `color_histogram.green` | array | Green channel histogram |
| `color_histogram.blue` | array | Blue channel histogram |
| `color_temperature` | integer | Estimated color temp (K) |
| `color_vibrancy` | float | Color vibrancy score |
| **Exposure/Quality** |
| `brightness_histogram` | array | Luminance distribution |
| `exposure_quality` | string | "underexposed" / "normal" / "overexposed" |
| `contrast_level` | float | Contrast score (0-1) |
| `sharpness_score` | float | Sharpness metric |
| `noise_level` | float | Estimated noise |
| `dynamic_range` | float | Tonal range |
| **Composition** |
| `faces_detected` | integer | Number of faces |
| `face_locations` | array | Face bounding boxes |
| `rule_of_thirds_score` | float | Rule of thirds compliance |
| `symmetry_score` | float | Symmetry metric |
| **Technical** |
| `blur_score` | float | Blur detection (0=sharp, 1=blurry) |
| `jpeg_quality` | integer | Estimated JPEG quality (1-100) |
| `compression_artifacts` | float | Compression artifact score |
| `moiré_detected` | boolean | Moiré pattern detected |

### ❌ Geolocation Enhancements (Not Implemented)
**Purpose**: Reverse geocoding
**API**: OpenStreetMap Nominatim, Google Geocoding

| Field | Type | Description |
|-------|------|-------------|
| `location_name` | string | Human-readable location |
| `address` | string | Full address |
| `street` | string | Street name |
| `neighborhood` | string | Neighborhood |
| `city` | string | City name |
| `county` | string | County |
| `state` | string | State/province |
| `postal_code` | string | Postal code |
| `country` | string | Country name |
| `country_code` | string | ISO country code |
| `continent` | string | Continent |
| `timezone` | string | Timezone (e.g., "America/New_York") |
| `elevation` | float | Elevation (meters) |
| `weather.temperature` | float | Temperature at capture time (if available) |
| `weather.conditions` | string | Weather conditions |
| `sunrise_time` | timestamp | Sunrise time for that location/date |
| `sunset_time` | timestamp | Sunset time |
| `golden_hour` | boolean | Captured during golden hour |
| `blue_hour` | boolean | Captured during blue hour |

### ❌ RAW Image Metadata (Limited Support)
**Purpose**: Professional RAW file support (CR2, NEF, ARW, DNG, etc.)
**Library**: `rawpy`, `exiftool-python`

PhotoSearch currently uses PIL/Pillow which has limited RAW support. Missing:

| Field | Type | Description |
|-------|------|-------------|
| `raw_format` | string | RAW format (CR2, NEF, ARW, DNG) |
| `raw_converter_version` | string | RAW converter version |
| `demosaic_algorithm` | string | Demosaicing algorithm |
| `black_level` | integer | Black level |
| `white_level` | integer | White level |
| `linearization_table` | array | Linearization table |
| `camera_calibration` | object | Camera calibration matrices |
| `color_matrix` | array | Color transformation matrix |
| `analog_balance` | array | Analog balance |
| `as_shot_neutral` | array | As-shot neutral |
| `as_shot_white_xy` | array | As-shot white balance |
| `baseline_exposure` | float | Baseline exposure |
| `baseline_noise` | float | Baseline noise |
| `baseline_sharpness` | float | Baseline sharpness |
| `bayer_pattern` | string | Bayer pattern (RGGB, BGGR, etc.) |
| `cfa_layout` | string | CFA layout |
| `crop_origin` | array | Crop origin |
| `crop_size` | array | Crop size |
| `default_crop_origin` | array | Default crop origin |
| `default_crop_size` | array | Default crop size |
| `active_area` | array | Active sensor area |

### ❌ Panorama/HDR Metadata (Not Implemented)
**Purpose**: Multi-shot images
**Source**: EXIF/XMP

| Field | Type | Description |
|-------|------|-------------|
| `is_panorama` | boolean | Is panoramic image |
| `panorama_width` | integer | Total panorama width |
| `panorama_height` | integer | Total panorama height |
| `panorama_stitch_count` | integer | Number of images stitched |
| `is_hdr` | boolean | Is HDR image |
| `hdr_bracket_count` | integer | Number of bracketed exposures |
| `hdr_exposures` | array | Exposure values used |
| `hdr_merge_method` | string | HDR merge algorithm |

### ❌ Focus Stacking Metadata (Not Implemented)

| Field | Type | Description |
|-------|------|-------------|
| `is_focus_stacked` | boolean | Is focus-stacked image |
| `focus_stack_count` | integer | Number of images stacked |
| `focus_step_size` | float | Focus step size |

---

## 2. VIDEO METADATA GAPS

### ❌ Advanced Video Codec Info (Partially Missing)
**Source**: ffprobe (extracting more fields)

| Field | Type | Description |
|-------|------|-------------|
| **Video Codec Advanced** |
| `profile` | string | Codec profile (High, Main, Baseline) |
| `level` | integer | Codec level |
| `tier` | string | Codec tier (Main, High) |
| `bit_rate_mode` | string | CBR/VBR |
| `encoding_settings` | string | Encoder settings string |
| `encoder` | string | Encoder name/version |
| `writing_library` | string | Library used to write file |
| `writing_application` | string | Application used |
| `scan_type` | string | Progressive/Interlaced |
| `scan_order` | string | Top field first/bottom field first |
| `gop_size` | integer | GOP (Group of Pictures) size |
| `closed_gop` | boolean | Uses closed GOPs |
| **Display/Aspect Ratio** |
| `display_aspect_ratio` | string | Display aspect ratio (16:9, 4:3) |
| `sample_aspect_ratio` | string | Sample/pixel aspect ratio |
| `pixel_aspect_ratio` | string | Pixel aspect ratio |
| **Frame Info** |
| `field_order` | string | Field order |
| `timecode` | string | SMPTE timecode |
| **Quality Metrics** |
| `max_bit_rate` | integer | Maximum bitrate |
| `buffer_size` | integer | Buffer size |
| **HDR Metadata** |
| `color_primaries` | string | BT.2020, DCI-P3, etc. |
| `transfer_characteristics` | string | PQ, HLG, etc. |
| `matrix_coefficients` | string | Matrix coefficients |
| `mastering_display_color_primaries` | string | HDR mastering display |
| `mastering_display_luminance` | string | Max/min luminance |
| `max_content_light_level` | integer | MaxCLL |
| `max_frame_average_light_level` | integer | MaxFALL |
| **3D/VR** |
| `stereo_mode` | string | Stereo 3D mode |
| `projection_type` | string | VR projection (equirectangular, cubemap) |
| `spherical` | boolean | Is 360° video |

### ❌ Video Container Metadata (Missing)
**Source**: ffprobe format tags

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Video title |
| `artist` | string | Artist/creator |
| `album` | string | Album/collection |
| `album_artist` | string | Album artist |
| `composer` | string | Composer |
| `genre` | string | Genre |
| `year` | integer | Release year |
| `date` | string | Release date |
| `comment` | string | Comments |
| `description` | string | Description |
| `synopsis` | string | Synopsis |
| `show` | string | TV show name |
| `episode_id` | string | Episode ID |
| `network` | string | Network/channel |
| `lyrics` | string | Lyrics/subtitles |
| `copyright` | string | Copyright notice |
| `publisher` | string | Publisher |
| `encoded_by` | string | Encoded by |
| `director` | string | Director |
| `producer` | string | Producer |
| `actors` | string | Cast/actors |
| `rating` | string | Content rating |

### ❌ Variable Frame Rate (VFR) Info

| Field | Type | Description |
|-------|------|-------------|
| `is_vfr` | boolean | Variable frame rate |
| `min_frame_rate` | float | Minimum FPS |
| `max_frame_rate` | float | Maximum FPS |
| `avg_frame_rate` | float | Average FPS |

### ❌ Subtitle/Caption Streams

| Field | Type | Description |
|-------|------|-------------|
| `subtitle_streams` | array | Array of subtitle streams |
| `subtitle_count` | integer | Number of subtitle tracks |
| `subtitle_languages` | array | Subtitle languages |
| `subtitle_formats` | array | Subtitle formats (SRT, ASS, etc.) |
| `has_closed_captions` | boolean | Has closed captions |

### ❌ Video Rotation Metadata (Partially Missing)

| Field | Type | Description |
|-------|------|-------------|
| `rotation` | integer | Rotation angle (0, 90, 180, 270) |
| `display_matrix` | array | Display transformation matrix |

---

## 3. AUDIO METADATA GAPS

### ❌ Advanced Audio Codec Info (Missing)
**Source**: ffprobe, mutagen

| Field | Type | Description |
|-------|------|-------------|
| `encoder` | string | Encoder name/version |
| `encoding_settings` | string | Encoder settings |
| `encoder_delay` | integer | Encoder delay samples |
| `encoder_padding` | integer | Encoder padding samples |
| `gapless_playback` | boolean | Supports gapless |
| `lossless` | boolean | Is lossless |
| `vbr` | boolean | Variable bitrate |
| `abr` | boolean | Average bitrate |
| `nominal_bitrate` | integer | Nominal bitrate |
| `min_bitrate` | integer | Minimum bitrate |
| `max_bitrate` | integer | Maximum bitrate |

### ❌ Music Metadata (Extended) - Missing
**Source**: ID3v2.4, Vorbis Comments, iTunes tags

| Field | ID3 Tag | Description |
|-------|---------|-------------|
| **Basic** |
| `album_sort` | TSOA | Album sort order |
| `artist_sort` | TSOP | Artist sort order |
| `title_sort` | TSOT | Title sort order |
| `album_artist_sort` | TSO2 | Album artist sort |
| **Track Info** |
| `disc_number` | TPOS | Disc number |
| `total_discs` | TPOS | Total discs |
| `total_tracks` | TRCK | Total tracks |
| `compilation` | TCMP | Is compilation |
| `part_of_set` | TPOS | Part of set |
| **Media Type** |
| `media_type` | TMED | Media type |
| `encoded_by` | TENC | Encoded by |
| `encoder_settings` | TSSE | Encoder settings |
| **Organization** |
| `grouping` | TIT1 | Content group |
| `movement_name` | MVNM | Movement name |
| `movement_number` | MVIN | Movement number |
| `work` | TIT1 | Work name |
| **People** |
| `conductor` | TPE3 | Conductor |
| `remixer` | TPE4 | Remixed by |
| `lyricist` | TEXT | Lyricist |
| `original_artist` | TOPE | Original artist |
| **Copyright** |
| `copyright` | TCOP | Copyright |
| `publisher` | TPUB | Publisher |
| `isrc` | TSRC | ISRC code |
| `barcode` | UPC | Barcode/UPC |
| `catalog_number` | CATALOGNUMBER | Catalog number |
| `label` | TPUB | Record label |
| **Dates** |
| `recording_date` | TDRC | Recording date |
| `release_date` | TDRL | Release date |
| `original_release_date` | TDOR | Original release |
| **Mood/Style** |
| `mood` | TMOO | Mood |
| `bpm` | TBPM | Beats per minute |
| `initial_key` | TKEY | Musical key |
| **Ratings** |
| `rating` | POPM | Popularimeter rating |
| `play_count` | PCNT | Play counter |
| **Podcast** |
| `podcast` | PCST | Is podcast |
| `podcast_url` | PURL | Podcast URL |
| `podcast_category` | TCAT | Podcast category |
| `podcast_description` | TDES | Podcast description |
| `episode_global_id` | TGID | Episode global unique ID |
| **ReplayGain** |
| `replaygain_track_gain` | TXXX | Track gain |
| `replaygain_track_peak` | TXXX | Track peak |
| `replaygain_album_gain` | TXXX | Album gain |
| `replaygain_album_peak` | TXXX | Album peak |
| **MusicBrainz IDs** |
| `musicbrainz_track_id` | UFID | Track ID |
| `musicbrainz_album_id` | TXXX | Album ID |
| `musicbrainz_artist_id` | TXXX | Artist ID |
| `musicbrainz_album_artist_id` | TXXX | Album artist ID |
| `musicbrainz_release_group_id` | TXXX | Release group ID |
| `musicbrainz_work_id` | TXXX | Work ID |

### ❌ Audio Technical Analysis (Not Implemented)
**Purpose**: Audio quality analysis
**Libraries**: `librosa`, `essentia`, `aubio`

| Field | Type | Description |
|-------|------|-------------|
| `loudness_lufs` | float | Integrated loudness (LUFS) |
| `loudness_range` | float | Loudness range (LU) |
| `true_peak` | float | True peak level (dBTP) |
| `dynamic_range` | float | Dynamic range (dB) |
| `crest_factor` | float | Crest factor |
| `spectral_centroid` | float | Spectral centroid |
| `spectral_rolloff` | float | Spectral rolloff |
| `zero_crossing_rate` | float | Zero crossing rate |
| `tempo_bpm` | float | Detected tempo (BPM) |
| `key` | string | Detected musical key |
| `mode` | string | Major/minor mode |
| `time_signature` | string | Time signature |

### ❌ Speech/Voice Detection (Not Implemented)

| Field | Type | Description |
|-------|------|-------------|
| `contains_speech` | boolean | Contains speech |
| `speech_percentage` | float | Percentage with speech |
| `voice_count` | integer | Number of distinct voices |
| `language_detected` | string | Detected language |

---

## 4. CROSS-FORMAT METADATA GAPS

### ❌ Thumbnail Extraction (Partially Implemented)
**Current**: Basic thumbnail detection
**Missing**: Embedded thumbnail extraction

| Field | Type | Description |
|-------|------|-------------|
| `thumbnail_embedded` | boolean | Has embedded thumbnail |
| `thumbnail_size` | string | Thumbnail dimensions |
| `thumbnail_format` | string | Thumbnail format |
| `thumbnail_data` | binary | Thumbnail image data |

### ❌ Preview Images (Not Implemented)
**Purpose**: RAW files often have embedded JPEGs

| Field | Type | Description |
|-------|------|-------------|
| `preview_image_count` | integer | Number of preview images |
| `preview_image_sizes` | array | Preview image sizes |

### ❌ Edit History/Provenance (Not Implemented)
**Purpose**: Track editing history
**Source**: XMP History, Photoshop layers

| Field | Type | Description |
|-------|------|-------------|
| `edit_history` | array | Array of edit operations |
| `derivative_of` | string | Original file ID |
| `has_layers` | boolean | Has layers (PSD, TIFF) |
| `layer_count` | integer | Number of layers |
| `software_history` | array | Software used for editing |

---

## 5. METADATA EXTRACTION LIBRARY GAPS

### Current Libraries
- ✅ `exifread` - Basic EXIF
- ✅ `PIL/Pillow` - Image properties
- ✅ `ffmpeg-python` - Video/audio properties
- ✅ `mutagen` - Audio tags
- ✅ `pypdf` - PDF metadata
- ❌ No IPTC support
- ❌ No XMP support
- ❌ Limited RAW support

### Recommended Additional Libraries

| Library | Purpose | Priority |
|---------|---------|----------|
| `iptcinfo3` | IPTC metadata | HIGH |
| `python-xmp-toolkit` | XMP metadata | HIGH |
| `imagehash` | Perceptual hashing | HIGH |
| `rawpy` | RAW image support | MEDIUM |
| `opencv-python` | Image analysis | MEDIUM |
| `librosa` | Audio analysis | LOW |
| `piexif` | EXIF writing | HIGH (for Phase 4) |
| `ExifTool` (subprocess) | Universal metadata reader | MEDIUM |

---

## 6. SUMMARY OF GAPS

### By Category

| Category | Fields Implemented | Fields Missing | Total Possible |
|----------|-------------------|----------------|----------------|
| **Images** | ~180 | ~220 | ~400 |
| **Videos** | ~60 | ~80 | ~140 |
| **Audio** | ~25 | ~60 | ~85 |
| **TOTAL** | ~265 | ~360 | ~625 |

### By Priority

| Priority | Description | Field Count |
|----------|-------------|-------------|
| **HIGH** | IPTC/XMP, perceptual hashing, reverse geocoding | ~100 |
| **MEDIUM** | RAW support, advanced analysis, edit history | ~150 |
| **LOW** | Technical analysis, speech detection, advanced codecs | ~110 |

---

## 7. RECOMMENDATIONS

### Immediate Additions (High ROI)
1. **IPTC Core** - Professional photography metadata (~50 fields)
2. **XMP Dublin Core** - Standard metadata (~15 fields)
3. **Perceptual Hashing** - Duplicate detection (~3 fields)
4. **Reverse Geocoding** - Location names (~10 fields)

### Medium-Term
5. **RAW File Support** - Professional photographers (~25 fields)
6. **Advanced Image Analysis** - Color palette, quality metrics (~20 fields)
7. **Extended Audio Tags** - MusicBrainz, ReplayGain (~30 fields)

### Long-Term
8. **Edit History/Provenance** - Track modifications (~10 fields)
9. **HDR/3D/VR Metadata** - Advanced video formats (~15 fields)
10. **Audio Analysis** - Tempo, key detection, loudness (~15 fields)

---

## 8. IMPLEMENTATION EFFORT ESTIMATES

| Feature | Fields Added | Library | Effort | Priority |
|---------|-------------|---------|--------|----------|
| IPTC extraction | ~50 | `iptcinfo3` | 2-3 days | HIGH |
| XMP extraction | ~50 | `python-xmp-toolkit` | 3-4 days | HIGH |
| Perceptual hashing | 3-5 | `imagehash` | 1 day | HIGH |
| Reverse geocoding | ~10 | API calls | 2 days | HIGH |
| Color palette | ~5 | `scikit-learn` | 1 day | MEDIUM |
| RAW support | ~25 | `rawpy` | 3-4 days | MEDIUM |
| Extended audio tags | ~30 | `mutagen` (extended) | 2 days | MEDIUM |
| Image quality metrics | ~10 | `opencv-python` | 2-3 days | LOW |
| Audio analysis | ~15 | `librosa` | 3-4 days | LOW |

---

**Next Step**: Prioritize HIGH priority items for METADATA_ENHANCEMENT_PLAN Phase 1
