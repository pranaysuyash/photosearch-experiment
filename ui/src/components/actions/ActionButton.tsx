import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import type { PhotoAction, Photo, ActionResult } from '../../types/actions';

interface ActionButtonProps {
  action: PhotoAction;
  photo: Photo;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  disabled?: boolean;
  onExecute?: (result: ActionResult) => void;
  className?: string;
}

// Icon mapping - same as ContextMenu
const getIconComponent = (iconName: string) => {
  const iconMap: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
    Copy: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
      </svg>
    ),
    FolderOpen: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M6 14l1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.73 3l-1.73 3H9.24a2 2 0 0 1-1.79-1.1L6 14Z"/>
        <path d="M4 5v-.5A2.5 2.5 0 0 1 6.5 2H10"/>
      </svg>
    ),
    ExternalLink: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M15 3h6v6"/>
        <path d="M10 14 21 3"/>
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      </svg>
    ),
    Download: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7,10 12,15 17,10"/>
        <line x1="12" x2="12" y1="15" y2="3"/>
      </svg>
    ),
    Share: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
        <polyline points="16,6 12,2 8,6"/>
        <line x1="12" x2="12" y1="2" y2="15"/>
      </svg>
    ),
    Edit: ({ size = 16, className }) => (
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z"/>
      </svg>
    )
  };

  return iconMap[iconName] || iconMap.Edit;
};

export const ActionButton: React.FC<ActionButtonProps> = ({
  action,
  photo,
  variant = 'secondary',
  size = 'md',
  showLabel = true,
  disabled = false,
  onExecute,
  className = ''
}) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const handleExecute = async () => {
    if (isExecuting || disabled) return;

    setIsExecuting(true);
    try {
      // Mock execution for now - in real implementation this would use ActionService
      const result = await action.execute(photo);
      onExecute?.(result);
    } catch (error) {
      console.error('Action execution failed:', error);
      onExecute?.({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const IconComponent = getIconComponent(action.icon);

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
    relative group
    ${sizeClasses[size]}
    ${variantClasses[variant]}
    ${className}
  `;

  return (
    <div className="relative">
      <motion.button
        onClick={handleExecute}
        disabled={disabled || isExecuting}
        className={baseClasses}
        whileHover={{ scale: disabled ? 1 : 1.02 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        title={action.description || action.label}
      >
        {isExecuting ? (
          <Loader2 size={iconSizes[size]} className="animate-spin" />
        ) : (
          <IconComponent size={iconSizes[size]} />
        )}
        
        {showLabel && (
          <span className={size === 'sm' ? 'hidden sm:inline' : ''}>
            {action.label}
          </span>
        )}

        {action.shortcut && size !== 'sm' && (
          <span className="text-xs opacity-60 ml-auto">
            {action.shortcut}
          </span>
        )}
      </motion.button>

      {/* Tooltip for small buttons or when label is hidden */}
      {showTooltip && (!showLabel || size === 'sm') && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 5 }}
          className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-black/80 text-white text-xs rounded whitespace-nowrap z-50"
        >
          {action.description || action.label}
          {action.shortcut && (
            <span className="ml-2 opacity-60">{action.shortcut}</span>
          )}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black/80" />
        </motion.div>
      )}
    </div>
  );
};