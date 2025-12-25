# Face Features Testing Checklist
**Date**: December 25, 2025  
**Purpose**: Validate implementation before deployment  

---

## 🧪 Manual Testing Checklist

### Phase 1: Critical Features
- [ ] **Undo Button**: Click undo after rename operation, verify operation reversal
- [ ] **Quality Badges**: Verify coherence badges appear on cluster cards
- [ ] **Hide/Unhide**: Hide a person, toggle "Show Hidden", verify person appears in hidden list
- [ ] **Unhide Person**: Unhide a person from hidden list, verify it returns to main view

### Phase 2: Advanced Clustering
- [ ] **Split Cluster**: Open split modal, select faces, create new person, verify split
- [ ] **Move Face**: Right-click face (when implemented), move to different person
- [ ] **Similar Search**: Click "Find Similar" (when implemented), verify results

### Phase 3: Search Features
- [ ] **Boolean Search**: Click "Advanced Search", create "Alice AND Bob" query, verify results
- [ ] **Query Builder**: Test include/exclude combinations, verify query description
- [ ] **Search Results**: Verify photo grid shows correct matches

### Phase 4: Integration
- [ ] **Data Refresh**: Verify all operations refresh cluster counts and stats
- [ ] **Error Handling**: Test with invalid inputs, verify error messages
- [ ] **Loading States**: Verify spinners appear during async operations

---

## 🔧 Technical Validation

### API Endpoints
```bash
# Test undo endpoint
curl -X POST http://localhost:8000/api/faces/undo

# Test coherence endpoint
curl http://localhost:8000/api/faces/clusters/{cluster_id}/coherence

# Test hide endpoint
curl -X POST http://localhost:8000/api/faces/clusters/{cluster_id}/hide

# Test split endpoint
curl -X POST http://localhost:8000/api/faces/split \
  -H "Content-Type: application/json" \
  -d '{"original_cluster_id":"1","face_ids":["face1"],"new_person_name":"Test"}'

# Test boolean search endpoint
curl -X POST http://localhost:8000/api/photos/by-people \
  -H "Content-Type: application/json" \
  -d '{"include_people":["1","2"],"operator":"and"}'
```

### Component Loading
- [ ] **SplitClusterModal**: Loads without errors
- [ ] **MoveFaceModal**: Loads without errors  
- [ ] **BooleanPeopleSearch**: Loads without errors
- [ ] **SimilarFaceSearch**: Loads without errors

### Living Language Compliance
- [ ] **No "AI detected"**: Search for AI terminology in user-facing strings
- [ ] **"We" language**: Verify natural language throughout
- [ ] **Professional tone**: Consistent with product positioning

---

## 🎯 Performance Testing

### Response Times
- [ ] **Cluster Loading**: <2 seconds for 100 clusters
- [ ] **Face Grid**: <1 second for 50 faces
- [ ] **Search Results**: <3 seconds for boolean queries
- [ ] **Modal Opening**: <200ms for all modals

### Memory Usage
- [ ] **No Memory Leaks**: Monitor during extended use
- [ ] **Image Loading**: Efficient thumbnail loading
- [ ] **Component Cleanup**: Proper unmounting

---

## 🐛 Edge Case Testing

### Data Edge Cases
- [ ] **Empty Clusters**: Handle clusters with no faces
- [ ] **Single Face**: Split button hidden for single-face clusters
- [ ] **No People**: Boolean search with empty people list
- [ ] **Network Errors**: Graceful handling of API failures

### UI Edge Cases
- [ ] **Long Names**: Person names that overflow containers
- [ ] **Many Faces**: Clusters with 100+ faces
- [ ] **Mobile View**: All features work on small screens
- [ ] **Keyboard Navigation**: Tab through all interactive elements

---

## ✅ Acceptance Criteria

### Functionality
- [ ] All 7 major features work as designed
- [ ] No JavaScript errors in console
- [ ] All API calls succeed with valid data
- [ ] Error states display helpful messages

### User Experience
- [ ] Intuitive workflows with clear feedback
- [ ] Professional visual design
- [ ] Responsive on all screen sizes
- [ ] Accessible with screen readers

### Performance
- [ ] Fast loading and smooth interactions
- [ ] No blocking operations
- [ ] Efficient memory usage
- [ ] Graceful degradation

### Business Requirements
- [ ] Privacy-first messaging throughout
- [ ] Professional-grade quality
- [ ] Competitive differentiation clear
- [ ] API access functional

---

## 🚀 Deployment Readiness

### Pre-Deployment
- [ ] All tests pass
- [ ] No critical bugs identified
- [ ] Performance acceptable
- [ ] Documentation updated

### Post-Deployment Monitoring
- [ ] User adoption metrics
- [ ] Error rate monitoring
- [ ] Performance metrics
- [ ] User feedback collection

---

**Testing Status**: Ready for validation  
**Estimated Testing Time**: 2-3 hours  
**Critical Path**: API endpoint validation, core workflow testing  
**Success Criteria**: 95% of checklist items pass