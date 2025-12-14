/**
 * Hook to detect and monitor safe viewport areas (notch, address bar, etc.)
 *
 * Priority:
 * 1. CSS environment variables (safe-area-inset-*) — Safari macOS/iOS, Chrome Android
 * 2. Browser UI detection — estimate insets from viewport changes & window.innerHeight
 * 3. Fallback — conservative defaults
 *
 * Works across all browsers: Safari, Chrome, Firefox, Edge
 */

import { useState, useEffect } from 'react';

export interface NotchInfo {
  hasNotch: boolean;
  topInset: number; // pixels
  rightInset: number;
  leftInset: number;
  bottomInset: number;
  method: 'env' | 'detected' | 'fallback'; // How we determined the values
}

export function useNotch(): NotchInfo {
  const [notchInfo, setNotchInfo] = useState<NotchInfo>({
    hasNotch: false,
    topInset: 0,
    rightInset: 0,
    leftInset: 0,
    bottomInset: 0,
    method: 'fallback',
  });

  useEffect(() => {
    const updateNotchInfo = () => {
      const root = document.documentElement;
      const style = getComputedStyle(root);

      // Method 1: Try CSS environment variables (most reliable)
      const envTopInset = parseInt(
        style.getPropertyValue('--safe-area-inset-top')?.trim() || '0'
      );
      const envRightInset = parseInt(
        style.getPropertyValue('--safe-area-inset-right')?.trim() || '0'
      );
      const envLeftInset = parseInt(
        style.getPropertyValue('--safe-area-inset-left')?.trim() || '0'
      );
      const envBottomInset = parseInt(
        style.getPropertyValue('--safe-area-inset-bottom')?.trim() || '0'
      );

      const hasEnvVars =
        envTopInset > 0 ||
        envRightInset > 0 ||
        envLeftInset > 0 ||
        envBottomInset > 0;

      if (hasEnvVars) {
        setNotchInfo({
          hasNotch: true,
          topInset: envTopInset,
          rightInset: envRightInset,
          leftInset: envLeftInset,
          bottomInset: envBottomInset,
          method: 'env',
        });
        return;
      }

      // Method 2: Browser UI detection (for browsers without env var support)
      // Estimate by comparing screen vs window dimensions
      const screenWidth = window.innerWidth;
      const screenHeight = window.innerHeight;
      const isCompactView = screenHeight < 600; // Small viewport (mobile/tablet)

      // Estimate top inset from typical browser chrome heights
      let detectedTopInset = 0;
      let detectedBottomInset = 0;

      if (isCompactView) {
        // Mobile: typical address bar height
        detectedTopInset =
          window.outerHeight - window.innerHeight > 0
            ? Math.round((window.outerHeight - window.innerHeight) / 2)
            : 44;
        detectedBottomInset = 0; // Usually no bottom chrome on mobile
      } else {
        // Desktop: smaller or no top chrome in fullscreen/windowed mode
        detectedTopInset = 0;
      }

      const hasPotentialSafeArea = detectedTopInset > 16 || screenWidth < 500;

      if (hasPotentialSafeArea) {
        setNotchInfo({
          hasNotch: true,
          topInset: detectedTopInset,
          rightInset: 0,
          leftInset: 0,
          bottomInset: detectedBottomInset,
          method: 'detected',
        });
        return;
      }

      // Method 3: Fallback — conservative defaults
      setNotchInfo({
        hasNotch: false,
        topInset: 0,
        rightInset: 0,
        leftInset: 0,
        bottomInset: 0,
        method: 'fallback',
      });
    };

    updateNotchInfo();
    window.addEventListener('resize', updateNotchInfo, { passive: true });
    window.addEventListener('orientationchange', updateNotchInfo, {
      passive: true,
    });
    window.addEventListener('fullscreenchange', updateNotchInfo, {
      passive: true,
    });

    return () => {
      window.removeEventListener('resize', updateNotchInfo);
      window.removeEventListener('orientationchange', updateNotchInfo);
      window.removeEventListener('fullscreenchange', updateNotchInfo);
    };
  }, []);

  return notchInfo;
}
