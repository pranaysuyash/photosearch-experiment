import type {
  PhotoAction,
  ActionResult,
  Photo,
  ActionOptions,
} from '../types/actions';
import { ActionCategory, ActionType } from '../types/actions';
import { api } from '../api';

/**
 * Default photo actions that are registered with the ActionRegistry
 */

export const copyPathAction: PhotoAction = {
  id: 'copy_path',
  label: 'Copy Path',
  icon: 'Copy',
  category: ActionCategory.FILE_SYSTEM,
  type: ActionType.COPY_PATH,
  contextRequirements: [{ type: 'fileLocation', value: 'local' }],
  priority: 80,
  shortcut: 'Ctrl+C',
  description: 'Copy the full file path to clipboard',

  isEnabled: (context) => {
    return context.fileLocation === 'local' && context.systemInfo.hasClipboard;
  },

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard API not available');
      }

      await navigator.clipboard.writeText(photo.path);

      return {
        success: true,
        message: 'File path copied to clipboard',
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to copy path',
      };
    }
  },
};

export const openLocationAction: PhotoAction = {
  id: 'open_location',
  label: 'Open File Location',
  icon: 'FolderOpen',
  category: ActionCategory.FILE_SYSTEM,
  type: ActionType.OPEN_LOCATION,
  contextRequirements: [
    { type: 'fileLocation', value: 'local' },
    { type: 'capability', value: 'canOpenLocation' },
  ],
  priority: 75,
  description: 'Open the file location in system file manager',

  isEnabled: (context) => {
    return (
      context.fileLocation === 'local' &&
      context.capabilities.canOpenLocation &&
      context.systemInfo.canOpenFileManager
    );
  },

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      // For web applications, we'll need to call a backend endpoint
      // that can trigger the system file manager
      const response = await fetch('/api/actions/open-location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: photo.path }),
      });

      if (!response.ok) {
        throw new Error('Failed to open file location');
      }

      return {
        success: true,
        message: 'File location opened',
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : 'Failed to open file location',
      };
    }
  },
};

export const openInNewTabAction: PhotoAction = {
  id: 'open_new_tab',
  label: 'Open in New Tab',
  icon: 'ExternalLink',
  category: ActionCategory.NAVIGATION,
  type: ActionType.OPEN_NEW_TAB,
  contextRequirements: [],
  priority: 70,
  shortcut: 'Ctrl+T',
  description: 'Open photo in a new browser tab',

  isEnabled: () => true, // Always available

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      const url = api.isVideo(photo.path)
        ? api.getVideoUrl(photo.path)
        : api.getFileUrl(photo.path);

      window.open(url, '_blank', 'noopener,noreferrer');

      return {
        success: true,
        message: 'Photo opened in new tab',
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : 'Failed to open in new tab',
      };
    }
  },
};

export const downloadAction: PhotoAction = {
  id: 'download',
  label: 'Download Original',
  icon: 'Download',
  category: ActionCategory.FILE_SYSTEM,
  type: ActionType.DOWNLOAD,
  contextRequirements: [],
  priority: 85,
  description: 'Download the original file',

  isEnabled: () => true, // Always available

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      const downloadUrl = api.getFileUrl(photo.path, { download: true });

      // Create a temporary link to trigger download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = photo.filename;
      link.style.display = 'none';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      return {
        success: true,
        message: 'Download started',
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : 'Failed to start download',
      };
    }
  },
};

export const exportAction: PhotoAction = {
  id: 'export',
  label: 'Export',
  icon: 'Share',
  category: ActionCategory.EXPORT,
  type: ActionType.EXPORT,
  contextRequirements: [{ type: 'capability', value: 'canExport' }],
  priority: 60,
  description: 'Export photo with format and quality options',

  isEnabled: (context) => context.capabilities.canExport,

  execute: async (
    photo: Photo,
    options?: ActionOptions
  ): Promise<ActionResult> => {
    try {
      const exportOptions = {
        format: 'zip',
        include_metadata: options?.includeMetadata ?? true,
        include_thumbnails: options?.includeThumbnails ?? false,
        max_resolution: options?.maxResolution ?? null,
        password_protect: Boolean(options?.password),
        password: options?.password,
      };

      const blob = await api.exportPhotos([photo.path], exportOptions);
      const url = URL.createObjectURL(
        blob instanceof Blob ? blob : new Blob([blob])
      );
      const link = document.createElement('a');
      link.href = url;
      link.download = 'photo_export.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      return {
        success: true,
        message: 'Export prepared',
        data: exportOptions,
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : 'Failed to export photo',
      };
    }
  },
};

export const openWithAction: PhotoAction = {
  id: 'open_with',
  label: 'Open With',
  icon: 'Edit',
  category: ActionCategory.EDITING,
  type: ActionType.OPEN_WITH,
  contextRequirements: [
    { type: 'fileLocation', value: 'local' },
    { type: 'app', value: ['photo_editor', 'raw_processor', 'video_editor'] },
  ],
  priority: 90,
  description: 'Open with installed editing applications',

  isEnabled: (context) => {
    return (
      context.fileLocation === 'local' &&
      context.availableApps.length > 0 &&
      context.systemInfo.canLaunchApps
    );
  },

  execute: async (
    photo: Photo,
    options?: ActionOptions
  ): Promise<ActionResult> => {
    try {
      const appId = options?.appId;
      if (!appId) {
        return {
          success: false,
          error: 'No application specified',
        };
      }

      const response = await fetch('/api/actions/launch-app', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          appId,
          filePath: photo.path,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to launch application');
      }

      const result = await response.json();

      return {
        success: true,
        message: `Opened with ${result.appName || 'application'}`,
        data: result,
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : 'Failed to open with application',
      };
    }
  },
};

// Cloud-specific actions
export const downloadOriginalAction: PhotoAction = {
  id: 'download_original',
  label: 'Download Original',
  icon: 'CloudDownload',
  category: ActionCategory.FILE_SYSTEM,
  type: ActionType.DOWNLOAD,
  contextRequirements: [{ type: 'fileLocation', value: 'cloud' }],
  priority: 85,
  description: 'Download original file from cloud storage',

  isEnabled: (context) => context.fileLocation === 'cloud',

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      // This would handle cloud-specific download logic
      const response = await fetch('/api/actions/cloud-download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: photo.path }),
      });

      if (!response.ok) {
        throw new Error('Cloud download failed');
      }

      return {
        success: true,
        message: 'Download from cloud started',
      };
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error
            ? error.message
            : 'Failed to download from cloud',
      };
    }
  },
};

export const copyLinkAction: PhotoAction = {
  id: 'copy_link',
  label: 'Copy Link',
  icon: 'Link',
  category: ActionCategory.SHARING,
  type: ActionType.SHARE,
  contextRequirements: [{ type: 'fileLocation', value: 'cloud' }],
  priority: 70,
  description: 'Copy shareable link to clipboard',

  isEnabled: (context) => {
    return (
      context.fileLocation === 'cloud' &&
      context.capabilities.canShare &&
      context.systemInfo.hasClipboard
    );
  },

  execute: async (photo: Photo): Promise<ActionResult> => {
    try {
      const share = await api.createShareLink([photo.path]);
      const shareableUrl =
        share.share_url || share.shareUrl || share.shareableUrl;
      if (!shareableUrl) {
        throw new Error('Share link unavailable');
      }

      if (!navigator.clipboard) {
        throw new Error('Clipboard API not available');
      }

      await navigator.clipboard.writeText(shareableUrl);

      return {
        success: true,
        message: 'Shareable link copied to clipboard',
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to copy link',
      };
    }
  },
};

// Export all default actions
export const defaultActions: PhotoAction[] = [
  copyPathAction,
  openLocationAction,
  openInNewTabAction,
  downloadAction,
  exportAction,
  openWithAction,
  downloadOriginalAction,
  copyLinkAction,
];
