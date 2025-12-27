/**
 * Provenance Chips Component
 *
 * Displays source and availability status for photos (Local/Cloud/Offline).
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  HardDrive,
  Cloud,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle,
  Clock,
  Globe,
  MapPin
} from 'lucide-react';
import { glass } from '../design/glass';

interface SourceInfo {
  id: string;
  name: string;
  type: 'local' | 'cloud' | 'network' | 'external';
  status: 'online' | 'offline' | 'syncing' | 'degraded';
  last_sync?: string;
  location?: string;
  is_available: boolean;
  sync_progress?: number; // 0-100 for syncing status
}

interface ProvenanceData {
  source: SourceInfo;
  availability: 'local' | 'cached' | 'cloud_only' | 'offline';
  sync_status: 'up_to_date' | 'syncing' | 'out_of_sync' | 'error';
  last_accessed?: string;
  file_size?: number;
  location_accuracy?: 'precise' | 'approximate' | 'none';
}

interface ProvenanceChipsProps {
  photoPath: string;
  size?: 'sm' | 'md' | 'lg';
  showSource?: boolean;
  showAvailability?: boolean;
  showSyncStatus?: boolean;
}

export function ProvenanceChips({
  photoPath,
  size = 'md',
  showSource = true,
  showAvailability = true,
  showSyncStatus = true
}: ProvenanceChipsProps) {
  const [provenance, setProvenance] = useState<ProvenanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProvenanceData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // In a real implementation, this would fetch from the API
      // For now, derive from photo path
      const isCloudPath = photoPath.startsWith('http://') ||
                         photoPath.startsWith('https://') ||
                         photoPath.startsWith('s3://') ||
                         photoPath.includes('cloud') ||
                         photoPath.includes('drive');

      const isNetworkPath = photoPath.startsWith('//') ||
                           photoPath.includes('network') ||
                           photoPath.includes('nas');

      const sourceType: 'local' | 'cloud' | 'network' | 'external' = isCloudPath
        ? 'cloud' : isNetworkPath ? 'network' : 'local';

      const status: 'online' | 'offline' | 'syncing' | 'degraded' =
        sourceType === 'cloud' ? 'online' : 'online';

      const availability: 'local' | 'cached' | 'cloud_only' | 'offline' = isCloudPath
        ? 'cloud_only' : 'local';

      const syncStatus: 'up_to_date' | 'syncing' | 'out_of_sync' | 'error' =
        isCloudPath ? 'up_to_date' : 'up_to_date';

      const mockSource: SourceInfo = {
        id: sourceType,
        name: sourceType === 'cloud' ? 'Cloud Storage' :
              sourceType === 'network' ? 'Network Drive' : 'Local Device',
        type: sourceType,
        status,
        is_available: true,
        last_sync: new Date().toISOString()
      };

      const mockProvenance: ProvenanceData = {
        source: mockSource,
        availability,
        sync_status: syncStatus,
        last_accessed: new Date().toISOString(),
        file_size: 2457600 // 2.4MB
      };

      setProvenance(mockProvenance);
    } catch (err) {
      console.error('Failed to load provenance data:', err);
      setError('Failed to load source information');
    } finally {
      setLoading(false);
    }
  }, [photoPath]);

  useEffect(() => {
    loadProvenanceData();
  }, [loadProvenanceData]);

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-lg px-2 py-1 inline-flex items-center gap-1.5`}>
        <div className="w-3 h-3 border border-primary/30 border-t-primary rounded-full animate-spin" />
        <span className="text-xs text-muted-foreground">Loading...</span>
      </div>
    );
  }

  if (error || !provenance) {
    return (
      <div className={`${glass.surface} rounded-lg px-2 py-1 inline-flex items-center gap-1.5`}>
        <AlertTriangle size={12} className="text-destructive" />
        <span className="text-xs text-destructive">Source data unavailable</span>
      </div>
    );
  }

  const { source, availability, sync_status } = provenance;

  const sizePadding = {
    sm: 'gap-1',
    md: 'gap-1.5',
    lg: 'gap-2'
  };

  const getSourceIcon = () => {
    switch (source.type) {
      case 'cloud':
        return <Cloud size={size === 'sm' ? 12 : size === 'lg' ? 16 : 14} />;
      case 'network':
        return <Wifi size={size === 'sm' ? 12 : size === 'lg' ? 16 : 14} />;
      case 'external':
        return <Globe size={size === 'sm' ? 12 : size === 'lg' ? 16 : 14} />;
      default:
        return <HardDrive size={size === 'sm' ? 12 : size === 'lg' ? 16 : 14} />;
    }
  };

  const getSourceColor = () => {
    if (source.status === 'offline') return 'text-destructive';
    if (source.status === 'syncing') return 'text-warning';
    if (source.status === 'degraded') return 'text-yellow-400';
    return 'text-primary';
  };

  const getAvailabilityIcon = () => {
    switch (availability) {
      case 'local':
        return <HardDrive size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />;
      case 'cached':
        return <Clock size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />;
      case 'cloud_only':
        return <Cloud size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />;
      case 'offline':
        return <WifiOff size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />;
      default:
        return <HardDrive size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />;
    }
  };

  const getAvailabilityColor = () => {
    if (availability === 'offline') return 'text-destructive';
    if (availability === 'cloud_only') return 'text-blue-400';
    if (availability === 'cached') return 'text-warning';
    return 'text-success';
  };

  return (
    <div className={`flex flex-wrap gap-1.5 ${sizePadding[size]}`}>
      {showSource && (
        <div className={`${glass.surfaceStrong} rounded-full px-2 py-1 flex items-center gap-1.5 ${getSourceColor()}`}>
          {getSourceIcon()}
          <span className="font-medium capitalize">{source.type}</span>
        </div>
      )}

      {showAvailability && (
        <div className={`${glass.surfaceStrong} rounded-full px-2 py-1 flex items-center gap-1.5 ${getAvailabilityColor()}`}>
          {getAvailabilityIcon()}
          <span className="capitalize">{availability.replace('_', ' ')}</span>
        </div>
      )}

      {showSyncStatus && (
        <div className={`${glass.surfaceStrong} rounded-full px-2 py-1 flex items-center gap-1.5 ${
          sync_status === 'error' ? 'text-destructive' :
          sync_status === 'out_of_sync' ? 'text-warning' :
          sync_status === 'syncing' ? 'text-primary' : 'text-success'
        }`}>
          {sync_status === 'syncing' && (
            <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
          )}
          {sync_status === 'up_to_date' && <CheckCircle size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />}
          {sync_status === 'error' && <AlertTriangle size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />}
          <span className="capitalize">{sync_status.replace('_', ' ')}</span>
        </div>
      )}

      {source.location && (
        <div className={`${glass.surfaceStrong} rounded-full px-2 py-1 flex items-center gap-1.5 text-muted-foreground`}>
          <MapPin size={size === 'sm' ? 10 : size === 'lg' ? 14 : 12} />
          <span>{source.location}</span>
        </div>
      )}
    </div>
  );
}

export default ProvenanceChips;
