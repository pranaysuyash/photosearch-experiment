import React, { useEffect, useState } from 'react';
import { X, Check, AlertCircle, Info } from 'lucide-react';

interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
  onClose: () => void;
}

export function Toast({ message, type = 'info', duration = 3000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Wait for fade out animation
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <Check size={16} className='text-green-400' />;
      case 'error':
        return <AlertCircle size={16} className='text-red-400' />;
      case 'warning':
        return <AlertCircle size={16} className='text-yellow-400' />;
      default:
        return <Info size={16} className='text-blue-400' />;
    }
  };

  const getColorClasses = () => {
    switch (type) {
      case 'success':
        return 'border-green-500/50 bg-green-500/10';
      case 'error':
        return 'border-red-500/50 bg-red-500/10';
      case 'warning':
        return 'border-yellow-500/50 bg-yellow-500/10';
      default:
        return 'border-blue-500/50 bg-blue-500/10';
    }
  };

  return (
    <div
      className={`fixed top-4 right-4 z-[9999] flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm transition-all duration-300 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'
      } ${getColorClasses()}`}
    >
      {getIcon()}
      <span className='text-sm text-white'>{message}</span>
      <button
        onClick={() => {
          setIsVisible(false);
          setTimeout(onClose, 300);
        }}
        className='text-white/60 hover:text-white transition-colors'
      >
        <X size={14} />
      </button>
    </div>
  );
}

// Toast context for managing multiple toasts
export function useToast() {
  const [toasts, setToasts] = useState<Array<{ id: string; message: string; type: ToastProps['type'] }>>([]);

  const showToast = (message: string, type: ToastProps['type'] = 'info') => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  const ToastContainer = () => (
    <div className='fixed top-4 right-4 z-[9999] space-y-2'>
      {toasts.map(toast => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );

  return { showToast, ToastContainer };
}