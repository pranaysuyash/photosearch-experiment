/**
 * Place Clustering Component
 *
 * Displays clusters of photos by location.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { MapPin, Globe, Users, Eye } from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface PlaceCluster {
  corrected_place_name: string;
  city: string;
  region: string;
  country: string;
  photo_count: number;
  avg_latitude: number;
  avg_longitude: number;
  min_latitude: number;
  max_latitude: number;
  min_longitude: number;
  max_longitude: number;
}

interface PlaceClusterProps {
  minPhotos?: number;
}

export function PlaceClustering({ minPhotos = 2 }: PlaceClusterProps) {
  const [clusters, setClusters] = useState<PlaceCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCluster, setActiveCluster] = useState<PlaceCluster | null>(null);

  // Load place clusters
  const loadClusters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const clusterData: PlaceCluster[] = await api.getPlaceClusters(minPhotos);
      setClusters(clusterData);
    } catch (err) {
      console.error('Failed to load place clusters:', err);
      setError('Failed to load place clusters');
    } finally {
      setLoading(false);
    }
  }, [minPhotos]);

  useEffect(() => {
    void loadClusters();
  }, [loadClusters]);

  const handleClusterClick = (cluster: PlaceCluster) => {
    setActiveCluster(cluster);
  };

  const viewCluster = (cluster: PlaceCluster) => {
    // In a real implementation, this would navigate to a map view or search
    // For now, we'll just log the action
    console.log('Viewing cluster:', cluster);
  };

  if (loading) {
    return (
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3`}>
        <div className="flex items-center gap-2 mb-2">
          <Globe size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Place Clusters</span>
        </div>
        <div className="text-xs text-muted-foreground">Loading place clusters...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3`}>
        <div className="flex items-center gap-2 mb-2">
          <Globe size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Place Clusters</span>
        </div>
        <div className="text-xs text-destructive">{error}</div>
      </div>
    );
  }

  return (
    <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 overflow-hidden`}>
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Place Clusters</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {clusters.length} {clusters.length === 1 ? 'cluster' : 'clusters'}
        </div>
      </div>

      {clusters.length === 0 ? (
        <div className="p-3 text-center">
          <Globe size={24} className="mx-auto text-muted-foreground mb-2" />
          <div className="text-sm text-muted-foreground">No place clusters found</div>
          <div className="text-xs text-muted-foreground">Photos need to be geotagged to form clusters</div>
        </div>
      ) : (
        <div className="p-3 space-y-3 max-h-80 overflow-y-auto">
          {clusters.map((cluster, index) => (
            <div
              key={index}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                activeCluster?.avg_latitude === cluster.avg_latitude &&
                activeCluster?.avg_longitude === cluster.avg_longitude
                  ? 'border-primary bg-primary/10'
                  : 'border-white/10 hover:border-white/20'
              }`}
              onClick={() => handleClusterClick(cluster)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <MapPin size={14} className="text-muted-foreground flex-shrink-0" />
                    <div className="font-medium text-foreground truncate">
                      {cluster.corrected_place_name || cluster.city || 'Unknown Location'}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 ml-6">
                    {cluster.city && cluster.city}, {cluster.region && cluster.region}, {cluster.country}
                  </div>
                  <div className="flex items-center gap-3 mt-2 ml-6">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Users size={10} />
                      {cluster.photo_count} {cluster.photo_count === 1 ? 'photo' : 'photos'}
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    viewCluster(cluster);
                  }}
                  className="btn-glass btn-glass--primary text-xs px-2 py-1 flex items-center gap-1"
                  title="View cluster on map"
                >
                  <Eye size={12} />
                  View
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeCluster && (
        <div className="p-3 border-t border-white/10 bg-white/5">
          <div className="text-xs text-muted-foreground mb-1">Active Cluster</div>
          <div className="text-sm font-medium text-foreground truncate">
            {activeCluster.corrected_place_name || activeCluster.city}
          </div>
          <div className="text-xs text-muted-foreground">
            {activeCluster.photo_count} photos
          </div>
        </div>
      )}
    </div>
  );
}
