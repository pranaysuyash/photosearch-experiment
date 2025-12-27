/**
 * Toast Provider Component
 *
 * Manages global toast notifications with undo functionality.
 */
import React, { useState, type ReactNode } from 'react';
import { Toast } from './Toast';
import { ToastContext, type ToastOptions } from './ToastContext';

interface ToastProviderProps {
  children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
  const [toasts, setToasts] = useState<Array<ToastOptions & { id: string }>>([]);

  const addToast = (options: ToastOptions): string => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { id, ...options };

    setToasts(prev => [...prev, newToast]);

    return id;
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[2000] max-w-sm w-full">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            id={toast.id}
            type={toast.type}
            message={toast.message}
            actionLabel={toast.actionLabel}
            onAction={() => {
              if (toast.onAction) {
                toast.onAction();
              }
              removeToast(toast.id);
            }}
            onClose={() => removeToast(toast.id)}
            duration={toast.duration}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
