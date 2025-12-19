/**
 * Location Clustering & Correction Component
 *
 * Provides UI for correcting location names and viewing location clusters.
 */
import React, { useState, useEffect } from 'react';
import { 
  MapPin, 
  Edit3, 
  Globe, 
  Users, 
  Building, 
  Flag, 
  Search,
  X,
  Check,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface LocationCluster {
  id: string;
  center_lat: number;
  center_lng: number;
  name: string;
  description: string;
  photo_count: number;
  min_lat: number;
  max_lat: number;
  min_lng: number;
  max_lng: number;
  created_at: string;
  updated_at: string;
}

interface PhotoLocation {
  photo_path: string;
  latitude: number;
  longitude: number;
  original_place_name: string | null;
  corrected_place_name: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  accuracy: number;  // GPS accuracy in meters
  created_at: string;
  updated_at: string;
}

interface LocationCorrectionProps {
  photoPath: string;
  initialLocation?: PhotoLocation;
  onLocationUpdate?: () => void;
}

export function LocationCorrection({ photoPath, initialLocation, onLocationUpdate }: LocationCorrectionProps) {
  const [location, setLocation] = useState<PhotoLocation | null>(initialLocation || null);
  const [correction, setCorrection] = useState({
    corrected_place_name: '',
    country: '',
    region: '',
    city: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (!location) {
      loadPhotoLocation();
    } else {
      setCorrection({
        corrected_place_name: location.corrected_place_name || '',
        country: location.country || '',
        region: location.region || '',
        city: location.city || ''
      });
    }
  }, [photoPath]);

  const loadPhotoLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const photoLocation = await api.getPhotoLocation(photoPath);
      setLocation(photoLocation);
      
      setCorrection({
        corrected_place_name: photoLocation.corrected_place_name || '',
        country: photoLocation.country || '',
        region: photoLocation.region || '',
        city: photoLocation.city || ''
      });
    } catch (err) {
      console.error('Failed to load photo location:', err);
      setError('Failed to load location data');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      await api.correctPhotoLocation(photoPath, {
        corrected_place_name: correction.corrected_place_name || null,
        country: correction.country || null,
        region: correction.region || null,
        city: correction.city || null
      });

      // Refresh location data
      const updatedLocation = await api.getPhotoLocation(photoPath);
      setLocation(updatedLocation);

      setEditing(false);

      if (onLocationUpdate) {
        onLocationUpdate();
      }
    } catch (err) {
      console.error('Failed to update location:', err);
      setError('Failed to update location');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-2">
          <MapPin size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Location</span>
        </div>
        <div className="text-xs text-muted-foreground">Loading location data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-2">
          <MapPin size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Location</span>
        </div>
        <div className="text-xs text-destructive">{error}</div>
      </div>
    );
  }

  if (!location) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center gap-2 mb-2">
          <MapPin size={16} className="text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">Location</span>
        </div>
        <div className="text-xs text-muted-foreground italic">No location data available</div>
      </div>
    );
  }

  return (
    <div className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden`}>
      <div className="flex items-center justify-between p-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <MapPin size={16} className="text-foreground" />
          <span className="text-sm font-medium text-foreground">Location</span>
        </div>
        
        {!editing ? (
          <button
            onClick={() => setEditing(true)}
            className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
          >
            <Edit3 size={12} />
            Edit
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEditing(false)}
              className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
            >
              <X size={12} />
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-glass btn-glass--primary text-xs px-2 py-1 flex items-center gap-1"
            >
              {saving ? (
                <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Check size={12} />
                  Save
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {editing ? (
        <div className="p-3 space-y-3">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Corrected Place Name</label>
            <input
              type="text"
              value={correction.corrected_place_name}
              onChange={(e) => setCorrection(prev => ({
                ...prev,
                corrected_place_name: e.target.value
              }))}
              placeholder={location.original_place_name || "e.g., Central Park, New York"}
              className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Country</label>
              <input
                type="text"
                value={correction.country}
                onChange={(e) => setCorrection(prev => ({ ...prev, country: e.target.value }))}
                placeholder={location.country || "e.g., United States"}
                className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Region</label>
              <input
                type="text"
                value={correction.region}
                onChange={(e) => setCorrection(prev => ({ ...prev, region: e.target.value }))}
                placeholder={location.region || "e.g., New York"}
                className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-xs text-muted-foreground mb-1">City</label>
            <input
              type="text"
              value={correction.city}
              onChange={(e) => setCorrection(prev => ({ ...prev, city: e.target.value }))}
              placeholder={location.city || "e.g., New York City"}
              className="w-full px-2 py-1.5 rounded border border-white/10 bg-white/5 text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          
          <div className="text-xs text-muted-foreground">
            <div className="flex items-center gap-1 mb-1">
              <Globe size={12} />
              Coordinates: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
            </div>
            <div className="flex items-center gap-1">
              <MapPin size={12} />
              Accuracy: {location.accuracy}m
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3 space-y-2">
          {location.corrected_place_name ? (
            <div className="flex items-start gap-2">
              <MapPin size={14} className="text-primary mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium text-foreground">{location.corrected_place_name}</div>
                <div className="text-xs text-muted-foreground">
                  {location.city && location.city}, {location.region && location.region}, {location.country}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <AlertCircle size={14} className="text-warning mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium text-warning">No location name</div>
                <div className="text-xs text-muted-foreground">
                  {location.original_place_name || 'No location name available'}
                </div>
              </div>
            </div>
          )}
          
          <div className="text-xs text-muted-foreground mt-2 pt-2 border-t border-white/5">
            <div className="flex items-center gap-1 mb-1">
              <Globe size={10} />
              <span>Coordinates: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPin size={10} />
              <span>Accuracy: {location.accuracy}m</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface LocationClusterListProps {
  limit?: number;
  offset?: number;
  onClusterSelect?: (cluster: LocationCluster) => void;
}

export function LocationClusterList({ 
  limit = 50, 
  offset = 0, 
  onClusterSelect 
}: LocationClusterListProps) {
  const [clusters, setClusters] = useState<LocationCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadLocationClusters();
  }, []);

  const loadLocationClusters = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const clusterData = await api.getLocationClusters(2); // minimum 2 photos per cluster
      setClusters(clusterData.clusters || []);
    } catch (err) {
      console.error('Failed to load location clusters:', err);
      setError('Failed to load location clusters');
    } finally {
      setLoading(false);
    }
  };

  const handleClusterSelect = (cluster: LocationCluster) => {
    if (onClusterSelect) {
      onClusterSelect(cluster);
    }
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="text-destructive flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      </div>
    );
  }

  const filteredClusters = clusters.filter(cluster => 
    cluster.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (cluster.description && cluster.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-foreground flex items-center gap-2">
          <MapPin size={18} />
          Photo Clusters by Location
        </h3>
        <div className="text-sm text-muted-foreground">
          {clusters.length} {clusters.length === 1 ? 'cluster' : 'clusters'}
        </div>
      </div>
      
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search clusters..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      
      {filteredClusters.length === 0 ? (
        <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-8 text-center`}>
          <MapPin size={48} className="mx-auto text-muted-foreground mb-4 opacity-50" />
          <h4 className="font-medium text-foreground mb-2">No Location Clusters</h4>
          <p className="text-sm text-muted-foreground">
            Group photos by location to create location-based clusters.
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredClusters.map(cluster => (
            <div 
              key={cluster.id} 
              onClick={() => handleClusterSelect && handleClusterSelect(cluster)}
              className={`p-4 rounded-xl border border-white/10 cursor-pointer hover:border-white/20 transition-colors ${
                onClusterSelect ? 'cursor-pointer' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-foreground">{cluster.name}</h4>
                <span className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                  {cluster.photo_count} photos
                </span>
              </div>
              
              {cluster.description && (
                <p className="text-sm text-muted-foreground mb-2 line-clamp-2">{cluster.description}</p>
              )}
              
              <div className="text-xs text-muted-foreground space-y-1">
                <div className="flex items-center gap-1">
                  <Globe size={10} />
                  <span>Center: {cluster.center_lat.toFixed(4)}, {cluster.center_lng.toFixed(4)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <MapPin size={10} />
                  <span>Bounded: {cluster.min_lat.toFixed(4)} to {cluster.max_lat.toFixed(4)} lat, {cluster.min_lng.toFixed(4)} to {cluster.max_lng.toFixed(4)} lng</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default LocationCorrection;