# Testing Guide - New Features (2025-12-17)

**Date**: 2025-12-17
**Features to Test**: Albums + Grid Zoom
**Estimated Time**: 20-30 minutes
**Difficulty**: Easy

---

## 🚀 Quick Start

### 1. Start the Application

```bash
# Terminal 1: Backend
cd /Users/pranay/Projects/photosearch_experiment/server
python main.py

# Terminal 2: Frontend
cd /Users/pranay/Projects/photosearch_experiment/ui
npm run dev

# Open browser: http://localhost:5173
```

---

## 📋 Test Scenarios

### ✅ Test 1: Albums Navigation (30 seconds)

1. Look for the 📁 **FolderOpen icon** in the top navigation bar
2. Click it
3. **Expected**: Navigate to `/albums` page
4. **Expected**: See "Albums" heading with "Organize your photos into collections" subtitle

---

### ✅ Test 2: Smart Albums Auto-Population (1 minute)

1. On Albums page, scroll to "Smart Albums" section
2. **Expected**: See 5 smart albums:
   - Screenshots
   - Large Videos
   - No Location
   - Recent Photos
   - With Location
3. Each should show photo count badge
4. Each should have yellow ⚡ "Smart" badge
5. Click any smart album
6. **Expected**: See photos that match the rule
7. **Expected**: See ↻ refresh button (top-right)
8. Click refresh button
9. **Expected**: Photo count updates if matches changed

---

### ✅ Test 3: Create Custom Album (2 minutes)

1. On Albums page, find floating blue + button (bottom-right)
2. Click it
3. **Expected**: Create Album dialog appears
4. Type album name: "Test Album"
5. Type description: "Testing the albums feature"
6. Click "Create Album"
7. **Expected**: Dialog closes, album appears in "My Albums" section
8. **Expected**: Photo count shows 0

---

### ✅ Test 4: Add Photos to Album (2 minutes)

1. Navigate to home page (/)
2. Enable multi-select mode (checkbox button in header)
3. Select 3-5 photos
4. **Expected**: Selection toolbar appears with actions
5. Look for "Add to Album" button (if implemented in multi-select)
6. **Alternative**: Open a single photo detail
7. Right-click or look for "Add to Album" option
8. Select your "Test Album"
9. **Expected**: Photos added successfully
10. Navigate back to Albums page
11. Click "Test Album"
12. **Expected**: See the photos you just added

---

### ✅ Test 5: Edit Album (1 minute)

1. Open "Test Album" detail
2. Click ⋮ (three dots) menu button (top-right)
3. Click "Edit Album"
4. **Expected**: Edit dialog opens with current values
5. Change name to "Updated Test Album"
6. Change description to "Updated description"
7. Click "Save Changes"
8. **Expected**: Dialog closes, changes reflected immediately

---

### ✅ Test 6: Delete Album (1 minute)

1. Open album detail
2. Click ⋮ menu button
3. Click "Delete Album"
4. **Expected**: Confirmation dialog appears
5. Confirm deletion
6. **Expected**: Return to albums grid
7. **Expected**: Album no longer appears
8. **Expected**: Photos remain in library (not deleted)

---

### ✅ Test 7: Grid Zoom Controls (2 minutes)

1. Navigate to home page (/)
2. Look for zoom controls in PhotoGrid header
3. **Expected**: See controls with current zoom level (e.g., "Comfortable")
4. Click **-** button (zoom out)
5. **Expected**: Grid becomes more dense (more columns)
6. **Expected**: Label changes to "Dense"
7. Click **+** button twice (zoom in)
8. **Expected**: Grid becomes more spacious (fewer columns)
9. **Expected**: Label changes to "Spacious"
10. Click the center label ("Spacious")
11. **Expected**: Cycles to "Dense"
12. Refresh page
13. **Expected**: Zoom level persists (stays at "Dense")

---

### ✅ Test 8: Keyboard Shortcuts (1 minute)

1. On home page with PhotoGrid visible
2. Press **+** key (or = key without shift)
3. **Expected**: Grid zooms in
4. Press **-** key
5. **Expected**: Grid zooms out
6. Click in search bar (input field)
7. Press **+** or **-**
8. **Expected**: Does NOT zoom (keyboard shortcuts disabled in inputs)

---

### ✅ Test 9: Albums Empty States (1 minute)

1. Navigate to /albums
2. If no custom albums exist:
   - **Expected**: "No custom albums yet" message
   - **Expected**: "Create Album" button
3. Create a new album
4. Open the empty album
5. **Expected**: "No photos in this album" message
6. **Expected**: For smart albums: "This smart album will automatically populate when matching photos are found"

---

### ✅ Test 10: Design System Consistency (2 minutes)

Visual inspection across all new components:

**Glass-morphism**:
- [ ] Album cards have glass-panel with backdrop-blur
- [ ] Dialogs have glass-panel background
- [ ] Buttons use btn-glass style
- [ ] Navigation pod uses glass-surface

**Colors**:
- [ ] Smart album badge is yellow (`text-yellow-400`)
- [ ] FAB button has blue-purple gradient
- [ ] Delete button is red
- [ ] Hover states work correctly

**Animations**:
- [ ] Album cards scale on hover
- [ ] Dialogs fade in/out smoothly
- [ ] Buttons have subtle animations
- [ ] Grid adjusts smoothly on zoom change

---

## 🐛 Common Issues & Fixes

### Issue: Albums Page Shows 404
**Fix**: Ensure Albums route is added to router
```bash
cd ui/src/router
grep "albums" MainRouter.tsx
# Should show: <Route path='/albums' element={<Albums />} />
```

### Issue: Smart Albums Empty
**Cause**: No photos match the rules yet
**Fix**: Upload some screenshots or large videos to test

### Issue: Zoom Controls Not Appearing
**Fix**: Check PhotoGrid component imports ZoomControls
```bash
cd ui/src/components/gallery
grep "ZoomControls" PhotoGrid.tsx
```

### Issue: Keyboard Shortcuts Not Working
**Cause**: Focus might be in an input field
**Fix**: Click anywhere on the page outside inputs, then try again

### Issue: Album Create Dialog Won't Open
**Fix**: Check browser console for errors
```
F12 → Console tab → Look for red errors
```

---

## ✅ Success Criteria

### Albums Feature
- [ ] Can create custom albums
- [ ] Can edit album details
- [ ] Can delete albums
- [ ] Can add photos to albums
- [ ] Can view album with photos
- [ ] Smart albums auto-populate
- [ ] Can refresh smart albums
- [ ] Albums navigation link works

### Grid Zoom Feature
- [ ] Zoom controls appear
- [ ] Zoom in button works
- [ ] Zoom out button works
- [ ] Current zoom label cycles
- [ ] + key zooms in
- [ ] - key zooms out
- [ ] Zoom persists after refresh
- [ ] Keyboard shortcuts ignore inputs

---

## 📊 Performance Targets

- **Album Creation**: < 200ms
- **Photo Grid Zoom**: Instant (no delay)
- **Smart Album Refresh**: < 1s for 1000 photos
- **Album Page Load**: < 500ms

---

## 📸 Screenshots to Capture

If everything works, capture screenshots of:

1. Albums page with smart and custom albums
2. Album detail view with photos
3. Create Album dialog
4. Grid Zoom controls at each level
5. Smart album with ⚡ badge

---

## 🆘 Reporting Issues

### Template

```markdown
**Feature**: Albums / Grid Zoom
**Issue**: [Describe what went wrong]
**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Expected vs Actual]

**Browser**: Chrome/Safari/Firefox [version]
**Console Errors**: [Copy/paste from F12 Console]
**Screenshots**: [Attach if helpful]
```

---

## ✨ Bonus Tests (Optional)

### Edge Cases
- [ ] Create album with very long name (100 chars)
- [ ] Create album with very long description (500 chars)
- [ ] Add 100+ photos to one album
- [ ] Create 20+ custom albums
- [ ] Test zoom with only 1 photo in grid
- [ ] Test zoom with 1000+ photos

### Cross-Browser
- [ ] Test in Chrome
- [ ] Test in Safari
- [ ] Test in Firefox
- [ ] Test on mobile (iOS/Android)

### Accessibility
- [ ] Tab through all buttons (keyboard navigation)
- [ ] Use screen reader (VoiceOver on Mac)
- [ ] Test with high contrast mode
- [ ] Test with 200% zoom

---

## 🎉 Completion

When all tests pass:
1. Mark features as ✅ Complete in ROADMAP.md
2. Deploy to staging environment
3. Schedule user acceptance testing
4. Plan next feature (Rotate/Flip)

---

**Happy Testing! 🚀**

*Estimated Total Time*: 20-30 minutes
*Difficulty*: Easy (just click and observe)
*Required*: Browser + Running app

---

*Testing Guide Generated on 2025-12-17*
*Living Museum v1.0 - Albums + Grid Zoom*
