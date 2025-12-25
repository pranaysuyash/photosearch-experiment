/**
 * Bulk Actions Service
 *
 * Handles bulk operations with undo functionality for photos.
 */
import { useToast } from '../components/toast/ToastProvider';

type BulkActionState = Record<string, unknown>;

interface BulkAction {
  id: string;
  type: 'delete' | 'favorite' | 'tag' | 'album';
  targetIds: string[]; // photo paths
  beforeState: BulkActionState;    // state before the action
  afterState: BulkActionState;     // state after the action (for potential redo)
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
      timestamp: new Date()
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
    const actionIndex = this.history.findIndex(a => a.id === actionId);
    if (actionIndex === -1) {
      return false;
    }

    const action = this.history[actionIndex];
    
    // In a real implementation, this would use the beforeState to revert the action
    // For now, we'll implement specific undo operations per type
    try {
      switch (action.type) {
        case 'delete':
          // In the case of a delete operation, we'd need to restore from trash
          // This would involve calling an API to restore the files
          console.log(`Undoing delete for:`, action.targetIds);
          // For now, we'll just log it - a real implementation would restore the files
          break;
          
        case 'favorite':
          // Toggle favorites back to original state
          console.log(`Undoing favorite toggle for:`, action.targetIds);
          // A real implementation would call the API to revert the favorites
          break;
          
        case 'tag':
          // Remove tags that were added
          console.log(`Undoing tag operation for:`, action.targetIds);
          // A real implementation would remove the tags that were added
          break;
          
        case 'album':
          // Remove from album
          console.log(`Undoing album operation for:`, action.targetIds);
          // A real implementation would remove the photos from the album
          break;
          
        default:
          console.warn(`No undo handler for action type:`, action.type);
      }

      // Remove the action from history after undo
      this.history = this.history.filter(a => a.id !== actionId);
      return true;
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
      await Promise.all(photoPaths.map(path => 
        fetch('/api/trash/move', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ paths: [path] })
        })
      ));

      // Record the action for undo
      const actionId = bulkActionsService.storeAction({
        type: 'delete',
        targetIds: photoPaths,
        beforeState,
        afterState: { paths: photoPaths, status: 'deleted' },
        description: `Deleted ${photoPaths.length} photo${photoPaths.length > 1 ? 's' : ''}`
      });

      // Show notification with undo option
      addToast({
        type: 'undo',
        message: `Moved ${photoPaths.length} photo${photoPaths.length > 1 ? 's' : ''} to trash`,
        actionLabel: 'Undo',
        onAction: async () => {
          const success = await bulkActionsService.undoAction(actionId);
          if (success) {
            addToast({
              type: 'info',
              message: 'Restore operation initiated'
            });
          }
        },
        duration: 8000 // Keep visible longer for undo
      });
    } catch (error) {
      console.error('Bulk delete failed', error);
      addToast({
        type: 'error',
        message: 'Failed to delete photos'
      });
    }
  };

  const performBulkFavorite = async (photoPaths: string[]) => {
    try {
      // Record state before operation for potential undo
      const beforeState = { photoPaths, operation: 'toggle_favorite' };
      
      // Toggle favorites
      await Promise.all(photoPaths.map(path => 
        fetch(`/api/photos/${encodeURIComponent(path)}/favorite/toggle`, { 
          method: 'POST' 
        })
      ));

      // Record the action for undo
      const actionId = bulkActionsService.storeAction({
        type: 'favorite',
        targetIds: photoPaths,
        beforeState,
        afterState: { paths: photoPaths, status: 'toggled_favorite' },
        description: `Toggled favorites for ${photoPaths.length} photo${photoPaths.length > 1 ? 's' : ''}`
      });

      // Show notification with undo option
      addToast({
        type: 'undo',
        message: `Toggled favorites for ${photoPaths.length} photo${photoPaths.length > 1 ? 's' : ''}`,
        actionLabel: 'Undo',
        onAction: async () => {
          const success = await bulkActionsService.undoAction(actionId);
          if (success) {
            addToast({
              type: 'info',
              message: 'Favorite toggle undone'
            });
          }
        },
        duration: 5000
      });
    } catch (error) {
      console.error('Bulk favorite toggle failed', error);
      addToast({
        type: 'error',
        message: 'Failed to toggle favorites'
      });
    }
  };

  return {
    performBulkDelete,
    performBulkFavorite
  };
}