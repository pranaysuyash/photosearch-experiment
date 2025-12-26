/**
 * Smart Collections Component
 *
 * Provides an interface for creating and managing smart collections
 * with automatic photo inclusion based on rules.
 */
import React, { useState, useEffect } from 'react';
import {
  FolderPlus,
  Eye,
  Trash2,
  Clock,
  Users,
  MapPin,
  Calendar,
  Sparkles,
  X,
  Plus,
  Filter,
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface SmartCollection {
  id: string;
  name: string;
  description: string;
  rule_definition: RuleDefinition;
  auto_update: boolean;
  photo_count: number;
  last_updated: string;
  created_at: string;
  is_favorite: boolean;
  privacy_level: string;
}

interface RuleDefinition {
  type: 'date' | 'location' | 'people' | 'event' | 'camera' | 'tag' | 'custom';
  params: Record<string, string | number | boolean>;
}

type RuleType = RuleDefinition['type'];
type RuleParams = RuleDefinition['params'];

export function SmartCollections() {
  const [collections, setCollections] = useState<SmartCollection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCollection, setNewCollection] = useState<{
    name: string;
    description: string;
    ruleType: RuleType;
    ruleParams: RuleParams;
  }>({
    name: '',
    description: '',
    ruleType: 'date',
    ruleParams: {},
  });
  const [selectedCollection, setSelectedCollection] = useState<SmartCollection | null>(null);

  // Load smart collections
  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/collections/smart');
      setCollections(response.collections || []);
    } catch (err) {
      console.error('Failed to load collections:', err);
      setError('Failed to load smart collections');
    } finally {
      setLoading(false);
    }
  };

  const createCollection = async () => {
    if (!newCollection.name.trim()) return;

    try {
      const ruleDefinition: RuleDefinition = {
        type: newCollection.ruleType,
        params: newCollection.ruleParams,
      };

      await api.post('/collections/smart', {
        name: newCollection.name,
        description: newCollection.description,
        rule_definition: ruleDefinition,
        auto_update: true,
        privacy_level: 'private'
      });

      setShowCreateModal(false);
      setNewCollection({
        name: '',
        description: '',
        ruleType: 'date',
        ruleParams: {}
      });

      // Reload collections
      loadCollections();
    } catch (err) {
      console.error('Failed to create collection:', err);
      setError('Failed to create collection');
    }
  };

  const deleteCollection = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this smart collection?')) return;

    try {
      await api.delete(`/collections/smart/${id}`);
      loadCollections();
    } catch (err) {
      console.error('Failed to delete collection:', err);
      setError('Failed to delete collection');
    }
  };

  const getRuleDisplay = (rule: RuleDefinition) => {
    switch (rule.type) {
      case 'date':
        return `Photos from ${rule.params.date_from || 'the beginning'} to ${rule.params.date_to || 'now'}`;
      case 'location':
        return `Photos near ${rule.params.location || 'anywhere'}`;
      case 'people':
        return `Photos with ${rule.params.person || 'anyone'}`;
      case 'event':
        return `Photos from ${rule.params.event_type || 'any event'}`;
      case 'camera':
        return `Photos taken with ${rule.params.camera_make || 'any camera'}`;
      case 'tag':
        return `Photos tagged with ${rule.params.tag || 'any tag'}`;
      default:
        return `Custom rule: ${rule.type}`;
    }
  };

  const getRuleIcon = (type: RuleType) => {
    const icons: Record<
      RuleType,
      React.ComponentType<{ size?: number }> | string
    > = {
      date: Calendar,
      location: MapPin,
      people: Users,
      event: Sparkles,
      camera: '📷',
      tag: '🏷️',
      custom: Filter,
    };

    const Icon = icons[type];
    return typeof Icon === 'string' ? (
      <span>{Icon}</span>
    ) : (
      <Icon size={14} />
    );
  };

  if (loading) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">Smart Collections</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
        >
          <Plus size={16} />
          Create Smart Collection
        </button>
      </div>

      {/* Collections List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {collections.map(collection => (
          <div
            key={collection.id}
            className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-4 hover:border-white/20 transition-colors`}
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-medium text-foreground flex items-center gap-2">
                <FolderPlus size={16} className="text-blue-400" />
                {collection.name}
              </h3>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setSelectedCollection(collection)}
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
                  title="View collection"
                >
                  <Eye size={14} />
                </button>
                <button
                  onClick={() => deleteCollection(collection.id)}
                  className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
                  title="Delete collection"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>

            <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
              {collection.description}
            </p>

            <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
              <div className="flex items-center gap-1">
                {getRuleIcon(collection.rule_definition.type)}
                <span>{getRuleDisplay(collection.rule_definition)}</span>
              </div>
              <div className="flex items-center gap-1">
                <FolderPlus size={10} />
                <span>{collection.photo_count}</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock size={10} />
                <span>{new Date(collection.last_updated).toLocaleDateString()}</span>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs ${
                collection.auto_update
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {collection.auto_update ? 'Auto' : 'Manual'}
              </span>
            </div>
          </div>
        ))}

        {collections.length === 0 && (
          <div className="col-span-full text-center py-12">
            <FolderPlus size={48} className="mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium text-foreground mb-2">No Smart Collections</h3>
            <p className="text-muted-foreground mb-4">
              Create smart collections that automatically organize your photos based on rules
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-glass btn-glass--primary px-4 py-2"
            >
              <Plus size={16} className="mr-2" />
              Create Your First Collection
            </button>
          </div>
        )}
      </div>

      {/* Create Collection Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowCreateModal(false)} />

          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-md`}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Create Smart Collection</h3>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Collection Name</label>
                  <input
                    type="text"
                    value={newCollection.name}
                    onChange={(e) => setNewCollection({...newCollection, name: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="e.g., Summer Vacation 2023"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={newCollection.description}
                    onChange={(e) => setNewCollection({...newCollection, description: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="Describe what photos should be included in this collection"
                    rows={3}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Rule Type</label>
                  <select
                    value={newCollection.ruleType}
                    onChange={(e) => setNewCollection({...newCollection, ruleType: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="date">Date Range</option>
                    <option value="location">Location</option>
                    <option value="people">People/Faces</option>
                    <option value="event">Event Type</option>
                    <option value="camera">Camera Model</option>
                    <option value="tag">Tags</option>
                    <option value="custom">Custom Rule</option>
                  </select>
                </div>

                {/* Rule-specific parameters would go here */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Rule Parameters</label>
                  <div className="text-xs text-muted-foreground p-2 bg-white/5 rounded-lg">
                    Rule parameters would be configurable based on the selected rule type
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="btn-glass btn-glass--muted px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  onClick={createCollection}
                  className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
                >
                  <Sparkles size={16} />
                  Create Collection
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View Collection Modal */}
      {selectedCollection && (
        <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setSelectedCollection(null)} />

          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden`}>
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
                    <FolderPlus size={20} className="text-blue-400" />
                    {selectedCollection.name}
                  </h3>
                  <p className="text-sm text-muted-foreground">{selectedCollection.description}</p>
                </div>
                <button
                  onClick={() => setSelectedCollection(null)}
                  className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-[calc(90vh-150px)]">
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className={`${glass.surfaceStrong} rounded-lg p-4`}>
                  <div className="text-2xl font-bold text-foreground">{selectedCollection.photo_count}</div>
                  <div className="text-xs text-muted-foreground">Photos</div>
                </div>

                <div className={`${glass.surfaceStrong} rounded-lg p-4`}>
                  <div className="text-sm text-foreground capitalize">{selectedCollection.privacy_level}</div>
                  <div className="text-xs text-muted-foreground">Privacy</div>
                </div>

                <div className={`${glass.surfaceStrong} rounded-lg p-4`}>
                  <div className="text-sm text-foreground">
                    {selectedCollection.auto_update ? 'Automatic' : 'Manual'}
                  </div>
                  <div className="text-xs text-muted-foreground">Update Mode</div>
                </div>

                <div className={`${glass.surfaceStrong} rounded-lg p-4`}>
                  <div className="text-sm text-foreground">
                    {new Date(selectedCollection.last_updated).toLocaleDateString()}
                  </div>
                  <div className="text-xs text-muted-foreground">Last Updated</div>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="font-medium text-foreground mb-2 flex items-center gap-2">
                  <Filter size={16} />
                  Inclusion Rule
                </h4>
                <div className={`${glass.surfaceStrong} rounded-lg p-4`}>
                  <div className="flex items-center gap-2 mb-2">
                    {getRuleIcon(selectedCollection.rule_definition.type)}
                    <span className="font-medium">{selectedCollection.rule_definition.type}</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {getRuleDisplay(selectedCollection.rule_definition)}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium text-foreground mb-2">Photos in Collection</h4>
                <div className="text-sm text-muted-foreground">
                  {selectedCollection.photo_count} photos would be displayed here.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="fixed bottom-4 right-4 bg-destructive/20 border border-destructive/30 text-destructive px-4 py-3 rounded-lg z-[2000]">
          {error}
          <button
            className="ml-2"
            onClick={() => setError(null)}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
