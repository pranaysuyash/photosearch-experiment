import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Copy, 
  FolderOpen, 
  ExternalLink, 
  Download, 
  Share, 
  Edit,
  ChevronRight,
  Loader2
} from 'lucide-react';
import type { Photo, PhotoAction, InstalledApp } from '../../types/actions';
import { usePhotoActions } from '../../hooks/useActionSystem';
import { ActionCategory } from '../../types/actions';

interface ContextMenuProps {
  photo: Photo;
  position: { x: number; y: number };
  onClose: () => void;
  onActionExecute?: (actionId: string, result: any) => void;
}

interface ActionIconProps {
  iconName: string;
  size?: number;
}

// Icon mapping for actions
const ActionIcon: React.FC<ActionIconProps> = ({ iconName, size = 16 }) => {
  const icons = {
    Copy,
    FolderOpen,
    ExternalLink,
    Download,
    Share,
    Edit,
    CloudDownload: Download,
    Link: Share
  };
  
  const IconComponent = icons[iconName as keyof typeof icons] || Edit;
  return <IconComponent size={size} />;
};

interface ActionItemProps {
  action: PhotoAction;
  photo: Photo;
  onExecute: (actionId: string, result: any) => void;
  onClose: () => void;
}

const ActionItem: React.FC<ActionItemProps> = ({ action, photo, onExecute, onClose }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [showSubmenu, setShowSubmenu] = useState(false);
  const [compatibleApps, setCompatibleApps] = useState<InstalledApp[]>([]);

  // Load compatible apps for "Open With" actions
  useEffect(() => {
    if (action.type === 'open_with') {
      // This would normally come from the action service
      // For now, we'll mock some apps
      setCompatibleApps([
        { id: 'photoshop', name: 'Adobe Photoshop', displayName: 'Photoshop', executablePath: '', supportedFormats: [], category: 'photo_editor' },
        { id: 'lightroom', name: 'Adobe Lightroom', displayName: 'Lightroom', executablePath: '', supportedFormats: [], category: 'raw_processor' }
      ]);
    }
  }, [action.type]);

  const handleExecute = async (options?: any) => {
    if (isExecuting) return;
    
    setIsExecuting(true);
    try {
      // Mock execution for now - in real implementation this would use ActionService
      const result = await action.execute(photo, options);
      onExecute(action.id, result);
      
      if (result.success) {
        onClose();
      }
    } catch (error) {
      console.error('Action execution failed:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleAppSelect = (app: InstalledApp) => {
    handleExecute({ appId: app.id });
  };

  if (action.type === 'open_with' && compatibleApps.length > 0) {
    return (
      <div 
        className="relative"
        onMouseEnter={() => setShowSubmenu(true)}
        onMouseLeave={() => setShowSubmenu(false)}
      >
        <button
          className="w-full flex items-center justify-between px-3 py-2 text-sm text-white/90 hover:bg-white/10 transition-colors"
          disabled={isExecuting}
        >
          <div className="flex items-center gap-3">
            {isExecuting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ActionIcon iconName={action.icon} />
            )}
            <span>{action.label}</span>
          </div>
          <ChevronRight size={14} className="text-white/50" />
        </button>

        <AnimatePresence>
          {showSubmenu && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="absolute left-full top-0 ml-1 min-w-48 glass-surface rounded-lg border border-white/10 py-1 z-50"
            >
              {compatibleApps.map((app) => (
                <button
                  key={app.id}
                  onClick={() => handleAppSelect(app)}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/90 hover:bg-white/10 transition-colors"
                >
                  <div className="w-4 h-4 bg-white/20 rounded flex-shrink-0" />
                  <span>{app.displayName}</span>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  return (
    <button
      onClick={() => handleExecute()}
      disabled={isExecuting}
      className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/90 hover:bg-white/10 transition-colors disabled:opacity-50"
    >
      {isExecuting ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <ActionIcon iconName={action.icon} />
      )}
      <span>{action.label}</span>
      {action.shortcut && (
        <span className="ml-auto text-xs text-white/50">{action.shortcut}</span>
      )}
    </button>
  );
};

interface CategorySectionProps {
  category: string;
  actions: PhotoAction[];
  photo: Photo;
  onExecute: (actionId: string, result: any) => void;
  onClose: () => void;
}

const CategorySection: React.FC<CategorySectionProps> = ({ 
  category, 
  actions, 
  photo, 
  onExecute, 
  onClose 
}) => {
  const categoryLabels = {
    [ActionCategory.FILE_SYSTEM]: 'File',
    [ActionCategory.EDITING]: 'Edit',
    [ActionCategory.SHARING]: 'Share',
    [ActionCategory.EXPORT]: 'Export',
    [ActionCategory.NAVIGATION]: 'View'
  };

  const categoryLabel = categoryLabels[category as keyof typeof categoryLabels] || category;

  return (
    <div className="py-1">
      <div className="px-3 py-1 text-xs font-medium text-white/50 uppercase tracking-wider">
        {categoryLabel}
      </div>
      {actions.map((action) => (
        <ActionItem
          key={action.id}
          action={action}
          photo={photo}
          onExecute={onExecute}
          onClose={onClose}
        />
      ))}
    </div>
  );
};

export const ContextMenu: React.FC<ContextMenuProps> = ({ 
  photo, 
  position, 
  onClose, 
  onActionExecute 
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const { actions, loading, error } = usePhotoActions(photo);
  const [adjustedPosition, setAdjustedPosition] = useState(position);

  // Adjust position to keep menu on screen
  useEffect(() => {
    if (menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      let { x, y } = position;
      
      // Adjust horizontal position
      if (x + rect.width > viewportWidth) {
        x = viewportWidth - rect.width - 10;
      }
      
      // Adjust vertical position
      if (y + rect.height > viewportHeight) {
        y = viewportHeight - rect.height - 10;
      }
      
      setAdjustedPosition({ x: Math.max(10, x), y: Math.max(10, y) });
    }
  }, [position, actions]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const handleActionExecute = (actionId: string, result: any) => {
    onActionExecute?.(actionId, result);
  };

  // Group actions by category
  const actionsByCategory = actions.reduce((acc, action) => {
    if (!acc[action.category]) {
      acc[action.category] = [];
    }
    acc[action.category].push(action);
    return acc;
  }, {} as Record<string, PhotoAction[]>);

  const categoryOrder = [
    ActionCategory.NAVIGATION,
    ActionCategory.FILE_SYSTEM,
    ActionCategory.EDITING,
    ActionCategory.EXPORT,
    ActionCategory.SHARING
  ];

  return (
    <motion.div
      ref={menuRef}
      initial={{ opacity: 0, scale: 0.95, y: -10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -10 }}
      transition={{ duration: 0.15, ease: 'easeOut' }}
      className="fixed z-[200] min-w-56 glass-surface rounded-lg border border-white/10 py-1 shadow-2xl"
      style={{
        left: adjustedPosition.x,
        top: adjustedPosition.y,
      }}
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-white/10">
        <div className="text-sm font-medium text-white/90 truncate">
          {photo.filename}
        </div>
        <div className="text-xs text-white/50 truncate">
          {photo.path}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="px-3 py-4 text-center">
          <Loader2 size={20} className="animate-spin mx-auto text-white/50" />
          <div className="text-xs text-white/50 mt-2">Loading actions...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="px-3 py-4 text-center">
          <div className="text-xs text-red-400">Failed to load actions</div>
          <div className="text-xs text-white/50 mt-1">{error}</div>
        </div>
      )}

      {/* Actions */}
      {!loading && !error && (
        <>
          {actions.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-white/50">
              No actions available
            </div>
          ) : (
            categoryOrder.map((category, index) => {
              const categoryActions = actionsByCategory[category];
              if (!categoryActions || categoryActions.length === 0) return null;

              return (
                <React.Fragment key={category}>
                  {index > 0 && <div className="border-t border-white/5 my-1" />}
                  <CategorySection
                    category={category}
                    actions={categoryActions}
                    photo={photo}
                    onExecute={handleActionExecute}
                    onClose={onClose}
                  />
                </React.Fragment>
              );
            })
          )}
        </>
      )}
    </motion.div>
  );
};