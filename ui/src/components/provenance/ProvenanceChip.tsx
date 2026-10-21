/**
 * Provenance Chip — renders the registry-derived origin of a media file.
 *
 * The data comes from the server (`/attribution`), which joins the photo to
 * the source registry. Nothing here infers a source from a path: an
 * unattributed file is shown as unattributed.
 *
 * This replaces the earlier fabricated implementation, which derived
 * "Local/Cloud" from path substrings and hardcoded a source name. See
 * docs/decisions/2026-10-21-photo-source-attribution.md.
 */
import React from 'react';
import {
  HardDrive,
  Cloud,
  CircleHelp,
  AlertTriangle,
  ShieldCheck,
  Clock,
} from 'lucide-react';
import { glass } from '@/design/glass';
import { type PhotoAttribution } from '@/api';

interface ProvenanceChipProps {
  /** Registry-derived attribution. `undefined`/`null` renders the unknown state. */
  attribution?: PhotoAttribution | null;
  size?: 'sm' | 'md';
  /** Show the source's last-sync date when the registry has one. */
  showSync?: boolean;
}

const sizeClasses = {
  sm: 'text-xs px-2 py-1 gap-1',
  md: 'text-sm px-2.5 py-1.5 gap-1.5',
};

const iconSizes = {
  sm: 12,
  md: 14,
};

type ChipTone = {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  color: string;
  bg: string;
  border: string;
};

function toneFor(attribution?: PhotoAttribution | null): ChipTone {
  const kind = attribution?.kind;

  if (kind === 'cloud') {
    return {
      icon: Cloud,
      label: 'Cloud',
      color: 'text-green-400',
      bg: 'bg-green-500/10',
      border: 'border-green-500/20',
    };
  }
  if (kind === 'local') {
    return {
      icon: HardDrive,
      label: 'Local',
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
    };
  }
  return {
    icon: CircleHelp,
    label: 'Unattributed',
    color: 'text-muted-foreground',
    bg: 'bg-muted/10',
    border: 'border-border/40',
  };
}

function describe(attribution?: PhotoAttribution | null): string {
  if (!attribution) return 'Origin unknown: no attribution was returned for this file.';

  const name = attribution.source_name || attribution.source_type || 'unknown source';
  const parts: string[] = [`Origin: ${name}`];

  if (attribution.kind === 'unknown') {
    parts.push('This file is not attributed to any registered source.');
  } else {
    parts.push(`origin: ${attribution.kind}`);
    if (attribution.source_type) parts.push(`type: ${attribution.source_type}`);
    if (attribution.source_status) parts.push(`source status: ${attribution.source_status}`);
    if (attribution.item_status) parts.push(`item status: ${attribution.item_status}`);
  }
  parts.push(`resolved by: ${attribution.match}`);

  if (attribution.content) {
    parts.push(
      attribution.content.present
        ? 'A content-provenance manifest marker was detected, but nothing was verified.'
        : 'No content-provenance manifest marker was detected in the scanned region.'
    );
  }
  return parts.join(' · ');
}

export function ProvenanceChip({
  attribution,
  size = 'md',
  showSync = true,
}: ProvenanceChipProps) {
  const tone = toneFor(attribution);
  const Icon = tone.icon;
  const sourceName = attribution?.source_name;
  const hasError = attribution?.source_status === 'error';
  const lastSync = attribution?.last_sync_at;
  const manifestDetected = attribution?.content?.present === true;

  return (
    <div
      className={`${glass.surfaceStrong} ${tone.border} ${tone.bg} border rounded-full flex items-center ${sizeClasses[size]} w-fit max-w-full`}
      title={describe(attribution)}
      data-testid='provenance-chip'
      data-kind={attribution?.kind ?? 'unknown'}
    >
      <Icon size={iconSizes[size]} className={tone.color} />
      <span className={`font-medium ${tone.color}`}>{tone.label}</span>

      {sourceName && (
        <span className='text-muted-foreground truncate max-w-[16rem]'>
          ({sourceName})
        </span>
      )}

      {hasError && (
        <AlertTriangle
          size={iconSizes[size]}
          className='text-red-400'
          aria-label='Source has an error'
        />
      )}

      {manifestDetected && (
        <ShieldCheck
          size={iconSizes[size]}
          className='text-emerald-400'
          aria-label='Content-provenance manifest marker detected (not verified)'
        />
      )}

      {showSync && lastSync && (
        <span className='flex items-center gap-1 text-muted-foreground'>
          <Clock size={size === 'sm' ? 10 : 12} />
          <span className='text-xs'>
            {new Date(lastSync).toLocaleDateString()}
          </span>
        </span>
      )}
    </div>
  );
}

export default ProvenanceChip;
