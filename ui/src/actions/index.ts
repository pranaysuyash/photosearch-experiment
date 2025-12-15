// Main exports for the context-aware photo actions system

// Core services
export { ActionRegistry, actionRegistry } from '../services/ActionRegistry';
export { ContextAnalyzer, contextAnalyzer } from '../services/ContextAnalyzer';
export { ActionService, actionService } from '../services/ActionService';

// Types
export type {
  PhotoAction,
  PhotoContext,
  ActionResult,
  ActionOptions,
  FileCapabilities,
  InstalledApp,
  SystemInfo,
  ContextRequirement,
  Photo
} from '../types/actions';

export {
  ActionCategory,
  ActionType,
  AppCategory
} from '../types/actions';

// Default actions
export { defaultActions } from './defaultActions';

// Individual actions for custom registration
export {
  copyPathAction,
  openLocationAction,
  openInNewTabAction,
  downloadAction,
  exportAction,
  openWithAction,
  downloadOriginalAction,
  copyLinkAction
} from './defaultActions';