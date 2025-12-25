import type { PhotoContext, FileCapabilities, SystemInfo, InstalledApp } from '../types/actions';
import type { Photo } from '../api';

/**
 * Analyzes photo context to determine appropriate actions.
 * Detects file location, type, capabilities, and system information.
 */
export class ContextAnalyzer {
  private systemInfo: SystemInfo;
  private installedApps: InstalledApp[] = [];

  constructor() {
    this.systemInfo = this.detectSystemInfo();
  }

  /**
   * Analyze a photo to determine its context
   */
  analyzePhoto(photo: Photo): PhotoContext {
    const fileLocation = this.determineFileLocation(photo.path);
    const fileType = this.determineFileType(photo);
    const capabilities = this.getFileCapabilities(photo.path, fileType);
    
    return {
      fileLocation,
      fileType,
      capabilities,
      availableApps: this.getCompatibleApps(fileType),
      systemInfo: this.systemInfo
    };
  }

  /**
   * Check if a file is local or cloud-based
   */
  isLocalFile(path: string): boolean {
    // Local file patterns
    const localPatterns = [
      /^[A-Za-z]:\\/, // Windows drive letters
      new RegExp('^/[^/]'), // Unix absolute paths
      /^~\//, // Home directory
      /^\.\//, // Relative paths
      new RegExp('^file://'), // File protocol
    ];

    return localPatterns.some(pattern => pattern.test(path));
  }

  /**
   * Check if a file is cloud-based
   */
  isCloudFile(path: string): boolean {
    // Cloud service patterns
    const cloudPatterns = [
      new RegExp('^https?://.*\\.googleapis\\.com'), // Google Drive/Photos
      new RegExp('^https?://.*\\.dropbox\\.com'), // Dropbox
      new RegExp('^https?://.*\\.onedrive\\.com'), // OneDrive
      new RegExp('^https?://.*\\.icloud\\.com'), // iCloud
      new RegExp('^https?://.*\\.amazonaws\\.com'), // AWS S3
      /^cloud:/, // Generic cloud prefix
      /^gdrive:/, // Google Drive
      /^dropbox:/, // Dropbox
      /^onedrive:/, // OneDrive
    ];

    return cloudPatterns.some(pattern => pattern.test(path));
  }

  /**
   * Get file capabilities based on path and type
   */
  getFileCapabilities(path: string, fileType: string): FileCapabilities {
    const isLocal = this.isLocalFile(path);
    const isCloud = this.isCloudFile(path);

    return {
      canEdit: isLocal && (fileType === 'image' || fileType === 'raw'),
      canExport: true, // Always allow export
      canShare: isCloud || isLocal,
      canOpenLocation: isLocal && this.systemInfo.canOpenFileManager,
      supportedFormats: this.getSupportedFormats(fileType)
    };
  }

  /**
   * Set the list of installed applications
   */
  setInstalledApps(apps: InstalledApp[]): void {
    this.installedApps = apps;
  }

  /**
   * Get applications compatible with the given file type
   */
  getCompatibleApps(fileType: string): InstalledApp[] {
    const fileExtensions = this.getFileExtensionsForType(fileType);
    
    return this.installedApps.filter(app => 
      app.supportedFormats.some(format => 
        fileExtensions.includes(format.toLowerCase())
      )
    );
  }

  /**
   * Determine file location (local, cloud, or hybrid)
   */
  private determineFileLocation(path: string): 'local' | 'cloud' | 'hybrid' {
    if (this.isLocalFile(path)) {
      return 'local';
    } else if (this.isCloudFile(path)) {
      return 'cloud';
    } else {
      // Could be a hybrid case or unknown
      return 'hybrid';
    }
  }

  /**
   * Determine file type from photo metadata and filename
   */
  private determineFileType(photo: Photo): 'image' | 'video' | 'raw' | 'document' {
    const filename = photo.filename.toLowerCase();
    const metadata = photo.metadata;

    // Check for video files
    const videoExtensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv'];
    if (videoExtensions.some(ext => filename.endsWith(ext))) {
      return 'video';
    }

    // Check for RAW files
    const rawExtensions = ['.raw', '.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.srw'];
    if (rawExtensions.some(ext => filename.endsWith(ext))) {
      return 'raw';
    }

    // Check for document files
    const documentExtensions = ['.pdf', '.svg', '.txt', '.doc', '.docx'];
    if (documentExtensions.some(ext => filename.endsWith(ext))) {
      return 'document';
    }

    // Check metadata for more specific type detection
    if (metadata?.video) {
      return 'video';
    }

    if (metadata?.pdf || metadata?.svg) {
      return 'document';
    }

    // Default to image
    return 'image';
  }

  /**
   * Detect system information
   */
  private detectSystemInfo(): SystemInfo {
    const userAgent = navigator.userAgent.toLowerCase();
    let platform: 'windows' | 'macos' | 'linux' = 'linux';

    if (userAgent.includes('win')) {
      platform = 'windows';
    } else if (userAgent.includes('mac')) {
      platform = 'macos';
    }

    return {
      platform,
      hasClipboard: 'clipboard' in navigator,
      canOpenFileManager: true, // Assume true, will be validated at runtime
      canLaunchApps: true, // Assume true, will be validated at runtime
      supportedProtocols: ['http', 'https', 'file']
    };
  }

  /**
   * Get supported formats for a file type
   */
  private getSupportedFormats(fileType: string): string[] {
    switch (fileType) {
      case 'image':
        return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg'];
      case 'video':
        return ['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'wmv', 'flv'];
      case 'raw':
        return ['raw', 'cr2', 'cr3', 'nef', 'arw', 'dng', 'orf', 'rw2', 'pef', 'srw'];
      case 'document':
        return ['pdf', 'svg', 'txt', 'doc', 'docx'];
      default:
        return [];
    }
  }

  /**
   * Get file extensions for a given file type
   */
  private getFileExtensionsForType(fileType: string): string[] {
    return this.getSupportedFormats(fileType);
  }
}

// Global instance
export const contextAnalyzer = new ContextAnalyzer();