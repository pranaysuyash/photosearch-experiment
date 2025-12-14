import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  message?: string;
  className?: string;
}

export function LoadingSpinner({
  size = 'md',
  message,
  className = '',
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 ${className}`}
    >
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        className='flex items-center justify-center'
      >
        <Loader2 className={`${sizeClasses[size]} text-primary`} />
      </motion.div>
      {message && (
        <p className='text-sm text-muted-foreground text-center'>{message}</p>
      )}
    </div>
  );
}
