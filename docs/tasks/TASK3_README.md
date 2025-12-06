## Task 3: Comprehensive Metadata Extraction

**File:** `metadata_extractor.py`  
**Status:** ✅ Complete  
**Dependencies:** Pillow, exifread, ffmpeg-python, python-magic, xattr

### Features

The MOST comprehensive metadata extraction system that captures absolutely everything from any file:

1. **Filesystem Metadata**
   - Size (bytes + human-readable)
   - Times: created, modified, accessed, changed
   - Permissions (octal + human-readable)
   - Owner/group (UID/GID + names)
   - Inode, device, hard links, file type

2. **Extended Attributes (xattr)**
   - All custom user attributes
   - macOS Spotlight metadata
   - Gracefully handles Windows (not available)

3. **EXIF Metadata**
   - ALL standard EXIF tags (IFD0, IFD1, ExifIFD, GPS, Interoperability)
   - MakerNote data (manufacturer-specific proprietary tags)
   - Organized by category for easy navigation

4. **GPS Metadata**
   - Latitude/longitude (DMS → decimal conversion)
   - Altitude, timestamp, datestamp
   - Speed, track, image direction
   - Satellites, DOP, map datum

5. **Image Properties**
   - Dimensions, format, mode
   - DPI, bits per pixel
   - Color palette, ICC profile
   - Animation support (frames)

6. **Video Properties**
   - ALL ffprobe fields (format, streams, chapters)
   - Duration, bitrate, codec
   - Frame rate, resolution
   - Audio tracks, subtitles

7. **File Integrity**
   - MD5 hash
   - SHA256 hash

8. **Thumbnails**
   - Embedded thumbnail detection
   - Thumbnail generation

9. **Calculated/Inferred Metadata**
   - **Image:** Aspect ratio, megapixels, orientation
   - **Video:** Total frames, size per second, quality estimate
   - **Time:** File age, time since modified/accessed (human-readable)
   - **Size:** Human-readable formatting

### Usage

```bash
# Extract metadata from single file
python metadata_extractor.py photo.jpg

# Save to JSON file
python metadata_extractor.py photo.jpg --output metadata.json

# Extract from multiple files
python metadata_extractor.py photo1.jpg video.mp4

# Batch process to directory
python metadata_extractor.py *.jpg --output-dir metadata/

# Works with filenames containing spaces and special characters
python metadata_extractor.py "My Photo 2024.jpg" "Screen Recording @ 3pm.mp4"
```

### Example Output

**PNG Image (3374x2156, 476KB):**
```json
{
  "file": {
    "path": "/Users/pranay/Projects/photosearch_experiment/image1.png",
    "mime_type": "image/png"
  },
  "filesystem": {
    "size_bytes": 487485,
    "size_human": "476.1 KB",
    "created": "2025-11-17T23:49:46",
    "permissions_human": "-rw-r--r--",
    "owner": "pranay"
  },
  "image": {
    "width": 3374,
    "height": 2156,
    "format": "PNG",
    "mode": "RGBA",
    "dpi": [144, 144],
    "icc_profile": "yes"
  },
  "exif": {
    "image": {
      "XResolution": "144",
      "YResolution": "144"
    },
    "exif": {
      "UserComment": "Screenshot"
    }
  },
  "hashes": {
    "md5": "c45f650a81796ea301f34b2357aa7fe3",
    "sha256": "7f12db35576193dcc64dfb1f037c4d456b95b1f13a5c8b7afbdf40e476d3a63a"
  },
  "calculated": {
    "aspect_ratio": "241:154",
    "aspect_ratio_decimal": 1.565,
    "megapixels": 7.27,
    "orientation": "landscape",
    "file_age": {
      "days": 18,
      "human_readable": "18 days ago"
    }
  }
}
```

**MP4 Video (3358x1522, 45.9MB, 49 seconds):**
```json
{
  "video": {
    "format": {
      "duration": "49.066667",
      "bit_rate": "7851222",
      "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
    },
    "streams": [{
      "codec_name": "h264",
      "width": 3358,
      "height": 1522,
      "r_frame_rate": "60/1",
      "nb_frames": "2932"
    }]
  },
  "calculated": {
    "duration_human": "0:49",
    "size_per_second": "958.4 KB"
  }
}
```

### Test Results

| Test | File Type | Result |
|------|-----------|--------|
| Filesystem metadata | All files | ✅ Pass |
| Extended attributes (xattr) | macOS files | ✅ Pass |
| File hashes (MD5, SHA256) | All files | ✅ Pass |
| Image properties | PNG screenshot | ✅ Pass (3374x2156, 7.27MP) |
| EXIF data | PNG screenshot | ✅ Pass (resolution, user comment) |
| Video metadata | MP4 screen recording | ✅ Pass (H.264, 60fps, 49s) |
| Calculated metadata | All files | ✅ Pass (aspect ratios, file age) |
| Filename handling | Files with spaces | ✅ Pass (fixed with Path objects) |

### What Worked

- ✅ **Comprehensive extraction** - Captures ALL possible metadata fields
- ✅ **Library selection** - exifread (ALL EXIF tags), ffmpeg-python (ALL video fields)
- ✅ **Hierarchical JSON** - Clean, organized structure
- ✅ **Human-readable formatting** - File sizes, time periods, permissions
- ✅ **Calculated metadata** - Aspect ratios, megapixels, file age
- ✅ **Cross-platform** - Works on macOS, Linux, Windows (xattr gracefully skips on Windows)
- ✅ **Filename handling** - Fixed to support spaces and special characters

### What Could Be Improved

- **Batch processing** - Extract metadata from all files in catalog
- **Metadata comparison** - Compare metadata between files
- **Metadata editing** - Update EXIF data (write mode)
- **Thumbnail extraction** - Save embedded thumbnails to files
- **Hash calculation optimization** - Parallel processing for large files
- **Metadata search** - Find files by metadata criteria
- **Export formats** - CSV, XML in addition to JSON

### Lessons Learned

1. **exifread is powerful** - Captures even obscure EXIF tags including MakerNote
2. **Path objects are essential** - Proper handling of filenames with spaces and special characters
3. **ffprobe returns complex JSON** - Need to preserve all fields for comprehensive metadata
4. **Time calculations add value** - Human-readable periods ("18 days ago") improve UX
5. **Chunk-based hashing is essential** - For handling large video files efficiently
6. **Error handling is critical** - Try-except blocks prevent crashes on corrupted files

---
## 🎯 Development Roadmap
