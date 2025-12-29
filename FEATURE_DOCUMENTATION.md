# Complete Feature Documentation

## Overview
Comprehensive documentation for the 6 new features added to PhotoSearch v2, including user guides, API documentation, troubleshooting, and best practices.

---

## Table of Contents
1. [Events Detection (Analytics)](#1-events-detection)
2. [Video Highlights](#2-video-highlights)
3. [Face Blur on Export](#3-face-blur-on-export)
4. [Hide/Unhide People](#4-hideunhide-people)
5. [API Reference](#5-api-reference)
6. [Troubleshooting](#6-troubleshooting)
7. [Best Practices](#7-best-practices)

---

## 1. Events Detection

### What Is It?
Events Detection automatically identifies when multiple people appear together in photos within a specific time window, detecting "moments" like gatherings, parties, or meetings.

### User Guide

#### Accessing Events
1. Go to **People** → **Events** tab
2. Adjust detection parameters:
   - **Minimum People**: How many people must appear together (2-10)
   - **Time Window**: Time span to consider people together (6-72 hours)

#### Understanding Event Types
| Type | Criteria | Typical Use |
|------|----------|------------|
| Large Gathering | 6+ people, 20+ photos | Conferences, celebrations |
| Party | 4-6 people, varied timing | Social events |
| Small Gathering | 2-4 people, close time range | Casual meetups |
| Meeting | 2-5 people, focused location | Work meetings, appointments |

#### Confidence Scores
- **90-100%**: High confidence event
- **70-89%**: Moderate confidence
- **50-69%**: Low confidence (may include false positives)

#### Viewing Event Details
1. Click an event card to expand
2. View:
   - People involved (person IDs/names)
   - Photos from the event (grid of thumbnails)
   - Time range and duration
   - Confidence score and event type

### Backend Implementation
**Endpoint**: `GET /api/analytics/events`

```python
# Parameters
min_people: int = 3           # Minimum people required
time_window_hours: int = 24   # Time window in hours

# Response
{
  "success": true,
  "events": [
    {
      "event_id": "evt_123",
      "start_time": "2024-01-15T10:00:00Z",
      "end_time": "2024-01-15T14:00:00Z",
      "photo_count": 25,
      "people_count": 5,
      "people_involved": ["person_1", "person_2", ...],
      "photos": ["/path/to/photo1.jpg", ...],
      "event_type": "small_gathering",
      "confidence_score": 0.85
    }
  ]
}
```

### Tips for Better Results
1. **Start with high minimum people count** (5-6) to reduce noise
2. **Use 24-hour window** as a starting point
3. **Adjust dynamically** based on your photo collection
4. **Check confidence scores** - filter by > 75% for reliable results
5. **Combine with manual review** for important events

### Limitations
- Requires at least 2 identified people in photos
- Relies on accurate face clustering
- Time-based analysis only (no location data)
- Detects presence, not necessarily interaction

### Performance
- **First load**: 2-5 seconds (depends on photo count)
- **Subsequent loads**: <500ms (cached)
- **Filter changes**: 1-2 seconds (re-calculation)

---

## 2. Video Highlights

### What Is It?
Video Highlights automatically identifies segments of videos where specific people are prominently featured, creating curated clips for quick review.

### User Guide

#### Accessing Video Highlights
1. Open a video from the **Videos** page
2. View **Highlights** tab
3. Highlights are grouped by person
4. Adjust **Highlights per person** slider (1-10)

#### Highlight Types
| Type | Meaning |
|------|---------|
| Prominent Face | Person is large/clear in frame |
| Multiple Instances | Person appears multiple times |
| Key Moment | High-confidence detection |
| Long Duration | Extended screen time |

#### Using Highlights
1. **View**: Click on a person's highlights to expand
2. **Duration**: See length of each highlight segment
3. **Confidence**: Check detection confidence (0-100%)
4. **Export**: Download highlights for a specific person

#### Exporting Highlights
1. Click the **Download** button for a person
2. System creates a video clip containing all highlights
3. Video is saved with person name and timestamp
4. Process takes 1-3 seconds per person

### Backend Implementation
**Endpoints**:
```
GET  /api/video/{video_path}/highlights?max_per_person=3
POST /api/video/{video_path}/export-highlights
```

**Response Format**:
```python
{
  "success": true,
  "highlights": [
    {
      "person_id": "pid_123",
      "person_name": "John Doe",
      "start_time": 45.5,          # Seconds
      "end_time": 67.2,
      "duration": 21.7,
      "highlight_type": "prominent_face",
      "confidence": 0.92,
      "description": "Large face in frame, clear view"
    }
  ]
}
```

### Tips for Better Results
1. **Start with max 3 highlights** per person
2. **Increase gradually** if you want more detail
3. **Check confidence scores** - filter mentally for > 80%
4. **Export top people** first (they'll have highest confidence)
5. **Use for video summaries** - great for review

### Limitations
- Requires detected faces in video
- Only works for face-based recognition
- Highlights are sequential segments only
- No audio analysis or speech detection

### Performance
- **First load**: 1-3 seconds per video
- **Export per person**: 1-3 seconds
- **Batch export**: 5-15 seconds (depends on video length)

---

## 3. Face Blur on Export

### What Is It?
Automatically blurs all detected faces in exported photos for privacy protection, useful when sharing photos publicly or with third parties.

### User Guide

#### Enabling Face Blur
1. Open **Export** dialog for selected photos
2. Check **"Blur faces"** checkbox
3. Adjust **blur strength** (1=light, 50=heavy)
4. Select other export options
5. Click **Export**

#### Blur Strength Guide
| Strength | Effect | Use Case |
|----------|--------|----------|
| 1-10 | Light blur | Subtle privacy, faces still recognizable |
| 11-25 | Medium blur | Good balance, faces identifiable but obscured |
| 26-35 | Heavy blur | Strong privacy, faces mostly unidentifiable |
| 36-50 | Very heavy | Extreme privacy, faces completely obscured |

#### Recommended Settings by Use Case
| Use Case | Strength | Metadata | Notes |
|----------|----------|----------|-------|
| Social Media | 15-20 | None | Medium blur, no metadata |
| Family Share | 10-15 | Include | Light blur, keep EXIF data |
| Public Release | 25-35 | None | Heavy blur, remove all data |
| Sensitive | 40+ | None | Maximum privacy |

#### What Gets Blurred
✅ All detected faces
✅ Any face detected by the AI model
✅ Multiple faces in same photo
✅ Partial faces at edges

❌ Eyes only (full face is blurred)
❌ Background objects
❌ Non-face regions

### Backend Implementation
**Processor Class**: `FaceBlurProcessor`

```python
class FaceBlurProcessor:
    def blur_image(
        self,
        image_path: str,
        blur_strength: int = 10,
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Args:
            image_path: Path to input image
            blur_strength: Blur radius (1-50)
            output_path: Optional output file path

        Returns:
            Bytes of blurred image
        """
```

**Export Options**:
```python
ExportOptions = {
    "format": "zip",
    "include_metadata": bool,
    "include_thumbnails": bool,
    "max_resolution": Optional[int],
    "blur_faces": bool,              # Enable blur
    "blur_strength": int,             # Blur amount (1-50)
    "password_protect": bool,
    "password": Optional[str]
}
```

### Tips for Best Results
1. **Test on single photo first** - check blur looks good
2. **Use strength 15-20** for most social media
3. **Increase for sensitive photos** (40+)
4. **Combine with metadata removal** for maximum privacy
5. **Disable metadata** for public sharing
6. **Save original** - blur creates new file

### Limitations
- Requires face detection on original photo
- Cannot blur faces not detected by AI
- Processing adds ~1-3 seconds per photo
- Blur cannot be perfectly reversed
- Large blur_strength increases file size slightly

### Performance
- **Single photo**: 1-2 seconds
- **10 photos**: 10-20 seconds
- **100 photos**: 2-4 minutes
- **Memory usage**: 500MB-1GB peak

### Error Handling
| Error | Cause | Solution |
|-------|-------|----------|
| "No faces detected" | Photo has no people | Export without blur or use different photo |
| "Blur strength invalid" | Value outside 1-50 | Use slider values between 1-50 |
| "File not found" | Original deleted | Re-select photos |
| "Permission denied" | No write access | Check folder permissions |

---

## 4. Hide/Unhide People

### What Is It?
Allows hiding person clusters from the main People view, useful for filtering out non-relevant people or duplicates while keeping data intact.

### User Guide

#### Hiding a Person
1. Go to **People** page
2. Find the person you want to hide
3. Click **Hide** button (eye-off icon)
4. Person is removed from main view
5. Data is preserved (not deleted)

#### Finding Hidden People
1. Go to **People** page
2. Click **Hidden** tab
3. View all hidden person clusters
4. Click **Unhide** to restore to main view

#### When to Hide
- Duplicate person clusters (before merging)
- Non-relevant detections (false positives)
- People with low quality images
- Test/placeholder clusters
- Faces you don't want to organize

#### Unhiding
1. Go to **People** → **Hidden** tab
2. Find the person
3. Click **Unhide** button
4. Person reappears in main People view
5. All photos and data intact

### Backend Implementation
**Endpoints**:
```
POST /api/faces/clusters/{cluster_id}/hide
POST /api/faces/clusters/{cluster_id}/unhide
```

**Database Field**:
```python
# In face_clusters table
hidden: bool = False

# Queries automatically exclude hidden clusters:
SELECT * FROM face_clusters WHERE hidden = FALSE
```

### Tips for Organization
1. **Hide duplicates** - after merging clusters
2. **Hide false positives** - non-people detections
3. **Regular review** - hidden tab for cleanup
4. **Don't delete** - hiding is safer, can restore
5. **Bulk operations** - consider bulk hide/unhide

### Limitations
- Hidden people still count toward statistics
- Hidden photos still processed
- No bulk hide operations (UI-only)
- Hidden people still indexed (search works)

### Performance
- **Hide action**: <100ms
- **Unhide action**: <100ms
- **Loading hidden tab**: 1-2 seconds

### State Management
```typescript
// Frontend state
interface FaceCluster {
  id: string;
  label?: string;
  hidden?: boolean;  // Shows hide status
  // ... other fields
}

// Toggle visibility
const handleHide = async (clusterId: string) => {
  await api.post(`/api/faces/clusters/${clusterId}/hide`);
  // UI updates to remove from view
};

const handleUnhide = async (clusterId: string) => {
  await api.post(`/api/faces/clusters/${clusterId}/unhide`);
  // UI updates to show in main view
};
```

---

## 5. API Reference

### Events Endpoint

#### GET /api/analytics/events
Retrieve detected events based on face co-occurrence.

**Parameters**:
```
min_people: int (default: 3, range: 2-10)
  Minimum number of people required for an event

time_window_hours: int (default: 24, options: 6, 12, 24, 48, 72)
  Time window in hours for grouping photos
```

**Response** (200 OK):
```json
{
  "success": true,
  "events": [
    {
      "event_id": "evt_12345",
      "start_time": "2024-01-15T10:30:00Z",
      "end_time": "2024-01-15T14:45:00Z",
      "photo_count": 42,
      "people_count": 5,
      "people_involved": ["person_1", "person_2", "person_3"],
      "photos": [
        "/home/user/Pictures/photo1.jpg",
        "/home/user/Pictures/photo2.jpg"
      ],
      "event_type": "small_gathering",
      "confidence_score": 0.87
    }
  ]
}
```

**Error Responses**:
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Database error

---

### Video Highlights Endpoint

#### GET /api/video/{video_path}/highlights
Get highlights for a video file.

**Parameters**:
```
video_path: string (path, required)
  URL-encoded path to video file

max_per_person: int (default: 3, range: 1-10)
  Maximum highlights to return per person
```

**Response** (200 OK):
```json
{
  "highlights": [
    {
      "person_id": "pid_456",
      "person_name": "Jane Doe",
      "start_time": 45.5,
      "end_time": 67.2,
      "duration": 21.7,
      "highlight_type": "prominent_face",
      "confidence": 0.92,
      "description": "Clear view of face"
    }
  ]
}
```

#### POST /api/video/{video_path}/export-highlights
Export highlights for a specific person.

**Request Body**:
```json
{
  "person_id": "pid_456"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "output_path": "/path/to/highlights_jane_doe.mp4"
}
```

---

### Face Blur Endpoint

#### POST /api/export
Export photos with optional face blur.

**Request Body**:
```json
{
  "photo_paths": ["/path/to/photo1.jpg", "/path/to/photo2.jpg"],
  "options": {
    "format": "zip",
    "include_metadata": true,
    "include_thumbnails": false,
    "max_resolution": 1920,
    "blur_faces": true,
    "blur_strength": 15
  }
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "download_url": "/api/export/file_abc123.zip",
  "file_size": "24.5 MB",
  "photo_count": 15,
  "blurred_count": 15
}
```

---

### Hide/Unhide Endpoints

#### POST /api/faces/clusters/{cluster_id}/hide
Hide a person cluster.

**Response** (200 OK):
```json
{
  "success": true,
  "cluster_id": "cluster_123",
  "hidden": true
}
```

#### POST /api/faces/clusters/{cluster_id}/unhide
Unhide a person cluster.

**Response** (200 OK):
```json
{
  "success": true,
  "cluster_id": "cluster_123",
  "hidden": false
}
```

---

## 6. Troubleshooting

### Events Issues

#### No events detected
**Symptoms**: "No events detected with current settings" message

**Causes**:
- Settings are too restrictive (min_people too high)
- No photos with multiple identified people
- Time window too small

**Solutions**:
1. Lower **Minimum People** to 2-3
2. Increase **Time Window** to 48-72 hours
3. Ensure faces are properly identified
4. Run face clustering first
5. Verify photo dates are correct

#### Events appear but confidence is low
**Symptoms**: Events showing but confidence < 50%

**Causes**:
- Face clustering accuracy issues
- Inconsistent lighting/angles
- Poor quality photos

**Solutions**:
1. Improve face clustering with manual merges
2. Re-run face detection on low-quality photos
3. Filter by confidence > 0.75 manually
4. Use stricter min_people (4-5) to get fewer, higher-quality events

---

### Video Highlights Issues

#### Video file not found
**Symptoms**: "Video file not found" error

**Causes**:
- Video path is incorrect
- Video moved or deleted
- Permission issues

**Solutions**:
1. Verify video file still exists
2. Check full path is correct
3. Ensure read permissions on video
4. Try different video format

#### No highlights detected
**Symptoms**: Empty highlights list

**Causes**:
- No faces detected in video
- Faces too small/blurry to detect
- Video quality too low

**Solutions**:
1. Verify faces are visible in video
2. Use higher quality video source
3. Adjust face detection sensitivity
4. Try manually adding people to video

#### Export highlights failed
**Symptoms**: Download fails or file corrupted

**Causes**:
- Video codec not supported
- Disk space full
- File permission issues

**Solutions**:
1. Check disk space
2. Try different video
3. Verify FFmpeg is installed
4. Check folder write permissions

---

### Face Blur Issues

#### Blur not applied to some faces
**Symptoms**: Some people's faces not blurred, others are

**Causes**:
- Face detection missed some faces
- Faces at image edges not detected
- Very small or obscured faces

**Solutions**:
1. Manually verify face detection in image
2. Use higher blur_strength (15-20) to catch edges
3. Re-run face detection
4. Manually blur using photo editor

#### Blur makes image quality poor
**Symptoms**: Image looks over-processed after blur

**Causes**:
- Blur strength too high
- JPEG compression too aggressive
- Image already low quality

**Solutions**:
1. Reduce blur strength to 10-15
2. Disable metadata removal if quality critical
3. Use highest quality JPEG setting
4. Blur on copy, keep original

#### Blur processing takes too long
**Symptoms**: Export with blur takes >30 seconds

**Causes**:
- Many photos to process
- Photos are high resolution
- Server under heavy load

**Solutions**:
1. Reduce photo count (export fewer at once)
2. Reduce max_resolution in export options
3. Disable blur if not needed
4. Try again during off-peak hours

#### Export fails with "Permission Denied"
**Symptoms**: Export fails with permission error

**Causes**:
- Export directory not writable
- Insufficient disk space
- File locked by another process

**Solutions**:
1. Check folder permissions: `chmod 755 export_dir`
2. Free up disk space
3. Close other applications
4. Try different export folder

---

### Hide/Unhide Issues

#### Hidden person still appearing in search
**Symptoms**: Hidden people appear in search results

**Causes**:
- Search indexes all people (design choice)
- Hidden people still have metadata

**Solutions**:
1. This is normal - hidden doesn't affect indexing
2. Use hidden tab to view hidden people
3. Consider merging instead of hiding
4. Use privacy controls for actual deletion

#### Can't unhide person
**Symptoms**: Unhide button doesn't work

**Causes**:
- Hidden tab not loading
- Person cluster was deleted
- Database corruption

**Solutions**:
1. Refresh page and try again
2. Check browser console for errors
3. Check database integrity
4. Contact support if cluster missing

---

### General Issues

#### API returns 500 Internal Server Error
**Symptoms**: "500 Internal Server Error" message

**Causes**:
- Database connection issue
- Invalid photo path
- Server side exception

**Solutions**:
1. Check server logs: `tail -f server.log`
2. Verify database is running
3. Check photo paths are valid
4. Restart server

#### Slow performance on all features
**Symptoms**: All features respond slowly

**Causes**:
- Database inefficient queries
- Large photo library
- Server resources exhausted

**Solutions**:
1. Check disk space
2. Monitor CPU/RAM usage
3. Optimize database: `sqlite3 photo_metadata.db "VACUUM;"`
4. Reduce max_per_person or min_people settings
5. Export in smaller batches

---

## 7. Best Practices

### Event Detection Best Practices

1. **Start Conservative**
   - Begin with min_people=5, time_window=24h
   - Adjust down if you get no results
   - This catches larger, more meaningful events

2. **Filter by Confidence**
   - Focus on events with >80% confidence
   - These are most likely real gatherings
   - Ignore lower confidence unless specific reason

3. **Regular Review**
   - Check events monthly
   - Delete false positives
   - Rename events with meaningful titles
   - Tag important events

4. **Combine with Photos**
   - Use event timeline to browse photos
   - Cross-reference with calendar
   - Verify people are correctly identified

### Video Highlights Best Practices

1. **Export Key People First**
   - Start with highest confidence
   - Export 1-3 people from video
   - Review quality before larger exports

2. **Adjust Max Per Person**
   - 1-3: Minimal, only key moments
   - 4-6: Good coverage
   - 7-10: Full details
   - Start at 3 and adjust based on video length

3. **Use Descriptive Names**
   - Export with meaningful timestamps
   - Include person name in filename
   - Organize by date/event

4. **Check Quality**
   - Preview before full export
   - Verify face quality
   - Check audio is retained

### Face Blur Best Practices

1. **Test First**
   - Blur 1-2 photos first
   - Check output quality
   - Verify all faces are blurred
   - Adjust strength if needed

2. **Balance Privacy & Clarity**
   - Social media: strength 10-15
   - Shared with strangers: 20-25
   - Extremely sensitive: 35+
   - Find your comfort level

3. **Remove Metadata When Sharing**
   - Disable "Include metadata" for public
   - Removes EXIF, location, timestamps
   - Removes person IDs

4. **Keep Originals**
   - Always keep unblurred originals
   - Blur creates new files
   - Original remains untouched
   - Can re-export with different settings

5. **Document Privacy Policy**
   - Inform viewers faces are blurred
   - Explain why (privacy protection)
   - Store originals securely

### Hide/Unhide Best Practices

1. **Use Before Deletion**
   - Hide suspicious duplicates
   - Review before deleting
   - Never permanently delete unless sure

2. **Regular Cleanup**
   - Monthly review of hidden people
   - Merge legitimate duplicates
   - Delete false positives

3. **Keep Notes**
   - Note why each person is hidden
   - Date of hiding
   - Plan for review

4. **Backup Before Major Changes**
   - Export database before bulk hiding
   - Keep backup of important data
   - Test on copy first

### General Best Practices

1. **Regular Backups**
   - Daily backup of database
   - Weekly photo backup
   - Monthly full system backup

2. **Monitor Performance**
   - Watch for slow responses
   - Check disk space regularly
   - Monitor memory usage
   - Run cleanup/optimize monthly

3. **Test Changes**
   - Test new features on small set first
   - Verify results before full deployment
   - Keep notes on what works

4. **Documentation**
   - Document custom settings
   - Note specific feature use cases
   - Keep troubleshooting notes
   - Share with team if collaborative

5. **Security Considerations**
   - Blur faces for sensitive photos
   - Remove metadata before sharing
   - Use password on sensitive shares
   - Limit access to people data
   - Regular security updates

---

## FAQ

### Q: Can I undo a hide action?
**A**: Yes! Go to People → Hidden tab and click Unhide. Your data is not lost.

### Q: How accurate are event detections?
**A**: ~75-85% accurate. Some false positives possible. Always verify before relying on results.

### Q: Does blur processing change original photos?
**A**: No. Blur creates new files. Originals are never modified.

### Q: Can I blur only specific faces?
**A**: Currently blurs all detected faces. No selective blurring per face.

### Q: How long are share links valid?
**A**: You choose: 1 hour to 1 month. Can set when creating link.

### Q: Are hidden people included in statistics?
**A**: Yes, they're still counted in total people/clusters. Consider merging or deleting instead.

### Q: What video formats are supported?
**A**: MP4, MOV, MKV, AVI, WebM (depends on FFmpeg installation).

### Q: How do I improve event detection?
**A**: Ensure faces are properly identified first. Run face clustering. Adjust parameters gradually.

---

## Support & Feedback

For issues or feature requests:
1. Check **Troubleshooting** section above
2. Review API documentation
3. Check application logs
4. Report with detailed error messages
5. Include system information (OS, Python version, etc.)

---

## Version History

### v1.0.0 - Initial Release
- ✅ Events Detection
- ✅ Video Highlights
- ✅ Face Blur on Export
- ✅ Hide/Unhide People
- ✅ Improved Error Handling
- ✅ Loading Skeletons

### Future Enhancements
- [ ] Bulk hide/unhide operations
- [ ] Custom event detection rules
- [ ] Real-time video processing
- [ ] Advanced blur options
- [ ] Event timeline visualization
- [ ] Selective face blurring
