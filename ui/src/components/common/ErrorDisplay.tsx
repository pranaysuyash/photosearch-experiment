import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  WifiOff,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ErrorDisplayProps {
  error: Error | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  className = '',
}: ErrorDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isNetworkError = useMemo(() => {
    if (!error) return false;
    const networkErrorPatterns = [
      'network',
      'fetch',
      'connection',
      'timeout',
      'offline',
      'cors',
      'failed to fetch',
    ];
    const errorMessage = error.message.toLowerCase();
    return networkErrorPatterns.some((pattern) =>
      errorMessage.includes(pattern)
    );
  }, [error]);

  // isNetworkError is computed via useMemo to avoid synchronous setState in effects

  if (!error) return null;

  const getErrorType = () => {
    if (isNetworkError) return 'network';
    if (error.message.includes('timeout')) return 'timeout';
    if (error.message.includes('aborted')) return 'aborted';
    return 'general';
  };

  const getErrorConfig = () => {
    switch (getErrorType()) {
      case 'network':
        return {
          icon: WifiOff,
          title: 'Connection Error',
          message:
            'Unable to connect to the server. Please check your internet connection.',
          suggestion: 'Try refreshing the page or check your network settings.',
          color: 'destructive',
        };
      case 'timeout':
        return {
          icon: RefreshCw,
          title: 'Request Timeout',
          message: 'The request took too long to complete.',
          suggestion: 'Try again or check your connection speed.',
          color: 'warning',
        };
      case 'aborted':
        return {
          icon: X,
          title: 'Request Cancelled',
          message: 'The request was cancelled.',
          suggestion: 'This usually happens when you start a new search.',
          color: 'muted',
        };
      default:
        return {
          icon: AlertTriangle,
          title: 'Something went wrong',
          message: 'An unexpected error occurred.',
          suggestion:
            'Try refreshing the page or contact support if the problem persists.',
          color: 'destructive',
        };
    }
  };

  const config = getErrorConfig();
  const Icon = config.icon;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        className={`border rounded-lg p-4 ${className} ${
          config.color === 'destructive'
            ? 'border-destructive/50 bg-destructive/10 text-destructive'
            : config.color === 'warning'
            ? 'border-yellow-500/50 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300'
            : 'border-muted bg-muted/50 text-muted-foreground'
        }`}
      >
        <div className='flex items-start gap-3'>
          <Icon size={20} className='flex-shrink-0 mt-0.5' />
          <div className='flex-1 min-w-0'>
            <div className='flex items-center justify-between'>
              <h3 className='font-medium text-sm'>{config.title}</h3>
              <div className='flex items-center gap-2'>
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className='flex items-center gap-1 px-2 py-1 text-xs bg-primary/10 hover:bg-primary/20 rounded transition-colors'
                  >
                    <RefreshCw size={12} />
                    Retry
                  </button>
                )}
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className='p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors'
                  title={isExpanded ? 'Collapse details' : 'Expand details'}
                  aria-label={
                    isExpanded ? 'Collapse details' : 'Expand details'
                  }
                >
                  {isExpanded ? (
                    <ChevronUp size={14} />
                  ) : (
                    <ChevronDown size={14} />
                  )}
                </button>
                {onDismiss && (
                  <button
                    onClick={onDismiss}
                    className='p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors'
                    title='Dismiss error'
                    aria-label='Dismiss error'
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>

            <p className='text-sm mt-1'>{config.message}</p>
            <p className='text-xs mt-1 opacity-75'>{config.suggestion}</p>

            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className='mt-3 pt-3 border-t border-current/20'
                >
                  <details className='text-xs'>
                    <summary className='cursor-pointer font-medium mb-2'>
                      Technical Details
                    </summary>
                    <div className='bg-black/5 dark:bg-white/5 p-2 rounded font-mono text-xs break-all'>
                      {error.name}: {error.message}
                      {error.stack && (
                        <pre className='mt-2 whitespace-pre-wrap text-xs opacity-75'>
                          {error.stack}
                        </pre>
                      )}
                    </div>
                  </details>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
