# PhotoSearch - Complete Metadata Catalog

**Generated**: 2025-12-29
**Purpose**: Master reference of ALL metadata fields in PhotoSearch
**Status**: Comprehensive inventory from implementation + documentation

---

## Executive Summary

PhotoSearch extracts **100+ metadata fields** across all file types. This catalog documents every field by:
- **Implementation Status**: ✅ Implemented | 🔶 Partially Implemented | ❌ Not Implemented
- **Category**: Filesystem, EXIF, GPS, Calculated, etc.
- **File Type**: Images, Videos, Audio, PDFs, SVGs, All Files

**Backend Extraction**: Comprehensive (100+ fields via `metadata_extractor.py`)
**Database Storage**: Basic fields stored in SQLite (`metadata_search.py`)
**Frontend Display**: ~30% visibility in UI (`DetailsTab.tsx`)
**Gap**: 70% of extracted metadata is hidden from users

---

## 1. UNIVERSAL METADATA (All File Types)

### ✅ Filesystem Metadata (Fully Implemented)
**Source**: `extract_filesystem_metadata()` in `metadata_extractor.py:93-167`
**Storage**: `metadata.db` (filesystem column)
**UI Display**: Partial in DetailsTab

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `size_bytes` | integer | File size in bytes | ✅ Shown |
| `size_human` | string | Human-readable size (KB, MB, GB) | ✅ Shown |
| `created` | timestamp | File creation time (ISO 8601) | ✅ Shown |
| `modified` | timestamp | Last modification time | ✅ Shown |
| `accessed` | timestamp | Last access time | ❌ Hidden |
| `changed` | timestamp | Metadata change time (ctime) | ❌ Hidden |
| `permissions_octal` | string | Unix permissions (octal format) | ❌ Hidden |
| `permissions_human` | string | Human-readable permissions (rwxr-xr-x) | ❌ Hidden |
| `owner` | string | File owner username | ❌ Hidden |
| `owner_uid` | integer | Owner user ID | ❌ Hidden |
| `group` | string | File group name | ❌ Hidden |
| `group_gid` | integer | Group ID | ❌ Hidden |
| `inode` | integer | File inode number | ❌ Hidden |
| `device` | integer | Device ID | ❌ Hidden |
| `hard_links` | integer | Number of hard links | ❌ Hidden |
| `file_type` | string | File type (regular, directory, symlink, etc.) | ❌ Hidden |

### ✅ Extended Attributes (macOS/Linux)
**Source**: `extract_extended_attributes()` in `metadata_extractor.py:169-201`
**Storage**: Not stored in database
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `available` | boolean | Whether xattr is available | ❌ Hidden |
| `attributes` | object | All extended attributes (key-value pairs) | ❌ Hidden |
| `com.apple.metadata:kMDItemWhereFroms` | string | Download source (macOS) | ❌ Hidden |
| `com.apple.quarantine` | string | Quarantine info (macOS) | ❌ Hidden |
| `user.comment` | string | User comments (Linux) | ❌ Hidden |

### ✅ File Identity
**Source**: `extract_all_metadata()` in `metadata_extractor.py:757-832`
**Storage**: Partial
**UI Display**: Partial

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `path` | string | Absolute file path | ✅ Shown |
| `name` | string | File name with extension | ✅ Shown |
| `extension` | string | File extension (.jpg, .mp4, etc.) | ✅ Shown |
| `mime_type` | string | MIME type (image/jpeg, video/mp4, etc.) | ❌ Hidden |

### ✅ File Hashes (Integrity Verification)
**Source**: `extract_file_hashes()` in `metadata_extractor.py:587-611`
**Storage**: `metadata.db` (file_hash column stores SHA256)
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `md5` | string | MD5 hash (hex) | ❌ Hidden |
| `sha256` | string | SHA256 hash (hex) | ✅ Stored, ❌ Not shown |

### ✅ Calculated/Inferred Metadata
**Source**: `calculate_inferred_metadata()` in `metadata_extractor.py:669-755`
**Storage**: Not stored
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `file_age.days` | integer | Age in days since creation | ❌ Hidden |
| `file_age.hours` | integer | Age in hours | ❌ Hidden |
| `file_age.human_readable` | string | "2 days ago", "3 months ago" | ❌ Hidden |
| `time_since_modified.days` | integer | Days since last modified | ❌ Hidden |
| `time_since_modified.hours` | integer | Hours since last modified | ❌ Hidden |
| `time_since_modified.human_readable` | string | Human-readable time delta | ❌ Hidden |
| `time_since_accessed.days` | integer | Days since last access | ❌ Hidden |
| `time_since_accessed.hours` | integer | Hours since last access | ❌ Hidden |
| `time_since_accessed.human_readable` | string | Human-readable access delta | ❌ Hidden |

---

## 2. IMAGE METADATA

### ✅ Image Properties (Pillow)
**Source**: `extract_image_properties()` in `metadata_extractor.py:353-380`
**Storage**: Partial
**UI Display**: Partial

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `width` | integer | Image width in pixels | ✅ Shown |
| `height` | integer | Image height in pixels | ✅ Shown |
| `format` | string | Image format (JPEG, PNG, GIF, etc.) | ✅ Shown |
| `mode` | string | Color mode (RGB, RGBA, L, CMYK, etc.) | ❌ Hidden |
| `dpi` | tuple | DPI/PPI resolution (x, y) | ❌ Hidden |
| `bits_per_pixel` | integer | Bit depth per pixel | ❌ Hidden |
| `color_palette` | string | "yes" if has indexed palette | ❌ Hidden |
| `animation` | boolean | True for animated GIFs/PNGs | ❌ Hidden |
| `frames` | integer | Number of frames (animation) | ❌ Hidden |
| `icc_profile` | string | "yes" if has ICC color profile | ❌ Hidden |

### ✅ Calculated Image Metadata
**Source**: `calculate_inferred_metadata()` in `metadata_extractor.py:683-706`
**Storage**: Not stored
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `aspect_ratio` | string | Aspect ratio (16:9, 4:3, 1:1, etc.) | ❌ Hidden |
| `aspect_ratio_decimal` | float | Decimal aspect ratio (1.778, 1.333, etc.) | ❌ Hidden |
| `megapixels` | float | Total megapixels (width × height / 1M) | ❌ Hidden |
| `orientation` | string | "landscape", "portrait", or "square" | ❌ Hidden |

### ✅ Thumbnails
**Source**: `extract_thumbnail()` in `metadata_extractor.py:613-635`
**Storage**: Not stored
**UI Display**: Generated on-the-fly

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `has_embedded` | boolean | Has embedded thumbnail in EXIF | ❌ Hidden |
| `width` | integer | Thumbnail width (after generation) | ❌ Hidden |
| `height` | integer | Thumbnail height (after generation) | ❌ Hidden |

---

## 3. EXIF METADATA (Comprehensive)

### ✅ EXIF - Image Tags
**Source**: `extract_exif_metadata()` in `metadata_extractor.py:233-288`
**Storage**: Not stored in database
**UI Display**: None (except Make/Model shown in basic metadata)

**Category**: `exif.image.*`

| Field | EXIF Tag | Type | Description | UI Status |
|-------|----------|------|-------------|-----------|
| `Make` | Image Make | string | Camera manufacturer | 🔶 Shown in basic view |
| `Model` | Image Model | string | Camera model | 🔶 Shown in basic view |
| `Software` | Image Software | string | Software used to create/edit | ❌ Hidden |
| `DateTime` | Image DateTime | timestamp | Image capture date/time | ❌ Hidden |
| `DateTimeOriginal` | Image DateTimeOriginal | timestamp | Original capture time | ❌ Hidden |
| `DateTimeDigitized` | Image DateTimeDigitized | timestamp | Digitization time | ❌ Hidden |
| `Orientation` | Image Orientation | integer | Image orientation (1-8) | ❌ Hidden |
| `XResolution` | Image XResolution | float | Horizontal resolution | ❌ Hidden |
| `YResolution` | Image YResolution | float | Vertical resolution | ❌ Hidden |
| `ResolutionUnit` | Image ResolutionUnit | integer | Resolution unit (2=inches, 3=cm) | ❌ Hidden |
| `YCbCrPositioning` | Image YCbCrPositioning | integer | YCbCr positioning | ❌ Hidden |
| `Copyright` | Image Copyright | string | Copyright notice | ❌ Hidden |
| `Artist` | Image Artist | string | Photographer/creator | ❌ Hidden |
| `ImageDescription` | Image ImageDescription | string | Image description/caption | ❌ Hidden |

### ✅ EXIF - Photo Tags (Camera Settings)
**Source**: Same as above
**Storage**: Not stored
**UI Display**: None

**Category**: `exif.exif.*`

| Field | EXIF Tag | Type | Description | UI Status |
|-------|----------|------|-------------|-----------|
| `ExposureTime` | EXIF ExposureTime | string | Shutter speed (e.g., "1/250") | ❌ Hidden |
| `FNumber` | EXIF FNumber | float | Aperture f-number | ❌ Hidden |
| `ISOSpeedRatings` | EXIF ISOSpeedRatings | integer | ISO sensitivity | ❌ Hidden |
| `ExposureProgram` | EXIF ExposureProgram | integer | Exposure program mode | ❌ Hidden |
| `DateTimeOriginal` | EXIF DateTimeOriginal | timestamp | Original capture time | ❌ Hidden |
| `DateTimeDigitized` | EXIF DateTimeDigitized | timestamp | Digitization time | ❌ Hidden |
| `ShutterSpeedValue` | EXIF ShutterSpeedValue | float | APEX shutter speed | ❌ Hidden |
| `ApertureValue` | EXIF ApertureValue | float | APEX aperture | ❌ Hidden |
| `BrightnessValue` | EXIF BrightnessValue | float | Brightness value | ❌ Hidden |
| `ExposureBiasValue` | EXIF ExposureBiasValue | float | Exposure compensation | ❌ Hidden |
| `MaxApertureValue` | EXIF MaxApertureValue | float | Maximum aperture | ❌ Hidden |
| `MeteringMode` | EXIF MeteringMode | integer | Metering mode | ❌ Hidden |
| `Flash` | EXIF Flash | integer | Flash status | ❌ Hidden |
| `FocalLength` | EXIF FocalLength | float | Focal length (mm) | ❌ Hidden |
| `FocalLengthIn35mmFilm` | EXIF FocalLengthIn35mmFilm | integer | 35mm equivalent focal length | ❌ Hidden |
| `SubjectDistance` | EXIF SubjectDistance | float | Distance to subject | ❌ Hidden |
| `LightSource` | EXIF LightSource | integer | Light source type | ❌ Hidden |
| `WhiteBalance` | EXIF WhiteBalance | integer | White balance mode | ❌ Hidden |
| `DigitalZoomRatio` | EXIF DigitalZoomRatio | float | Digital zoom ratio | ❌ Hidden |
| `SceneCaptureType` | EXIF SceneCaptureType | integer | Scene type | ❌ Hidden |
| `GainControl` | EXIF GainControl | integer | Gain control | ❌ Hidden |
| `Contrast` | EXIF Contrast | integer | Contrast processing | ❌ Hidden |
| `Saturation` | EXIF Saturation | integer | Saturation processing | ❌ Hidden |
| `Sharpness` | EXIF Sharpness | integer | Sharpness processing | ❌ Hidden |
| `SubjectDistanceRange` | EXIF SubjectDistanceRange | integer | Subject distance range | ❌ Hidden |
| `ColorSpace` | EXIF ColorSpace | integer | Color space (1=sRGB, 2=Adobe RGB) | ❌ Hidden |
| `ExifImageWidth` | EXIF ExifImageWidth | integer | Image width (from EXIF) | ❌ Hidden |
| `ExifImageHeight` | EXIF ExifImageHeight | integer | Image height (from EXIF) | ❌ Hidden |
| `SensingMethod` | EXIF SensingMethod | integer | Sensor type | ❌ Hidden |
| `FileSource` | EXIF FileSource | integer | File source | ❌ Hidden |
| `SceneType` | EXIF SceneType | integer | Scene type | ❌ Hidden |
| `CFAPattern` | EXIF CFAPattern | bytes | Color filter array pattern | ❌ Hidden |
| `CustomRendered` | EXIF CustomRendered | integer | Custom rendering | ❌ Hidden |
| `ExposureMode` | EXIF ExposureMode | integer | Exposure mode | ❌ Hidden |
| `ComponentsConfiguration` | EXIF ComponentsConfiguration | bytes | Components config | ❌ Hidden |
| `CompressedBitsPerPixel` | EXIF CompressedBitsPerPixel | float | Compression ratio | ❌ Hidden |
| `PixelXDimension` | EXIF PixelXDimension | integer | Valid image width | ❌ Hidden |
| `PixelYDimension` | EXIF PixelYDimension | integer | Valid image height | ❌ Hidden |
| `UserComment` | EXIF UserComment | string | User comment | ❌ Hidden |
| `FlashPixVersion` | EXIF FlashPixVersion | string | FlashPix version | ❌ Hidden |
| `ExifVersion` | EXIF ExifVersion | string | EXIF version | ❌ Hidden |

### ✅ EXIF - Lens Information
**Source**: Same as above
**Storage**: Not stored
**UI Display**: None

| Field | EXIF Tag | Type | Description | UI Status |
|-------|----------|------|-------------|-----------|
| `LensModel` | EXIF LensModel | string | Lens model name | ❌ Hidden |
| `LensMake` | EXIF LensMake | string | Lens manufacturer | ❌ Hidden |
| `LensSpecification` | EXIF LensSpecification | array | Lens spec (min/max focal, aperture) | ❌ Hidden |
| `LensSerialNumber` | EXIF LensSerialNumber | string | Lens serial number | ❌ Hidden |

### ✅ EXIF - MakerNote (Proprietary)
**Source**: `extract_exif_metadata()` line 267-268
**Storage**: Not stored
**UI Display**: None

**Category**: `exif.makernote.*`

**Note**: MakerNote contains proprietary camera-specific metadata. Fields vary by manufacturer (Canon, Nikon, Sony, Fuji, etc.). Extracted but not parsed into structured fields.

| Field | Description | UI Status |
|-------|-------------|-----------|
| `*` (all MakerNote fields) | Proprietary camera settings and metadata | ❌ Hidden |

### ✅ EXIF - Interoperability
**Source**: Same as above
**Storage**: Not stored
**UI Display**: None

**Category**: `exif.interoperability.*`

| Field | Description | UI Status |
|-------|-------------|-----------|
| `InteroperabilityIndex` | Interoperability identification | ❌ Hidden |
| `InteroperabilityVersion` | Interoperability version | ❌ Hidden |

---

## 4. GPS METADATA

### ✅ GPS Coordinates
**Source**: `extract_gps_metadata()` in `metadata_extractor.py:290-351`
**Storage**: Partial
**UI Display**: Partial (shown on map if available)

| Field | EXIF Tag | Type | Description | UI Status |
|-------|----------|------|-------------|-----------|
| `latitude` | GPS GPSLatitude | float | Latitude in decimal degrees | ✅ Shown on map |
| `latitude_ref` | GPS GPSLatitudeRef | string | "N" or "S" | ❌ Hidden |
| `longitude` | GPS GPSLongitude | float | Longitude in decimal degrees | ✅ Shown on map |
| `longitude_ref` | GPS GPSLongitudeRef | string | "E" or "W" | ❌ Hidden |
| `altitude` | GPS GPSAltitude | float | Altitude in meters | ❌ Hidden |
| `altitude_ref` | GPS GPSAltitudeRef | string | "above_sea_level" or "below_sea_level" | ❌ Hidden |

### ✅ GPS Additional Fields
**Source**: Same as above
**Storage**: Not stored
**UI Display**: None

| Field | EXIF Tag | Type | Description | UI Status |
|-------|----------|------|-------------|-----------|
| `timestamp` | GPS GPSTimeStamp | string | GPS timestamp | ❌ Hidden |
| `datestamp` | GPS GPSDateStamp | string | GPS date | ❌ Hidden |
| `speed` | GPS GPSSpeed | float | Speed when photo taken | ❌ Hidden |
| `speed_ref` | GPS GPSSpeedRef | string | Speed unit (K/M/N) | ❌ Hidden |
| `track` | GPS GPSTrack | float | Movement direction | ❌ Hidden |
| `track_ref` | GPS GPSTrackRef | string | Track reference (T/M) | ❌ Hidden |
| `image_direction` | GPS GPSImgDirection | float | Direction camera was pointing | ❌ Hidden |
| `image_direction_ref` | GPS GPSImgDirectionRef | string | Direction reference (T/M) | ❌ Hidden |
| `satellites` | GPS GPSSatellites | string | GPS satellites used | ❌ Hidden |
| `dop` | GPS GPSDOP | float | GPS dilution of precision | ❌ Hidden |
| `map_datum` | GPS GPSMapDatum | string | Geodetic survey datum | ❌ Hidden |
| `processing_method` | GPS GPSProcessingMethod | string | GPS processing method | ❌ Hidden |

---

## 5. VIDEO METADATA

### ✅ Video Properties (FFprobe)
**Source**: `extract_video_properties()` in `metadata_extractor.py:382-406`
**Storage**: Partial
**UI Display**: Minimal

### Video Format Metadata
**Source**: `probe.format` from ffprobe
**Storage**: Not stored
**UI Display**: Partial

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `filename` | string | File path | ✅ Shown |
| `nb_streams` | integer | Number of streams | ❌ Hidden |
| `nb_programs` | integer | Number of programs | ❌ Hidden |
| `format_name` | string | Format name (mov,mp4,m4a,3gp,3g2,mj2) | ❌ Hidden |
| `format_long_name` | string | Format long name | ❌ Hidden |
| `start_time` | float | Start time (seconds) | ❌ Hidden |
| `duration` | float | Duration (seconds) | 🔶 Shown as calculated |
| `size` | integer | File size (bytes) | ✅ Shown |
| `bit_rate` | integer | Total bit rate | ❌ Hidden |
| `probe_score` | integer | Format detection confidence | ❌ Hidden |
| `tags.major_brand` | string | Major brand (mp42, isom, etc.) | ❌ Hidden |
| `tags.minor_version` | string | Minor version | ❌ Hidden |
| `tags.compatible_brands` | string | Compatible brands | ❌ Hidden |
| `tags.creation_time` | timestamp | Creation time | ❌ Hidden |

### Video Stream Metadata
**Source**: `probe.streams[0]` (video stream)
**Storage**: Not stored
**UI Display**: Partial

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `index` | integer | Stream index | ❌ Hidden |
| `codec_name` | string | Codec name (h264, hevc, vp9, etc.) | ❌ Hidden |
| `codec_long_name` | string | Full codec name | ❌ Hidden |
| `codec_type` | string | "video" | ❌ Hidden |
| `codec_tag_string` | string | Codec tag | ❌ Hidden |
| `codec_tag` | string | Codec tag hex | ❌ Hidden |
| `width` | integer | Video width (pixels) | ✅ Shown |
| `height` | integer | Video height (pixels) | ✅ Shown |
| `coded_width` | integer | Coded width | ❌ Hidden |
| `coded_height` | integer | Coded height | ❌ Hidden |
| `has_b_frames` | integer | Has B-frames | ❌ Hidden |
| `pix_fmt` | string | Pixel format (yuv420p, etc.) | ❌ Hidden |
| `level` | integer | Codec level | ❌ Hidden |
| `color_range` | string | Color range (tv, pc) | ❌ Hidden |
| `color_space` | string | Color space (bt709, bt470bg, etc.) | ❌ Hidden |
| `color_transfer` | string | Color transfer characteristics | ❌ Hidden |
| `color_primaries` | string | Color primaries | ❌ Hidden |
| `chroma_location` | string | Chroma sample location | ❌ Hidden |
| `refs` | integer | Reference frames | ❌ Hidden |
| `is_avc` | string | Is AVC | ❌ Hidden |
| `nal_length_size` | string | NAL length size | ❌ Hidden |
| `r_frame_rate` | string | Real frame rate | ❌ Hidden |
| `avg_frame_rate` | string | Average frame rate | ❌ Hidden |
| `time_base` | string | Time base | ❌ Hidden |
| `start_pts` | integer | Start PTS | ❌ Hidden |
| `start_time` | float | Start time | ❌ Hidden |
| `duration_ts` | integer | Duration (time stamps) | ❌ Hidden |
| `duration` | float | Duration (seconds) | 🔶 Calculated and shown |
| `bit_rate` | integer | Bit rate | ❌ Hidden |
| `bits_per_raw_sample` | string | Bits per raw sample | ❌ Hidden |
| `nb_frames` | string | Number of frames | ❌ Hidden |
| `disposition.*` | integers | Stream disposition flags | ❌ Hidden |
| `tags.creation_time` | timestamp | Creation time | ❌ Hidden |
| `tags.language` | string | Language code | ❌ Hidden |
| `tags.handler_name` | string | Handler name | ❌ Hidden |

### Audio Stream Metadata (in video files)
**Source**: `probe.streams[1]` (audio stream)
**Storage**: Not stored
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `index` | integer | Stream index | ❌ Hidden |
| `codec_name` | string | Audio codec (aac, mp3, opus, etc.) | ❌ Hidden |
| `codec_long_name` | string | Full codec name | ❌ Hidden |
| `codec_type` | string | "audio" | ❌ Hidden |
| `codec_tag_string` | string | Codec tag | ❌ Hidden |
| `codec_tag` | string | Codec tag hex | ❌ Hidden |
| `sample_fmt` | string | Sample format (fltp, s16p, etc.) | ❌ Hidden |
| `sample_rate` | integer | Sample rate (Hz) | ❌ Hidden |
| `channels` | integer | Number of channels | ❌ Hidden |
| `channel_layout` | string | Channel layout (stereo, 5.1, etc.) | ❌ Hidden |
| `bits_per_sample` | integer | Bits per sample | ❌ Hidden |
| `r_frame_rate` | string | Frame rate | ❌ Hidden |
| `avg_frame_rate` | string | Average frame rate | ❌ Hidden |
| `time_base` | string | Time base | ❌ Hidden |
| `start_pts` | integer | Start PTS | ❌ Hidden |
| `start_time` | float | Start time | ❌ Hidden |
| `duration_ts` | integer | Duration (timestamps) | ❌ Hidden |
| `duration` | float | Duration (seconds) | ❌ Hidden |
| `bit_rate` | integer | Bit rate | ❌ Hidden |
| `nb_frames` | string | Number of frames | ❌ Hidden |
| `disposition.*` | integers | Stream disposition flags | ❌ Hidden |
| `tags.creation_time` | timestamp | Creation time | ❌ Hidden |
| `tags.language` | string | Language code | ❌ Hidden |
| `tags.handler_name` | string | Handler name | ❌ Hidden |

### Video Chapters
**Source**: `probe.chapters`
**Storage**: Not stored
**UI Display**: None

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `id` | integer | Chapter ID | ❌ Hidden |
| `time_base` | string | Time base | ❌ Hidden |
| `start` | integer | Start time | ❌ Hidden |
| `end` | integer | End time | ❌ Hidden |
| `tags.title` | string | Chapter title | ❌ Hidden |

### ✅ Calculated Video Metadata
**Source**: `calculate_inferred_metadata()` lines 708-719
**Storage**: Not stored
**UI Display**: Partial

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `duration_human` | string | Human-readable duration (MM:SS) | 🔶 Shown |
| `size_per_second` | string | File size per second (for bitrate estimate) | ❌ Hidden |

---

## 6. AUDIO METADATA

### ✅ Audio Properties (Mutagen)
**Source**: `extract_audio_properties()` in `metadata_extractor.py:408-487`
**Storage**: Not stored
**UI Display**: None

**Supported Formats**: MP3, FLAC, OGG, WAV, AAC, M4A, MP4 audio

| Field | Type | Description | UI Status |
|-------|------|-------------|-----------|
| `format` | string | Audio format type (MP3, FLAC, etc.) | ❌ Hidden |
| `length_seconds` | float | Duration in seconds | ❌ Hidden |
| `length_human` | string | Human-readable duration (MM:SS) | ❌ Hidden |
| `bitrate` | integer | Bitrate (bits/second) | ❌ Hidden |
| `sample_rate` | integer | Sample rate (Hz) | ❌ Hidden |
| `channels` | integer | Number of channels (1=mono, 2=stereo) | ❌ Hidden |
| `bits_per_sample` | integer | Bit depth | ❌ Hidden |

### ✅ Audio Tags (ID3, Vorbis, etc.)
**Source**: Same as above
**Storage**: Not stored
**UI Display**: None

| Field | EXIF/ID3 Tag | Type | Description | UI Status |
|-------|--------------|------|-------------|-----------|
| `tags.title` | TIT2/TITLE | string | Song title | ❌ Hidden |
| `tags.artist` | TPE1/ARTIST | string | Artist name | ❌ Hidden |
| `tags.album` | TALB/ALBUM | string | Album name | ❌ Hidden |
| `tags.year` | TDRC/DATE | string | Release year | ❌ Hidden |
| `tags.genre` | TCON/GENRE | string | Music genre | ❌ Hidden |
| `tags.track_number` | TRCK/TRACKNUMBER | string | Track number | ❌ Hidden |
| `tags.composer` | TCOM/COMPOSER | string | Composer name | ❌ Hidden |
| `tags.album_artist` | TPE2/ALBUMARTIST | string | Album artist | ❌ Hidden |
| `tags.comment` | COMM/COMMENT | string | Comments | ❌ Hidden |
| `tags.lyrics` | USLT/LYRICS | string | Song lyrics | ❌ Hidden |
| `has_album_art` | - | boolean | Has embedded album art | ❌ Hidden |
| `album_art_count` | - | integer | Number of embedded images | ❌ Hidden |
| `raw_tags` | - | object | All raw tags (complete dump) | ❌ Hidden |

---

## 7. PDF METADATA

### ✅ PDF Properties (PyPDF)
**Source**: `extract_pdf_properties()` in `metadata_extractor.py:489-532`
**Storage**: Not stored
**UI Display**: None

| Field | PDF Info Key | Type | Description | UI Status |
|-------|--------------|------|-------------|-----------|
| `page_count` | - | integer | Number of pages | ❌ Hidden |
| `encrypted` | - | boolean | Is password-protected | ❌ Hidden |
| `author` | /Author | string | Document author | ❌ Hidden |
| `creator` | /Creator | string | Application that created the PDF | ❌ Hidden |
| `producer` | /Producer | string | PDF producer software | ❌ Hidden |
| `subject` | /Subject | string | Document subject | ❌ Hidden |
| `title` | /Title | string | Document title | ❌ Hidden |
| `creation_date` | /CreationDate | timestamp | When PDF was created | ❌ Hidden |
| `modification_date` | /ModDate | timestamp | When PDF was modified | ❌ Hidden |
| `keywords` | /Keywords | string | Document keywords | ❌ Hidden |
| `page_width` | - | float | Page width (from first page) | ❌ Hidden |
| `page_height` | - | float | Page height (from first page) | ❌ Hidden |

---

## 8. SVG METADATA

### ✅ SVG Properties (XML Parsing)
**Source**: `extract_svg_properties()` in `metadata_extractor.py:534-585`
**Storage**: Not stored
**UI Display**: None

| Field | SVG Attribute | Type | Description | UI Status |
|-------|---------------|------|-------------|-----------|
| `width` | width | string | SVG width (with units) | ❌ Hidden |
| `height` | height | string | SVG height (with units) | ❌ Hidden |
| `viewBox` | viewBox | string | ViewBox coordinates | ❌ Hidden |
| `version` | version | string | SVG version | ❌ Hidden |
| `viewBox_width` | - | string | Parsed viewBox width | ❌ Hidden |
| `viewBox_height` | - | string | Parsed viewBox height | ❌ Hidden |
| `element_count` | - | integer | Total XML elements | ❌ Hidden |
| `path_count` | - | integer | Number of path elements | ❌ Hidden |
| `has_embedded_styles` | - | boolean | Has style elements | ❌ Hidden |
| `has_scripts` | - | boolean | Has script elements (security concern) | ❌ Hidden |

---

## 9. PLANNED METADATA (Not Yet Implemented)

### ❌ IPTC/XMP Metadata
**Status**: Discussed in METADATA_ENHANCEMENT_PLAN but not implemented
**Priority**: High (professional photographers need this)
**Storage**: Would need new database columns
**UI**: Would need new UI sections

| Field | Standard | Type | Description |
|-------|----------|------|-------------|
| `title` | IPTC/XMP | string | Image title |
| `headline` | IPTC | string | Headline |
| `description` | IPTC/XMP | string | Description/caption |
| `keywords` | IPTC/XMP | array | Keyword tags |
| `creator` | IPTC/XMP | string | Creator/photographer |
| `credit_line` | IPTC | string | Photo credit |
| `source` | IPTC | string | Source/provider |
| `instructions` | IPTC | string | Special instructions |
| `copyright_notice` | IPTC/XMP | string | Copyright info |
| `rights_usage_terms` | XMP | string | Usage rights |
| `city` | IPTC | string | City (location) |
| `state` | IPTC | string | State/province |
| `country` | IPTC | string | Country |
| `country_code` | IPTC | string | ISO country code |
| `location` | IPTC | string | Sublocation |
| `date_created` | IPTC | date | Creation date |
| `intellectual_genre` | IPTC | string | Intellectual genre |
| `scene_code` | IPTC | array | IPTC scene codes |
| `subject_code` | IPTC | array | IPTC subject codes |

### ❌ Perceptual Hashing
**Status**: Discussed for duplicate detection
**Priority**: Medium
**Storage**: Would need new columns

| Field | Type | Description |
|-------|------|-------------|
| `phash` | string | Perceptual hash (for duplicate detection) |
| `dhash` | string | Difference hash |
| `ahash` | string | Average hash |

### ❌ Color Palette Extraction
**Status**: Prototyped but not integrated
**Priority**: Medium
**Storage**: Would need new columns

| Field | Type | Description |
|-------|------|-------------|
| `dominant_colors` | array | Array of RGB colors (k-means clustering) |
| `color_count` | integer | Number of unique colors |
| `color_histogram` | array | Color distribution histogram |

### ❌ Reverse Geocoding
**Status**: Planned for GPS enhancement
**Priority**: Medium
**Storage**: Would need new columns

| Field | Type | Description |
|-------|------|-------------|
| `location_name` | string | Human-readable location |
| `city` | string | City name |
| `state` | string | State/province |
| `country` | string | Country name |
| `timezone` | string | Timezone |

### ❌ Histogram Analysis
**Status**: Planned for image quality assessment
**Priority**: Low
**Storage**: Would need new columns

| Field | Type | Description |
|-------|------|-------------|
| `brightness_histogram` | array | Brightness distribution |
| `exposure_quality` | string | "underexposed", "normal", "overexposed" |
| `contrast_level` | string | "low", "medium", "high" |

### ❌ OCR Text (Burned-in Visual Metadata)
**Status**: Discussed but not implemented for metadata extraction
**Priority**: Low
**Note**: OCR exists separately in `ocr_search.py`, but not integrated into metadata pipeline

| Field | Type | Description |
|-------|------|-------------|
| `ocr_text` | string | Extracted text from image |
| `watermark_detected` | boolean | Watermark detected |
| `license_plate` | string | License plate text |
| `signage_text` | array | Text from signs/banners |

---

## 10. DATABASE STORAGE MAPPING

### Current Database Schema (`metadata.db`)

**Table**: `metadata`

| Column | Type | Maps To | Status |
|--------|------|---------|--------|
| `id` | INTEGER PK | Auto-increment | ✅ |
| `file_path` | TEXT UNIQUE | `file.path` | ✅ |
| `file_hash` | TEXT | `hashes.sha256` | ✅ |
| `metadata_json` | TEXT | Complete metadata dump (JSON) | ✅ |
| `extracted_at` | TIMESTAMP | Extraction timestamp | ✅ |
| `version` | INTEGER | Metadata version number | ✅ |
| `deleted_at` | TIMESTAMP | Soft delete timestamp | ✅ |

**Storage Strategy**: Currently stores ALL extracted metadata as JSON blob in `metadata_json` column. Individual fields are NOT indexed or searchable via SQL.

### Planned Schema Extensions (from METADATA_ENHANCEMENT_PLAN.md)

**New Table**: `metadata_extended` (or added columns to `metadata`)

```sql
-- Camera & Lens
camera_make TEXT,
camera_model TEXT,
lens_model TEXT,
lens_make TEXT,

-- Exposure Settings
iso INTEGER,
aperture REAL,
shutter_speed TEXT,
shutter_speed_decimal REAL,
exposure_compensation REAL,
exposure_mode TEXT,
exposure_program TEXT,
metering_mode TEXT,

-- Focal Length
focal_length REAL,
focal_length_35mm INTEGER,

-- Flash
flash_used BOOLEAN,
flash_mode TEXT,

-- White Balance
white_balance TEXT,
color_temperature INTEGER,

-- Image Quality
image_quality TEXT,
color_space TEXT,
bit_depth INTEGER,

-- Software
software TEXT,
edit_software TEXT,

-- Copyright
copyright TEXT,
creator TEXT,
creator_tool TEXT,

-- Composite
exposure_triangle TEXT,
searchable_text TEXT
```

---

## 11. UI DISPLAY GAPS

### Current UI Exposure (~30% of available metadata)

**File**: `frontend/src/components/DetailsTab.tsx`

**Shown**:
- ✅ File name
- ✅ File size
- ✅ Dimensions (width × height)
- ✅ File format
- ✅ Creation date
- ✅ Modification date
- ✅ GPS location (if available, on map)
- ✅ Camera make/model (basic EXIF)

**Hidden** (70% gap):
- ❌ All advanced EXIF (exposure settings, lens info, etc.)
- ❌ Extended attributes
- ❌ File permissions/ownership
- ❌ Video stream details (codec, bitrate, frame rate)
- ❌ Audio metadata (for videos and audio files)
- ❌ PDF metadata (page count, author, title)
- ❌ SVG metadata
- ❌ Calculated metadata (aspect ratio, megapixels, file age)
- ❌ All GPS metadata except coordinates
- ❌ Hashes (MD5, SHA256)

### Recommended UI Enhancements (from METADATA_ENHANCEMENT_PLAN.md)

1. **File Type-Specific Sections**:
   - `AudioMetadataSections.tsx` - Show audio tags, bitrate, sample rate
   - `VideoMetadataSections.tsx` - Show codec, streams, chapters
   - `PDFMetadataSections.tsx` - Show page count, author, title
   - `SVGMetadataSections.tsx` - Show SVG-specific properties

2. **Extended Sections for Images**:
   - `ExtendedAttributesSection.tsx` - Show xattr, permissions
   - `CalculatedMetadataSection.tsx` - Show aspect ratio, megapixels, file age
   - `AdvancedExifSection.tsx` - Show all EXIF fields (collapsible)
   - `GPSDetailsSection.tsx` - Show all GPS fields, not just map

3. **Search Enhancements**:
   - `AdvancedFilters.tsx` - Filter by camera, lens, ISO, aperture, etc.
   - `MetadataFieldAutocomplete.tsx` - Dynamic field discovery from `/api/metadata/schema`

---

## 12. SUMMARY STATISTICS

### Implementation Status

| Category | Total Fields | Implemented | Partial | Not Implemented |
|----------|-------------|-------------|---------|-----------------|
| **Filesystem** | 16 | 16 | 0 | 0 |
| **Extended Attributes** | 2+ | 2 | 0 | 0 |
| **File Identity** | 4 | 4 | 0 | 0 |
| **Hashes** | 2 | 2 | 0 | 0 |
| **Calculated (Universal)** | 9 | 9 | 0 | 0 |
| **Image Properties** | 10 | 10 | 0 | 0 |
| **Calculated (Image)** | 4 | 4 | 0 | 0 |
| **Thumbnails** | 3 | 3 | 0 | 0 |
| **EXIF - Image Tags** | 14 | 14 | 0 | 0 |
| **EXIF - Photo Tags** | 43 | 43 | 0 | 0 |
| **EXIF - Lens** | 4 | 4 | 0 | 0 |
| **EXIF - MakerNote** | 50+ | 50+ | 0 | 0 |
| **EXIF - Interoperability** | 2 | 2 | 0 | 0 |
| **GPS** | 18 | 18 | 0 | 0 |
| **Video Format** | 15 | 15 | 0 | 0 |
| **Video Streams** | 40+ | 40+ | 0 | 0 |
| **Audio Properties** | 7 | 7 | 0 | 0 |
| **Audio Tags** | 12 | 12 | 0 | 0 |
| **PDF** | 12 | 12 | 0 | 0 |
| **SVG** | 10 | 10 | 0 | 0 |
| **IPTC/XMP** | 20 | 0 | 0 | 20 |
| **Perceptual Hashing** | 3 | 0 | 0 | 3 |
| **Color Palette** | 3 | 0 | 0 | 3 |
| **Reverse Geocoding** | 5 | 0 | 0 | 5 |
| **Histogram Analysis** | 3 | 0 | 0 | 3 |
| **OCR (integrated)** | 4 | 0 | 0 | 4 |
| **TOTAL** | **280+** | **240+** | **0** | **38** |

### UI Display Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Shown in UI | ~15 fields | ~6% |
| 🔶 Partially shown | ~10 fields | ~4% |
| ❌ Hidden from UI | ~255 fields | ~90% |

---

## 13. NEXT STEPS (from METADATA_ENHANCEMENT_PLAN.md)

### Phase 1: Enhanced Extraction & Storage
1. Implement `MetadataMapper` class to normalize extracted data
2. Extend database schema with searchable columns
3. Add IPTC/XMP extraction (new library: `iptcinfo3` or `python-xmp-toolkit`)

### Phase 2: Search API & Autocomplete
1. Create `/api/metadata/fields` endpoint
2. Create `/api/metadata/search` with filters
3. Dynamic field autocomplete

### Phase 3: UI Components
1. Build file type-specific metadata panels
2. Add advanced search filters
3. Create metadata statistics dashboard

### Phase 4: Metadata Editor
1. Bulk metadata editing
2. EXIF write-back (using `piexif` or `exiftool`)

### Phase 5: Migration
1. Backfill existing photos with enhanced metadata
2. Performance optimization for 10k+ libraries

---

## Appendix A: Field Naming Conventions

| Convention | Example | Used In |
|------------|---------|---------|
| Dot notation | `exif.image.Make` | Query engine, nested JSON |
| Snake case | `size_bytes` | Database columns, Python |
| Camel case | `sizeBytes` | TypeScript/React |
| EXIF tags | `GPS GPSLatitude` | Raw EXIF extraction |

---

## Appendix B: File Format Support Matrix

| Format | Filesystem | EXIF | GPS | Image Props | Video Props | Audio Props | PDF Props | SVG Props |
|--------|-----------|------|-----|-------------|-------------|-------------|-----------|-----------|
| **JPEG** | ✅ | ✅ | ✅ | ✅ | - | - | - | - |
| **PNG** | ✅ | ✅ | ❌ | ✅ | - | - | - | - |
| **GIF** | ✅ | ❌ | ❌ | ✅ | - | - | - | - |
| **HEIC/HEIF** | ✅ | ✅ | ✅ | ✅ | - | - | - | - |
| **TIFF** | ✅ | ✅ | ✅ | ✅ | - | - | - | - |
| **RAW (CR2, NEF, ARW)** | ✅ | 🔶 | 🔶 | ❌ | - | - | - | - |
| **MP4** | ✅ | - | - | - | ✅ | ✅ | - | - |
| **MOV** | ✅ | - | - | - | ✅ | ✅ | - | - |
| **AVI** | ✅ | - | - | - | ✅ | ✅ | - | - |
| **MKV** | ✅ | - | - | - | ✅ | ✅ | - | - |
| **MP3** | ✅ | - | - | - | - | ✅ | - | - |
| **FLAC** | ✅ | - | - | - | - | ✅ | - | - |
| **WAV** | ✅ | - | - | - | - | ✅ | - | - |
| **M4A/AAC** | ✅ | - | - | - | - | ✅ | - | - |
| **PDF** | ✅ | - | - | - | - | - | ✅ | - |
| **SVG** | ✅ | - | - | - | - | - | - | ✅ |

---

**Document Version**: 1.0
**Last Updated**: 2025-12-29
**Maintainer**: PhotoSearch Development Team
