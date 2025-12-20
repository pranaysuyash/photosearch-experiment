/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useAmbientTheme } from '../hooks/useAmbientTheme';

type AmbientThemeContextValue = {
  /** Whether the OS/browser currently prefers a dark color scheme. */
  isDark: boolean;
  setBaseAccentUrl: (url: string | null) => void;
  setOverrideAccentUrl: (key: string, url: string | null) => void;
  clearOverrideAccent: (key: string) => void;
};

const AmbientThemeContext = createContext<AmbientThemeContextValue | null>(
  null
);

function getLastOverrideUrl(overrides: Map<string, string>) {
  let last: string | null = null;
  for (const value of overrides.values()) last = value;
  return last;
}

export function AmbientThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isDark, setIsDark] = useState<boolean>(() => {
    if (
      typeof window === 'undefined' ||
      typeof window.matchMedia !== 'function'
    ) {
      return false;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  const [baseAccentUrl, setBaseAccentUrl] = useState<string | null>(null);
  const overridesRef = useRef<Map<string, string>>(new Map());
  const [lastOverrideUrl, setLastOverrideUrl] = useState<string | null>(null);

  const effectiveAccentUrl = useMemo(() => {
    return lastOverrideUrl ?? baseAccentUrl;
  }, [baseAccentUrl, lastOverrideUrl]);

  useAmbientTheme(effectiveAccentUrl);

  // Keep a simple signal available to components that want to tweak styling.
  useEffect(() => {
    if (
      typeof window === 'undefined' ||
      typeof window.matchMedia !== 'function'
    ) {
      return;
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setIsDark(media.matches);
    onChange();

    // Modern browsers
    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', onChange);
      return () => media.removeEventListener('change', onChange);
    }

    // Legacy Safari
    const legacy = media as unknown as {
      addListener: (cb: () => void) => void;
      removeListener: (cb: () => void) => void;
    };
    legacy.addListener(onChange);
    return () => legacy.removeListener(onChange);
  }, []);

  const setOverrideAccentUrl = useCallback(
    (key: string, url: string | null) => {
      const map = overridesRef.current;
      if (!url) {
        if (map.has(key)) {
          map.delete(key);
          setLastOverrideUrl(getLastOverrideUrl(map));
        }
        return;
      }

      map.delete(key);
      map.set(key, url);
      setLastOverrideUrl(getLastOverrideUrl(map));
    },
    []
  );

  const clearOverrideAccent = useCallback((key: string) => {
    const map = overridesRef.current;
    if (!map.has(key)) return;
    map.delete(key);
    setLastOverrideUrl(getLastOverrideUrl(map));
  }, []);

  const value = useMemo<AmbientThemeContextValue>(
    () => ({
      isDark,
      setBaseAccentUrl,
      setOverrideAccentUrl,
      clearOverrideAccent,
    }),
    [isDark, setOverrideAccentUrl, clearOverrideAccent]
  );

  return (
    <AmbientThemeContext.Provider value={value}>
      {children}
    </AmbientThemeContext.Provider>
  );
}

export function useAmbientThemeContext() {
  const ctx = useContext(AmbientThemeContext);
  if (!ctx) {
    throw new Error(
      'useAmbientThemeContext must be used within AmbientThemeProvider'
    );
  }
  return ctx;
}
