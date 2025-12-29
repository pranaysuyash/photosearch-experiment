# Testing New Features - PhotoSearch V2

## 1. Events Tab Testing

### Setup
- Navigate to People page
- Click on "Events" tab

### Test Cases

#### 1.1 Events Display
- [ ] Events list loads without errors
- [ ] Shows correct number of people and highlights
- [ ] No spinner/loading state after 3 seconds

#### 1.2 Event Expansion
- [ ] Clicking event expands to show details
- [ ] Shows people involved with proper formatting
- [ ] Shows photo thumbnails in grid
- [ ] Click again collapses the event

#### 1.3 Detection Parameters
- [ ] "Minimum People" slider works (2-10)
- [ ] "Time Window" dropdown changes values (6h, 12h, 24h, 48h, 72h)
- [ ] Events list updates when parameters change
- [ ] Loading spinner shows during update

#### 1.4 Edge Cases
- [ ] No crashes when zero events detected
- [ ] Shows "No events detected" message
- [ ] Handles missing person names gracefully
- [ ] Broken image thumbnails show placeholder

---

## 2. Video Highlights Testing

### Setup
- Navigate to Videos page
- Open a video that has face detections
- (Component not yet integrated into video player, but can be tested standalone)

### Test Cases

#### 2.1 Highlights Loading
- [ ] Highlights load without errors
- [ ] Shows people featured with avatar circles
- [ ] Shows correct number of highlights per person
- [ ] Total duration calculation is correct

#### 2.2 Person Expansion
- [ ] Clicking person expands highlights list
- [ ] Each highlight shows type, time range, duration, confidence
- [ ] Click again collapses the list
- [ ] Multiple people can be expanded

#### 2.3 Export Functionality
- [ ] Export button appears and is clickable
- [ ] Shows loading spinner while exporting
- [ ] Success message shows on completion
- [ ] Exported files exist in specified directory

#### 2.4 Max Per Person Control
- [ ] Slider updates value correctly (1-10)
- [ ] Highlights re-load with new limit
- [ ] Number of highlights matches slider value

#### 2.5 Edge Cases
- [ ] Handles zero highlights gracefully
- [ ] Shows "No highlights" message when appropriate
- [ ] Handles missing/broken video path
- [ ] Export with network error shows retry

---

## 3. Face Blur on Export Testing

### Setup
- Select multiple photos (3-5)
- Open Export dialog
- Check "Blur faces" option

### Test Cases

#### 3.1 Blur Toggle & Controls
- [ ] "Blur faces" checkbox toggles blur controls
- [ ] Blur strength slider appears when enabled
- [ ] Slider range is 1-50
- [ ] Current strength value displays (e.g., "Blur strength: 25")
- [ ] Unchecking hides the slider

#### 3.2 Export with Blur
- [ ] Photos export successfully with blur enabled
- [ ] Exported images show blurred faces
- [ ] Blur quality matches slider strength
- [ ] Export time reasonable (not too slow)

#### 3.3 Blur + Other Options
- [ ] Blur works with "Include metadata"
- [ ] Blur works with "Include thumbnails"
- [ ] Blur works with "Max resolution"
- [ ] Blur works with password protection

#### 3.4 Edge Cases
- [ ] Exports without errors when photo has no faces
- [ ] Handles corrupted image gracefully
- [ ] Shows error message if blur processor fails
- [ ] Falls back to unblurred image on error

---

## 4. Hide/Unhide Button Testing

### Setup
- Navigate to People page
- Look at person cards in "People" tab

### Test Cases

#### 4.1 Hide Button Display
- [ ] Hide button appears on each person card
- [ ] Button shows EyeOff icon
- [ ] Tooltip says "Hide this person"
- [ ] Button is disabled state briefly during operation

#### 4.2 Hide Functionality
- [ ] Click hide button removes person from list
- [ ] Loading spinner shows during hide
- [ ] Success message appears (or silent on success)
- [ ] Person doesn't reappear on page refresh

#### 4.3 Unhide Functionality
- [ ] Switch to "Hidden" view
- [ ] Hidden people appear in list
- [ ] Unhide button shows on hidden people
- [ ] Click unhide brings person back to main view
- [ ] Person reappears in main list

#### 4.4 Mixed Operations
- [ ] Can hide multiple people
- [ ] Can unhide multiple people
- [ ] Hidden count updates correctly
- [ ] Stats update after hide/unhide

#### 4.5 Edge Cases
- [ ] No crashes if hide fails
- [ ] Error message shows on failure
- [ ] Button remains functional after error
- [ ] Works with people that have no photos
- [ ] Works with all person types (singletons, clusters, etc.)

---

## 5. SQL Bug Fixes Verification

### Test Cases

#### 5.1 Timeline Feature
- [ ] Person timeline loads without SQL errors
- [ ] Shows photos in chronological order
- [ ] Age progression calculates correctly
- [ ] Quality trends display

#### 5.2 Analytics
- [ ] Person analytics loads
- [ ] Relationships display correctly
- [ ] No "no such column" errors in console

#### 5.3 Advanced Search
- [ ] Attribute search works (age, emotion, etc.)
- [ ] Results display with correct face info
- [ ] Bounding boxes show correctly

#### 5.4 Review Queue
- [ ] Queue loads without errors
- [ ] Shows needs review items
- [ ] Photos display with face boxes

---

## Bug Report Template

If issues found:
```
## Bug: [Feature] - [Brief Description]

### Steps to Reproduce
1.
2.
3.

### Expected Result

### Actual Result

### Screenshots/Video

### Environment
- Browser:
- OS:
- Reproducible: [Yes/No/Sometimes]

### Console Errors
```

---

## Performance Checklist

- [ ] Events load in < 3 seconds
- [ ] Video highlights load in < 2 seconds
- [ ] Export with blur completes in < 30 seconds (for 5 photos)
- [ ] Hide/Unhide responds in < 1 second
- [ ] No memory leaks (check DevTools)
- [ ] No excessive re-renders (React DevTools)
