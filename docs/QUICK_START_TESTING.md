# Quick Start: Testing Guide

**Last Updated**: 2025-12-17

## 🎯 What Was Built Today

4 new features are ready to test:
1. ✅ **Sort** - Date/Name/Size
2. ✅ **Filter** - Photos/Videos/All
3. ✅ **Favorites** - Star toggle + filter
4. ✅ **Delete** - Trash with 5-second undo

---

## 🚀 How to Test

### Start the App
```bash
# Terminal 1: Backend
cd /Users/pranay/Projects/photosearch_experiment/server
python main.py

# Terminal 2: Frontend
cd /Users/pranay/Projects/photosearch_experiment/ui
npm run dev

# Open: http://localhost:5173
```

---

## 🧪 Test Scenarios

### Test 1: Sort Photos (30 seconds)
1. Open the app
2. Look for dropdown in search bar (says "Newest First")
3. Click and try each option:
   - Newest First
   - Oldest First
   - Filename A-Z
   - Largest Files
4. ✅ **Success**: Photos reorder each time

### Test 2: Filter Media Types (30 seconds)
1. Find media type buttons (All/Photos/Videos)
2. Click "Photos" → only images show
3. Click "Videos" → only videos show
4. Click "All" → everything shows
5. ✅ **Success**: Grid updates correctly

### Test 3: Favorite a Photo (1 minute)
1. Click any photo thumbnail
2. Look top-right → see ⭐ star button
3. Click star → turns yellow and fills
4. Click star again → unfills
5. Close photo detail
6. In search bar, click "Favorites" filter
7. ✅ **Success**: Only favorited photo(s) show

### Test 4: Delete with Undo (2 minutes)
1. Open any photo detail
2. Click 🗑️ trash icon (top-right, red)
3. Confirm deletion dialog → click "Delete"
4. Photo disappears from grid
5. Toast appears at bottom with countdown
6. Click "Undo" before 5 seconds
7. ✅ **Success**: Photo restored to grid

### Test 5: Permanent Delete (1 minute)
1. Delete another photo
2. Wait 5 seconds (watch progress bar)
3. Toast disappears
4. Refresh page
5. ✅ **Success**: Photo still gone (permanent)

---

## 🐛 What to Look For

### Expected Behavior
- ✅ Instant UI updates (no lag)
- ✅ Smooth animations
- ✅ Clear visual feedback
- ✅ No errors in browser console

### Potential Issues
- ❌ Photos don't reorder after sort
- ❌ Star doesn't change color
- ❌ Delete confirmation doesn't appear
- ❌ Undo doesn't work
- ❌ Grid doesn't refresh after undo
- ❌ Browser console shows errors

---

## 📸 What to Screenshot

If everything works, capture:
1. Sort dropdown open
2. Media type filter active
3. Photo detail with yellow star
4. Delete confirmation dialog
5. Undo toast with countdown

---

## 🆘 If Something Breaks

### Check Browser Console
```
F12 → Console tab
```
Look for red errors, copy and share.

### Check Terminal Output
Look at both backend and frontend terminals for errors.

### Common Fixes
```bash
# Frontend not loading?
cd ui
rm -rf node_modules
npm install
npm run dev

# Backend errors?
cd server
pip install -r requirements.txt
python main.py
```

---

## ✅ Quick Verification Checklist

```
[ ] App loads without errors
[ ] Can see photos in grid
[ ] Sort dropdown works
[ ] Media type filter works
[ ] Can open photo detail
[ ] Star button works
[ ] Star turns yellow when clicked
[ ] Favorites filter works
[ ] Delete button appears
[ ] Confirmation dialog shows
[ ] Photo disappears after delete
[ ] Undo toast appears
[ ] Undo button restores photo
[ ] Permanent delete after 5 seconds
```

---

## 📊 Performance Targets

- Sort/Filter: < 200ms response
- Favorite toggle: Instant (optimistic)
- Delete: Instant grid removal
- Undo: Immediate restore
- No UI freezing or lag

---

## 🎉 Success Criteria

**Ready to ship when**:
- All 14 checkboxes above are ✅
- No console errors
- Smooth and responsive
- Looks good on desktop and mobile
- Undo works reliably

---

## 📝 Report Template

```markdown
## Test Results: [Your Name]
**Date**: 2025-12-17
**Browser**: Chrome/Safari/Firefox [version]

### Features Tested
- [ ] Sort: ✅ Works / ❌ Issue: [describe]
- [ ] Filter: ✅ Works / ❌ Issue: [describe]
- [ ] Favorites: ✅ Works / ❌ Issue: [describe]
- [ ] Delete: ✅ Works / ❌ Issue: [describe]

### Issues Found
1. [Issue description]
2. [Issue description]

### Screenshots
[Attach if needed]

### Console Errors
[Copy/paste any errors]

### Overall Assessment
**Ready for Production**: Yes / No / With fixes
```

---

## 🚀 Next Steps After Testing

If all tests pass:
1. Mark features as ✅ Complete
2. Deploy to staging
3. User acceptance testing
4. Plan Albums implementation (next feature)

If issues found:
1. Document specific problems
2. Check browser console for errors
3. Review implementation code
4. Fix and retest

---

**Estimated Testing Time**: 15-30 minutes
**Difficulty**: Easy (just click and observe)
**Required**: One person + browser

---

*Happy Testing! 🎉*
