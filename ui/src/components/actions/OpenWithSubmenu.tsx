import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Edit, Loader2, AlertCircle } from 'lucide-react';
import type { Photo, InstalledApp, ActionResult } from '../../types/actions';

interface OpenWithSubmenuProps {
  photo: Photo;
  availableApps: InstalledApp[];
  onAppSelect: (app: InstalledApp) => Promise<ActionResult>;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

interface AppItemProps {
  app: InstalledApp;
  onSelect: (app: InstalledApp) => void;
  isExecuting: boolean;
}

const AppItem: React.FC<AppItemProps> = ({ app, onSelect, isExecuting }) => {
  const getCategoryIcon = (category: string) => {
    const icons = {
      photo_editor: '🎨',
      raw_processor: '📸',
      video_editor: '🎬',
      viewer: '👁️',
      organizer: '📁'
    };
    return icons[category as keyof typeof icons] || '📱';
  };

  return (
    <button
      onClick={() => onSelect(app)}
      disabled={isExecuting}
      className="w-full flex items-center gap-3 px-3 py-2 text-sm text-white/90 hover:bg-white/10 transition-colors disabled:opacity-50 text-left"
    >
      <span className="text-base flex-shrink-0">
        {getCategoryIcon(app.category)}
      </span>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate">{app.displayName}</div>
        {app.version && (
          <div className="text-xs text-white/50 truncate">v{app.version}</div>
        )}
      </div>
      {isExecuting && (
        <Loader2 size={14} className="animate-spin text-white/50" />
      )}
    </button>
  );
};

export const OpenWithSubmenu: React.FC<OpenWithSubmenuProps> = ({
  photo,
  availableApps,
  onAppSelect,
  disabled = false,
  variant = 'secondary',
  size = 'md',
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [executingAppId, setExecutingAppId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current && 
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const handleAppSelect = async (app: InstalledApp) => {
    if (executingAppId) return;

    setExecutingAppId(app.id);
    setError(null);

    try {
      const result = await onAppSelect(app);
      if (result.success) {
        setIsOpen(false);
      } else {
        setError(result.error || 'Failed to open with application');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
    } finally {
      setExecutingAppId(null);
    }
  };

  const toggleMenu = () => {
    if (!disabled && availableApps.length > 0) {
      setIsOpen(!isOpen);
      setError(null);
    }
  };

  // Size classes
  const sizeClasses = {
    sm: 'px-2 py-1.5 text-xs',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-2.5 text-base'
  };

  const iconSizes = {
    sm: 14,
    md: 16,
    lg: 18
  };

  // Variant classes
  const variantClasses = {
    primary: 'btn-glass btn-glass--primary',
    secondary: 'btn-glass btn-glass--muted',
    ghost: 'hover:bg-white/10 text-white/80 hover:text-white'
  };

  const baseClasses = `
    inline-flex items-center gap-2 font-medium transition-all duration-200
    disabled:opacity-50 disabled:cursor-not-allowed
    ${sizeClasses[size]}
    ${variantClasses[variant]}
    ${className}
  `;

  const isDisabled = disabled || availableApps.length === 0;

  return (
    <div className="relative">
      <motion.button
        ref={buttonRef}
        onClick={toggleMenu}
        disabled={isDisabled}
        className={baseClasses}
        whileHover={{ scale: isDisabled ? 1 : 1.02 }}
        whileTap={{ scale: isDisabled ? 1 : 0.98 }}
        title={
          availableApps.length === 0 
            ? 'No compatible applications found' 
            : `Open with ${availableApps.length} available app${availableApps.length === 1 ? '' : 's'}`
        }
      >
        <Edit size={iconSizes[size]} />
        <span>Open With</span>
        <ChevronDown 
          size={iconSizes[size] - 2} 
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
        {availableApps.length > 0 && (
          <span className="bg-white/20 text-xs px-1.5 py-0.5 rounded-full">
            {availableApps.length}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={menuRef}
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute top-full left-0 mt-2 min-w-64 glass-surface rounded-lg border border-white/10 py-1 shadow-2xl z-50"
          >
            {/* Header */}
            <div className="px-3 py-2 border-b border-white/10">
              <div className="text-sm font-medium text-white/90">
                Open with Application
              </div>
              <div className="text-xs text-white/50 truncate">
                {photo.filename}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="px-3 py-2 border-b border-white/10">
                <div className="flex items-center gap-2 text-xs text-red-400">
                  <AlertCircle size={14} />
                  <span>{error}</span>
                </div>
              </div>
            )}

            {/* App List */}
            <div className="max-h-64 overflow-y-auto">
              {availableApps.length === 0 ? (
                <div className="px-3 py-4 text-center text-xs text-white/50">
                  No compatible applications found
                </div>
              ) : (
                availableApps.map((app) => (
                  <AppItem
                    key={app.id}
                    app={app}
                    onSelect={handleAppSelect}
                    isExecuting={executingAppId === app.id}
                  />
                ))
              )}
            </div>

            {/* Footer */}
            {availableApps.length > 0 && (
              <div className="px-3 py-2 border-t border-white/10">
                <div className="text-xs text-white/50">
                  {availableApps.length} application{availableApps.length === 1 ? '' : 's'} available
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};