import { actionRegistry } from './ActionRegistry';
import { contextAnalyzer } from './ContextAnalyzer';
import { defaultActions } from '../actions/defaultActions';
import type { InstalledApp, PhotoContext, ActionResult, Photo } from '../types/actions';

/**
 * Main service for managing the photo action system.
 * Handles initialization, app detection, and provides high-level API.
 */
export class ActionService {
  private initialized = false;
  private appDetectionPromise: Promise<InstalledApp[]> | null = null;

  /**
   * Initialize the action system
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    // Register default actions
    actionRegistry.registerActions(defaultActions);

    // Start app detection in background
    this.appDetectionPromise = this.detectInstalledApps();
    
    // Wait for app detection to complete
    const apps = await this.appDetectionPromise;
    contextAnalyzer.setInstalledApps(apps);

    this.initialized = true;
  }

  /**
   * Get actions for a specific photo
   */
  async getActionsForPhoto(photo: Photo): Promise<{
    context: PhotoContext;
    actions: import('../types/actions').PhotoAction[];
    actionsByCategory: Record<string, import('../types/actions').PhotoAction[]>;
  }> {
    await this.ensureInitialized();
    
    const context = contextAnalyzer.analyzePhoto(photo);
    const actions = actionRegistry.getActionsForContext(context);
    const actionsByCategory = actionRegistry.getActionsByCategory(context);

    return {
      context,
      actions,
      actionsByCategory
    };
  }

  /**
   * Execute an action on a photo
   */
  async executeAction(
    actionId: string, 
    photo: Photo, 
    options?: import('../types/actions').ActionOptions
  ): Promise<ActionResult> {
    await this.ensureInitialized();
    
    const context = contextAnalyzer.analyzePhoto(photo);
    return actionRegistry.executeAction(actionId, photo, context, options);
  }

  /**
   * Get compatible apps for a photo
   */
  async getCompatibleApps(photo: Photo): Promise<InstalledApp[]> {
    await this.ensureInitialized();
    
    const context = contextAnalyzer.analyzePhoto(photo);
    return context.availableApps;
  }

  /**
   * Refresh the list of installed applications
   */
  async refreshApps(): Promise<InstalledApp[]> {
    this.appDetectionPromise = this.detectInstalledApps();
    const apps = await this.appDetectionPromise;
    contextAnalyzer.setInstalledApps(apps);
    return apps;
  }

  /**
   * Get the current list of installed applications
   */
  async getInstalledApps(): Promise<InstalledApp[]> {
    if (this.appDetectionPromise) {
      return this.appDetectionPromise;
    }
    return this.refreshApps();
  }

  /**
   * Check if the action system is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  /**
   * Ensure the action system is initialized
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  /**
   * Detect installed applications
   */
  private async detectInstalledApps(): Promise<InstalledApp[]> {
    try {
      const response = await fetch('/api/actions/detect-apps', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        console.warn('Failed to detect installed apps:', response.statusText);
        return [];
      }

      const data = await response.json();
      return data.apps || [];
    } catch (error) {
      console.warn('Error detecting installed apps:', error);
      return [];
    }
  }
}

// Global instance
export const actionService = new ActionService();