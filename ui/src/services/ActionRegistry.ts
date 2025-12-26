import type {
  PhotoAction,
  PhotoContext,
  ActionResult,
  Photo,
  ActionOptions,
  FileCapabilities,
} from '../types/actions';

/**
 * Central registry for all available photo actions with context-aware filtering.
 * Manages action registration, context-based filtering, and execution.
 */
export class ActionRegistry {
  private actions: Map<string, PhotoAction> = new Map();

  /**
   * Register a new photo action
   */
  registerAction(action: PhotoAction): void {
    this.actions.set(action.id, action);
  }

  /**
   * Register multiple actions at once
   */
  registerActions(actions: PhotoAction[]): void {
    actions.forEach((action) => this.registerAction(action));
  }

  /**
   * Get all actions appropriate for the given context, sorted by priority
   */
  getActionsForContext(context: PhotoContext): PhotoAction[] {
    const availableActions = Array.from(this.actions.values())
      .filter((action) => this.isActionAvailable(action, context))
      .sort((a, b) => b.priority - a.priority); // Higher priority first

    return availableActions;
  }

  /**
   * Get actions grouped by category for the given context
   */
  getActionsByCategory(context: PhotoContext): Record<string, PhotoAction[]> {
    const actions = this.getActionsForContext(context);
    const grouped: Record<string, PhotoAction[]> = {};

    actions.forEach((action) => {
      if (!grouped[action.category]) {
        grouped[action.category] = [];
      }
      grouped[action.category].push(action);
    });

    return grouped;
  }

  /**
   * Execute a specific action by ID
   */
  async executeAction(
    actionId: string,
    photo: Photo,
    context: PhotoContext,
    options?: ActionOptions
  ): Promise<ActionResult> {
    const action = this.actions.get(actionId);

    if (!action) {
      return {
        success: false,
        error: `Action with ID '${actionId}' not found`,
      };
    }

    if (!this.isActionAvailable(action, context)) {
      return {
        success: false,
        error: `Action '${action.label}' is not available in the current context`,
      };
    }

    try {
      return await action.execute(photo, options);
    } catch (error) {
      return {
        success: false,
        error:
          error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  /**
   * Get a specific action by ID
   */
  getAction(actionId: string): PhotoAction | undefined {
    return this.actions.get(actionId);
  }

  /**
   * Get all registered actions
   */
  getAllActions(): PhotoAction[] {
    return Array.from(this.actions.values());
  }

  /**
   * Remove an action from the registry
   */
  unregisterAction(actionId: string): boolean {
    return this.actions.delete(actionId);
  }

  /**
   * Clear all registered actions
   */
  clearActions(): void {
    this.actions.clear();
  }

  /**
   * Check if an action is available in the given context
   */
  private isActionAvailable(
    action: PhotoAction,
    context: PhotoContext
  ): boolean {
    // First check the action's own isEnabled function
    if (!action.isEnabled(context)) {
      return false;
    }

    // Then check context requirements
    return action.contextRequirements.every((requirement) =>
      this.checkContextRequirement(requirement, context)
    );
  }

  /**
   * Check if a specific context requirement is met
   */
  private checkContextRequirement(
    requirement: { type: string; value: string | string[]; operator?: string },
    context: PhotoContext
  ): boolean {
    const { type, value, operator = 'equals' } = requirement;

    switch (type) {
      case 'fileLocation':
        return this.checkValue(context.fileLocation, value, operator);

      case 'fileType':
        return this.checkValue(context.fileType, value, operator);

      case 'capability':
        if (typeof value === 'string') {
          return this.checkCapability(value, context.capabilities);
        }
        return false;

      case 'app':
        if (typeof value === 'string') {
          return context.availableApps.some(
            (app) => app.category === value || app.name === value
          );
        }
        if (Array.isArray(value)) {
          return value.some((v) =>
            context.availableApps.some(
              (app) => app.category === v || app.name === v
            )
          );
        }
        return false;

      default:
        return true;
    }
  }

  /**
   * Check if a value matches the requirement
   */
  private checkValue(
    contextValue: string,
    requirementValue: string | string[],
    operator: string
  ): boolean {
    switch (operator) {
      case 'equals':
        return Array.isArray(requirementValue)
          ? requirementValue.includes(contextValue)
          : contextValue === requirementValue;

      case 'includes':
        return Array.isArray(requirementValue)
          ? requirementValue.some((v) => contextValue.includes(v))
          : contextValue.includes(requirementValue);

      case 'excludes':
        return Array.isArray(requirementValue)
          ? !requirementValue.some((v) => contextValue.includes(v))
          : !contextValue.includes(requirementValue);

      default:
        return false;
    }
  }

  /**
   * Check if a capability is available
   */
  private checkCapability(
    capability: string,
    capabilities: FileCapabilities
  ): boolean {
    switch (capability) {
      case 'canEdit':
        return capabilities.canEdit === true;
      case 'canExport':
        return capabilities.canExport === true;
      case 'canShare':
        return capabilities.canShare === true;
      case 'canOpenLocation':
        return capabilities.canOpenLocation === true;
      default:
        return false;
    }
  }
}

// Global instance
export const actionRegistry = new ActionRegistry();
