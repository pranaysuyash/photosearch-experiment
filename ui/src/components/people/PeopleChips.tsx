/**
 * People Chips Component
 *
 * Displays people associated with a photo as clickable chips.
 */
import React, { useState, useEffect } from 'react';
import { User, X, Plus, Search } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface PeopleChipsProps {
  photoPath: string;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

interface FaceCluster {
  id: string;
  label?: string;
  face_count: number;
  image_count: number;
}

export function PeopleChips({ photoPath, size = 'md', showLabel = true }: PeopleChipsProps) {
  const [people, setPeople] = useState<FaceCluster[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [availablePeople, setAvailablePeople] = useState<FaceCluster[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [busy, setBusy] = useState(false);

  // Load people associated with this photo
  useEffect(() => {
    const loadPeople = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get people associated with this specific photo
        const peopleInPhoto = await api.getPeopleInPhoto(photoPath);

        // For each person, we need to fetch the cluster details
        const detailedPeople = await Promise.all(
          peopleInPhoto.map(async (personId: string) => {
            // In a full implementation, we would fetch individual cluster details
            // For now, we'll just return the personId as a cluster object
            return { id: personId, label: personId, face_count: 1, image_count: 1 };
          })
        );

        setPeople(detailedPeople);
      } catch (err) {
        console.error('Failed to load people for photo:', err);
        setError('Failed to load people');
      } finally {
        setLoading(false);
      }
    };

    if (photoPath) {
      loadPeople();
    }
  }, [photoPath]);

  // Load all available people for adding
  useEffect(() => {
    if (showAdd) {
      loadAvailablePeople();
    }
  }, [showAdd]);

  const loadAvailablePeople = async () => {
    try {
      const response = await api.get('/api/faces/clusters');
      const allClusters: FaceCluster[] = response.clusters || [];
      setAvailablePeople(allClusters.filter(cluster => cluster.label));
    } catch (err) {
      console.error('Failed to load available people:', err);
      setError('Failed to load available people');
    }
  };

  const handleRemovePerson = async (personId: string) => {
    setBusy(true);
    try {
      // Remove the association between person and photo
      await api.removePersonFromPhoto(photoPath, personId);
      setPeople(people.filter(p => p.id !== personId));
    } catch (err) {
      console.error('Failed to remove person:', err);
      setError('Failed to remove person');
    } finally {
      setBusy(false);
    }
  };

  const handleAddPerson = async (personId: string) => {
    setBusy(true);
    try {
      // Associate the person with the photo in the backend
      await api.addPersonToPhoto(photoPath, personId);
      const person = availablePeople.find(p => p.id === personId);
      if (person) {
        setPeople([...people, person]);
        setShowAdd(false);
      }
    } catch (err) {
      console.error('Failed to add person:', err);
      setError('Failed to add person');
    } finally {
      setBusy(false);
    }
  };

  const filteredAvailablePeople = availablePeople.filter(person => 
    !people.some(p => p.id === person.id) && 
    person.label?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const textSizeClass = size === 'sm' ? 'text-xs' : size === 'lg' ? 'text-lg' : 'text-sm';
  const paddingClass = size === 'sm' ? 'p-1' : size === 'lg' ? 'p-4' : 'p-2';

  return (
    <div className="w-full">
      {showLabel && (
        <div className={`flex items-center justify-between gap-2 mb-2`}>
          <div className={`uppercase tracking-wider text-white/60 flex items-center gap-2 ${textSizeClass}`}>
            <User size={size === 'sm' ? 12 : 14} />
            People
          </div>
          
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="btn-glass btn-glass--muted text-xs px-2 py-1 flex items-center gap-1"
          >
            <Plus size={12} />
            {showAdd ? 'Cancel' : 'Add'}
          </button>
        </div>
      )}

      {showAdd && (
        <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-3 mb-3`}>
          <div className="flex items-center gap-2 mb-2">
            <Search size={14} className="text-muted-foreground" />
            <input
              type="text"
              placeholder="Search people..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-transparent border border-white/10 rounded-lg px-2 py-1 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          
          {filteredAvailablePeople.length > 0 ? (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {filteredAvailablePeople.map(person => (
                <div key={person.id} className="flex items-center justify-between p-2 bg-white/5 rounded-lg">
                  <span className="text-sm">{person.label || `Person ${person.id.substring(0, 8)}`}</span>
                  <button
                    onClick={() => handleAddPerson(person.id)}
                    disabled={busy}
                    className="btn-glass btn-glass--primary text-xs px-2 py-1"
                  >
                    Add
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground text-center py-2">
              {searchTerm ? 'No people found' : 'No available people'}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className={`text-xs text-white/50 ${paddingClass}`}>Loading people...</div>
      ) : error ? (
        <div className={`text-xs text-destructive ${paddingClass}`}>{error}</div>
      ) : people.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {people.map(person => (
            <div
              key={person.id}
              className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1"
            >
              <span className={`text-xs text-white/85`}>
                {person.label || `Person ${person.id.substring(0, 8)}`}
              </span>
              <button
                className="btn-glass btn-glass--muted w-6 h-6 p-0 justify-center"
                title="Remove person"
                aria-label="Remove person"
                onClick={() => handleRemovePerson(person.id)}
              >
                <X size={10} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className={`text-xs text-white/50 italic ${paddingClass}`}>
          No people detected. Run face detection to identify people in this photo.
        </div>
      )}
    </div>
  );
}