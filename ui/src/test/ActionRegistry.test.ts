/**
 * Property-based tests for ActionRegistry
 * Feature: context-aware-photo-actions, Property 1: Context-aware menu behavior
 * Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as fc from 'fast-check';
import { ActionRegistry } from '../services/ActionRegistry';
import { ActionCategory, ActionType } from '../types/actions';
import type { PhotoAction } from '../types/actions';

describe('ActionRegistry Property Tests', () => {
  let registry: ActionRegistry;

  beforeEach(() => {
    registry = new ActionRegistry();
  });

  // Generators for property-based testing
  const actionCategoryArb = fc.constantFrom(
    ActionCategory.FILE_SYSTEM,
    ActionCategory.EDITING,
    ActionCategory.SHARING,
    ActionCategory.EXPORT,
    ActionCategory.NAVIGATION
  );

  const actionTypeArb = fc.constantFrom(
    ActionType.COPY_PATH,
    ActionType.OPEN_LOCATION,
    ActionType.OPEN_WITH,
    ActionType.DOWNLOAD,
    ActionType.EXPORT,
    ActionType.SHARE,
    ActionType.OPEN_NEW_TAB
  );

  const fileLocationArb = fc.constantFrom('local', 'cloud', 'hybrid');
  const fileTypeArb = fc.constantFrom('image', 'video', 'raw', 'document');

  const photoContextArb = fc.record({
    fileLocation: fileLocationArb,
    fileType: fileTypeArb,
    capabilities: fc.record({
      canEdit: fc.boolean(),
      canExport: fc.boolean(),
      canShare: fc.boolean(),
      canOpenLocation: fc.boolean(),
      supportedFormats: fc.array(fc.string(), { minLength: 0, maxLength: 5 })
    }),
    availableApps: fc.array(fc.record({
      id: fc.string(),
      name: fc.string(),
      displayName: fc.string(),
      executablePath: fc.string(),
      supportedFormats: fc.array(fc.string(), { minLength: 0, maxLength: 3 }),
      category: fc.constantFrom('photo_editor', 'raw_processor', 'video_editor', 'viewer', 'organizer')
    }), { minLength: 0, maxLength: 5 }),
    systemInfo: fc.record({
      platform: fc.constantFrom('windows', 'macos', 'linux'),
      hasClipboard: fc.boolean(),
      canOpenFileManager: fc.boolean(),
      canLaunchApps: fc.boolean(),
      supportedProtocols: fc.array(fc.string(), { minLength: 1, maxLength: 3 })
    })
  });

  const photoActionArb = fc.record({
    id: fc.string({ minLength: 1 }).filter(s => s.trim().length > 0),
    label: fc.string({ minLength: 1 }).filter(s => s.trim().length > 0),
    icon: fc.string({ minLength: 1 }).filter(s => s.trim().length > 0),
    category: actionCategoryArb,
    type: actionTypeArb,
	    contextRequirements: fc.array(fc.record({
	      type: fc.constantFrom('fileLocation', 'fileType', 'capability', 'app'),
	      value: fc.oneof(fc.string().filter(s => s.trim().length > 0), fc.array(fc.string().filter(s => s.trim().length > 0), { minLength: 1, maxLength: 3 })),
	      operator: fc.option(fc.constantFrom('equals', 'includes', 'excludes'), { nil: undefined })
	    }), { minLength: 0, maxLength: 3 }),
	    priority: fc.integer({ min: 0, max: 100 }),
	    shortcut: fc.option(fc.string(), { nil: undefined }),
	    description: fc.option(fc.string(), { nil: undefined }),
	    isEnabled: fc.constant(() => true),
	    execute: fc.constant(async () => ({ success: true }))
	  });

  const photoArb = fc.record({
    path: fc.string({ minLength: 1 }).filter(s => s.trim().length > 0),
    filename: fc.string({ minLength: 1 }).filter(s => s.trim().length > 0),
    score: fc.float({ min: 0, max: 1 }),
    metadata: fc.record({})
  });

  /**
   * Property 1: Context-aware menu behavior
   * For any photo and system context, the context menu should display only appropriate actions 
   * for the file location, prioritized by workflow frequency, with proper visual indicators 
   * distinguishing action types
   */
  it('should only return actions appropriate for the given context', () => {
    fc.assert(
      fc.property(
        fc.array(photoActionArb, { minLength: 1, maxLength: 10 }).map(actions => {
          // Ensure unique IDs
          const uniqueActions = actions.map((action, index) => ({
            ...action,
            id: `${action.id}-${index}`
          }));
          return uniqueActions;
        }),
        photoContextArb,
        (actions, context) => {
          // Clear registry before test
          registry.clearActions();
          
          // Register all actions
          actions.forEach(action => registry.registerAction(action));

          // Get actions for context
          const availableActions = registry.getActionsForContext(context);

          // All returned actions should be from the registered actions
          availableActions.forEach(action => {
            expect(actions.some(a => a.id === action.id)).toBe(true);
          });

          // All returned actions should be enabled for this context
          availableActions.forEach(action => {
            expect(action.isEnabled(context)).toBe(true);
          });

          // Actions should be sorted by priority (higher priority first)
          for (let i = 0; i < availableActions.length - 1; i++) {
            expect(availableActions[i].priority).toBeGreaterThanOrEqual(
              availableActions[i + 1].priority
            );
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should group actions by category correctly', () => {
    fc.assert(
      fc.property(
        fc.array(photoActionArb, { minLength: 1, maxLength: 10 }).map(actions => {
          // Ensure unique IDs
          const uniqueActions = actions.map((action, index) => ({
            ...action,
            id: `${action.id}-${index}`
          }));
          return uniqueActions;
        }),
        photoContextArb,
        (actions, context) => {
          // Clear registry before test
          registry.clearActions();
          
          // Register all actions
          actions.forEach(action => registry.registerAction(action));

          // Get actions grouped by category
          const actionsByCategory = registry.getActionsByCategory(context);

          // Verify all actions are in the correct category
          Object.entries(actionsByCategory).forEach(([category, categoryActions]) => {
            categoryActions.forEach(action => {
              expect(action.category).toBe(category);
            });
          });

          // Verify no actions are duplicated across categories
          const allActionsFromCategories = Object.values(actionsByCategory).flat();
          const uniqueActionIds = new Set(allActionsFromCategories.map(a => a.id));
          expect(allActionsFromCategories.length).toBe(uniqueActionIds.size);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should execute actions successfully when context requirements are met', async () => {
    await fc.assert(
      fc.asyncProperty(
        photoActionArb,
        photoContextArb,
        photoArb,
        async (action, context, photo) => {
          // Clear registry before test
          registry.clearActions();
          
          // Create a mock action with no context requirements to ensure it's always available
          const mockAction: PhotoAction = {
            ...action,
            id: `test-${action.id}`,
            contextRequirements: [], // Remove context requirements to ensure action is available
            isEnabled: () => true,
            execute: vi.fn().mockResolvedValue({ success: true, message: 'Test success' })
          };

          registry.registerAction(mockAction);

          // Execute the action
          const result = await registry.executeAction(mockAction.id, photo, context);

          // Should succeed since isEnabled returns true and no context requirements
          expect(result.success).toBe(true);
          expect(mockAction.execute).toHaveBeenCalledWith(photo, undefined);
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should reject actions when context requirements are not met', async () => {
    await fc.assert(
      fc.asyncProperty(
        photoActionArb,
        photoContextArb,
        photoArb,
        async (action, context, photo) => {
          // Clear registry before test
          registry.clearActions();
          
          // Create a mock action that is never enabled
          const mockAction: PhotoAction = {
            ...action,
            id: `test-${action.id}`,
            isEnabled: () => false,
            execute: vi.fn().mockResolvedValue({ success: true })
          };

          registry.registerAction(mockAction);

          // Execute the action
          const result = await registry.executeAction(mockAction.id, photo, context);

          // Should fail since isEnabled returns false
          expect(result.success).toBe(false);
          expect(result.error).toContain('not available in the current context');
          expect(mockAction.execute).not.toHaveBeenCalled();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('should handle file location context requirements correctly', () => {
    fc.assert(
      fc.property(
        fileLocationArb,
        photoContextArb,
        (requiredLocation, context) => {
          // Clear registry before test
          registry.clearActions();
          
          // Create action that requires specific file location
          const action: PhotoAction = {
            id: 'test-location-action',
            label: 'Test Action',
            icon: 'Test',
            category: ActionCategory.FILE_SYSTEM,
            type: ActionType.COPY_PATH,
            contextRequirements: [
              { type: 'fileLocation', value: requiredLocation }
            ],
            priority: 50,
            isEnabled: () => true,
            execute: async () => ({ success: true })
          };

          registry.registerAction(action);

          // Update context to have the required location
          const testContext = { ...context, fileLocation: requiredLocation };
          const availableActions = registry.getActionsForContext(testContext);

          // Action should be available when location matches
          expect(availableActions.some(a => a.id === action.id)).toBe(true);

          // Action should not be available when location doesn't match
          const differentLocations = ['local', 'cloud', 'hybrid'].filter(loc => loc !== requiredLocation);
          if (differentLocations.length > 0) {
            const wrongLocation = differentLocations[0] as 'local' | 'cloud' | 'hybrid';
            const wrongContext = { ...context, fileLocation: wrongLocation };
            const wrongLocationActions = registry.getActionsForContext(wrongContext);
            expect(wrongLocationActions.some(a => a.id === action.id)).toBe(false);
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('should maintain action registry state correctly', () => {
    fc.assert(
      fc.property(
        fc.array(photoActionArb, { minLength: 1, maxLength: 10 }).map(actions => {
          // Ensure unique IDs
          const uniqueActions = actions.map((action, index) => ({
            ...action,
            id: `${action.id}-${index}`
          }));
          return uniqueActions;
        }),
        (actions) => {
          // Clear registry before test
          registry.clearActions();
          
          // Register actions
          actions.forEach(action => registry.registerAction(action));

          // Verify all actions are registered
          const allActions = registry.getAllActions();
          expect(allActions.length).toBe(actions.length);

          // Verify each action can be retrieved by ID
          actions.forEach(action => {
            const retrieved = registry.getAction(action.id);
            expect(retrieved).toBeDefined();
            expect(retrieved?.id).toBe(action.id);
          });

          // Test unregistering actions
          const firstAction = actions[0];
          const unregistered = registry.unregisterAction(firstAction.id);
          expect(unregistered).toBe(true);

          // Verify action is no longer available
          const afterUnregister = registry.getAllActions();
          expect(afterUnregister.length).toBe(actions.length - 1);
          expect(registry.getAction(firstAction.id)).toBeUndefined();
        }
      ),
      { numRuns: 50 }
    );
  });
});
