import { useEffect } from 'react';

type RGB = { r: number; g: number; b: number };

const DEFAULT_ACCENT: RGB = { r: 59, g: 130, b: 246 };

function clampByte(n: number) {
  return Math.max(0, Math.min(255, Math.round(n)));
}

function setAccent(rgb: RGB) {
  const root = document.documentElement;
  root.style.setProperty('--lm-accent-rgb', `${rgb.r} ${rgb.g} ${rgb.b}`);
}

async function averageColorFromImageUrl(url: string): Promise<RGB> {
  return await new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = 'async';
    
    // For cross-origin requests, always use CORS mode
    if (url.includes('localhost:8000') || url.includes('127.0.0.1:8000')) {
      img.crossOrigin = 'anonymous';
    }
    
    img.src = url;

    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) throw new Error('No canvas context');

        const w = 24;
        const h = 24;
        canvas.width = w;
        canvas.height = h;
        ctx.drawImage(img, 0, 0, w, h);

        const data = ctx.getImageData(0, 0, w, h).data;
        let r = 0;
        let g = 0;
        let b = 0;
        let count = 0;

        for (let i = 0; i < data.length; i += 4) {
          const a = data[i + 3];
          if (a < 16) continue;
          r += data[i];
          g += data[i + 1];
          b += data[i + 2];
          count += 1;
        }

        if (count === 0) return resolve(DEFAULT_ACCENT);
        resolve({
          r: clampByte(r / count),
          g: clampByte(g / count),
          b: clampByte(b / count),
        });
      } catch (e) {
        // If canvas access fails, fall back to default accent
        console.warn('Canvas access failed for ambient theme, using default accent:', e);
        resolve(DEFAULT_ACCENT);
      }
    };

    img.onerror = () => {
      console.warn('Failed to load image for ambient theme, using default accent');
      resolve(DEFAULT_ACCENT);
    };
  });
}

export function useAmbientTheme(accentImageUrl: string | null | undefined) {
  useEffect(() => {
    let cancelled = false;

    if (!accentImageUrl) {
      setAccent(DEFAULT_ACCENT);
      return;
    }

    averageColorFromImageUrl(accentImageUrl)
      .then((rgb) => {
        if (cancelled) return;
        setAccent(rgb);
      })
      .catch(() => {
        if (cancelled) return;
        setAccent(DEFAULT_ACCENT);
      });

    return () => {
      cancelled = true;
    };
  }, [accentImageUrl]);
}

