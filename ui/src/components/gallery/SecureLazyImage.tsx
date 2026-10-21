import { useEffect, useState } from 'react';
import { LazyImage } from './LazyImage';
import { api, type PhotoAttribution } from '../../api';
import { contextAnalyzer } from '../../services/ContextAnalyzer';

interface SecureLazyImageProps {
  path: string;
  size?: number;
  className?: string;
  alt?: string;
  placeholder?: string;
  showBadge?: boolean;
  aspectRatio?: number;
  /**
   * Registry-derived origin of the file. When present the badge reports the
   * real origin; when absent the badge falls back to where the file is
   * *read from* (on this device vs remote) — never to a path-substring guess
   * about provenance.
   */
  attribution?: PhotoAttribution | null;
}

type BadgeKind = 'local' | 'cloud' | 'remote' | null;

export function SecureLazyImage({
  path,
  size,
  className,
  alt,
  placeholder,
  showBadge = true,
  aspectRatio,
  attribution,
}: SecureLazyImageProps) {
  const [src, setSrc] = useState<string>(() => api.getImageUrl(path, size));
  const [location, setLocation] = useState<'local' | 'cloud' | 'unknown'>('local');

  useEffect(() => {
    let mounted = true;

    async function resolve() {
      try {
        // Where the file is read from (transport), not where it came from.
        const fileLocation = contextAnalyzer.isLocalFile(path)
          ? 'local'
          : contextAnalyzer.isCloudFile(path)
          ? 'cloud'
          : 'unknown';
        setLocation(fileLocation);

        // Ask server for config to know if signed URLs are enabled
        const cfg = await api.getServerConfig();
        const signedEnabled = cfg?.signed_url_enabled;

        // If signed URLs are enabled and the file is not on this device, request signed URL
        if (signedEnabled && fileLocation !== 'local') {
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

  // Prefer the registry-derived origin; fall back to the transport location
  // and say so, rather than implying provenance we cannot assert.
  const badgeKind: BadgeKind = attribution
    ? attribution.kind === 'cloud'
      ? 'cloud'
      : attribution.kind === 'local'
      ? 'local'
      : null
    : location === 'cloud'
    ? 'remote'
    : location === 'local'
    ? 'local'
    : null;

  const badgeLabel =
    badgeKind === 'cloud'
      ? 'Cloud'
      : badgeKind === 'remote'
      ? 'Remote'
      : badgeKind === 'local'
      ? 'Local'
      : null;

  const badgeTitle = attribution
    ? `Origin: ${attribution.source_name || attribution.source_type || 'unknown'}${
        attribution.kind === 'unknown' ? ' (not attributed to a registered source)' : ''
      }`
    : `Read from: ${badgeKind === 'remote' ? 'a remote location' : 'this device'}`;

  return (
    <div className='relative'>
      <LazyImage
        src={src}
        alt={alt || ''}
        placeholder={placeholder}
        className={className}
        aspectRatio={aspectRatio}
      />
      {showBadge && badgeLabel && (
        <div
          title={badgeTitle}
          className='absolute left-2 bottom-2 bg-black/40 text-white text-xs px-2 py-0.5 rounded-md'
        >
          {badgeLabel}
        </div>
      )}
    </div>
  );
}

export default SecureLazyImage;
