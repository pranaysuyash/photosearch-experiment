/**
 * Collaborative Spaces Component
 *
 * Provides UI for creating and managing collaborative photo spaces with sharing and permissions.
 */
import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  UserPlus, 
  UserMinus, 
  Image, 
  MessageSquare,
  Settings,
  Eye,
  EyeOff,
  Lock,
  Globe,
  Share2,
  X,
  Check,
  Edit3,
  Trash2
} from 'lucide-react';
import { api } from '../../api';
import { glass } from '../../design/glass';

interface CollaborativeSpace {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  privacy_level: 'public' | 'shared' | 'private';
  max_members: number;
  current_members: number;
  role?: string; // User's role in this space if they're a member
}

interface SpaceMember {
  space_id: string;
  user_id: string;
  role: string;
  joined_at: string;
  permissions: Record<string, boolean>;
  is_active: boolean;
  user_username?: string;
}

interface SpacePhoto {
  space_id: string;
  photo_path: string;
  added_by: string;
  added_at: string;
  caption: string;
  added_by_username?: string;
}

interface SpaceComment {
  id: string;
  space_id: string;
  photo_path: string;
  user_id: string;
  comment: string;
  created_at: string;
  author_username?: string;
}

export function CollaborativeSpaces() {
  const [spaces, setSpaces] = useState<CollaborativeSpace[]>([]);
  const [selectedSpace, setSelectedSpace] = useState<CollaborativeSpace | null>(null);
  const [spaceMembers, setSpaceMembers] = useState<SpaceMember[]>([]);
  const [spacePhotos, setSpacePhotos] = useState<SpacePhoto[]>([]);
  const [spaceComments, setSpaceComments] = useState<SpaceComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentUserSpaces, setCurrentUserSpaces] = useState<CollaborativeSpace[]>([]);
  
  // Forms
  const [createSpaceForm, setCreateSpaceForm] = useState({
    name: '',
    description: '',
    privacy_level: 'private',
    max_members: 10
  });
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [inviteForm, setInviteForm] = useState({
    user_id: '',
    role: 'contributor'
  });
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [addPhotoForm, setAddPhotoForm] = useState({
    photo_path: '',
    caption: ''
  });
  const [showAddPhotoForm, setShowAddPhotoForm] = useState(false);
  const [newComment, setNewComment] = useState('');

  // Load user's spaces
  useEffect(() => {
    loadCurrentUserSpaces();
  }, []);

  const loadCurrentUserSpaces = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // In a real app, the user_id would come from authentication
      // For this example, we'll use a placeholder user ID
      const response = await api.get('/collaborative/spaces/user/user-placeholder-id');
      setCurrentUserSpaces(response.spaces || []);
    } catch (err) {
      console.error('Failed to load user spaces:', err);
      setError('Failed to load collaborative spaces');
    } finally {
      setLoading(false);
    }
  };

  const loadSpaceDetails = async (spaceId: string) => {
    try {
      // Load space members
      const membersResponse = await api.get(`/collaborative/spaces/${spaceId}/members`);
      setSpaceMembers(membersResponse.members || []);
      
      // Load space photos
      const photosResponse = await api.get(`/collaborative/spaces/${spaceId}/photos`);
      setSpacePhotos(photosResponse.photos || []);
      
      // Load space stats
      const statsResponse = await api.get(`/collaborative/spaces/${spaceId}/stats`);
      
      // Find and update the space in the main list
      setCurrentUserSpaces(prev => 
        prev.map(space => 
          space.id === spaceId 
            ? { ...space, ...statsResponse.stats } 
            : space
        )
      );
    } catch (err) {
      console.error('Failed to load space details:', err);
      setError('Failed to load space details');
    }
  };

  const handleCreateSpace = async () => {
    if (!createSpaceForm.name.trim()) return;
    
    try {
      const response = await api.post('/collaborative/spaces', {
        name: createSpaceForm.name,
        description: createSpaceForm.description,
        privacy_level: createSpaceForm.privacy_level,
        max_members: createSpaceForm.max_members
      });
      
      // Refresh the list
      loadCurrentUserSpaces();
      setShowCreateForm(false);
      setCreateSpaceForm({
        name: '',
        description: '',
        privacy_level: 'private',
        max_members: 10
      });
    } catch (err) {
      console.error('Failed to create space:', err);
      setError('Failed to create collaborative space');
    }
  };

  const handleInviteMember = async () => {
    if (!selectedSpace || !inviteForm.user_id) return;
    
    try {
      await api.post(`/collaborative/spaces/${selectedSpace.id}/members`, {
        user_id: inviteForm.user_id,
        role: inviteForm.role
      });
      
      // Refresh the space details
      loadSpaceDetails(selectedSpace.id);
      setShowInviteForm(false);
      setInviteForm({ user_id: '', role: 'contributor' });
    } catch (err) {
      console.error('Failed to invite member:', err);
      setError('Failed to invite member');
    }
  };

  const handleAddPhoto = async () => {
    if (!selectedSpace || !addPhotoForm.photo_path) return;
    
    try {
      await api.post(`/collaborative/spaces/${selectedSpace.id}/photos`, {
        photo_path: addPhotoForm.photo_path,
        caption: addPhotoForm.caption
      });
      
      // Refresh the space photos
      loadSpaceDetails(selectedSpace.id);
      setShowAddPhotoForm(false);
      setAddPhotoForm({ photo_path: '', caption: '' });
    } catch (err) {
      console.error('Failed to add photo:', err);
      setError('Failed to add photo to space');
    }
  };

  const handleAddComment = async (photoPath: string) => {
    if (!selectedSpace || !newComment.trim()) return;
    
    try {
      await api.post(`/collaborative/spaces/${selectedSpace.id}/photos/${photoPath}/comments`, {
        comment: newComment
      });
      
      // Refresh comments for this photo
      const commentsResponse = await api.get(`/collaborative/spaces/${selectedSpace.id}/photos/${photoPath}/comments`);
      // In a real implementation, we would update only the specific photo's comments
      // For now, refresh all space details
      loadSpaceDetails(selectedSpace.id);
      setNewComment('');
    } catch (err) {
      console.error('Failed to add comment:', err);
      setError('Failed to add comment');
    }
  };

  const removeMember = async (userId: string) => {
    if (!selectedSpace || !window.confirm('Are you sure you want to remove this member?')) return;
    
    try {
      await api.delete(`/collaborative/spaces/${selectedSpace.id}/members/${userId}`);
      loadSpaceDetails(selectedSpace.id);
    } catch (err) {
      console.error('Failed to remove member:', err);
      setError('Failed to remove member');
    }
  };

  const removePhoto = async (photoPath: string) => {
    if (!selectedSpace || !window.confirm('Are you sure you want to remove this photo?')) return;
    
    try {
      await api.delete(`/collaborative/spaces/${selectedSpace.id}/photos/${encodeURIComponent(photoPath)}`);
      loadSpaceDetails(selectedSpace.id);
    } catch (err) {
      console.error('Failed to remove photo:', err);
      setError('Failed to remove photo');
    }
  };

  const getPrivacyIcon = (level: string) => {
    switch (level) {
      case 'public': return <Globe size={16} className="text-green-400" />;
      case 'shared': return <Share2 size={16} className="text-blue-400" />;
      case 'private': return <Lock size={16} className="text-gray-400" />;
      default: return <Lock size={16} className="text-gray-400" />;
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="text-foreground" size={28} />
          <div>
            <h1 className="text-2xl font-bold text-foreground">Collaborative Spaces</h1>
            <p className="text-sm text-muted-foreground">
              Share and collaborate on photo collections with others
            </p>
          </div>
        </div>
        
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn-glass btn-glass--primary px-4 py-2 flex items-center gap-2"
        >
          <Plus size={16} />
          Create Space
        </button>
      </div>

      {/* Create Space Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowCreateForm(false)} />
          
          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-md`}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Create Collaborative Space</h3>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Space Name</label>
                  <input
                    type="text"
                    value={createSpaceForm.name}
                    onChange={(e) => setCreateSpaceForm({...createSpaceForm, name: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="e.g., Family Vacation Photos"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <textarea
                    value={createSpaceForm.description}
                    onChange={(e) => setCreateSpaceForm({...createSpaceForm, description: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="Brief description of the space"
                    rows={3}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Privacy</label>
                    <select
                      value={createSpaceForm.privacy_level}
                      onChange={(e) => setCreateSpaceForm({...createSpaceForm, privacy_level: e.target.value})}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="private">Private</option>
                      <option value="shared">Shared</option>
                      <option value="public">Public</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Max Members</label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={createSpaceForm.max_members}
                      onChange={(e) => setCreateSpaceForm({...createSpaceForm, max_members: parseInt(e.target.value) || 10})}
                      className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="btn-glass btn-glass--muted px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateSpace}
                  className="btn-glass btn-glass--primary px-4 py-2"
                >
                  Create Space
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Space Details Modal */}
      {selectedSpace && (
        <div className="fixed inset-0 z-[1400] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setSelectedSpace(null)} />
          
          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden`}>
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    {getPrivacyIcon(selectedSpace.privacy_level)}
                    <h2 className="text-xl font-bold text-foreground">{selectedSpace.name}</h2>
                  </div>
                  <p className="text-sm text-muted-foreground">{selectedSpace.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedSpace(null)}
                    className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
            </div>
            
            <div className="flex overflow-hidden h-[calc(90vh-150px)]">
              {/* Sidebar */}
              <div className={`${glass.surfaceStrong} w-64 border-r border-white/10 overflow-y-auto`}>
                <div className="p-4">
                  <div className="mb-4">
                    <h3 className="font-medium text-foreground mb-2">Members</h3>
                    <div className="space-y-2">
                      {spaceMembers.map(member => (
                        <div 
                          key={member.user_id} 
                          className="flex items-center justify-between p-2 rounded-lg bg-white/5"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                              <UserPlus size={14} className="text-primary" />
                            </div>
                            <div>
                              <div className="text-sm font-medium text-foreground">
                                {member.user_username || `User ${member.user_id.substring(0, 8)}`}
                              </div>
                              <div className="text-xs text-muted-foreground capitalize">
                                {member.role}
                              </div>
                            </div>
                          </div>
                          {member.role !== 'owner' && (
                            <button
                              onClick={() => removeMember(member.user_id)}
                              className="btn-glass btn-glass--muted w-7 h-7 p-0 flex items-center justify-center"
                              title="Remove member"
                            >
                              <UserMinus size={12} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => setShowInviteForm(true)}
                      className="btn-glass btn-glass--primary text-sm py-2 flex items-center gap-2"
                    >
                      <UserPlus size={14} />
                      Invite Member
                    </button>
                    
                    <button
                      onClick={() => setShowAddPhotoForm(true)}
                      className="btn-glass btn-glass--primary text-sm py-2 flex items-center gap-2"
                    >
                      <Image size={14} />
                      Add Photo
                    </button>
                    
                    <button className="btn-glass btn-glass--muted text-sm py-2 flex items-center gap-2">
                      <Settings size={14} />
                      Space Settings
                    </button>
                  </div>
                </div>
              </div>
              
              {/* Main Content */}
              <div className="flex-1 overflow-y-auto p-4">
                {/* Photos Grid */}
                <h3 className="font-medium text-foreground mb-4 flex items-center gap-2">
                  <Image size={16} />
                  Shared Photos
                </h3>
                
                {spacePhotos.length === 0 ? (
                  <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-8 text-center`}>
                    <Image size={48} className="mx-auto text-muted-foreground mb-4 opacity-50" />
                    <h4 className="font-medium text-foreground mb-2">No Photos Yet</h4>
                    <p className="text-sm text-muted-foreground">
                      Add photos to this collaborative space to start sharing.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                    {spacePhotos.map(photo => (
                      <div key={photo.photo_path} className={`${glass.surfaceStrong} rounded-xl border border-white/10 overflow-hidden`}>
                        <div className="aspect-square relative">
                          <img
                            src={api.getImageUrl(photo.photo_path, 300)}
                            alt={photo.caption || "Shared photo"}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute top-2 right-2 flex gap-1">
                            <button
                              onClick={() => removePhoto(photo.photo_path)}
                              className="btn-glass btn-glass--muted p-1.5"
                              title="Remove photo"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        </div>
                        <div className="p-3">
                          {photo.caption && (
                            <p className="text-sm text-foreground line-clamp-2 mb-2">{photo.caption}</p>
                          )}
                          
                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Added by {photo.added_by_username || 'Someone'}</span>
                            <span>{new Date(photo.added_at).toLocaleDateString()}</span>
                          </div>
                          
                          {/* Comments */}
                          <div className="mt-3">
                            <div className="flex items-center gap-2 mb-2">
                              <MessageSquare size={14} className="text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">Comments</span>
                            </div>
                            
                            <div className="space-y-2">
                              {spaceComments
                                .filter(comment => comment.photo_path === photo.photo_path)
                                .slice(0, 2)
                                .map(comment => (
                                  <div key={comment.id} className="text-xs text-muted-foreground">
                                    <span className="font-medium text-foreground">
                                      {comment.author_username || 'User'}:
                                    </span> {comment.comment}
                                  </div>
                                ))}
                              
                              <div className="flex items-center gap-2 pt-1">
                                <input
                                  type="text"
                                  value={newComment}
                                  onChange={(e) => setNewComment(e.target.value)}
                                  placeholder="Add a comment..."
                                  className="flex-1 bg-white/5 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      handleAddComment(photo.photo_path);
                                    }
                                  }}
                                />
                                <button
                                  onClick={() => handleAddComment(photo.photo_path)}
                                  className="btn-glass btn-glass--muted p-1"
                                  title="Post comment"
                                >
                                  <MessageSquare size={12} />
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
          </div>
        </div>
      )}

      {/* Invite Member Modal */}
      {showInviteForm && selectedSpace && (
        <div className="fixed inset-0 z-[1500] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowInviteForm(false)} />
          
          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-md`}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Invite to "{selectedSpace.name}"</h3>
                <button
                  onClick={() => setShowInviteForm(false)}
                  className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">User ID or Email</label>
                  <input
                    type="text"
                    value={inviteForm.user_id}
                    onChange={(e) => setInviteForm({...inviteForm, user_id: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="Enter user ID or email"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Role</label>
                  <select
                    value={inviteForm.role}
                    onChange={(e) => setInviteForm({...inviteForm, role: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="viewer">Viewer (can view)</option>
                    <option value="contributor">Contributor (can add photos)</option>
                    <option value="admin">Admin (can manage members)</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowInviteForm(false)}
                  className="btn-glass btn-glass--muted px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  onClick={handleInviteMember}
                  className="btn-glass btn-glass--primary px-4 py-2"
                >
                  Send Invitation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Photo Modal */}
      {showAddPhotoForm && selectedSpace && (
        <div className="fixed inset-0 z-[1500] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowAddPhotoForm(false)} />
          
          <div className={`${glass.surface} ${glass.surfaceStrong} rounded-2xl border border-white/10 shadow-2xl w-full max-w-md`}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Add Photo to "{selectedSpace.name}"</h3>
                <button
                  onClick={() => setShowAddPhotoForm(false)}
                  className="btn-glass btn-glass--muted w-9 h-9 p-0 flex items-center justify-center"
                >
                  <X size={18} />
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Photo Path</label>
                  <input
                    type="text"
                    value={addPhotoForm.photo_path}
                    onChange={(e) => setAddPhotoForm({...addPhotoForm, photo_path: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="/path/to/photo.jpg"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Caption (Optional)</label>
                  <textarea
                    value={addPhotoForm.caption}
                    onChange={(e) => setAddPhotoForm({...addPhotoForm, caption: e.target.value})}
                    className="w-full px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                    placeholder="Add a description for this photo..."
                    rows={3}
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <button
                  onClick={() => setShowAddPhotoForm(false)}
                  className="btn-glass btn-glass--muted px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddPhoto}
                  className="btn-glass btn-glass--primary px-4 py-2"
                >
                  Add Photo
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Spaces List */}
      {currentUserSpaces.length === 0 ? (
        <div className={`${glass.surfaceStrong} rounded-xl border border-white/10 p-8 text-center`}>
          <Users size={48} className="mx-auto text-muted-foreground mb-4 opacity-50" />
          <h3 className="font-medium text-foreground mb-2">No Collaborative Spaces</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create a collaborative space to start sharing photos with others.
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn-glass btn-glass--primary px-4 py-2"
          >
            Create Your First Space
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {currentUserSpaces.map(space => (
            <div 
              key={space.id} 
              className={`${glass.surfaceStrong} rounded-xl border border-white/10 overflow-hidden hover:border-white/20 transition-colors cursor-pointer`}
              onClick={() => {
                setSelectedSpace(space);
                loadSpaceDetails(space.id);
              }}
            >
              <div className="p-4 border-b border-white/10">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {getPrivacyIcon(space.privacy_level)}
                    <h3 className="font-semibold text-foreground truncate">{space.name}</h3>
                  </div>
                  <div className="text-xs px-2 py-1 rounded-full bg-primary/10 text-primary">
                    {space.current_members}/{space.max_members} members
                  </div>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{space.description}</p>
              </div>
              
              <div className="p-4">
                <div className="flex justify-between text-xs text-muted-foreground mb-3">
                  <span>Created: {new Date(space.created_at).toLocaleDateString()}</span>
                  <span>Updated: {new Date(space.updated_at).toLocaleDateString()}</span>
                </div>
                
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Users size={14} />
                    <span>{space.current_members} members</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedSpace(space);
                      loadSpaceDetails(space.id);
                    }}
                    className="btn-glass btn-glass--primary px-3 py-1.5 text-xs"
                  >
                    View Space
                  </button>
                </div>
              </div>
            </div>
          ))}
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