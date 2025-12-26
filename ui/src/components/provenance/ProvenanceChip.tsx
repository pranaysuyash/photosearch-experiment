/**
 * Provenance Chip Component
 *
 * Displays the source and availability status of a photo (Local/Cloud/Offline).
 */
import React from 'react';
import {
  HardDrive,
  Cloud,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader
} from 'lucide-react';
import { glass } from '../design/glass';

type ProvenanceStatus = 'local' | 'cloud' | 'offline' | 'syncing' | 'degraded';

interface ProvenanceChipProps {
  status: ProvenanceStatus;
  source?: string; // e.g., 'Local Drive', 'Google Drive', 'iCloud'
  lastSync?: string; // ISO date string
  size?: 'sm' | 'md' | 'lg';
}

const statusConfig = {
  local: {
    label: 'Local',
    icon: HardDrive,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20'
  },
  cloud: {
    label: 'Cloud',
    icon: Cloud,
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/20'
  },
  offline: {
    label: 'Offline',
    icon: WifiOff,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20'
  },
  syncing: {
    label: 'Syncing',
    icon: Loader,
    color: 'text-yellow-400',
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/20'
  },
  degraded: {
    label: 'Limited',
    icon: AlertTriangle,
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/20'
  }
};

export function ProvenanceChip({ status, source, lastSync, size = 'md' }: ProvenanceChipProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-2.5 py-1.5',
    lg: 'text-base px-3 py-2'
  };

  return (
    <div className={`${glass.surfaceStrong} ${config.border} ${config.bg} border rounded-full flex items-center gap-1.5 ${sizeClasses[size]}`}>
      <Icon size={size === 'sm' ? 12 : size === 'lg' ? 18 : 14} className={config.color} />
      <span className={`font-medium ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-sm' : 'text-sm'}`}>
        {config.label}
      </span>
      {source && (
        <span className={`text-muted-foreground ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-sm' : 'text-sm'}`}>
          ({source})
        </span>
      )}
      {status === 'syncing' && (
        <Loader size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} className="animate-spin text-yellow-400" />
      )}
      {lastSync && status !== 'syncing' && (
        <div className="flex items-center gap-1 text-muted-foreground">
          <Clock size={size === 'sm' ? 10 : size === 'lg' ? 12 : 10} />
          <span className={`text-xs ${size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-xs' : 'text-xs'}`}>
            {new Date(lastSync).toLocaleDateString()}
          </span>
        </div>
      )}
    </div>
  );
}
