/**
 * Story Creation & Timeline Component
 *
 * Provides UI for creating photo stories and managing photo timelines.
 */
import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Calendar, 
  MapPin, 
  Image, 
  Plus, 
  X, 
  Edit3, 
  Share2, 
  Eye,
  EyeOff,
  Lock,
  Globe,
  UserPlus,
  Tag,
  TrendingUp,
  Settings
} from 'lucide-react';
import { api } from '../api';
import { glass } from '../design/glass';

interface TimelineEntry {
  id: string;
  story_id: string;
  photo_path: string;
  date: string;
  location: string | null;
  caption: string | null;
  narrative_order: number;
  created_at: string;
  updated_at: string;
}

interface StoryNarrative {
  id: string;
  title: string;
  description: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  is_published: boolean;
  metadata: Record<string, any>;
  timeline_entries: TimelineEntry[];
}

export function StoryCreator({ 
  isOpen, 
  onClose, 
  photoPaths,
  onStoryCreated 
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  photoPaths: string[];
  onStoryCreated?: (storyId: string) => void;
}) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [privacyLevel, setPrivacyLevel] = useState<'private' | 'shared' | 'public'>('private');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storyId, setStoryId] = useState<string | null>(null);
  const [currentPrivacy, setCurrentPrivacy] = useState<'private' | 'shared' | 'public'>('private');
  const [newCaption, setNewCaption] = useState('');
  const [editingCaption, setEditingCaption] = useState<{entryId: string, caption: string} | null>(null);

  if (!isOpen) return null;

  const createStory = async () => {
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      // Create the story
      const newStory = await api.createStory({
        title,
        description,
        privacy_level: privacyLevel
      });

      const storyId = newStory.story_id;

      // Add all selected photos to the story's timeline
      for (const photoPath of photoPaths) {
        await api.addPhotoToStory(storyId, {
          photo_path: photoPath,
          date: new Date().toISOString().split('T')[0], // Use today's date as default
          caption: '' // Empty caption initially
        });
      }

      setStoryId(storyId);
      
      if (onStoryCreated) {
        onStoryCreated(storyId);
      }
      
      // Close the dialog after a short delay to show success
      setTimeout(() => {
        resetForm();
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Failed to create story:', err);
      setError('Failed to create story');
    } finally {
      setCreating(false);
    }
  };

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setPrivacyLevel('private');
    setCreating(false);
    setError(null);
    setStoryId(null);
  };

  const handleCancel = () => {
    resetForm();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[1500] flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm" 
        onClick={onCancel}
      />
      
      <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden`}>
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <BookOpen size={24} className="text-foreground" />
            <div>
              <h2 className="text-xl font-semibold text-foreground">Create Photo Story</h2>
              <p className="text-sm text-muted-foreground">
                {photoPaths.length} {photoPaths.length === 1 ? 'photo' : 'photos'} selected
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="btn-glass btn-glass--muted w-10 h-10 p-0 flex items-center justify-center"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {success ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check size={32} className="text-green-400" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">Story Created!</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Your photo story "{title}" has been created successfully.
              </p>
              <button
                onClick={() => {
                  resetForm();
                  onClose();
                }}
                className="btn-glass btn-glass--primary px-4 py-2"
              >
                Done
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Story Title
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Summer Vacation 2023"
                  className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Tell the story of these photos..."
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Privacy Level
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { value: 'private', label: 'Private', icon: Lock, desc: 'Only visible to you' },
                    { value: 'shared', label: 'Shared', icon: UserPlus, desc: 'Shared with specific users' },
                    { value: 'public', label: 'Public', icon: Globe, desc: 'Visible to everyone' }
                  ] as const).map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setPrivacyLevel(option.value)}
                      className={`p-3 rounded-lg border text-left transition-colors ${
                        privacyLevel === option.value
                          ? 'border-primary bg-primary/10 text-foreground'
                          : 'border-white/10 hover:border-white/20 text-muted-foreground'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <option.icon size={16} />
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <div className="text-xs">{option.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Preview of photos to be included */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-foreground flex items-center gap-2">
                    <Image size={16} />
                    Included Photos
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {photoPaths.length} photos
                  </span>
                </div>
                
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {photoPaths.slice(0, 12).map((path, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={api.getImageUrl(path, 150)}
                        alt={`Preview ${index + 1}`}
                        className="w-full h-20 object-cover rounded-lg border border-white/10"
                      />
                      {index >= 11 && photoPaths.length > 12 && (
                        <div className="absolute inset-0 bg-black/50 rounded-lg flex items-center justify-center">
                          <span className="text-white font-medium">+{photoPaths.length - 12}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              
              {error && (
                <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                  {error}
                </div>
              )}
            </div>
          )}
        </div>
        
        <div className="flex justify-end gap-3 p-6 border-t border-white/10">
          <button
            onClick={handleCancel}
            disabled={creating}
            className="btn-glass btn-glass--muted px-4 py-2"
          >
            Cancel
          </button>
          <button
            onClick={createStory}
            disabled={creating || !title.trim()}
            className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
          >
            {creating ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Plus size={16} />
            )}
            {creating ? 'Creating...' : 'Create Story'}
          </button>
        </div>
      </div>
    </div>
  );
}

export function StoryTimeline({ storyId }: { storyId: string }) {
  const [story, setStory] = useState<StoryNarrative | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingCaption, setEditingCaption] = useState<string | null>(null);
  const [newCaption, setNewCaption] = useState('');
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);

  useEffect(() => {
    if (storyId) {
      loadStoryDetails();
    }
  }, [storyId]);

  const loadStoryDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get story details
      const storyData = await api.getStory(storyId);
      setStory(storyData);
      
      // Get story timeline
      const timelineData = await api.getStoryTimeline(storyId);
      setTimeline(timelineData.timeline || []);
    } catch (err) {
      console.error('Failed to load story details:', err);
      setError('Failed to load story details');
    } finally {
      setLoading(false);
    }
  };

  const updateCaption = async (entryId: string, caption: string) => {
    try {
      await api.updateTimelineEntry(entryId, { caption });
      
      // Update local state
      setTimeline(timeline.map(entry => 
        entry.id === entryId ? { ...entry, caption } : entry
      ));
      
      setEditingCaption(null);
      setEditingEntryId(null);
    } catch (err) {
      console.error('Failed to update caption:', err);
      setError('Failed to update caption');
    }
  };

  const removePhotoFromTimeline = async (entryId: string) => {
    if (!window.confirm('Are you sure you want to remove this photo from the story?')) return;
    
    try {
      await api.removePhotoFromTimeline(entryId);
      
      // Update local state
      setTimeline(timeline.filter(entry => entry.id !== entryId));
    } catch (err) {
      console.error('Failed to remove photo:', err);
      setError('Failed to remove photo from story');
    }
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

  if (error) {
    return (
      <div className={`${glass.surface} rounded-xl border border-white/10 p-6`}>
        <div className="text-destructive">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Story Header */}
      {story && (
        <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-6`}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-foreground">{story.title}</h2>
              {story.description && (
                <p className="text-muted-foreground mt-2">{story.description}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${
                story.is_published 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {story.is_published ? <Eye size={12} /> : <EyeOff size={12} />}
                <span>{story.is_published ? 'Published' : 'Draft'}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar size={14} />
              <span>Created {new Date(story.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-center gap-1">
              <Image size={14} />
              <span>{timeline.length} photos</span>
            </div>
            <div className="flex items-center gap-1">
              <Tag size={14} />
              <span>0 tags</span>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Calendar size={18} />
            Story Timeline
          </h3>
          <div className="text-sm text-muted-foreground">
            {timeline.length} {timeline.length === 1 ? 'photo' : 'photos'}
          </div>
        </div>
        
        {timeline.length === 0 ? (
          <div className={`${glass.surface} rounded-xl border border-white/10 p-8 text-center`}>
            <Image size={48} className="mx-auto text-muted-foreground mb-4" />
            <h4 className="font-medium text-foreground mb-2">No Photos in Timeline</h4>
            <p className="text-sm text-muted-foreground">
              This story is empty. Add photos to start building the narrative.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {timeline.map((entry, index) => (
              <div 
                key={entry.id} 
                className={`${glass.surface} rounded-xl border border-white/10 overflow-hidden`}
              >
                <div className="flex">
                  <div className="w-32 flex-shrink-0">
                    <img
                      src={api.getImageUrl(entry.photo_path, 300)}
                      alt={`Timeline entry ${index + 1}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  
                  <div className="flex-1 p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-primary">
                            {index + 1}
                          </span>
                          {entry.date && (
                            <span className="text-xs text-muted-foreground">
                              {new Date(entry.date).toLocaleDateString()}
                            </span>
                          )}
                          {entry.location && (
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <MapPin size={12} />
                              {entry.location}
                            </div>
                          )}
                        </div>
                        
                        {editingCaption === entry.id ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={newCaption}
                              onChange={(e) => setNewCaption(e.target.value)}
                              placeholder="Add a caption..."
                              className="flex-1 px-2 py-1 rounded border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                              autoFocus
                              onBlur={() => {
                                setEditingCaption(null);
                                setEditingEntryId(null);
                              }}
                              onKeyPress={(e) => {
                                if (e.key === 'Enter') {
                                  updateCaption(entry.id, newCaption);
                                }
                              }}
                            />
                            <button
                              onClick={() => updateCaption(entry.id, newCaption)}
                              className="btn-glass btn-glass--primary px-2 py-1"
                            >
                              <Check size={14} />
                            </button>
                          </div>
                        ) : (
                          <div 
                            className="text-sm text-foreground min-h-6 cursor-text"
                            onClick={() => {
                              setEditingCaption(entry.id);
                              setNewCaption(entry.caption || '');
                              setEditingEntryId(entry.id);
                            }}
                          >
                            {entry.caption ? (
                              entry.caption
                            ) : (
                              <span className="text-muted-foreground italic">Click to add caption...</span>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-1 ml-4">
                        <button
                          onClick={() => {
                            setEditingCaption(entry.id);
                            setNewCaption(entry.caption || '');
                            setEditingEntryId(entry.id);
                          }}
                          className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
                          title="Edit caption"
                        >
                          <Edit3 size={14} />
                        </button>
                        
                        <button
                          onClick={() => removePhotoFromTimeline(entry.id)}
                          className="btn-glass btn-glass--muted w-8 h-8 p-0 flex items-center justify-center"
                          title="Remove from story"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}