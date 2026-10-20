import React, { useRef, useState, useCallback } from 'react';
import { motion, useMotionValue, useTransform } from 'framer-motion';
import type { PanInfo } from 'framer-motion';
import {
  Star,
  Trash2,
  Share,
  Edit3,
  ArrowRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown
} from 'lucide-react';

interface GestureActionsProps {
  onAction: (action: string) => void;
  children: React.ReactNode;
  disabled?: boolean;
}

interface GestureConfig {
  direction: 'up' | 'down' | 'left' | 'right';
  threshold: number;
  action: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  color: string;
  label: string;
}

const GESTURE_CONFIGS: GestureConfig[] = [
  {
    direction: 'right',
    threshold: 100,
    action: 'favorite',
    icon: Star,
    color: 'text-yellow-400',
    label: 'Add to favorites'
  },
  {
    direction: 'left',
    threshold: 100,
    action: 'delete',
    icon: Trash2,
    color: 'text-red-400',
    label: 'Move to trash'
  },
  {
    direction: 'up',
    threshold: 80,
    action: 'share',
    icon: Share,
    color: 'text-blue-400',
    label: 'Share photo'
  },
  {
    direction: 'down',
    threshold: 80,
    action: 'edit',
    icon: Edit3,
    color: 'text-green-400',
    label: 'Edit photo'
  }
];

export const GestureActions: React.FC<GestureActionsProps> = ({
  onAction,
  children,
  disabled = false
}) => {
  const [activeGesture, setActiveGesture] = useState<GestureConfig | null>(null);
  const [gestureProgress, setGestureProgress] = useState(0);
  const constraintsRef = useRef<HTMLDivElement>(null);

  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const opacity = useTransform([x, y], ([xVal, yVal]) => {
    const x = xVal as number;
    const y = yVal as number;
    const distance = Math.sqrt(x * x + y * y);
    return Math.min(distance / 50, 1);
  });

  const handlePan = useCallback((event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    if (disabled) return;

    const { offset } = info;
    const absX = Math.abs(offset.x);
    const absY = Math.abs(offset.y);

    // Determine primary direction
    let gesture: GestureConfig | null = null;
    let progress = 0;

    if (absX > absY) {
      // Horizontal gesture
      if (offset.x > 0) {
        gesture = GESTURE_CONFIGS.find(g => g.direction === 'right') || null;
        progress = Math.min(offset.x / (gesture?.threshold || 100), 1);
      } else {
        gesture = GESTURE_CONFIGS.find(g => g.direction === 'left') || null;
        progress = Math.min(Math.abs(offset.x) / (gesture?.threshold || 100), 1);
      }
    } else {
      // Vertical gesture
      if (offset.y < 0) {
        gesture = GESTURE_CONFIGS.find(g => g.direction === 'up') || null;
        progress = Math.min(Math.abs(offset.y) / (gesture?.threshold || 80), 1);
      } else {
        gesture = GESTURE_CONFIGS.find(g => g.direction === 'down') || null;
        progress = Math.min(offset.y / (gesture?.threshold || 80), 1);
      }
    }

    setActiveGesture(gesture);
    setGestureProgress(progress);
  }, [disabled]);

  const handlePanEnd = useCallback(() => {
    if (disabled) return;

    if (activeGesture && gestureProgress >= 1) {
      const isDelete = activeGesture.action === 'delete';
      if (!isDelete || window.confirm('Move this photo to trash?')) {
        onAction(activeGesture.action);
      }
    }

    setActiveGesture(null);
    setGestureProgress(0);
    x.set(0);
    y.set(0);
  }, [disabled, activeGesture, gestureProgress, onAction, x, y]);

  const getGestureIndicatorPosition = () => {
    if (!activeGesture) return {};

    switch (activeGesture.direction) {
      case 'right':
        return { right: '10px', top: '50%', transform: 'translateY(-50%)' };
      case 'left':
        return { left: '10px', top: '50%', transform: 'translateY(-50%)' };
      case 'up':
        return { top: '10px', left: '50%', transform: 'translateX(-50%)' };
      case 'down':
        return { bottom: '10px', left: '50%', transform: 'translateX(-50%)' };
      default:
        return {};
    }
  };

  const getDirectionArrow = () => {
    if (!activeGesture) return null;

    const arrows = {
      right: ArrowRight,
      left: ArrowLeft,
      up: ArrowUp,
      down: ArrowDown
    };

    return arrows[activeGesture.direction];
  };

  return (
    <div ref={constraintsRef} className="relative overflow-hidden">
      <motion.div
        drag
        dragConstraints={constraintsRef}
        dragElastic={0.1}
        onPan={handlePan}
        onPanEnd={handlePanEnd}
        style={{ x, y }}
        className="cursor-grab active:cursor-grabbing"
        whileTap={{ scale: 0.98 }}
      >
        {children}

        {/* Gesture indicator */}
        {activeGesture && (
          <motion.div
            className="absolute z-10 pointer-events-none"
            style={{
              ...getGestureIndicatorPosition(),
              opacity
            }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
          >
            <div className="glass-surface rounded-full p-3 flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${activeGesture.color} bg-current/20`}
                style={{
                  transform: `scale(${0.5 + gestureProgress * 0.5})`
                }}
              >
                <activeGesture.icon size={16} className={activeGesture.color} />
              </div>

              {/* Progress indicator */}
              <div className="w-16 h-1 bg-white/20 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-white/80 rounded-full"
                  style={{
                    width: `${gestureProgress * 100}%`
                  }}
                />
              </div>

              {/* Direction arrow */}
              {(() => {
                const Arrow = getDirectionArrow();
                return Arrow ? <Arrow size={14} className="text-white/60" /> : null;
              })()}
            </div>

            {/* Action label */}
            <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 whitespace-nowrap">
              <div className="glass-surface rounded px-2 py-1">
                <span className="text-xs text-white/80">{activeGesture.label}</span>
              </div>
            </div>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};
