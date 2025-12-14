/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useAmbientTheme } from '../hooks/useAmbientTheme';

type AmbientThemeContextValue = {
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
  const [baseAccentUrl, setBaseAccentUrl] = useState<string | null>(null);
  const overridesRef = useRef<Map<string, string>>(new Map());
  const [lastOverrideUrl, setLastOverrideUrl] = useState<string | null>(null);

  const effectiveAccentUrl = useMemo(() => {
    return lastOverrideUrl ?? baseAccentUrl;
  }, [baseAccentUrl, lastOverrideUrl]);

  useAmbientTheme(effectiveAccentUrl);

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
      setBaseAccentUrl,
      setOverrideAccentUrl,
      clearOverrideAccent,
    }),
    [setOverrideAccentUrl, clearOverrideAccent]
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
