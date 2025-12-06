# Photo Search Application - FAQ

**Purpose:** Track all questions, clarifications, and decisions made during development  
**Last Updated:** 2025-12-06

---

## Project Setup & Structure

### Q1: Where should documentation be stored?
**Asked:** 2025-12-06  
**Question:** "Would you like me to first create an initial project overview document that outlines the potential architecture and task breakdown for the photo search application? Or would you prefer to jump straight into the first specific task you have in mind? - first create your docs and put in a folder called antigravity (under docs folder at the root), all docs would be put under docs folder at the root then i will start with each task, i will ask questions for clarity, understanding etc as well which you should put under an faq doc of what i asked etc."

**Answer:**  
All documentation should be organized as follows:
- **Antigravity (AI) documentation** → `docs/antigravity/`
  - Architecture documents
  - Task breakdowns
  - Technical decisions
- **General project documentation** → `docs/`
  - FAQ (this file)
  - User guides
  - Other project docs

**Decision:** Created the following structure:
```
docs/
├── antigravity/
│   ├── PROJECT_ARCHITECTURE.md
│   ├── TASK_BREAKDOWN.md
│   ├── AI_PROVIDERS.md
│   └── DEVELOPMENT_GUIDE.md
└── FAQ.md
```

---

### Q2: What should be the first task?
**Asked:** 2025-12-06  
**Question:** "once we get to the point create the config etc as needed...for now 1st req. is program that looks through the system (no system files and folders - only user ones) lists/saves all image and video files, so it would be something like folder name, file names, 1st would be the full list and 2nd user can enter a folder name it gives all image and video file names, or user enters file name it gives folders where it exists else result for all is that not found"

**Answer:**  
First task is to create a file discovery system before configuration. This makes sense as we need to:
1. Discover and catalog all image/video files on the system
2. Build a searchable index
3. This will be the foundation for the photo search application

**Decision:** 
- Skip Task 1 (config) for now, implement as needed later
- Start with file discovery system as `file_discovery.py`
- This becomes the new Task 1 in practical implementation order

---

### Q3: Implementation details for file discovery system
**Asked:** 2025-12-06  
**Question:** "yes keep it to /users/pranay/ but we generalise so when run on any computer it does so only in the users folder, all media file images and videos gifs etc., json is fine, no unless we are at the last node, also how would it work in case files are added or removed, folders are added removed?"

**Answer:**
1. **Dynamic user home** - Use `pathlib.Path.home()` to automatically detect user home directory on any computer (not hardcoded)
2. **All media formats** - Include all image, video, and animated formats (JPG, PNG, GIF, MP4, MOV, etc.)
3. **JSON format** - Confirmed, will use JSON for catalog storage
4. **Scan depth** - No depth limit, scan all the way to leaf nodes (deepest directories)
5. **Incremental updates** - Implement change detection:
   - Track file modification times
   - Detect added/removed files
   - Detect added/removed folders
   - Provide both full scan and incremental update options

**Decision:**
- Use `pathlib.Path.home()` for cross-platform user home detection
- Expand media format list to include all common types
- Store file `mtime` (modification time) in catalog for change detection
- Add `detect_changes()` and `update_catalog()` functions
- CLI will offer both "Full Scan" and "Incremental Update" options

---

### Q4: Task 2 - Format analysis extension
**Asked:** 2025-12-06  
**Question:** "next would be an extension to this: list directory wise formats like dir 1 has 4 jpg, 3 png etc, so now search becomes find jpg , list all folders with jpg, find by jpg in dir 1, if yes list else say no, and other file type wise...this would be our proj file 2 as its a new second task but has dependency on task 1"

**Answer:**
Task 2 will be a format analysis extension that builds on Task 1's file discovery system.

**Features to implement:**
1. **Directory-wise format statistics** - Show format breakdown per directory (e.g., "Photos: 4 JPG, 3 PNG, 2 GIF")
2. **Search by format** - Find all folders containing specific format (e.g., "find JPG" → list all folders with JPG files)
3. **Format in specific directory** - Check if format exists in directory and list files (e.g., "JPG in Photos?" → Yes + list of JPG files, or No)
4. **Support all formats** - Work with all image/video formats from Task 1

**Decision:**
- Create new file: `format_analyzer.py`
- Import catalog loading from `file_discovery.py` (reuse existing functionality)
- Add format-specific analysis and search functions
- Maintain same CLI + interactive interface pattern
- This is Task 2 with dependency on Task 1

---

### Q5: Task 3 - Comprehensive metadata extraction
**Asked:** 2025-12-06  
**Question:** "task 3 - read a file's metadata - everything i mean the most comprehensive metadata reader- created by, modified, times, size, permissions, formats, camera exifs, locations, resolutions etc. so for anu given file should be able to get everything in a properly readable json"

**Answer:**
Task 3 will be a comprehensive metadata extraction system that reads ALL metadata from any file.

**Metadata to extract:**
1. **Filesystem metadata** - Created, modified, accessed times, size, permissions, owner, group
2. **EXIF data** - Camera make/model, lens info, camera settings (ISO, aperture, shutter speed, focal length, flash)
3. **GPS location** - Latitude, longitude, altitude, timestamp if available
4. **Image properties** - Resolution, dimensions, color space, DPI, orientation
5. **Video properties** - Duration, codec, bitrate, frame rate, audio tracks
6. **Format info** - MIME type, file format, compression details

**Output:**
- Clean, readable JSON format
- Hierarchical structure for organization
- Handle missing metadata gracefully (null/not available)

**Decision:**
- Create new file: `metadata_extractor.py`
- Use libraries: Pillow (images), exifread (EXIF), ffprobe (video), os/stat (filesystem)
- Support all media formats from Task 1
- CLI + interactive interface pattern
- This is Task 3 with no dependencies on Task 1 or 2 (standalone)

---

## Questions Awaiting Answers

*No pending questions at this time*

---

## Development Workflow Questions

*This section will be populated as questions arise during task implementation*

---

## Technical Questions

*This section will be populated as technical questions arise*

---

## API & Service Questions

*This section will be populated as questions about AI providers and services arise*

---

## Design & Architecture Questions

*This section will be populated as design decisions require clarification*

---

## Notes

- This FAQ will be updated after each question/clarification
- Questions will be organized by category for easy reference
- Each entry will include the full context for future reference
- Decisions made based on questions will be clearly documented

---

**How to Use This FAQ:**
1. When you ask a question, it will be added here with full context
2. The answer and any resulting decisions will be documented
3. This serves as a living record of our development discussions
4. Can be referenced later to understand why certain decisions were made
