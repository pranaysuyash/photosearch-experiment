/**
 * Boolean People Search Component
 *
 * Advanced search interface for finding photos with specific people combinations.
 * Supports AND, OR, and NOT operations for sophisticated queries.
 * Uses the glass design system and follows living language guidelines.
 */
import { useState, useEffect } from 'react';
import { Search, Plus, X, User, Camera, RefreshCw } from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface Person {
  id: string;
  label: string;
  face_count: number;
  image_count: number;
}

interface SearchQuery {
  includePeople: string[];
  excludePeople: string[];
  operator: 'AND' | 'OR';
}

interface SearchResult {
  photo_path: string;
  people_in_photo: string[];
  match_reason: string;
}

interface ClusterListItem {
  id?: string;
  cluster_id?: string;
  label?: string;
  face_count?: number;
  image_count?: number;
  photo_count?: number;
}

interface BooleanPeopleSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export function BooleanPeopleSearch({ isOpen, onClose }: BooleanPeopleSearchProps) {
  const [people, setPeople] = useState<Person[]>([]);
  const [query, setQuery] = useState<SearchQuery>({
    includePeople: [],
    excludePeople: [],
    operator: 'AND'
  });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchPeople();
    }
  }, [isOpen]);

  const fetchPeople = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.getFaceClusters();
      const clusters = response.clusters || [];

      // Convert clusters to people format
      const peopleList: Person[] = (clusters as ClusterListItem[])
        .filter((cluster) => cluster.label) // Only include named people
        .map((cluster) => ({
          id: cluster.id ?? cluster.cluster_id ?? '',
          label: cluster.label || 'Unknown',
          face_count: cluster.face_count || 0,
          image_count: cluster.image_count || cluster.photo_count || 0
        }));

      setPeople(peopleList.filter((person) => person.id));
    } catch (err) {
      console.error('Failed to fetch people:', err);
      setError('Failed to load people');
    } finally {
      setLoading(false);
    }
  };

  const addPersonToInclude = (personId: string) => {
    if (!query.includePeople.includes(personId) && !query.excludePeople.includes(personId)) {
      setQuery({
        ...query,
        includePeople: [...query.includePeople, personId]
      });
    }
  };

  const addPersonToExclude = (personId: string) => {
    if (!query.excludePeople.includes(personId) && !query.includePeople.includes(personId)) {
      setQuery({
        ...query,
        excludePeople: [...query.excludePeople, personId]
      });
    }
  };

  const removePersonFromInclude = (personId: string) => {
    setQuery({
      ...query,
      includePeople: query.includePeople.filter(id => id !== personId)
    });
  };

  const removePersonFromExclude = (personId: string) => {
    setQuery({
      ...query,
      excludePeople: query.excludePeople.filter(id => id !== personId)
    });
  };

  const executeSearch = async () => {
    if (query.includePeople.length === 0) {
      setError('Please select at least one person to include');
      return;
    }

    try {
      setSearching(true);
      setError(null);
      setResults([]);

      const response = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/photos/by-people`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            include_people: query.includePeople,
            exclude_people: query.excludePeople,
            operator: query.operator.toLowerCase()
          })
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Search failed');
      }

      const data = await response.json();
      setResults(data.photos || []);

    } catch (err: unknown) {
      console.error('Search failed:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const clearQuery = () => {
    setQuery({
      includePeople: [],
      excludePeople: [],
      operator: 'AND'
    });
    setResults([]);
    setError(null);
  };

  const getPersonName = (personId: string) => {
    const person = people.find(p => p.id === personId);
    return person?.label || `Person ${personId}`;
  };

  const filteredPeople = people.filter(person =>
    person.label.toLowerCase().includes(searchTerm.toLowerCase()) &&
    !query.includePeople.includes(person.id) &&
    !query.excludePeople.includes(person.id)
  );

  const buildQueryDescription = () => {
    if (query.includePeople.length === 0) return 'No search criteria';

    let description = 'Photos with ';

    if (query.includePeople.length === 1) {
      description += getPersonName(query.includePeople[0]);
    } else if (query.operator === 'AND') {
      description += query.includePeople.map(getPersonName).join(' AND ');
    } else {
      description += query.includePeople.map(getPersonName).join(' OR ');
    }

    if (query.excludePeople.length > 0) {
      description += ' (excluding ' + query.excludePeople.map(getPersonName).join(', ') + ')';
    }

    return description;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div
        className={`${glass.surface} border border-white/20 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Search className="text-primary" size={24} />
            <div>
              <h2 className="text-xl font-semibold text-foreground">
                Advanced People Search
              </h2>
              <p className="text-sm text-muted-foreground">
                Find photos with specific combinations of people
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-glass btn-glass--muted w-10 h-10 p-0 justify-center"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Query Builder */}
          <div className="space-y-6 mb-6">
            {/* Include People */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                Include People
              </label>

              {query.includePeople.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs text-muted-foreground">Operator:</span>
                    <select
                      value={query.operator}
                      onChange={(e) => setQuery({...query, operator: e.target.value as 'AND' | 'OR'})}
                      className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-foreground"
                    >
                      <option value="AND">ALL people (AND)</option>
                      <option value="OR">ANY people (OR)</option>
                    </select>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {query.includePeople.map((personId) => (
                      <div
                        key={personId}
                        className="flex items-center gap-2 bg-green-500/20 border border-green-500/30 text-green-400 px-3 py-1 rounded-full text-sm"
                      >
                        <User size={12} />
                        <span>{getPersonName(personId)}</span>
                        <button
                          onClick={() => removePersonFromInclude(personId)}
                          className="hover:text-green-300"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Exclude People */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                Exclude People (Optional)
              </label>

              {query.excludePeople.length > 0 && (
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2">
                    {query.excludePeople.map((personId) => (
                      <div
                        key={personId}
                        className="flex items-center gap-2 bg-red-500/20 border border-red-500/30 text-red-400 px-3 py-1 rounded-full text-sm"
                      >
                        <X size={12} />
                        <span>{getPersonName(personId)}</span>
                        <button
                          onClick={() => removePersonFromExclude(personId)}
                          className="hover:text-red-300"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* People Selector */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-3">
                Available People
              </label>

              {/* Search */}
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={16} />
                <input
                  type="text"
                  placeholder="Search people..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/50"
                />
              </div>

              {/* People List */}
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw size={20} className="animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="max-h-40 overflow-y-auto space-y-2">
                  {filteredPeople.map((person) => (
                    <div
                      key={person.id}
                      className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded-lg hover:border-white/20 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <User size={16} className="text-muted-foreground" />
                        <div>
                          <div className="text-sm font-medium text-foreground">
                            {person.label}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {person.image_count} photos
                          </div>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => addPersonToInclude(person.id)}
                          className="btn-glass btn-glass--muted text-xs px-2 py-1 hover:text-green-400"
                          title="Include this person"
                        >
                          <Plus size={12} />
                        </button>
                        <button
                          onClick={() => addPersonToExclude(person.id)}
                          className="btn-glass btn-glass--muted text-xs px-2 py-1 hover:text-red-400"
                          title="Exclude this person"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    </div>
                  ))}

                  {filteredPeople.length === 0 && !loading && (
                    <div className="text-center py-8 text-muted-foreground">
                      {searchTerm ? 'No people found matching your search' : 'All people are already selected'}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Query Preview */}
            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <div className="text-sm font-medium text-blue-400 mb-1">Search Query:</div>
              <div className="text-sm text-foreground">{buildQueryDescription()}</div>
            </div>
          </div>

          {/* Search Results */}
          {results.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Camera size={16} />
                <span>Found {results.length} photo{results.length === 1 ? '' : 's'}</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {results.slice(0, 20).map((result, index) => (
                  <div
                    key={index}
                    className="bg-white/5 border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors"
                  >
                    <div className="aspect-square bg-black/20">
                      <img
                        src={api.getImageUrl(result.photo_path, 300)}
                        alt="Search result"
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>
                    <div className="p-2">
                      <div className="text-xs text-muted-foreground truncate" title={result.photo_path}>
                        {result.photo_path.split('/').pop()}
                      </div>
                      {result.people_in_photo && (
                        <div className="text-xs text-muted-foreground mt-1">
                          People: {result.people_in_photo.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {results.length > 20 && (
                <div className="text-center text-sm text-muted-foreground">
                  Showing first 20 of {results.length} results
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-white/10">
          <button
            onClick={clearQuery}
            className="btn-glass btn-glass--muted px-4 py-2"
            disabled={searching}
          >
            Clear
          </button>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="btn-glass btn-glass--muted px-4 py-2"
              disabled={searching}
            >
              Close
            </button>
            <button
              onClick={executeSearch}
              className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
              disabled={searching || query.includePeople.length === 0}
            >
              {searching && <RefreshCw size={14} className="animate-spin" />}
              {searching ? 'Searching...' : 'Search Photos'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BooleanPeopleSearch;
