import { useEffect, useState } from 'react';
import { LazyImage } from './LazyImage';
import { api } from '../../api';
import { contextAnalyzer } from '../../services/ContextAnalyzer';

interface SecureLazyImageProps {
  path: string;
  size?: number;
  className?: string;
  alt?: string;
  placeholder?: string;
  showBadge?: boolean;
  aspectRatio?: number;
  objectFit?: 'cover' | 'contain' | 'fill' | 'none' | 'scale-down';
}

export function SecureLazyImage({
  path,
  size,
  className,
  alt,
  placeholder,
  showBadge = true,
  aspectRatio,
  objectFit = 'cover',
}: SecureLazyImageProps) {
  const [src, setSrc] = useState<string>(() => api.getImageUrl(path, size));
  const [badge, setBadge] = useState<'local' | 'cloud' | 'hybrid'>('local');

  useEffect(() => {
    let mounted = true;

    async function resolve() {
      try {
        // Determine if file is cloud or local
        const fileLocation = contextAnalyzer.isLocalFile(path)
          ? 'local'
          : contextAnalyzer.isCloudFile(path)
            ? 'cloud'
            : 'hybrid';
        setBadge(fileLocation);

        // Ask server for config to know if signed URLs are enabled
        const cfg = await api.getServerConfig();
        const signedEnabled = cfg?.signed_url_enabled;

        // If signed URLs are enabled and the file is cloud or hybrid, request signed URL
        if (
          signedEnabled &&
          (fileLocation === 'cloud' || fileLocation === 'hybrid')
        ) {
          const signed = await api.getSignedImageUrl(path, size);
          if (mounted && signed) setSrc(signed);
        } else {
          // fallback to plain URL
          const url = api.getImageUrl(path, size);
          if (mounted) setSrc(url);
        }
      } catch {
        // on error, fallback to non-signed URL
        const url = api.getImageUrl(path, size);
        if (mounted) setSrc(url);
      }
    }

    resolve();
    return () => {
      mounted = false;
    };
  }, [path, size]);

  return (
    <div className='relative'>
      <LazyImage
        src={src}
        alt={alt || ''}
        placeholder={placeholder}
        className={className}
        aspectRatio={aspectRatio}
        objectFit={objectFit}
      />
      {showBadge && (
        <div
          aria-label={`File source: ${badge}`}
          title={`Source: ${badge}`}
          className='absolute left-2 bottom-2 bg-black/40 text-white text-xs px-2 py-0.5 rounded-md'
        >
          {badge === 'local' ? 'Local' : badge === 'cloud' ? 'Cloud' : 'Hybrid'}
        </div>
      )}
    </div>
  );
}

export default SecureLazyImage;
