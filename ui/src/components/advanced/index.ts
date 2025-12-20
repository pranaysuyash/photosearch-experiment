/**
 * Advanced Features Components Index
 *
 * Exports all advanced features components for easy integration
 */

export { default as FaceRecognitionPanel } from './FaceRecognitionPanel';
export { default as DuplicateManagementPanel } from './DuplicateManagementPanel';
export { default as OCRTextSearchPanel } from './OCRTextSearchPanel';
export { default as SmartAlbumsBuilder } from './SmartAlbumsBuilder';
export { default as AnalyticsDashboard } from './AnalyticsDashboard';

// Re-export types for external use
export type { FaceCluster, FaceDetection } from './FaceRecognitionPanel';

export type {
  DuplicateGroup,
  ResolutionSuggestion,
} from './DuplicateManagementPanel';

export type { TextRegion, OCRResult } from './OCRTextSearchPanel';

export type {
  AlbumRule,
  AlbumTemplate,
  SmartAlbum,
} from './SmartAlbumsBuilder';

export type {
  LibraryAnalytics,
  ContentInsight,
  SearchAnalytics,
  PerformanceMetric,
} from './AnalyticsDashboard';
