# Design Document

## Overview

The Context-Aware Photo Actions feature transforms the photo management application into a true workflow hub by providing intelligent, context-sensitive action menus for photos. The system adapts available actions based on file location (local vs cloud), detects installed professional editing tools, and positions the application as the central interface for photo workflow management.

This feature replaces the current simple "Copy path", "Open", "Download" actions with a sophisticated, adaptive system that understands user context and provides the most relevant actions for their workflow.

## Architecture

### High-Level Architecture

The system follows a layered architecture with clear separation between detection, context analysis, and action execution:

```
┌─────────────────────────────────────────────────────────────┐
│                    UI Layer                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Context Menu   │  │  Action Buttons │  │  Shortcuts  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Action Management Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Action Registry │  │ Context Analyzer│  │ Action Queue│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Detection Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ App Detector    │  │ File Analyzer   │  │ System APIs │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                 Execution Layer                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Local Executor  │  │ Cloud Executor  │  │ App Launcher│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Integration Points

The feature integrates with existing application components:

- **PhotoDetail Component**: Enhanced with new action buttons and context menu
- **PhotoGrid Component**: Right-click context menu support
- **API Layer**: New endpoints for application detection and action execution
- **File System**: Direct integration for local file operations
- **Cloud Services**: Future integration points for cloud file operations

## Components and Interfaces

### Core Components

#### 1. ActionRegistry
Central registry for all available photo actions with context-aware filtering.

```typescript
interface ActionRegistry {
  registerAction(action: PhotoAction): void;
  getActionsForContext(context: PhotoContext): PhotoAction[];
  executeAction(actionId: string, photo: Photo, options?: ActionOptions): Promise<ActionResult>;
}

interface PhotoAction {
  id: string;
  label: string;
  icon: string;
  category: ActionCategory;
  contextRequirements: ContextRequirement[];
  priority: number;
  execute: (photo: Photo, options?: ActionOptions) => Promise<ActionResult>;
}

enum ActionCategory {
  FILE_SYSTEM = 'file_system',
  EDITING = 'editing',
  SHARING = 'sharing',
  EXPORT = 'export',
  NAVIGATION = 'navigation'
}
```

#### 2. ContextAnalyzer
Analyzes photo context to determine appropriate actions.

```typescript
interface ContextAnalyzer {
  analyzePhoto(photo: Photo): PhotoContext;
  isLocalFile(path: string): boolean;
  isCloudFile(path: string): boolean;
  getFileCapabilities(path: string): FileCapabilities;
}

interface PhotoContext {
  fileLocation: 'local' | 'cloud' | 'hybrid';
  fileType: 'image' | 'video' | 'raw' | 'document';
  capabilities: FileCapabilities;
  availableApps: InstalledApp[];
  systemInfo: SystemInfo;
}

interface FileCapabilities {
  canEdit: boolean;
  canExport: boolean;
  canShare: boolean;
  canOpenLocation: boolean;
  supportedFormats: string[];
}
```

#### 3. AppDetector
Detects and manages installed professional editing applications.

```typescript
interface AppDetector {
  scanForApps(): Promise<InstalledApp[]>;
  getAppForFileType(fileType: string): InstalledApp[];
  launchApp(appId: string, filePath: string): Promise<LaunchResult>;
  refreshAppCache(): Promise<void>;
}

interface InstalledApp {
  id: string;
  name: string;
  displayName: string;
  executablePath: string;
  supportedFormats: string[];
  icon?: string;
  version?: string;
  category: AppCategory;
}

enum AppCategory {
  PHOTO_EDITOR = 'photo_editor',
  RAW_PROCESSOR = 'raw_processor',
  VIDEO_EDITOR = 'video_editor',
  VIEWER = 'viewer',
  ORGANIZER = 'organizer'
}
```

#### 4. ActionExecutor
Handles execution of different action types with proper error handling.

```typescript
interface ActionExecutor {
  executeFileSystemAction(action: FileSystemAction, photo: Photo): Promise<ActionResult>;
  executeAppLaunch(app: InstalledApp, photo: Photo): Promise<ActionResult>;
  executeCloudAction(action: CloudAction, photo: Photo): Promise<ActionResult>;
  executeExportAction(action: ExportAction, photo: Photo): Promise<ActionResult>;
}

interface ActionResult {
  success: boolean;
  message?: string;
  error?: string;
  data?: any;
}
```

### UI Components

#### 1. ContextMenu
Right-click context menu with adaptive actions.

```typescript
interface ContextMenuProps {
  photo: Photo;
  position: { x: number; y: number };
  onClose: () => void;
  onActionExecute: (actionId: string) => void;
}
```

#### 2. ActionButton
Individual action button with loading states and feedback.

```typescript
interface ActionButtonProps {
  action: PhotoAction;
  photo: Photo;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  onExecute?: (result: ActionResult) => void;
}
```

#### 3. OpenWithSubmenu
Submenu for "Open With" actions showing detected applications.

```typescript
interface OpenWithSubmenuProps {
  photo: Photo;
  availableApps: InstalledApp[];
  onAppSelect: (app: InstalledApp) => void;
}
```

## Data Models

### Photo Action Model
```typescript
interface PhotoActionModel {
  id: string;
  type: ActionType;
  label: string;
  description?: string;
  icon: string;
  shortcut?: string;
  category: ActionCategory;
  contextRequirements: ContextRequirement[];
  priority: number;
  isEnabled: (context: PhotoContext) => boolean;
  execute: (photo: Photo, options?: ActionOptions) => Promise<ActionResult>;
}

enum ActionType {
  COPY_PATH = 'copy_path',
  OPEN_LOCATION = 'open_location',
  OPEN_WITH = 'open_with',
  DOWNLOAD = 'download',
  EXPORT = 'export',
  SHARE = 'share',
  OPEN_NEW_TAB = 'open_new_tab'
}
```

### Application Detection Model
```typescript
interface AppDetectionModel {
  detectionRules: DetectionRule[];
  knownApps: KnownAppDefinition[];
  userCustomApps: CustomAppDefinition[];
  lastScanTime: Date;
  cacheExpiry: number;
}

interface DetectionRule {
  platform: 'windows' | 'macos' | 'linux';
  searchPaths: string[];
  executablePatterns: string[];
  registryKeys?: string[]; // Windows only
  bundleIdentifiers?: string[]; // macOS only
}

interface KnownAppDefinition {
  id: string;
  name: string;
  displayName: string;
  category: AppCategory;
  supportedFormats: string[];
  detectionRules: DetectionRule[];
  launchArgs?: string[];
  icon?: string;
}
```

### Context Analysis Model
```typescript
interface ContextAnalysisModel {
  fileAnalysis: FileAnalysis;
  systemCapabilities: SystemCapabilities;
  userPreferences: UserPreferences;
  environmentContext: EnvironmentContext;
}

interface FileAnalysis {
  path: string;
  type: FileType;
  size: number;
  format: string;
  isLocal: boolean;
  isReadable: boolean;
  isWritable: boolean;
  parentDirectory: string;
}

interface SystemCapabilities {
  platform: string;
  hasClipboard: boolean;
  canOpenFileManager: boolean;
  canLaunchApps: boolean;
  supportedProtocols: string[];
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis and property reflection to eliminate redundancy, the following consolidated properties ensure system correctness:

**Property 1: Context-aware menu behavior**
*For any* photo and system context, the context menu should display only appropriate actions for the file location, prioritized by workflow frequency, with proper visual indicators distinguishing action types
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

**Property 2: Professional tool integration**
*For any* system with installed applications, the detection process should accurately identify professional tools, cache their metadata, and successfully launch them with compatible files
**Validates: Requirements 2.1, 2.2, 2.3, 6.1, 6.2, 6.3**

**Property 3: File system operations consistency**
*For any* local file, both copy path and open file location operations should complete successfully, with copy path placing the correct absolute path in the clipboard and open location launching the file manager with the file selected
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

**Property 4: Cloud operations reliability**
*For any* cloud file, both download and copy link operations should function correctly, with downloads providing progress indication and link copying generating valid shareable URLs
**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

**Property 5: In-app navigation preservation**
*For any* photo opened in a new tab, the original search context and navigation state should remain unchanged while the new tab displays the photo with full metadata and action options
**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

**Property 6: Application cache synchronization**
*For any* change in system applications (installation/removal), the cached application list should accurately reflect the current system state either automatically or on user request
**Validates: Requirements 6.4**

**Property 7: Export operation completeness**
*For any* export request with valid parameters, the operation should complete successfully with the specified format and quality settings, handle metadata according to preferences, provide progress indication for batch operations, and offer location access upon completion
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

**Property 8: Error handling consistency**
*For any* failed operation (application launch, file system access, cloud operations, or detection), the system should display appropriate error messages and provide alternative actions or recovery options
**Validates: Requirements 2.5, 3.5, 4.5, 6.5**

## Error Handling

### Error Categories

1. **Detection Errors**
   - Application not found
   - Permission denied during scan
   - Invalid application metadata

2. **Execution Errors**
   - Application launch failure
   - File system permission errors
   - Network connectivity issues (cloud operations)

3. **Context Errors**
   - File not accessible
   - Unsupported file format
   - Invalid file path

4. **System Errors**
   - Clipboard access denied
   - File manager unavailable
   - Insufficient system resources

### Error Handling Strategy

```typescript
interface ErrorHandler {
  handleDetectionError(error: DetectionError): ErrorRecovery;
  handleExecutionError(error: ExecutionError): ErrorRecovery;
  handleContextError(error: ContextError): ErrorRecovery;
  handleSystemError(error: SystemError): ErrorRecovery;
}

interface ErrorRecovery {
  canRecover: boolean;
  recoveryActions: RecoveryAction[];
  fallbackActions: PhotoAction[];
  userMessage: string;
}
```

### Graceful Degradation

- If professional tools are not detected, hide "Open With" options
- If clipboard access fails, show manual copy instructions
- If file manager cannot be opened, provide file path for manual navigation
- If cloud operations fail, offer offline alternatives

## Testing Strategy

### Unit Testing Approach

Unit tests will focus on individual component behavior and integration points:

- **ActionRegistry**: Test action registration, filtering, and execution
- **ContextAnalyzer**: Test file type detection and context analysis
- **AppDetector**: Test application scanning and detection logic
- **ActionExecutor**: Test individual action execution with mocked dependencies

### Property-Based Testing Approach

Property-based tests will verify universal behaviors across all valid inputs using **fast-check** for TypeScript:

- **Context Filtering Property**: Generate random photo contexts and verify only appropriate actions are shown
- **Application Detection Property**: Generate various system states and verify detection accuracy
- **Launch Success Property**: Generate valid app/file combinations and verify successful launches
- **File Operation Property**: Generate local file paths and verify file system operations
- **Export Consistency Property**: Generate export parameters and verify output correctness

Each property-based test will run a minimum of 100 iterations to ensure comprehensive coverage of the input space.

### Integration Testing

- Test complete workflows from context menu to action execution
- Test cross-platform compatibility for application detection
- Test error handling and recovery scenarios
- Test performance with large numbers of detected applications

### Testing Configuration

The testing strategy uses **fast-check** as the property-based testing library, configured for:
- Minimum 100 iterations per property test
- Custom generators for photo contexts, file paths, and application definitions
- Shrinking support for minimal failing examples
- Integration with existing Jest test suite
