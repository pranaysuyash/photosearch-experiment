/**
 * Advanced Features Components Index
 *
 * Exports all advanced features components for easy integration
 */

export { FaceRecognitionPanel } from './FaceRecognitionPanel';
export { DuplicateManagementPanel } from './DuplicateManagementPanel';
export { OCRTextSearchPanel } from './OCRTextSearchPanel';
export { SmartAlbumsBuilder } from './SmartAlbumsBuilder';
export { AnalyticsDashboard } from './AnalyticsDashboard';

// Re-export types for external use
export type {
  FaceCluster,
  FaceDetection
} from './FaceRecognitionPanel';

export type {
  DuplicateGroup,
  ResolutionSuggestion
} from './DuplicateManagementPanel';

export type {
  TextRegion,
  OCRResult
} from './OCRTextSearchPanel';

export type {
  AlbumRule,
  AlbumTemplate,
  SmartAlbum
} from './SmartAlbumsBuilder';

export type {
  LibraryAnalytics,
  ContentInsight,
  SearchAnalytics,
  PerformanceMetric
} from './AnalyticsDashboard';