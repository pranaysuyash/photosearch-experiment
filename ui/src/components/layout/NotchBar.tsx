/**
 * NotchBar Component
 *
 * Renders a condensed control bar at the top of the viewport, respecting:
 * 1. MacBook Pro notch (Safari macOS) via safe-area-inset-top
 * 2. iPhone/iPad safe areas (iOS Safari, Chrome)
 * 3. Browser address bars & toolbars (all browsers)
 * 4. Regular window chrome (Firefox, Edge, etc.)
 *
 * Automatically adapts padding & positioning to browser/device capabilities.
 */

import React, { type ReactNode } from 'react';
import { useNotch } from '../../hooks/useNotch';
import { motion } from 'framer-motion';

interface NotchBarProps {
  children?: ReactNode;
  className?: string;
  show?: boolean;
  compact?: boolean; // Reduce height for tight spaces
}

export function NotchBar({
  children,
  className = '',
  show = true,
  compact = false,
}: NotchBarProps) {
  const { topInset, leftInset, rightInset, method } = useNotch();

  if (!show) return null;

  // Determine height based on compact mode and detection method
  const baseHeight = compact ? 'h-10' : 'h-12';
  const barHeight = compact ? 40 : 48;

  // Use max() to respect both CSS env vars and JS-detected insets
  const paddingTop = topInset > 0 ? `${topInset}px` : '0';
  const paddingLeft = leftInset > 0 ? `${leftInset}px` : '1rem';
  const paddingRight = rightInset > 0 ? `${rightInset}px` : '1rem';

  // Show a subtle indicator of which detection method is active (dev only)
  const methodIndicator = import.meta.env.DEV
    ? ({ '--notch-method': method } as React.CSSProperties)
    : {};

  return (
    <motion.div
      className={`fixed top-0 left-0 right-0 z-[1200] glass-surface border-b border-white/5 ${className}`}
      style={{
        paddingTop,
        paddingLeft,
        paddingRight,
        minHeight: `${barHeight}px`,
        ...methodIndicator,
      }}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      <div className={`flex items-center justify-between ${baseHeight}`}>
        {children}
      </div>
    </motion.div>
  );
}

/**
 * Hook for consuming components to know if they should use NotchBar
 * or adjust their layout for safe areas
 */
// Note: helper hook moved to a dedicated file to keep fast-refresh happy
