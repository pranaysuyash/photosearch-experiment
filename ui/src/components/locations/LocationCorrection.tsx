/**
 * Location Correction Component
 *
 * Allows users to correct and enhance location information for photos.
 */
import React, { useState, useEffect } from 'react';
import {
  MapPin,
  Edit3,
  Globe,
  Building2,
  Search,
  Check,
  X,
  Clock,
  Locate,
  AlertCircle
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface LocationData {
  photo_path: string;
  latitude: number;
  longitude: number;
  original_place_name: string | null;
  corrected_place_name: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  accuracy: number; // GPS accuracy in meters
  created_at: string;
  updated_at: string;
}

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

interface LocationCorrectionProps {
  photoPath: string;
  initialLocation?: LocationData;
  onLocationUpdate?: () => void;
}

export function LocationCorrection({ 
  photoPath, 
  initialLocation, 
  onLocationUpdate 
}: LocationCorrectionProps) {
  const [location, setLocation] = useState<LocationData | null>(initialLocation || null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [newLocation, setNewLocation] = useState({
    corrected_place_name: '',
    country: '',
    region: '',
    city: ''
  });

  // Load location data for the photo
  useEffect(() => {
    loadLocation();
  }, [photoPath]);

  const loadLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const locationData = await api.getPhotoLocation(photoPath);
      setLocation(locationData);
      
      if (locationData) {
        setNewLocation({
          corrected_place_name: locationData.corrected_place_name || locationData.original_place_name || '',
          country: locationData.country || '',
          region: locationData.region || '',
          city: locationData.city || ''
        });
      }
    } catch (err) {
      console.error('Failed to load location data:', err);
      setError('Failed to load location data');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!location) return;

    setSaving(true);
    setError(null);

    try {
      await api.updatePhotoLocation(photoPath, {
        corrected_place_name: newLocation.corrected_place_name || null,
        country: newLocation.country || null,
        region: newLocation.region || null,
        city: newLocation.city || null
      });

      // Refresh location data
      await loadLocation();
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

  const handleCancel = () => {
    // Reset to initial values
    if (location) {
      setNewLocation({
        corrected_place_name: location.corrected_place_name || location.original_place_name || '',
        country: location.country || '',
        region: location.region || '',
        city: location.city || ''
      });
    }
    setEditing(false);
  };

  const handleEditClick = () => {
    setEditing(true);
  };

  const searchLocations = async (query: string) => {
    if (query.length < 3) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    try {
      const results = await api.searchLocations(query);
      setSuggestions(results.slice(0, 8).map((r: any) => r.name)); // Get top 8 suggestions
      setShowSuggestions(true);
    } catch (err) {
      console.error('Failed to search locations:', err);
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  const handleLocationSearch = (value: string) => {
    setNewLocation(prev => ({ ...prev, corrected_place_name: value }));
    searchLocations(value);
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="flex items-center justify-center h-24">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
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
            onClick={handleEditClick}
            className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
          >
            <Edit3 size={12} />
            Edit
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              disabled={saving}
              className="btn-glass btn-glass--muted text-xs px-2 py-1"
            >
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
      
      <div className="p-4">
        {error && (
          <div className="mb-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
            {error}
            <button 
              className="ml-2" 
              onClick={() => setError(null)}
            >
              <X size={14} />
            </button>
          </div>
        )}
        
        {location ? (
          <div>
            {editing ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">Corrected Place Name</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={newLocation.corrected_place_name}
                      onChange={(e) => handleLocationSearch(e.target.value)}
                      placeholder={location.original_place_name || "e.g., Central Park, New York"}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    
                    {showSuggestions && suggestions.length > 0 && (
                      <div className={`${glass.surfaceStrong} absolute z-10 mt-1 w-full border border-white/10 rounded-lg shadow-lg max-h-40 overflow-y-auto`}>
                        {suggestions.map((suggestion, index) => (
                          <button
                            key={index}
                            onClick={() => {
                              setNewLocation(prev => ({ ...prev, corrected_place_name: suggestion }));
                              setShowSuggestions(false);
                            }}
                            className="w-full text-left px-3 py-2 hover:bg-white/5 text-foreground truncate"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">Country</label>
                    <input
                      type="text"
                      value={newLocation.country}
                      onChange={(e) => setNewLocation(prev => ({ ...prev, country: e.target.value }))}
                      placeholder={location.country || "e.g., United States"}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">Region/State</label>
                    <input
                      type="text"
                      value={newLocation.region}
                      onChange={(e) => setNewLocation(prev => ({ ...prev, region: e.target.value }))}
                      placeholder={location.region || "e.g., New York"}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-xs font-medium text-foreground mb-1">City</label>
                  <input
                    type="text"
                    value={newLocation.city}
                    onChange={(e) => setNewLocation(prev => ({ ...prev, city: e.target.value }))}
                    placeholder={location.city || "e.g., New York City"}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                
                <div className="text-xs text-muted-foreground mt-2 p-3 rounded-lg bg-white/5">
                  <div className="flex items-center gap-2 mb-1">
                    <Locate size={14} />
                    <span>Coordinates: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin size={14} />
                    <span>Accuracy: {location.accuracy}m</span>
                  </div>
                  {location.original_place_name && (
                    <div className="flex items-center gap-2 mt-1">
                      <Globe size={14} />
                      <span>Originally: {location.original_place_name}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {location.corrected_place_name || location.original_place_name ? (
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5"> {/* Align with text baseline */}
                      {location.corrected_place_name ? <Check className="text-green-400" size={16} /> : <AlertCircle className="text-warning" size={16} />}
                    </div>
                    <div>
                      <div className="font-medium text-foreground text-sm">
                        {location.corrected_place_name || location.original_place_name}
                      </div>
                      {location.city || location.region || location.country ? (
                        <div className="text-sm text-muted-foreground">
                          {location.city && `${location.city}, `}
                          {location.region && `${location.region}, `}
                          {location.country}
                        </div>
                      ) : (
                        <div className="text-xs text-muted-foreground italic">
                          Location information available but not enhanced
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <MapPin size={24} className="mx-auto text-muted-foreground mb-2 opacity-50" />
                    <p className="text-sm text-muted-foreground">No location information available</p>
                  </div>
                )}
                
                {location.latitude && location.longitude && (
                  <div className="text-xs text-muted-foreground p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2 mb-1">
                      <Locate size={12} />
                      <span>Coordinates: {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin size={12} />
                      <span>GPS Accuracy: {location.accuracy.toFixed(0)}m</span>
                    </div>
                    {location.original_place_name && (
                      <div className="flex items-center gap-2 mt-1">
                        <Globe size={12} />
                        <span>Original GPS name: {location.original_place_name}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-4">
            <MapPin size={24} className="mx-auto text-muted-foreground mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">No location data for this photo</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Location Clustering Component
export function LocationClustering({ 
  minPhotos = 2,
  onClusterSelect 
}: { 
  minPhotos?: number; 
  onClusterSelect?: (cluster: LocationCluster) => void;
}) {
  const [clusters, setClusters] = useState<LocationCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLocationClusters();
  }, []);

  const loadLocationClusters = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const clusterData = await api.getLocationClusters(minPhotos);
      setClusters(clusterData.clusters || []);
    } catch (err) {
      console.error('Failed to load location clusters:', err);
      setError('Failed to load location clusters');
    } finally {
      setLoading(false);
    }
  };

  const handleClusterClick = (cluster: LocationCluster) => {
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
        <div className="text-destructive">{error}</div>
      </div>
    );
  }

  if (clusters.length === 0) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-4`}>
        <div className="text-center py-8">
          <MapPin size={48} className="mx-auto text-muted-foreground mb-4 opacity-50" />
          <h3 className="font-medium text-foreground mb-2">No Location Clusters</h3>
          <p className="text-sm text-muted-foreground">
            Photos need to be grouped in similar locations to form clusters
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-foreground flex items-center gap-2">
          <MapPin size={16} />
          Photo Clusters by Location
        </h3>
        <span className="text-xs text-muted-foreground">{clusters.length} clusters</span>
      </div>
      
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {clusters.map(cluster => (
          <div 
            key={cluster.id} 
            onClick={() => handleClusterSelect && handleClusterSelect(cluster)}
            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
              onClusterSelect ? 'hover:border-white/20 hover:bg-white/5' : 'border-white/10'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <h4 className="font-medium text-foreground">{cluster.name}</h4>
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                {cluster.photo_count} photos
              </span>
            </div>
            
            {cluster.description && (
              <p className="text-sm text-muted-foreground mb-2 line-clamp-1">{cluster.description}</p>
            )}
            
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Locate size={12} />
                <span>
                  {cluster.center_lat.toFixed(4)}, {cluster.center_lng.toFixed(4)}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <MapPin size={12} />
                <span>
                  {Math.abs(cluster.max_lat - cluster.min_lat).toFixed(4)}° × {Math.abs(cluster.max_lng - cluster.min_lng).toFixed(4)}°
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default LocationCorrection;