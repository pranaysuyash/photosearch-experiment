/**
 * Toast Component with Undo Functionality
 *
 * Provides notifications with optional undo actions for bulk operations.
 */
import React, { useEffect, useState } from 'react';
import { 
  X, 
  RotateCcw, 
  AlertCircle, 
  CheckCircle, 
  Info,
  Trash2,
  FolderPlus,
  Tag
} from 'lucide-react';
import { glass } from '../design/glass';

type ToastType = 'info' | 'success' | 'warning' | 'error' | 'undo';

interface ToastProps {
  id: string;
  type: ToastType;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  onClose: () => void;
  duration?: number; // in milliseconds, 0 for persistent
}

const toastIcons = {
  info: Info,
  success: CheckCircle,
  warning: AlertCircle,
  error: AlertCircle,
  undo: RotateCcw
};

const toastColors = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  undo: 'text-blue-400'
};

export function Toast({ 
  id, 
  type, 
  message, 
  actionLabel, 
  onAction, 
  onClose, 
  duration = 5000 
}: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);
  const Icon = toastIcons[type];
  const colorClass = toastColors[type];

  useEffect(() => {
    if (duration === 0) return; // Don't auto-close persistent toasts

    const timer = setTimeout(() => {
      setIsVisible(false);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration]);

  useEffect(() => {
    if (!isVisible) {
      const timer = setTimeout(() => {
        onClose();
      }, 300); // Allow time for exit animation

      return () => clearTimeout(timer);
    }
  }, [isVisible, onClose]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className={`
      ${glass.surfaceStrong} border border-white/10 rounded-xl p-4 mb-3 shadow-lg
      transform transition-all duration-300
      translate-y-0 opacity-100
      ${type === 'error' ? 'bg-red-500/10' : 
        type === 'success' ? 'bg-green-500/10' : 
        type === 'warning' ? 'bg-yellow-500/10' : 
        type === 'info' ? 'bg-blue-500/10' : 
        'bg-purple-500/10'}
    `}>
      <div className="flex items-start gap-3">
        <Icon className={colorClass} size={20} />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-foreground">{message}</p>
        </div>
        <div className="flex items-center gap-2">
          {onAction && actionLabel && (
            <button
              onClick={onAction}
              className="btn-glass btn-glass--primary text-xs px-3 py-1.5 flex items-center gap-1"
            >
              <RotateCcw size={12} />
              {actionLabel}
            </button>
          )}
          <button
            onClick={() => setIsVisible(false)}
            className="btn-glass btn-glass--muted w-8 h-8 p-0 justify-center"
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}