/**
 * Bulk Actions Service
 *
 * Handles bulk operations with undo functionality for photos.
 */
import { useToast } from '../components/toast/useToast';
import { apiFetch } from '../api';

type BulkActionState = Record<string, unknown>;

type TrashMoveResponse = {
  moved: Array<{ id: string; original_path: string }>;
  errors: string[];
};

type TrashRestoreResponse = {
  restored: string[];
  errors: string[];
};

const pluralize = (count: number, noun: string) =>
  `${count} ${noun}${count === 1 ? '' : 's'}`;

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await apiFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const message = (await response.text()) || response.statusText;
    throw new Error(message || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

interface BulkAction {
  id: string;
  type: 'delete' | 'favorite' | 'tag' | 'album';
  targetIds: string[]; // photo paths
  beforeState: BulkActionState; // state before the action
  afterState: BulkActionState; // state after the action (for potential redo)
  description: string; // user-friendly description
  timestamp: Date;
}

class BulkActionsService {
  private history: BulkAction[] = [];
  private capacity = 50; // Max number of actions to keep in history

  // Store actions with before/after state for potential undo
  storeAction(action: Omit<BulkAction, 'id' | 'timestamp'>): string {
    const id = Math.random().toString(36).substring(2, 9);
    const newAction: BulkAction = {
      ...action,
      id,
      timestamp: new Date(),
    };

    this.history.push(newAction);

    // Trim history to capacity
    if (this.history.length > this.capacity) {
      this.history = this.history.slice(-this.capacity);
    }

    return id;
  }

  // Get the last action for potential undo
  getLastAction(): BulkAction | null {
    if (this.history.length === 0) {
      return null;
    }
    return this.history[this.history.length - 1];
  }

  // Perform an undo operation
  async undoAction(actionId: string): Promise<boolean> {
    const actionIndex = this.history.findIndex((a) => a.id === actionId);
    if (actionIndex === -1) {
      return false;
    }

    const action = this.history[actionIndex];
    let success = false;

    // In a real implementation, this would use the beforeState to revert the action
    // For now, we'll implement specific undo operations per type
    try {
      switch (action.type) {
        case 'delete':
          // In the case of a delete operation, we'd need to restore from trash
          // This would involve calling an API to restore the files
          {
            const itemIds = (action.afterState as { itemIds?: string[] }).itemIds;
            if (!itemIds || itemIds.length === 0) {
              console.warn('Undo delete missing trash item IDs');
              break;
            }
            const payload = await postJson<TrashRestoreResponse>(
              '/api/trash/restore',
              { item_ids: itemIds }
            );
            if (payload.errors?.length) {
              console.warn('Trash restore errors:', payload.errors);
            }
            success = payload.errors?.length === 0;
          }
          break;

        case 'favorite':
          // Toggle favorites back to original state
          {
            const results = await Promise.allSettled(
              action.targetIds.map(async (path) => {
                const response = await apiFetch(
                  `/api/photos/${encodeURIComponent(path)}/favorite/toggle`,
                  { method: 'POST' }
                );
                return { ok: response.ok };
              })
            );
            let failures = 0;
            for (const result of results) {
              if (result.status !== 'fulfilled' || !result.value.ok) {
                failures += 1;
              }
            }
            if (failures > 0) {
              console.warn(`Favorite undo failed for ${failures} item(s)`);
            }
            success = failures === 0;
          }
          break;

        case 'tag':
          // Remove tags that were added
          console.warn('Undo not implemented for tag actions');
          break;

        case 'album':
          // Remove from album
          console.warn('Undo not implemented for album actions');
          break;

        default:
          console.warn(`No undo handler for action type:`, action.type);
      }

      // Remove the action from history after a successful undo
      if (success) {
        this.history = this.history.filter((a) => a.id !== actionId);
      }
      return success;
    } catch (error) {
      console.error('Error performing undo:', error);
      return false;
    }
  }
}

// Singleton instance
export const bulkActionsService = new BulkActionsService();

// Hook to use bulk actions with notification
export function useBulkActions() {
  const { addToast } = useToast();

  const performBulkDelete = async (photoPaths: string[]) => {
    try {
      // Record state before deletion for potential undo
      const beforeState = { photoPaths, operation: 'delete' };

      // Perform the delete operation (move to trash)
      const payload = await postJson<TrashMoveResponse>('/api/trash/move', {
        file_paths: photoPaths,
      });

      const moved = payload.moved ?? [];
      const errors = payload.errors ?? [];
      const movedIds = moved.map((item) => item.id);
      const movedPaths = moved.map((item) => item.original_path);

      if (movedIds.length === 0) {
        addToast({
          type: 'error',
          message: 'Failed to move photos to trash',
        });
        return;
      }

      if (errors.length > 0) {
        addToast({
          type: 'warning',
          message: `Failed to move ${pluralize(
            errors.length,
            'item'
          )} to trash`,
        });
      }

      // Record the action for undo
      const actionId = bulkActionsService.storeAction({
        type: 'delete',
        targetIds: movedPaths,
        beforeState: { ...beforeState, photoPaths: movedPaths },
        afterState: { itemIds: movedIds, status: 'deleted' },
        description: `Deleted ${pluralize(movedIds.length, 'photo')}`,
      });

      // Show notification with undo option
      addToast({
        type: 'undo',
        message: `Moved ${pluralize(movedIds.length, 'photo')} to trash`,
        actionLabel: 'Undo',
        onAction: async () => {
          const success = await bulkActionsService.undoAction(actionId);
          addToast({
            type: success ? 'info' : 'error',
            message: success
              ? 'Restore operation initiated'
              : 'Failed to restore from trash',
          });
        },
        duration: 8000, // Keep visible longer for undo
      });
    } catch (error) {
      console.error('Bulk delete failed', error);
      addToast({
        type: 'error',
        message: 'Failed to delete photos',
      });
    }
  };

  const performBulkFavorite = async (photoPaths: string[]) => {
    try {
      // Record state before operation for potential undo
      const beforeState = { photoPaths, operation: 'toggle_favorite' };

      // Toggle favorites
      const results = await Promise.allSettled(
        photoPaths.map(async (path) => {
          const response = await apiFetch(
            `/api/photos/${encodeURIComponent(path)}/favorite/toggle`,
            {
              method: 'POST',
            }
          );
          return { path, ok: response.ok };
        })
      );

      const successfulPaths: string[] = [];
      let failures = 0;
      for (const result of results) {
        if (result.status === 'fulfilled' && result.value.ok) {
          successfulPaths.push(result.value.path);
        } else {
          failures += 1;
        }
      }

      if (successfulPaths.length === 0) {
        addToast({
          type: 'error',
          message: 'Failed to toggle favorites',
        });
        return;
      }

      if (failures > 0) {
        addToast({
          type: 'warning',
          message: `Failed to toggle ${pluralize(failures, 'item')}`,
        });
      }

      // Record the action for undo
      const actionId = bulkActionsService.storeAction({
        type: 'favorite',
        targetIds: successfulPaths,
        beforeState: { ...beforeState, photoPaths: successfulPaths },
        afterState: {
          paths: successfulPaths,
          status: 'toggled_favorite',
        },
        description: `Toggled favorites for ${pluralize(
          successfulPaths.length,
          'photo'
        )}`,
      });

      // Show notification with undo option
      addToast({
        type: 'undo',
        message: `Toggled favorites for ${pluralize(
          successfulPaths.length,
          'photo'
        )}`,
        actionLabel: 'Undo',
        onAction: async () => {
          const success = await bulkActionsService.undoAction(actionId);
          addToast({
            type: success ? 'info' : 'error',
            message: success
              ? 'Favorite toggle undone'
              : 'Failed to undo favorite toggle',
          });
        },
        duration: 5000,
      });
    } catch (error) {
      console.error('Bulk favorite toggle failed', error);
      addToast({
        type: 'error',
        message: 'Failed to toggle favorites',
      });
    }
  };

  return {
    performBulkDelete,
    performBulkFavorite,
  };
}
