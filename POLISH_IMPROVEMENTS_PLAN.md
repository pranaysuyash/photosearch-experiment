# Polish & Improvements Plan

## 1. Export Dialog Improvements
- [ ] Add error state UI (currently just logs to console)
- [ ] Show user-facing error messages in the dialog
- [ ] Add success notification/toast
- [ ] Improve password input UX (toggle logic is inconsistent)
- [ ] Add validation for blur strength limits
- [ ] Show estimated file size before export

## 2. Events Component Enhancements
- [ ] Add sorting options (by date, people count, confidence)
- [ ] Add person name/label instead of just ID
- [ ] Improve empty state with helpful text
- [ ] Add loading skeleton for better UX
- [ ] Add ability to open people profiles from events

## 3. Video Highlights Improvements
- [ ] Add download/play video segment functionality
- [ ] Improve highlight type labels and descriptions
- [ ] Add more context about how highlights are generated
- [ ] Add sharing options for individual highlights
- [ ] Better error handling for missing video files

## 4. Hide/Unhide Button Improvements
- [ ] Add confirmation dialog before hiding person
- [ ] Show hidden count in UI
- [ ] Add filter to show/hide hidden people
- [ ] Add undo functionality for recent hides
- [ ] Add reason/note when hiding a person

## 5. General Improvements
- [ ] Add loading skeletons to all data-loading components
- [ ] Improve accessibility (ARIA labels, keyboard navigation)
- [ ] Add tooltips to explain features
- [ ] Consistent error message formatting
- [ ] Better progress indication for long operations

## 6. Performance Improvements
- [ ] Lazy load components in tabs
- [ ] Debounce filter/search inputs
- [ ] Cache Events and Highlights data
- [ ] Optimize image loading in Events photo grid

## 7. Documentation
- [ ] Add inline component documentation
- [ ] User-facing help text for each feature
- [ ] API documentation for new endpoints
- [ ] Troubleshooting guide for common issues
