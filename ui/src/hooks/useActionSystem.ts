import { useState, useEffect, useCallback } from 'react';
import { actionService } from '../services/ActionService';
import type { Photo, PhotoAction, ActionResult, InstalledApp, PhotoContext } from '../types/actions';

/**
 * React hook for using the context-aware photo action system
 */
export function useActionSystem() {
  const [initialized, setInitialized] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize the action system
  useEffect(() => {
    let mounted = true;

    const initialize = async () => {
      try {
        setLoading(true);
        setError(null);
        
        await actionService.initialize();
        
        if (mounted) {
          setInitialized(true);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to initialize action system');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    initialize();

    return () => {
      mounted = false;
    };
  }, []);

  // Get actions for a photo
  const getActionsForPhoto = useCallback(async (photo: Photo) => {
    if (!initialized) {
      throw new Error('Action system not initialized');
    }
    return actionService.getActionsForPhoto(photo);
  }, [initialized]);

  // Execute an action
  const executeAction = useCallback(async (
    actionId: string, 
    photo: Photo, 
    options?: any
  ): Promise<ActionResult> => {
    if (!initialized) {
      throw new Error('Action system not initialized');
    }
    return actionService.executeAction(actionId, photo, options);
  }, [initialized]);

  // Get compatible apps for a photo
  const getCompatibleApps = useCallback(async (photo: Photo): Promise<InstalledApp[]> => {
    if (!initialized) {
      throw new Error('Action system not initialized');
    }
    return actionService.getCompatibleApps(photo);
  }, [initialized]);

  // Refresh installed apps
  const refreshApps = useCallback(async (): Promise<InstalledApp[]> => {
    if (!initialized) {
      throw new Error('Action system not initialized');
    }
    return actionService.refreshApps();
  }, [initialized]);

  return {
    initialized,
    loading,
    error,
    getActionsForPhoto,
    executeAction,
    getCompatibleApps,
    refreshApps
  };
}

/**
 * Hook for getting actions for a specific photo
 */
export function usePhotoActions(photo: Photo | null) {
  const { initialized, getActionsForPhoto } = useActionSystem();
  const [actions, setActions] = useState<PhotoAction[]>([]);
  const [context, setContext] = useState<PhotoContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!photo || !initialized) {
      setActions([]);
      setContext(null);
      return;
    }

    let mounted = true;

    const loadActions = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const result = await getActionsForPhoto(photo);
        
        if (mounted) {
          setActions(result.actions);
          setContext(result.context);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load actions');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadActions();

    return () => {
      mounted = false;
    };
  }, [photo, initialized, getActionsForPhoto]);

  return {
    actions,
    context,
    loading,
    error
  };
}