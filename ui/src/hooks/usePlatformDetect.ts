import { useState, useEffect } from 'react';

/**
 * State representing the detected platform capabilities.
 */
interface PlatformState {
  /** True if running within the Tauri desktop application wrapper */
  isDesktopApp: boolean;
  /** True if the device is a mobile phone or tablet (based on screen width or user agent) */
  isMobile: boolean;
  /**
   * True if a physical notch matches the active platform.
   * Currently infers TRUE for all Desktop Apps (assuming macOS).
   * TODO: Integrate with useNotch() for precise geometric detection.
   */
  hasNotch: boolean;
}

/**
 * Hook to detect the current runtime environment (Tauri vs Browser) and device attributes.
 * Useful for adaptive layouts that need to switch between Floating/Notch/Mobile modes.
 */
export function usePlatformDetect(): PlatformState {
  const [state, setState] = useState<PlatformState>({
    isDesktopApp: false,
    isMobile: false,
    hasNotch: false,
  });

  useEffect(() => {
    // 1. Detect Tauri (Desktop App)
    // Tauri injects `__TAURI__` or similar into window, but standard check is:
    // @ts-ignore
    const isTauri = !!window.__TAURI__;

    // 2. Detect Mobile
    // Simple check for touch capability or width
    const isMobileDevice =
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent
      ) || window.innerWidth < 768;

    // 3. Detect Notch (Simplified initial check)
    // We can refine this if we have the useNotch hook's logic,
    // but typically "hasNotch" is true if it's a desktop app on macOS (we'll assume for now)
    // or if specific CSS environment variables are present.
    // For now, if it's the desktop app, we assume it *might* have a notch
    // until we get the specific `useNotch` data.
    // Ideally, this boolean should check actual notch existence.
    const hasNotchCandidate = isTauri;

    setState({
      isDesktopApp: isTauri,
      isMobile: isMobileDevice,
      hasNotch: hasNotchCandidate,
    });
  }, []);

  return state;
}
