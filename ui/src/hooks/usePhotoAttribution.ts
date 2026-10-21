import { useEffect, useState } from 'react';
import { api, type Photo, type PhotoAttribution } from '@/api';

/**
 * Resolve the registry-derived origin of a photo.
 *
 * List surfaces (`/browse`, `/search`) already carry `photo.attribution`, so
 * the common path is free. Surfaces that do not yet decorate their payloads
 * fall back to a single `/attribution` request.
 *
 * Effect discipline (skills/react-effect-discipline): the repo has no
 * data-fetching library, so this is the "must fetch in an effect" case — it
 * carries cleanup, never calls setState synchronously inside the effect
 * body, and derives `loading` from the result instead of a second state
 * variable.
 */
export function usePhotoAttribution(
  photo: Pick<Photo, 'path' | 'attribution'> | null | undefined
): { attribution: PhotoAttribution | null; loading: boolean } {
  const inline = photo?.attribution ?? null;
  const path = photo?.path;
  const [result, setResult] = useState<{
    path: string;
    attribution: PhotoAttribution | null;
  } | null>(null);

  useEffect(() => {
    if (inline || !path) return;
    let cancelled = false;
    api
      .getAttribution(path)
      .then((attribution) => {
        if (!cancelled) setResult({ path, attribution });
      })
      .catch(() => {
        if (!cancelled) setResult({ path, attribution: null });
      });
    return () => {
      cancelled = true;
    };
  }, [path, inline]);

  const resolved =
    inline ?? (result && result.path === path ? result.attribution : null);
  const loading = !inline && !!path && (!result || result.path !== path);

  return { attribution: resolved, loading };
}

export default usePhotoAttribution;
