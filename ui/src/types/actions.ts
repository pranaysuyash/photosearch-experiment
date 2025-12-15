// Core types for the context-aware photo actions system

export interface PhotoContext {
  fileLocation: 'local' | 'cloud' | 'hybrid';
  fileType: 'image' | 'video' | 'raw' | 'document';
  capabilities: FileCapabilities;
  availableApps: InstalledApp[];
  systemInfo: SystemInfo;
}

export interface FileCapabilities {
  canEdit: boolean;
  canExport: boolean;
  canShare: boolean;
  canOpenLocation: boolean;
  supportedFormats: string[];
}

export interface InstalledApp {
  id: string;
  name: string;
  displayName: string;
  executablePath: string;
  supportedFormats: string[];
  icon?: string;
  version?: string;
  category: AppCategory;
}

export const AppCategory = {
  PHOTO_EDITOR: 'photo_editor',
  RAW_PROCESSOR: 'raw_processor',
  VIDEO_EDITOR: 'video_editor',
  VIEWER: 'viewer',
  ORGANIZER: 'organizer'
} as const;

export type AppCategory = typeof AppCategory[keyof typeof AppCategory];

export interface SystemInfo {
  platform: 'windows' | 'macos' | 'linux';
  hasClipboard: boolean;
  canOpenFileManager: boolean;
  canLaunchApps: boolean;
  supportedProtocols: string[];
}

export const ActionCategory = {
  FILE_SYSTEM: 'file_system',
  EDITING: 'editing',
  SHARING: 'sharing',
  EXPORT: 'export',
  NAVIGATION: 'navigation'
} as const;

export type ActionCategory = typeof ActionCategory[keyof typeof ActionCategory];

export const ActionType = {
  COPY_PATH: 'copy_path',
  OPEN_LOCATION: 'open_location',
  OPEN_WITH: 'open_with',
  DOWNLOAD: 'download',
  EXPORT: 'export',
  SHARE: 'share',
  OPEN_NEW_TAB: 'open_new_tab'
} as const;

export type ActionType = typeof ActionType[keyof typeof ActionType];

export interface ContextRequirement {
  type: 'fileLocation' | 'fileType' | 'capability' | 'app';
  value: string | string[];
  operator?: 'equals' | 'includes' | 'excludes';
}

export interface ActionOptions {
  [key: string]: unknown;
}

export interface ActionResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: unknown;
}

export interface PhotoAction {
  id: string;
  label: string;
  icon: string;
  category: ActionCategory;
  type: ActionType;
  contextRequirements: ContextRequirement[];
  priority: number;
  shortcut?: string;
  description?: string;
  isEnabled: (context: PhotoContext) => boolean;
  execute: (photo: Photo, options?: ActionOptions) => Promise<ActionResult>;
}

// Import Photo type from api
import type { Photo } from '../api';

// Re-export Photo type for convenience
export type { Photo };