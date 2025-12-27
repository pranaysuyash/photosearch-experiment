import { createContext } from 'react';

export type ToastType = 'info' | 'success' | 'warning' | 'error' | 'undo';

export interface ToastOptions {
  type: ToastType;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  duration?: number; // in milliseconds, 0 for persistent
}

export interface ToastContextType {
  addToast: (options: ToastOptions) => string;
  removeToast: (id: string) => void;
}

export const ToastContext = createContext<ToastContextType | undefined>(
  undefined
);
